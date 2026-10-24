"""Actual restricted PG39 cases; no SQLite or prebound production Sessions."""
from datetime import date
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import event,select
from sqlalchemy.exc import DBAPIError,IntegrityError
from sqlalchemy.orm import Session
from tests.ci_web39.pg_fixtures import (database_schema,isolated_database,pg39_runtime,
    pg39_database,released)  # noqa:F401 -- explicit finite fixture composition
from tests.ci_web39.pg_physical import physical_contract
from tests.privacy39_pg_actors import (seed_actor,seed_personal_data,enable_factor,policy_at,
    proof,request,close,snapshot)
from web.database.models import (Usuario,RefreshToken,MfaAuthorization,MfaCredential,
    PrivacyRequest,PrivacyDispositionItem,PersonalDiaryDay,ClientProgress,ProductAnalyticsFact)
from web.database.tenant_context import tenant_scope
from web.services import account_privacy as privacy,mfa_service as mfa
from web.services.mfa_crypto import opaque_digest,totp
from web.services.privacy_disposition import apply_batch


def test_pg39_restricted_role_durable_self_requests_and_persisted_A_B_RLS(pg39_database,monkeypatch):
    database=pg39_database
    observed=physical_contract(database.app)
    assert observed['role_five_flags']==[False]*5
    assert set(observed['protected_tables_FORCE_RLS'])=={'privacy_requests','privacy_disposition_items','product_analytics_facts'}
    a,b=(seed_actor(database,monkeypatch) for _ in range(2))
    key=str(uuid.uuid4())
    first=privacy.create_request(a['expected'],key,factory=a['factory'])
    assert privacy.create_request(a['expected'],key,factory=a['factory'])==first
    second=request(b)
    with Session(database.app) as db:
        assert db.scalars(select(PrivacyRequest.id)).all()==[]
    with tenant_scope(b['user']),Session(database.app) as db:
        assert db.scalars(select(PrivacyRequest.id)).all()==[second['id']]
        assert db.get(PrivacyRequest,first['id']) is None
    with pytest.raises(HTTPException) as denied:
        privacy.read_request(b['expected'],first['id'],factory=b['factory'])
    assert denied.value.status_code==404
    before_b=snapshot(database.admin,b['user'])
    with tenant_scope(b['user']),Session(database.app) as db:
        with pytest.raises(DBAPIError):
            db.add(PrivacyRequest(subject_id=a['user'],idempotency_key=str(uuid.uuid4()),
                intent='erase_personal_data',state='requested'))
            db.commit()
        db.rollback()
    assert snapshot(database.admin,b['user'])==before_b
    with Session(database.admin) as db:
        assert db.get(PrivacyRequest,first['id']).subject_id==a['user']


def test_pg39_MFA_actor_factor_budget_atomic_closure_and_real_deletes_preserve_B(pg39_database,monkeypatch):
    database=pg39_database;a,b=(seed_actor(database,monkeypatch) for _ in range(2))
    seed_personal_data(a);seed_personal_data(b)
    now=mfa.instant();seed=enable_factor(a,now);proof(b,now=now)
    row=request(a);token=proof(a,now=now);policy=policy_at(now)
    before_b=snapshot(database.admin,b['user'])
    # The ordinary application Session begins without MFA actor authority.
    with a['factory']() as db:assert db.get(MfaCredential,a['user']) is None
    code=totp(seed,int(now.timestamp())//30);wrong=str((int(code)+1)%1000000).zfill(6)
    with pytest.raises(HTTPException) as failed:
        close(a,row,policy,token=token,code=wrong,now=now)
    assert failed.value.status_code==400
    with Session(database.admin) as db:
        factor=db.get(MfaCredential,a['user'])
        assert factor.attempts['privacy']['count']==1 and 'password' not in factor.attempts
        assert db.get(MfaAuthorization,opaque_digest('reauth',token)).consumed_at is None
        assert db.get(Usuario,a['user']).activo and db.get(PrivacyRequest,row['id']).closed_at is None
        assert db.scalar(select(RefreshToken.jti).where(RefreshToken.user_id==a['user'],RefreshToken.revoked.is_(False))) is not None
    output=close(a,row,policy,token=token,code=code,now=now)
    assert output['account_closed'] and output['sessions_revoked'] and not output['erasure_complete']
    with Session(database.admin) as db:
        user=db.get(Usuario,a['user']);assert not user.activo and user.session_version==1
        assert db.get(MfaAuthorization,opaque_digest('reauth',token)).consumed_at is not None
        factor=db.get(MfaCredential,a['user'])
        assert (factor.pending_id,factor.pending_ciphertext,factor.pending_expires_at)==(None,None,None)
        assert db.scalar(select(RefreshToken.jti).where(RefreshToken.user_id==a['user'],RefreshToken.revoked.is_(False))) is None
        assert len(db.scalars(select(PrivacyDispositionItem).where(PrivacyDispositionItem.request_id==row['id'])).all())==9
    with a['factory']() as db:
        first=apply_batch(db,a['user'],row['id'],output['version'],policy,now=now);db.commit()
    assert first['state']=='partially_applied' and not first['erasure_complete']
    with Session(database.admin) as db:
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==a['user'])) is None
        assert db.scalar(select(ClientProgress.id).where(ClientProgress.gym_id==a['user'])) is None
        db.add(PersonalDiaryDay(user_id=a['user'],local_date=date(2026,10,23),meals_json='{}'));db.commit()
    with a['factory']() as db:
        repeated=apply_batch(db,a['user'],row['id'],first['version'],policy,now=now);db.commit()
    with Session(database.admin) as db:
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==a['user'])) is None
    assert next(item for item in repeated['items'] if item['category']=='personal_diary_days')['deleted_rows']==2
    assert snapshot(database.admin,b['user'])==before_b


def test_pg39_missing_policy_commit_failure_and_prior_flush_have_zero_destructive_effect(pg39_database,monkeypatch):
    database=pg39_database;a,b=(seed_actor(database,monkeypatch) for _ in range(2))
    seed_personal_data(a);seed_personal_data(b)
    row=request(a);token=proof(a);now=mfa.instant();policy=policy_at(now)
    before_b=snapshot(database.admin,b['user'])
    blocked=privacy.close_account(a['expected'],a['access'],row['id'],row['version'],token,
        factory=a['factory'],policy_provider=None,now=now)
    assert blocked['state']=='blocked' and not blocked['account_closed']
    with Session(database.admin) as db:
        assert db.get(Usuario,a['user']).activo
        assert db.get(MfaAuthorization,opaque_digest('reauth',token)).consumed_at is None
    original=privacy._commit
    def reject(_):raise HTTPException(503,{'code':'synthetic_commit_failure'})
    before_a=snapshot(database.admin,a['user'])
    monkeypatch.setattr(privacy,'_commit',reject)
    with pytest.raises(HTTPException) as rejected:close(a,blocked,policy,token=token,now=now)
    assert rejected.value.status_code==503
    monkeypatch.setattr(privacy,'_commit',original)
    assert snapshot(database.admin,a['user'])==before_a and snapshot(database.admin,b['user'])==before_b
    output=close(a,blocked,policy,token=token,now=now)
    before_a=snapshot(database.admin,a['user']);deletes=[]
    def observe(_connection,_cursor,statement,_parameters,_context,_many):
        if statement.lstrip().upper().startswith('DELETE'):deletes.append(statement.split()[2])
    event.listen(database.app,'before_cursor_execute',observe)
    try:
        with a['factory']() as db:
            db.add(Usuario(id=str(uuid.uuid4()),email=None,password_hash='not-a-login',nombre='Invalid pending fixture'))
            with pytest.raises(IntegrityError):apply_batch(db,a['user'],row['id'],output['version'],policy,now=now)
            db.rollback()
    finally:event.remove(database.app,'before_cursor_execute',observe)
    assert deletes==[]
    assert snapshot(database.admin,a['user'])==before_a and snapshot(database.admin,b['user'])==before_b
    with a['factory']() as db:
        retry=apply_batch(db,a['user'],row['id'],output['version'],policy,now=now);db.commit()
    assert retry['state']=='partially_applied' and not retry['erasure_complete']
    assert snapshot(database.admin,b['user'])==before_b


def test_pg39_personal_facts_keysets_and_owner_exclusion_preserve_B(pg39_database,monkeypatch):
    from web.services.product_analytics_v2 import origin
    from web.services.privacy_facts_export import export_personal_facts,FIELDS
    database=pg39_database;a,b=(seed_actor(database,monkeypatch) for _ in range(2))
    for case,labels in ((a,('demo','customer')),(b,('customer',))):
        for version,label in enumerate(labels):
            with case['factory']() as db:
                origin(db,case['expected'],'personal',None,value=label,expected_version=version)
    before_b=snapshot(database.admin,b['user'])
    with a['factory']() as db:
        first=export_personal_facts(db,a['user'],limit=1)
        second=export_personal_facts(db,a['user'],limit=1,after=first['next_after'])
    assert first['next_after'] and second['next_after'] is None
    rows=first['records']+second['records'];assert len(rows)==2 and len({item['id'] for item in rows})==2
    assert all(set(item)==set(FIELDS) and item['source_id']==a['user'] for item in rows)
    assert {item['origin'] for item in rows}=={'demo','customer'}
    assert first['max_response_bytes']==131072 and 'professional_portfolio' in first['excluded_categories']
    owner=seed_actor(database,monkeypatch,professional=True)
    with owner['factory']() as db,pytest.raises(HTTPException) as denied:
        export_personal_facts(db,owner['user'])
    assert denied.value.status_code==403
    assert snapshot(database.admin,b['user'])==before_b
