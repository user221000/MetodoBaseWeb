"""Unknown SQL failures are uncertainty; actual BUSY remains a closed conflict."""
import json
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests import nutrition35_fixtures as http_fixtures
from tests.nutrition35_fixtures import candidate
from web.database.models import FollowupTask, FollowupTaskEvent

followup_db = http_fixtures.followup_db
followup_http = http_fixtures.followup_http


def command(c):
    evidence=candidate(c)
    return {'client_id':c['profile'],'cause':'no_saved_plan','cause_evidence_hash':evidence['cause_evidence_hash'],
        'next_step':'review_plan_history','assignee_id':None,'expected_active_task_id':None,'confirm':True}


def counts(c):
    with Session(c['admin']) as db:
        return [len(db.scalars(select(model.id).where(model.gym_id==c['user'])).all())
            for model in (FollowupTask,FollowupTaskEvent)]


@pytest.mark.parametrize('fault,rollback_uncertain',[
    ('integrity',False),('schema_plain',False),('schema_blocked',False),
    ('integrity',True),('schema_blocked',True),
])
def test_unknown_SQL_failure_never_claims_an_ordinary_conflict(followup_http,monkeypatch,fault,rollback_uncertain):
    from web.database import followup_task_repository as repo
    c=followup_http;body=command(c);key=str(uuid.uuid4());observed=[]
    original_flush=Session.flush;original_rollback=Session.rollback
    def flush(db,*args,**kwargs):
        if any(isinstance(row,FollowupTaskEvent) for row in db.new):
            db.info['independent_SQL_fault']=True;observed.append({'kind':'IntegrityError'})
            raise IntegrityError('PRIVATE_UNRECOGNIZED_CONSTRAINT',None,Exception('PRIVATE_UNKNOWN_INTEGRITY'))
        return original_flush(db,*args,**kwargs)
    def schema_error(db,*args,**kwargs):
        db.info['independent_SQL_fault']=True
        try:
            # Both are actual SQLITE_ERROR=1; the second name happens to contain
            # "locked". Neither is SQLITE_BUSY/LOCKED or a known constraint race.
            db.execute(text('SELECT * FROM independent_blocked_missing_table' if fault=='schema_blocked'
                else 'SELECT * FROM independent_missing_table'))
        except Exception as error:
            observed.append({'kind':type(error).__name__,'SQLite_errorcode':getattr(error.orig,'sqlite_errorcode',None)})
            raise
        raise AssertionError('The synthetic missing table unexpectedly exists')
    def rollback(db):
        if rollback_uncertain and db.info.get('independent_SQL_fault'):
            raise RuntimeError('PRIVATE_UNCERTAIN_ROLLBACK')
        return original_rollback(db)
    with monkeypatch.context() as patch:
        patch.setattr(Session,'rollback',rollback)
        if fault=='integrity':patch.setattr(Session,'flush',flush)
        else:patch.setattr(repo,'sources',schema_error)
        reply=c['raw'].post('/api/seguimiento/tareas',json=body,headers={'Idempotency-Key':key})
    assert len(observed)==1
    assert counts(c)==[0,0]
    assert not {'ack','task','operation','token','refresh_token'} & reply.json().keys()
    assert 'PRIVATE_' not in reply.text and 'missing_table' not in reply.text
    assert reply.headers['Cache-Control']=='no-store' and reply.headers['Referrer-Policy']=='no-referrer'
    explicit=c['raw'].post('/api/seguimiento/tareas',json=body,headers={'Idempotency-Key':key})
    assert explicit.status_code==200 and explicit.json()['operation']['replayed'] is False
    assert counts(c)==[1,1]
    report={'factory':c['factory_name'],'fault':fault,'rollback_uncertain':rollback_uncertain,
        'observed_driver_error':observed,'status':reply.status_code,'code':reply.json().get('detail',{}).get('code'),
        'no_partial_event_or_projection':True,'opaque_private_error':True,'no_false_ACK':True,
        'explicit_new_request_after_fault_is_one_operation':True,'identity_or_MFA_overrides':False}
    path=Path(os.environ['SEC_FOLLOWUP34_RECEIPTS'])/(c['factory_name'].replace('.','_')+'-'+fault+'-'+str(rollback_uncertain)+'.json')
    with path.open('xb') as output:output.write((json.dumps(report,indent=2)+'\n').encode())
    assert reply.status_code==503
    assert reply.json()['detail']['code']=='followup_unconfirmed'


def test_actual_SQLite_BUSY_is_a_conflict_without_partial_operation(followup_http):
    c=followup_http;body=command(c);key=str(uuid.uuid4())
    with c['engine'].connect() as blocker:
        blocker.exec_driver_sql('BEGIN IMMEDIATE')
        reply=c['raw'].post('/api/seguimiento/tareas',json=body,headers={'Idempotency-Key':key})
        assert reply.status_code==409 and reply.json()['detail']['code']=='followup_busy'
        assert not {'ack','task','operation'} & reply.json().keys()
        blocker.rollback()
    assert counts(c)==[0,0]
    explicit=c['raw'].post('/api/seguimiento/tareas',json=body,headers={'Idempotency-Key':key})
    assert explicit.status_code==200 and counts(c)==[1,1]


@pytest.fixture(autouse=True)
def isolated_SQL_error_receipts(tmp_path, monkeypatch):
    """Keep structural observations in each pytest-owned private test directory."""
    monkeypatch.setenv('SEC_FOLLOWUP34_RECEIPTS', str(tmp_path))
