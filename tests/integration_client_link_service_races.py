"""Real29 service transactions: separate processes, partial failure and stale SV."""
import multiprocessing

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine,event,text
from sqlalchemy.orm import Session

from tests import integration_client_link_services as shared
from web.client_link_schemas import InvitationAccept
from web.database.models import ClientAccountLink,ClientLinkInvitation,Usuario
from web.database.tenant_context import configure_tenant_engine,tenant_scope
from web.services import client_link_invitations as invitations

case=shared.case
link_db=shared.link_db
issue=shared.issue
accept=shared.accept
principal=shared.principal
session=shared.session


def _consume(url,actor,token,ready,start,output):
    from tests.isolation import block_external_sockets,validate_postgres_test_url
    validate_postgres_test_url(url);block_external_sockets()
    engine=configure_tenant_engine(create_engine(url,pool_size=1,max_overflow=0,hide_parameters=True))
    try:
        ready.put(True)
        if not start.wait(20):raise RuntimeError('Synthetic process coordination timed out')
        with tenant_scope(actor),Session(engine) as db:
            result=invitations.accept_invitation(db,principal(actor),InvitationAccept(token=token,expected_version=1,confirm=True))
            output.put(('accepted',result['version']))
    except HTTPException as denied:output.put(('denied',denied.status_code,denied.detail['code']))
    except Exception as error:output.put(('unexpected',type(error).__name__))
    finally:engine.dispose()


def test_two_processes_consume_one_proof_once_under_restricted_role(case):
    if case['app'].dialect.name!='postgresql':pytest.skip('PostgreSQL process proof; SQLite covered by services')
    issued,token=issue(case)
    context=multiprocessing.get_context('spawn');ready=context.Queue();output=context.Queue();start=context.Event()
    processes=[context.Process(target=_consume,args=(case['app'].url.render_as_string(hide_password=False),case['person'],token,ready,start,output)) for _ in range(2)]
    try:
        for process in processes:process.start()
        assert [ready.get(timeout=25) for _ in processes]==[True,True]
        start.set();results=[output.get(timeout=25) for _ in processes]
        for process in processes:process.join(10)
        assert all(process.exitcode==0 for process in processes)
        assert sum(result[0]=='accepted' for result in results)==1,results
        assert sum(result[0]=='denied' and result[1]==409 for result in results)==1,results
        with Session(case['admin']) as db:
            link=db.get(ClientAccountLink,issued['link_id']);invitation=db.get(ClientLinkInvitation,issued['invitation_id'])
            assert link.status=='active' and link.user_id==case['person'] and link.version==2
            assert invitation.status=='consumed' and invitation.consumed_by==case['person'] and invitation.version==2
            assert invitation.consumed_at==link.accepted_at
    finally:
        start.set()
        for process in processes:
            if process.is_alive():process.terminate()
            process.join(5)


def test_failure_between_consumption_and_activation_rolls_back_every_row(case):
    issued,token=issue(case);reached=[]
    def fail_link(connection,cursor,statement,parameters,context,executemany):
        if statement.upper().startswith('UPDATE CLIENT_ACCOUNT_LINKS SET '):
            reached.append(True);raise RuntimeError('Synthetic failure after actual invitation UPDATE')
    event.listen(case['app'],'before_cursor_execute',fail_link)
    try:
        with session(case,'person') as db,pytest.raises(HTTPException) as denied:
            invitations.accept_invitation(db,principal(case['person']),InvitationAccept(token=token,expected_version=1,confirm=True))
    finally:event.remove(case['app'],'before_cursor_execute',fail_link)
    assert reached==[True] and denied.value.status_code==503
    with Session(case['admin']) as db:
        link=db.get(ClientAccountLink,issued['link_id']);invitation=db.get(ClientLinkInvitation,issued['invitation_id'])
        assert link.status=='pending' and link.user_id is None and invitation.status=='pending' and invitation.consumed_by is None
    assert accept(case,issued,token)['status']=='active'
    if case['app'].dialect.name=='postgresql':
        with case['app'].connect() as db:
            assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
            assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''


def test_session_revoked_between_proof_lookup_and_account_lock_cannot_accept(case):
    if case['app'].dialect.name!='postgresql':pytest.skip('PG lock/reload interleaving')
    issued,token=issue(case);changed=[]
    def revoke(connection,cursor,statement,parameters,context,executemany):
        if not changed and statement.upper().startswith('SELECT USUARIOS.') and 'FOR UPDATE NOWAIT' in statement.upper():
            changed.append(True)
            with Session(case['admin']) as db:
                db.get(Usuario,case['person']).session_version=1;db.commit()
    event.listen(case['app'],'before_cursor_execute',revoke)
    try:
        with session(case,'person') as db,pytest.raises(HTTPException) as denied:
            invitations.accept_invitation(db,principal(case['person']),InvitationAccept(token=token,expected_version=1,confirm=True))
    finally:event.remove(case['app'],'before_cursor_execute',revoke)
    assert changed==[True] and denied.value.status_code==401
    with Session(case['admin']) as db:
        assert db.get(ClientAccountLink,issued['link_id']).status=='pending'
        assert db.get(ClientLinkInvitation,issued['invitation_id']).status=='pending'
