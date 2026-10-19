"""Setup-only clock ownership with real HTTP factor verification.

No business clock freeze, identity override, bearer mint, factor retry or
cryptographic substitution. Only deterministic clock/entropy test seams and
an explicitly invalid submitted OTP are used.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC,datetime,timedelta
import uuid

import pytest
from sqlalchemy import select

from tests.test_team_invitation_contract import team_case


@pytest.fixture
def crossed_clock(monkeypatch):
    from tests import mfa31_contract_client as helper
    from web.services import mfa_service as service
    from web.services.mfa_crypto import totp
    generated=(datetime.now(UTC)-timedelta(minutes=2)).replace(second=29,microsecond=900000)
    arrival=generated+timedelta(milliseconds=200)
    seed=b'12345678901234567890'
    assert totp(seed,int(generated.timestamp())//30)!=totp(seed,int(arrival.timestamp())//30)
    class GeneratorClock:
        @staticmethod
        def now(_zone=None):return generated
    original=service.instant;entropy=service.secrets.token_bytes
    clock=lambda supplied=None:original(arrival if supplied is None else supplied)
    monkeypatch.setattr(helper,'datetime',GeneratorClock)
    monkeypatch.setattr(service,'instant',clock)
    monkeypatch.setattr(service.secrets,'token_bytes',lambda size=32:seed if size==20 else entropy(size))
    return arrival,clock


def test_real_counter_confirmation_and_business_grant_use_separate_clock_scopes(crossed_clock,team_case,monkeypatch):
    from tests import mfa31_contract_client as helper
    from web.database.models import MfaCredential,MfaAuthorization,MfaRecoveryCode
    from web.services import mfa_service as service
    client,factory,actor,_=team_case;arrival,original=crossed_clock
    assert service.instant is original and helper._AUTHENTICATION_INSTANT.get() is None
    with factory() as db:
        credential=db.get(MfaCredential,actor['id'])
        assert credential.last_counter==int(arrival.timestamp())//30
        assert len(db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id==actor['id'],MfaRecoveryCode.used_at.is_(None))).all())==7
    seen=[];request=client.raw.request
    def business(method,url,**kwargs):
        seen.append((str(url),service.instant is original,helper._AUTHENTICATION_INSTANT.get() is None))
        return request(method,url,**kwargs)
    monkeypatch.setattr(client.raw,'request',business)
    result=client.post('/api/gym/team/invite',json={'email':'clock-contract-member@example.invalid','nombre':'Clock contract','role':'viewer'})
    assert result.status_code==200
    assert [row[0] for row in seen]==['/api/auth/mfa/step-up','/api/gym/team/invite']
    assert all(row[1] and row[2] for row in seen)
    with factory() as db:
        actions=db.scalars(select(MfaAuthorization).where(MfaAuthorization.user_id==actor['id'],MfaAuthorization.purpose=='action')).all()
        assert len(actions)==1 and actions[0].consumed_at is not None


def test_wrong_real_otp_is_not_retried_or_accepted_and_clock_restores(team_case,monkeypatch):
    from tests import mfa31_contract_client as helper
    from web import auth
    from web.database.models import Usuario,UserRole,MfaCredential,MfaRecoveryCode
    from web.services import mfa_service as service
    from web.services.mfa_crypto import totp
    client,factory,_,_=team_case;identity='clock-'+uuid.uuid4().hex[:24]
    with factory() as db:
        db.add(Usuario(id=identity,email=identity+'@example.invalid',nombre='Clock test',tipo='gym',role=UserRole.OWNER,
            password_hash=auth.hash_password(client.password),activo=True));db.commit()
    subject=helper.MfaContractClient(client.raw,{'id':identity},factory,client.password)
    original_clock=service.instant;post=client.raw.post;state={};attempts=[]
    def invalid_otp(url,**kwargs):
        if str(url)=='/api/auth/mfa/enroll/confirm':
            counter=int(service.instant().timestamp())//30
            forbidden={totp(state['seed'],counter+offset) for offset in (-1,0,1)}
            bad=next(str(number).zfill(6) for number in range(4) if str(number).zfill(6) not in forbidden)
            kwargs['json']={**kwargs['json'],'code':bad}
            response=post(url,**kwargs);attempts.append(response.status_code);return response
        response=post(url,**kwargs)
        if str(url)=='/api/auth/mfa/enroll':state['seed']=base64.b32decode(response.json()['secret'])
        return response
    monkeypatch.setattr(client.raw,'post',invalid_otp)
    try:
        with pytest.raises(AssertionError,match='fixture TOTP confirmation: HTTP 400, expected 200'):subject.authenticate()
    finally:state.clear()
    assert attempts==[400] and subject._sessions=={} and subject._active is None
    assert service.instant is original_clock and helper._AUTHENTICATION_INSTANT.get() is None
    with factory() as db:
        assert db.get(MfaCredential,identity).enabled_at is None
        assert db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id==identity)).all()==[]


def test_unrelated_thread_real_reauthentication_keeps_live_clock(team_case,monkeypatch):
    from tests import mfa31_contract_client as helper
    from web.database.models import MfaAuthorization
    from web.services import mfa_service as service
    from web.services.mfa_crypto import opaque_digest
    client,factory,actor,_=team_case;original=service.instant;fixed=original()-timedelta(minutes=2);first=[True]
    def source(supplied=None):
        if supplied is None and first[0]:first[0]=False;return original(fixed)
        return original(supplied)
    monkeypatch.setattr(service,'instant',source)
    with helper._authentication_clock() as captured:
        assert captured==fixed and service.instant()==fixed
        with ThreadPoolExecutor(max_workers=1) as pool:
            response=pool.submit(client.raw.post,'/api/auth/mfa/reauth',json={'password':client.password}).result(timeout=10)
        assert response.status_code==200
        key=opaque_digest('reauth',response.json()['reauthentication_token'])
        with factory() as db:
            row=db.get(MfaAuthorization,key)
            assert row.user_id==actor['id'] and service.aware(row.created_at)>fixed+timedelta(seconds=60)
    assert service.instant is source and helper._AUTHENTICATION_INSTANT.get() is None


def test_explicit_now_uses_original_validator_and_exception_restores_exact_clock():
    from tests import mfa31_contract_client as helper
    from web.services import mfa_service as service
    original=service.instant;explicit=original()-timedelta(seconds=5)
    with pytest.raises(RuntimeError,match='synthetic clock body'):
        with helper._authentication_clock() as observed:
            assert service.instant()==observed
            assert service.instant(explicit)==explicit
            with pytest.raises(ValueError):service.instant('invalid-clock')
            raise RuntimeError('synthetic clock body')
    assert service.instant is original and helper._AUTHENTICATION_INSTANT.get() is None


def test_other_owner_replacement_is_detected_without_overwriting_it(monkeypatch):
    from tests import mfa31_contract_client as helper
    from web.services import mfa_service as service
    original=service.instant
    def replacement(supplied=None):return original(supplied)
    with monkeypatch.context() as cleanup:
        cleanup.setattr(service,'instant',original)
        with pytest.raises(RuntimeError,match='fixture clock ownership changed'):
            with helper._authentication_clock():service.instant=replacement
        assert service.instant is replacement
        assert helper._AUTHENTICATION_INSTANT.get() is None
    assert service.instant is original
