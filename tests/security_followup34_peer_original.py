"""Prepared independent probes; NOT executed, explicit PG handoff required.

Requires a later frozen revision34 PostgreSQL target captured by its author.
Do not use the author22-case file as independent evidence.
"""
import os
from time import monotonic
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from tests.followup34_fixtures import owned_database, REVISION
from tests.followup34_http import followup_http, candidate, create, PASSWORD
from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
from tests.mfa31_contract_client import MfaContractClient


@pytest.fixture(scope='module')
def followup_db(tmp_path_factory):
    if not os.environ.get('METODOBASE_TEST_MIGRATOR_URL'):
        pytest.skip('Future explicit exclusive own UUID PostgreSQL handoff required')
    with owned_database('postgresql',tmp_path_factory.mktemp('independent-followup34')) as (url,admin):
        run_migration(url,'db_bootstrap.py','--revision',REVISION)
        app=application_engine(url,admin)
        try:
            with app.connect() as db:
                assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid=\'usuarios\'::regclass),\'MEMBER\') FROM pg_roles WHERE rolname=current_user')).one())==(False,False,False,False,False)
                assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))==28
            assert app.pool.size()==1
            yield admin,app
        finally:app.dispose()


def blank(c):
    assert c['engine'].pool.checkedout()==0 and c['engine'].pool.size()==1
    with c['engine'].connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one())==('','','')


def test_unassigned_nutri_does_not_probe_other_responsibles_lock(followup_http):
    from web.auth import hash_password
    from web.database.models import Usuario,UserRole,FollowupTask,FollowupTaskEvent
    c=followup_http;third=str(uuid.uuid4())
    with Session(c['admin']) as db:
        db.add(Usuario(id=third,email=uuid.uuid4().hex+'@example.invalid',password_hash=hash_password(PASSWORD),
            nombre='Other synthetic responsible',tipo='usuario',role=UserRole.NUTRIOLOGO,team_gym_id=c['user']))
        db.commit()
    made,_,_=create(c,assignee_id=third);assert made.status_code==200
    identifier=made.json()['task']['id']
    actor=MfaContractClient(c['raw'],{'id':c['member']},c['factory'],PASSWORD);actor.authenticate()
    body={'expected_version':1,'outcome':'review_recorded','confirm':True}
    with c['admin'].connect() as held:
        held.execute(text('SELECT id FROM usuarios WHERE id=:id FOR UPDATE'),{'id':third})
        missing=c['raw'].post('/api/seguimiento/tareas/'+str(uuid.uuid4())+'/completar',json=body,
            headers={'Idempotency-Key':str(uuid.uuid4())})
        foreign=c['raw'].post('/api/seguimiento/tareas/'+identifier+'/completar',json=body,
            headers={'Idempotency-Key':str(uuid.uuid4())})
    assert missing.status_code==foreign.status_code==404
    assert missing.json()==foreign.json()
    with Session(c['admin']) as db:
        assert db.get(FollowupTask,identifier).version==1
        assert len(db.scalars(select(FollowupTaskEvent.id).where(FollowupTaskEvent.task_id==identifier)).all())==1
    blank(c)


def test_contended_client_aborts_nowait_as_busy_instead_of_statement_timeout(followup_http):
    from web.database.models import FollowupTask,FollowupTaskEvent
    c=followup_http;fact=candidate(c)
    body={'client_id':c['profile'],'cause':'no_saved_plan','cause_evidence_hash':fact['cause_evidence_hash'],
        'next_step':'review_plan_history','assignee_id':None,'expected_active_task_id':None,'confirm':True}
    # Own pool1 connection only. Restore this session setting even on failure;
    # no role/global database setting, pool disposal or foreign session action.
    with c['engine'].connect() as db:
        previous=db.scalar(text('SHOW statement_timeout'))
        db.execute(text("SELECT set_config('statement_timeout','700ms',false)"));db.commit()
    try:
        with c['admin'].connect() as held:
            held.execute(text('SELECT id_cliente FROM clientes WHERE id_cliente=:id FOR UPDATE'),{'id':c['profile']})
            started=monotonic()
            reply=c['raw'].post('/api/seguimiento/tareas',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
            elapsed=monotonic()-started
        assert reply.status_code==409 and reply.json()['detail']['code']=='followup_busy'
        assert elapsed<0.6
        assert not {'ack','task','operation'} & reply.json().keys()
        with Session(c['admin']) as db:
            assert db.scalar(select(FollowupTask.id).where(FollowupTask.gym_id==c['user'])) is None
            assert db.scalar(select(FollowupTaskEvent.id).where(FollowupTaskEvent.gym_id==c['user'])) is None
    finally:
        with c['engine'].connect() as db:
            db.execute(text("SELECT set_config('statement_timeout',:previous,false)"),{'previous':previous});db.commit()
            assert db.scalar(text('SHOW statement_timeout'))==previous
        blank(c)
