"""Adversarial actual32 source scope, live authority and contention; no load."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from threading import Event
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine,event,select,text
from sqlalchemy.orm import Session

from tests.integration_progress32_postgres import progress_db,progress_http,make_source,blank_pool
from tests.test_personal_progress_http import grant,shared_path
from web.database.tenant_context import configure_tenant_engine,tenant_scope,current_tenant


def test_live_entitlement_and_source_identity_are_revalidated_after_each_read(progress_http):
    from web.database.models import Subscription,Cliente,Usuario
    c=progress_http;link,consent=make_source(c);client=c['client_http'];path=shared_path(c,link,consent)
    assert client.get(path,headers=c['headers']['gym']).status_code==200
    with Session(c['admin']) as db:
        sub=db.scalar(select(Subscription).where(Subscription.gym_id==c['gym']));sub.plan='standard';db.commit()
    assert client.get(path,headers=c['headers']['gym']).status_code==402
    with Session(c['admin']) as db:
        sub=db.scalar(select(Subscription).where(Subscription.gym_id==c['gym']));sub.plan='clinica';sub.status='past_due';db.commit()
    assert client.get(path,headers=c['headers']['gym']).status_code==402
    with Session(c['admin']) as db:
        sub=db.scalar(select(Subscription).where(Subscription.gym_id==c['gym']));sub.status='active';sub.current_period_end=datetime.now(timezone.utc)-timedelta(days=1);db.commit()
    assert client.get(path,headers=c['headers']['gym']).status_code==402
    with Session(c['admin']) as db:
        sub=db.scalar(select(Subscription).where(Subscription.gym_id==c['gym']));sub.current_period_end=datetime.now(timezone.utc)+timedelta(days=1);db.commit()
        db.scalar(select(Cliente).where(Cliente.id_cliente==c['profile'])).activo=False;db.commit()
    assert client.get(path,headers=c['headers']['gym']).status_code==409
    with Session(c['admin']) as db:
        db.scalar(select(Cliente).where(Cliente.id_cliente==c['profile'])).activo=True;db.commit()
        db.get(Usuario,c['person']).activo=False;db.commit()
    assert client.get(path,headers=c['headers']['gym']).status_code==404
    with Session(c['admin']) as db:db.get(Usuario,c['person']).activo=True;db.commit()
    # Account toggling does not erase consent; an unchanged exact link may qualify again.
    assert client.get(path,headers=c['headers']['gym']).status_code==200
    blank_pool(c['engine'])


def test_scope_dates_categories_other_recipient_and_replacement_cas_are_not_cacheable(progress_http):
    c=progress_http;link,consent=make_source(c);client=c['client_http'];path=shared_path(c,link,consent)
    assert client.get(path,headers=c['headers']['other']).status_code in (403,404)
    assert client.get(path.replace('expected_version=1','expected_version=2'),headers=c['headers']['gym']).status_code==409
    assert client.get(path.replace('expected_link_version=2','expected_link_version=3'),headers=c['headers']['gym']).status_code==409
    before=c['today']-timedelta(days=1)
    assert client.get(path.replace('from='+c['today'].isoformat(),'from='+before.isoformat()),headers=c['headers']['gym']).status_code==409
    replacement,_=grant(c,link,expected_consent_id=consent['id'],expected_version=1,source_profile_id=None,
        categories={'weight':False,'body_fat':False,'lean_mass':False,'completion':True})
    assert replacement.status_code==200
    assert client.get(path,headers=c['headers']['gym']).status_code==409
    current=client.get(shared_path(c,link,replacement.json()['consent']),headers=c['headers']['gym'])
    assert current.status_code==200 and current.json()['measurements']=={'items':[],'next_after':None}
    assert current.json()['completion']['items'][0]['registered_snapshots']==1
    blank_pool(c['engine'])


def test_context_restores_existing_capabilities_on_success_and_invalidates_uncertain_scope(progress_http):
    from web.services.progress_readers import _source_connection
    c=progress_http
    with tenant_scope(c['gym']),Session(c['engine']) as db:
        db.info['tenant_id']=c['gym'];connection=db.connection()
        connection.execute(text("SELECT set_config('app.client_invitation_digest','prior-purpose',true),set_config('app.mfa_actor',:actor,true)"),{'actor':c['gym']})
        with _source_connection(db,c['gym'],c['person']) as source:
            assert source is connection
            assert source.scalar(text("SELECT current_setting('app.current_tenant',true)"))==c['person']
            assert current_tenant.get()==c['gym'] and db.info['tenant_id']==c['gym']
        assert tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.client_invitation_digest',true),current_setting('app.mfa_actor',true)")).one())==(c['gym'],'prior-purpose',c['gym'])
        db.rollback()
    with tenant_scope(c['gym']),Session(c['engine']) as db:
        db.info['tenant_id']=c['gym'];connection=db.connection()
        with pytest.raises(RuntimeError):
            with _source_connection(db,c['gym'],c['person']) as source:
                source.execute(text("SELECT set_config('app.mfa_actor','unconfirmed-other',true)"))
        # SAVEPOINT rollback restores the original mfa_actor too; no scalar result escaped.
        assert connection.scalar(text("SELECT current_setting('app.mfa_actor',true)"))==''
        db.rollback()
    for mismatched in ('',None):
        with Session(c['engine']) as db:
            db.info['tenant_id']=c['gym'];connection=db.connection()
            connection.execute(text("SELECT set_config('app.current_tenant',:value,true)"),{'value':mismatched})
            with pytest.raises(HTTPException) as failed:
                with _source_connection(db,c['gym'],c['person']):pytest.fail('Source scope entered with absent context')
            assert failed.value.status_code==503
            db.rollback()
    blank_pool(c['engine'])


def test_same_connection_needs_no_second_checkout_and_rejects_nested_or_changed_python_scope(progress_http):
    from web.services.progress_readers import _source_connection
    c=progress_http
    with tenant_scope(c['gym']),Session(c['engine']) as db:
        db.info['tenant_id']=c['gym'];db.connection()
        with db.begin_nested():
            with pytest.raises(HTTPException) as failed:
                with _source_connection(db,c['gym'],c['person']):pytest.fail('Nested transaction accepted')
            assert failed.value.status_code==503
        db.rollback()
    with tenant_scope(c['gym']),Session(c['engine']) as db:
        db.info['tenant_id']=c['gym'];db.connection()
        with pytest.raises(RuntimeError):
            with _source_connection(db,c['gym'],c['person']):
                token=current_tenant.set(c['other'])
        current_tenant.reset(token);db.rollback()
    blank_pool(c['engine'])


def test_consent_withdrawal_and_measurement_write_contend_with_authorized_read_without_partial_retry(progress_http):
    from web.services.progress_share import withdraw_consent
    from web.personal_progress_schemas import ConsentWithdraw,MeasurementWrite
    from web.services.personal_progress import write_measurement
    c=progress_http;link,consent=make_source(c);started=Event();release=Event()
    second=configure_tenant_engine(create_engine(c['engine'].url,pool_size=1,max_overflow=0))
    def hold(connection,cursor,statement,parameters,context,many):
        if 'WITH days AS MATERIALIZED' in statement:
            started.set();assert release.wait(8)
    event.listen(c['engine'],'before_cursor_execute',hold)
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            future=workers.submit(c['client_http'].get,shared_path(c,link,consent),headers=c['headers']['gym'])
            assert started.wait(8)
            for operation in ('withdraw','measurement'):
                with Session(second) as db:
                    with pytest.raises(HTTPException) as failed:
                        if operation=='withdraw':withdraw_consent(db,{'id':c['person'],'session_version':0},link,ConsentWithdraw(expected_consent_id=consent['id'],expected_version=1))
                        else:write_measurement(db,{'id':c['person'],'session_version':0},str(uuid.uuid4()),MeasurementWrite(expected_version=0,source_profile_id=c['profile'],measured_on=c['today'],values={'peso_kg':72}))
                    assert failed.value.status_code==409 and failed.value.detail['code']=='progress_busy'
            release.set();assert future.result(timeout=10).status_code==200
        removed=c['client_http'].post('/api/usuario/vinculos/'+link+'/progreso/consentimiento/retirar',headers=c['headers']['person'],json={'expected_consent_id':consent['id'],'expected_version':1})
        assert removed.status_code==200
        assert c['client_http'].get(shared_path(c,link,consent),headers=c['headers']['gym']).status_code==409
    finally:
        release.set();event.remove(c['engine'],'before_cursor_execute',hold);second.dispose()
    blank_pool(c['engine'])
