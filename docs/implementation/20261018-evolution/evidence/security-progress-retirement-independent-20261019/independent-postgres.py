"""Independent PostgreSQL pool1 tests plus identical cleanup fault canaries."""
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from tests.integration_progress_retirement import progress_db,blank
from tests.test_progress_retirement_http import progress_http,retired_scope,query
from tests.test_security_retirement_peer import (
    invoke,
    test_close_raises_before_cleanup_after_confirmed_operation,
    test_admission_ack_loss_is_durable_and_does_not_consume_factor,
    test_unavailable_commit_rollback_and_precleanup_close_invalidates_owned_session,
)


def test_checked_out_ambient_session_is_not_retagged_when_pool_exhausted(retired_scope):
    from web.database.tenant_context import current_tenant,bind_verified_subject
    c=retired_scope;old_timeout=c['engine'].pool._timeout
    c['engine'].pool._timeout=.05
    outer=current_tenant.set(c['other'])
    try:
        with Session(c['engine']) as old:
            bind_verified_subject(old,c['other'])
            prior=tuple(old.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one())
            info=dict(old.info)
            with pytest.raises(HTTPException) as error:invoke(c,query(c))
            assert error.value.status_code==503
            assert old.info==info and current_tenant.get()==c['other']
            assert tuple(old.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one())==prior
    finally:
        c['engine'].pool._timeout=old_timeout;current_tenant.reset(outer)
    blank(c['engine'])


def test_older_separate_pool_session_retains_scope_while_new_primary_succeeds(retired_scope):
    from web.database.tenant_context import current_tenant,bind_verified_subject,configure_tenant_engine
    c=retired_scope
    secondary=configure_tenant_engine(create_engine(c['engine'].url,pool_size=1,max_overflow=0))
    outer=current_tenant.set(c['other'])
    try:
        with Session(secondary) as old:
            bind_verified_subject(old,c['other'])
            prior=tuple(old.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one())
            info=dict(old.info)
            result=invoke(c,query(c))
            assert result['items'][0]['link_id']==c['link']
            assert current_tenant.get()==c['other'] and old.info==info
            assert tuple(old.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one())==prior
    finally:
        current_tenant.reset(outer);secondary.dispose()
    blank(c['engine'])
