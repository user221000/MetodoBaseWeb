"""Retain the accepted R24 physical-lock assertions on real current31.

Original independent QA driver is pinned in current-business-mapping.json.
Only the owned schema31/MFA fixture changes; every lock/business assertion stays.
"""
import json, os, time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select, text, event
from sqlalchemy.orm import Session
from tests.ci_mfa31.current_link_fixtures import case, http, link_db as _current_db
from tests.test_publication_diary_consumption import prepare_publication
from web.database.tenant_context import configure_tenant_engine, tenant_scope
from web.database.models import Usuario, ClientPlanPublication

@pytest.fixture(scope='module', params=['postgresql'])
def link_db(request, tmp_path_factory):
    owner = _current_db.__wrapped__(request, tmp_path_factory)
    admin, small = next(owner)
    app = configure_tenant_engine(create_engine(small.url, pool_size=6, max_overflow=0,
        pool_timeout=5, connect_args={'options':'-c statement_timeout=8000'}))
    try:
        yield admin, app
    finally:
        app.dispose()
        owner.close()

@pytest.mark.parametrize('http',['web.main_web'],indirect=True)
def test_account_NOWAIT_and_real_publication_wait_then_revocation_never_write_after_revoke(http):
    client=http['client_http'];headers=http['headers']['person'];day,body=prepare_publication(http)
    statements=[];account_locks=[];publication_attempt=Event();publication_pid=[];owner_ids={http['gym'],http['person']}
    def observe(conn,cursor,sql,parameters,context,many):
        upper=sql.upper();statements.append(upper.split()[0])
        if 'FROM USUARIOS 'in upper and 'FOR UPDATE NOWAIT'in upper:
            values=parameters.values()if isinstance(parameters,dict)else parameters
            account_locks.extend(v for v in values if v in owner_ids)
        if 'FROM CLIENT_PLAN_PUBLICATIONS 'in upper and 'FOR UPDATE'in upper:
            publication_pid.append(conn.connection.driver_connection.get_backend_pid());publication_attempt.set()
    event.listen(http['app'],'before_cursor_execute',observe)
    holder=Session(http['app'])
    try:
        with tenant_scope(http['gym']):holder.scalar(select(Usuario).where(Usuario.id==http['gym']).with_for_update())
        denied=client.patch(day,headers=headers,json=body)
        assert denied.status_code==503 and denied.json()['detail']['code']=='diary_save_unconfirmed'
        assert account_locks and account_locks==sorted(account_locks)and set(account_locks)<=owner_ids
        assert not {'INSERT','UPDATE','DELETE'}&set(statements)
    finally:holder.rollback();holder.close();event.remove(http['app'],'before_cursor_execute',observe)
    untouched=client.get(day,headers=headers).json();assert untouched['version']==0 and untouched['meals']=={}
    statements.clear();account_locks.clear();publication_attempt.clear();publication_pid.clear()
    holder=Session(http['app']);executor=ThreadPoolExecutor(max_workers=1);future=None
    event.listen(http['app'],'before_cursor_execute',observe)
    blocked=False;busy_code=None
    try:
        with tenant_scope(http['gym']):
            holder.scalar(select(ClientPlanPublication).where(ClientPlanPublication.id==body['publication_id']).with_for_update())
            holder_pid=holder.scalar(text('SELECT pg_backend_pid()'))
        # Ignore the intentionally held fixture query itself; observe only worker's actual lock attempt.
        publication_attempt.clear();publication_pid.clear();account_locks.clear();statements.clear()
        future=executor.submit(client.patch,day,headers=headers,json=body)
        assert publication_attempt.wait(5),'Consumption never reached its physical publication lock'
        assert len(publication_pid)==1 and publication_pid[0]!=holder_pid
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            with http['admin'].connect()as control:
                blockers=control.execute(text('SELECT pg_blocking_pids(:pid)'),{'pid':publication_pid[0]}).scalar_one()
            if holder_pid in blockers:blocked=True;break
            time.sleep(.05)
        assert blocked and not future.done(),'Expected real PG publication wait was not witnessed'
        assert account_locks==sorted(owner_ids),'Account locks must be acquired once in total order before publication wait'
        revoked_busy=client.request('DELETE','/api/usuario/vinculos/'+body['link_id'],headers=headers,json={'expected_version':2})
        busy_code=revoked_busy.json()['detail']['code'];assert revoked_busy.status_code==409 and busy_code=='member_operation_busy'
        holder.rollback();saved=future.result(timeout=8);assert saved.status_code==200
    finally:
        holder.rollback();holder.close();executor.shutdown(wait=True);event.remove(http['app'],'before_cursor_execute',observe)
    committed=saved.json();assert committed['version']==1
    revoked=client.request('DELETE','/api/usuario/vinculos/'+body['link_id'],headers=headers,json={'expected_version':2});assert revoked.status_code==200
    after=client.patch(day,headers=headers,json={**body,'expected_version':1,'meal':'cena'});assert after.status_code==404
    assert client.get(day,headers=headers).json()==committed
    report={'case':'account-NOWAIT/publication-lock/consumption-vs-revocation','passed':True,'account_lock_ids_expected_sorted':sorted(owner_ids),'account_NOWAIT_denial':503,'publication_lock_actual_blocker_PID':holder_pid,'consumption_backend_PID':publication_pid[0],'real_publication_wait_witness':blocked,'concurrent_revoke_busy_status':409,'concurrent_revoke_busy_code':busy_code,'consumption_after_lock_release':200,'subsequent_revocation':200,'fresh_consumption_after_revocation':404,'personal_version_preserved':1,'scope':'Functional bounded real lock witness only; no latency/SLO/performance claim.'}
    (Path(os.environ['R24_PG_OUTPUT'])/'lock-review.json').write_text(json.dumps(report,indent=2)+'\n')
