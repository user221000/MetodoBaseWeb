"""Actual transaction/proof/ownership cases on genuine39 migrations."""
from datetime import date
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.privacy39_fixtures import (privacy39_engine,account37_engine,account37,database_schema,isolated_database)
from tests.account_security37_fixtures import PASSWORD
from tests.test_privacy39_policy import synthetic_policy,NOW
from web.database.models import (Base,PrivacyRequest,PrivacyDispositionItem,Usuario,UserRole,RefreshToken,
    MfaAuthorization,MfaCredential,PersonalDiaryDay,Cliente,ClientProgress)
from web.services import account_privacy as privacy,mfa_service as mfa
from web.services.privacy_disposition import apply_batch


def policy_for_now(**_):
    from datetime import timedelta
    now=mfa.instant()
    return synthetic_policy(valid_from=now-timedelta(minutes=5),valid_through=now+timedelta(hours=1))


def proof(case):
    with case['factory']() as db:
        return mfa.reauthenticate(db,case['expected'],case['access'],password=PASSWORD)['reauthentication_token']


def request(case):
    return privacy.create_request(case['expected'],str(uuid.uuid4()),factory=case['factory'])


def close(case,row,token,provider=policy_for_now):
    # Keep the exact typed policy stable across planning and disposition.
    policy=provider(subject_id=case['user'],now=mfa.instant()) if provider else None
    output=privacy.close_account(case['expected'],case['access'],row['id'],row['version'],token,
        factory=case['factory'],policy_provider=(lambda **_:policy) if policy else None)
    return output,policy


def test_request_is_durable_idempotent_self_only_and_missing_policy_never_closes(account37):
    case=account37;key=str(uuid.uuid4())
    first=privacy.create_request(case['expected'],key,factory=case['factory'])
    second=privacy.create_request(case['expected'],key,factory=case['factory'])
    assert first==second and first['account_closed'] is False and first['erasure_complete'] is False
    blocked,_=close(case,first,proof(case),provider=None)
    assert blocked['state']=='blocked' and not blocked['account_closed']
    with case['factory']() as db:
        user=db.get(Usuario,case['user'])
        assert user.activo and user.session_version==0
        assert db.scalars(select(RefreshToken).where(RefreshToken.user_id==user.id,RefreshToken.revoked.is_(False))).all()
    other={**case['expected'],'id':str(uuid.uuid4())}
    with pytest.raises(HTTPException):privacy.read_request(other,first['id'],factory=case['factory'])


def test_closure_atomically_consumes_proof_revokes_sessions_and_preserves_account_row(account37):
    case=account37;row=request(case);token=proof(case)
    output,policy=close(case,row,token)
    assert output['account_closed'] and output['sessions_revoked'] and not output['erasure_complete']
    with case['factory']() as db:
        user=db.get(Usuario,case['user'])
        assert user is not None and not user.activo and user.session_version==1
        assert db.scalars(select(RefreshToken).where(RefreshToken.user_id==user.id,RefreshToken.revoked.is_(False))).all()==[]
        from web.services.mfa_crypto import opaque_digest
        assert db.get(MfaAuthorization,opaque_digest('reauth',token)).consumed_at is not None
        assert len(db.scalars(select(PrivacyDispositionItem).where(PrivacyDispositionItem.request_id==row['id'])).all())==9
    with pytest.raises(HTTPException):privacy.read_request(case['expected'],row['id'],factory=case['factory'])


def test_failed_caller_commit_rolls_back_closure_proof_and_refresh_together(account37,monkeypatch):
    case=account37;row=request(case);token=proof(case)
    def rejected(_):raise HTTPException(503,{'code':'synthetic_commit_failure'})
    monkeypatch.setattr(privacy,'_commit',rejected)
    with pytest.raises(HTTPException):close(case,row,token)
    with case['factory']() as db:
        user=db.get(Usuario,case['user']);assert user.activo and user.session_version==0
        assert db.get(PrivacyRequest,row['id']).closed_at is None
        from web.services.mfa_crypto import opaque_digest
        assert db.get(MfaAuthorization,opaque_digest('reauth',token)).consumed_at is None
        assert db.scalar(select(RefreshToken.jti).where(RefreshToken.user_id==user.id,RefreshToken.revoked.is_(False))) is not None


def test_real_owned_deletions_leave_foreign_rows_and_ledger_categories_blocked(account37):
    case=account37;foreign=str(uuid.uuid4());client=str(uuid.uuid4());foreign_client=str(uuid.uuid4())
    with case['factory']() as db:
        db.add(Usuario(id=foreign,email=foreign+'@example.invalid',password_hash='not-a-login',nombre='Synthetic',tipo='usuario',role=UserRole.VIEWER));db.flush()
        db.add_all([Cliente(id_cliente=client,gym_id=case['user'],nombre='Own'),Cliente(id_cliente=foreign_client,gym_id=foreign,nombre='Foreign')]);db.flush()
        for owner in (case['user'],foreign):
            db.add(PersonalDiaryDay(user_id=owner,local_date=date(2026,10,23),meals_json='{}'))
        db.add_all([ClientProgress(gym_id=case['user'],id_cliente=client),ClientProgress(gym_id=foreign,id_cliente=foreign_client)])
        db.commit()
    output,policy=close(case,request(case),proof(case))
    with case['factory']() as db:
        applied=apply_batch(db,case['user'],output['id'],output['version'],policy);db.commit()
        assert applied['state']=='partially_applied' and not applied['erasure_complete']
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==case['user'])) is None
        assert db.scalar(select(ClientProgress.id).where(ClientProgress.gym_id==case['user'])) is None
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==foreign)) is not None
        assert db.scalar(select(ClientProgress.id).where(ClientProgress.gym_id==foreign)) is not None
        repeated=apply_batch(db,case['user'],output['id'],applied['version'],policy);db.commit()
        assert repeated==applied


def test_privacy_factor_failure_budget_is_distinct_and_current_factor_is_required(account37):
    import base64
    from datetime import timedelta
    from web.services.mfa_crypto import encrypt,totp
    from web.settings import get_settings
    case=account37;row=request(case);proof(case);now=mfa.instant();seed=b'P'*20
    with case['factory']() as db:
        factor=db.get(MfaCredential,case['user']);factor.generation=1;factor.enabled_at=now
        factor.secret_ciphertext=encrypt(seed,base64.urlsafe_b64decode(get_settings().MFA_ENCRYPTION_KEY),mfa._aad(factor,1,'active'))
        db.commit()
    token=proof(case);now=mfa.instant();policy=synthetic_policy(valid_from=now-timedelta(minutes=5),valid_through=now+timedelta(hours=1))
    code=totp(seed,int(now.timestamp())//30);wrong=str((int(code)+1)%1000000).zfill(6)
    with pytest.raises(HTTPException) as denied:
        privacy.close_account(case['expected'],case['access'],row['id'],row['version'],token,code=wrong,
            factory=case['factory'],policy_provider=lambda **_:policy,now=now)
    assert denied.value.status_code==400
    with case['factory']() as db:
        factor=db.get(MfaCredential,case['user'])
        assert factor.attempts['privacy']['count']==1 and 'password' not in factor.attempts
        assert db.get(PrivacyRequest,row['id']).closed_at is None and db.get(Usuario,case['user']).activo
    output=privacy.close_account(case['expected'],case['access'],row['id'],row['version'],token,code=code,
        factory=case['factory'],policy_provider=lambda **_:policy,now=now)
    assert output['account_closed'] and output['sessions_revoked']


def test_disposition_ambiguous_progress_owner_is_retained_and_marked_blocked(account37):
    case=account37;foreign=str(uuid.uuid4());client=str(uuid.uuid4())
    with case['factory']() as db:
        db.add(Usuario(id=foreign,email=foreign+'@example.invalid',password_hash='not-a-login',nombre='Synthetic',tipo='usuario',role=UserRole.VIEWER));db.flush()
        db.add(Cliente(id_cliente=client,gym_id=foreign,nombre='Foreign profile'));db.flush()
        row=ClientProgress(gym_id=case['user'],id_cliente=client);db.add(row);db.commit();identity=row.id
    output,policy=close(case,request(case),proof(case))
    with case['factory']() as db:
        result=apply_batch(db,case['user'],output['id'],output['version'],policy);db.commit()
        assert db.get(ClientProgress,identity) is not None
        item=next(value for value in result['items'] if value['category']=='personal_client_progress')
        assert item['status']=='blocked' and item['reason']=='ownership_mismatch_requires_review'
        assert not result['erasure_complete']


def test_prior_flush_failure_is_not_relabelled_as_category_hold_and_explicit_retry_is_clean(account37):
    from sqlalchemy.exc import IntegrityError
    case=account37
    with case['factory']() as db:
        db.add(PersonalDiaryDay(user_id=case['user'],local_date=date(2026,10,23),meals_json='{}'));db.commit()
    output,policy=close(case,request(case),proof(case))
    with case['factory']() as db:
        db.add(Usuario(id=str(uuid.uuid4()),email=None,password_hash='not-a-login',nombre='Invalid pending fixture'))
        with pytest.raises(IntegrityError):apply_batch(db,case['user'],output['id'],output['version'],policy)
        db.rollback()
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==case['user'])) is not None
        row=db.get(PrivacyRequest,output['id']);assert row.version==output['version'] and row.state=='eligible'
    with case['factory']() as db:
        retried=apply_batch(db,case['user'],output['id'],output['version'],policy);db.commit()
        assert retried['state']=='partially_applied'
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==case['user'])) is None


def test_category_marked_deleted_rechecks_reappeared_rows_before_reporting_success(account37):
    case=account37;output,policy=close(case,request(case),proof(case))
    with case['factory']() as db:
        first=apply_batch(db,case['user'],output['id'],output['version'],policy);db.commit()
        db.add(PersonalDiaryDay(user_id=case['user'],local_date=date(2026,10,23),meals_json='{}'));db.commit()
        repeated=apply_batch(db,case['user'],output['id'],first['version'],policy);db.commit()
        assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==case['user'])) is None
        item=next(row for row in repeated['items'] if row['category']=='personal_diary_days')
        assert item['status']=='deleted' and item['deleted_rows']==1
