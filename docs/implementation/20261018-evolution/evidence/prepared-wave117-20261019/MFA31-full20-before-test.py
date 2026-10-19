"""Independent combined-boundary MFA probes. Never print or persist credentials."""
import base64,json,uuid
from datetime import timedelta
from pathlib import Path
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from conftest import database_schema,isolated_database,test_gym_user
from tests.test_mfa31_http import mfa_client,enroll,authenticate

ACTION={'method':'POST','path':'/api/billing/portal','body':{'return_url':'/dashboard'}}

def enroll_login(fixture):
    client,actor,clock=fixture
    started,kit=enroll(client,clock)
    pair,_=authenticate(client,actor,clock,recovery=kit['recovery_codes'][0])
    return client,actor,clock,started,kit,pair

def assert_opaque(response,known=()):
    assert set(response.json())=={'detail'}
    assert isinstance(response.json()['detail'],dict)
    assert set(response.json()['detail'])=={'code','message'}
    for value in known:assert value not in response.text
    assert response.headers['referrer-policy']=='no-referrer'
    assert response.headers['cache-control']=='no-store'

def rt_count(actor):
    from web.database.engine import get_engine
    from web.database.models import RefreshToken
    with Session(get_engine()) as db:return db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id==actor['id']))

def test_primary_challenge_tamper_expiry_never_mints_session_until_exact_factor(mfa_client):
    client,actor,clock=mfa_client;started,kit=enroll(client,clock);before=rt_count(actor)
    reply=client.post('/api/auth/login',json={'email':actor['email'],'password':'test123'})
    assert reply.status_code==202
    assert set(reply.json())=={'mfa_required','challenge','expires_at','methods'}
    assert rt_count(actor)==before
    challenge=reply.json()['challenge'];mutated=challenge[:-1]+('A' if challenge[-1]!='A' else 'B')
    for proof in [mutated,'A'*43]:
        denied=client.post('/api/auth/mfa/login/verify',json={'challenge':proof,'recovery_code':kit['recovery_codes'][0]})
        assert denied.status_code==400;assert_opaque(denied,[challenge,started['secret'],*kit['recovery_codes']])
        assert rt_count(actor)==before
    clock[0]+=timedelta(seconds=300)
    expired=client.post('/api/auth/mfa/login/verify',json={'challenge':challenge,'recovery_code':kit['recovery_codes'][0]})
    assert expired.status_code==400;assert_opaque(expired,[challenge]);assert rt_count(actor)==before
    pair,_=authenticate(client,actor,clock,recovery=kit['recovery_codes'][0])
    assert rt_count(actor)==before+1 and 'token'in pair and 'refresh_token'in pair

def test_factor_one_use_is_global_across_login_stepup_and_replacement(mfa_client):
    from web.services.mfa_crypto import totp
    client,actor,clock=mfa_client;started,kit=enroll(client,clock);clock[0]+=timedelta(seconds=31)
    seed=base64.b32decode(started['secret']);pair,_=authenticate(client,actor,clock,seed=seed)
    code=totp(seed,int(clock[0].timestamp())//30)
    repeated=client.post('/api/auth/mfa/step-up',json={**ACTION,'code':code})
    assert repeated.status_code==400;assert_opaque(repeated,[code,started['secret']])
    assert client.post('/api/auth/mfa/step-up',json=ACTION).status_code==200
    primary=client.post('/api/auth/mfa/reauth',json={'password':'test123'});assert primary.status_code==200
    repeated=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':primary.json()['reauthentication_token'],'code':code})
    assert repeated.status_code==400
    fresh=client.post('/api/auth/mfa/step-up',json={**ACTION,'recovery_code':kit['recovery_codes'][0]})
    assert fresh.status_code==200
    challenge=client.post('/api/auth/login',json={'email':actor['email'],'password':'test123'});assert challenge.status_code==202
    repeated=client.post('/api/auth/mfa/login/verify',json={'challenge':challenge.json()['challenge'],'recovery_code':kit['recovery_codes'][0]})
    assert repeated.status_code==400
    assert client.get('/api/auth/mfa/status').json()['recovery_codes_remaining']==7

def test_proof_purposes_actor_and_access_are_distinct_even_with_valid_other_factor(mfa_client,monkeypatch):
    from web.auth import crear_access_token,identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole
    client,actor,clock,started,kit,pair=enroll_login(mfa_client)
    primary=client.post('/api/auth/mfa/reauth',json={'password':'test123'}).json()['reauthentication_token']
    grant=client.post('/api/auth/mfa/step-up',json=ACTION).json()['grant']
    challenge=client.post('/api/auth/login',json={'email':actor['email'],'password':'test123'}).json()['challenge']
    for proof in [primary,grant]:
        denied=client.post('/api/auth/mfa/login/verify',json={'challenge':proof,'recovery_code':kit['recovery_codes'][1]})
        assert denied.status_code==400;assert_opaque(denied,[proof])
    for proof in [grant,challenge]:
        denied=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':proof,'recovery_code':kit['recovery_codes'][1]})
        assert denied.status_code==400
    other_id=str(uuid.uuid4())
    with Session(get_engine()) as db:
        original=db.get(Usuario,actor['id']);other=Usuario(id=other_id,email=other_id+'@example.invalid',nombre='Synthetic B',password_hash=original.password_hash,tipo='gym',role=UserRole.OWNER,activo=True,session_version=0)
        db.add(other);db.commit();other_actor={'id':other_id,'email':other.email};other_bearer=crear_access_token(identity_from_user(other,db))
    client.headers['Authorization']='Bearer '+other_bearer
    _,other_kit=enroll(client,clock);other_pair,_=authenticate(client,other_actor,clock,recovery=other_kit['recovery_codes'][0])
    denied=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':primary,'recovery_code':other_kit['recovery_codes'][1]});assert denied.status_code==400
    denied=client.post('/api/billing/portal',json=ACTION['body'],headers={'X-MFA-Grant':grant});assert denied.status_code==400
    denied=client.post('/api/auth/mfa/login/verify',json={'challenge':challenge,'recovery_code':other_kit['recovery_codes'][1]});assert denied.status_code==400
    assert client.get('/api/auth/mfa/status').json()['recovery_codes_remaining']==7
    client.headers['Authorization']='Bearer '+pair['token']
    # Failed foreign use did not consume A's own unused recovery evidence.
    good=client.post('/api/auth/mfa/step-up',json={**ACTION,'recovery_code':kit['recovery_codes'][1]});assert good.status_code==200

def test_consumed_witness_never_slides_or_crosses_a_refresh_access(mfa_client,monkeypatch):
    from web.services import stripe_service
    from web.database.engine import get_engine
    from web.database.models import MfaAuthorization
    from web.auth import _decode_token
    client,actor,clock,started,kit,pair=enroll_login(mfa_client)
    monkeypatch.setattr(stripe_service,'create_portal_session',lambda **kwargs:{'url':'https://provider.example.invalid/synthetic'})
    clock[0]+=timedelta(seconds=301);original_factor=clock[0]
    first=client.post('/api/auth/mfa/step-up',json={**ACTION,'recovery_code':kit['recovery_codes'][1]});assert first.status_code==200
    assert client.post('/api/billing/portal',json=ACTION['body'],headers={'X-MFA-Grant':first.json()['grant']}).status_code==200
    clock[0]+=timedelta(seconds=299)
    second=client.post('/api/auth/mfa/step-up',json=ACTION);assert second.status_code==200
    assert second.json()['expires_at']==first.json()['expires_at']
    refreshed=client.post('/api/auth/refresh',json={'refresh_token':pair['refresh_token']});assert refreshed.status_code==200
    assert _decode_token(refreshed.json()['token'])['mfa_at']==_decode_token(pair['token'])['mfa_at']
    client.headers['Authorization']='Bearer '+refreshed.json()['token']
    assert client.post('/api/auth/mfa/step-up',json=ACTION).status_code==403
    assert client.post('/api/auth/mfa/step-up',json={**ACTION,'recovery_code':kit['recovery_codes'][2]}).status_code==200
    client.headers['Authorization']='Bearer '+pair['token']
    clock[0]+=timedelta(seconds=1)
    assert client.post('/api/auth/mfa/step-up',json=ACTION).status_code==403
    assert client.post('/api/billing/portal',json=ACTION['body'],headers={'X-MFA-Grant':second.json()['grant']}).status_code==400
    with Session(get_engine()) as db:
        values=db.scalars(select(MfaAuthorization.factor_verified_at).where(MfaAuthorization.user_id==actor['id'],MfaAuthorization.purpose=='action').order_by(MfaAuthorization.created_at)).all()
        assert values[0].replace(tzinfo=original_factor.tzinfo)==original_factor
        assert values[1].replace(tzinfo=original_factor.tzinfo)==original_factor
        assert values[2].replace(tzinfo=original_factor.tzinfo)==original_factor+timedelta(seconds=299)

@pytest.mark.parametrize('after_real_commit',[False,True])
def test_login_commit_uncertainty_never_returns_pair_and_has_no_premature_reuse(mfa_client,monkeypatch,caplog,after_real_commit):
    from web.database.models import RefreshToken
    client,actor,clock=mfa_client;started,kit=enroll(client,clock)
    primary=client.post('/api/auth/login',json={'email':actor['email'],'password':'test123'});assert primary.status_code==202
    challenge=primary.json()['challenge'];before=rt_count(actor);actual=Session.commit;triggered=False
    def uncertain(db):
        nonlocal triggered
        eligible=not triggered and any(isinstance(row,RefreshToken) and row.user_id==actor['id'] for row in db.new)
        if eligible:
            triggered=True
            if after_real_commit:actual(db)
            raise RuntimeError('synthetic-private-commit-parameter@example.invalid')
        return actual(db)
    body={'challenge':challenge,'recovery_code':kit['recovery_codes'][0]}
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',uncertain)
        response=client.post('/api/auth/mfa/login/verify',json=body)
    assert triggered and response.status_code==503
    assert response.json()['detail']['code']=='mfa_unconfirmed'
    assert_opaque(response,[challenge,started['secret'],*kit['recovery_codes']])
    assert 'synthetic-private-commit-parameter@example.invalid' not in caplog.text
    assert challenge not in caplog.text and started['secret'] not in caplog.text
    assert rt_count(actor)==before+int(after_real_commit)
    repeated=client.post('/api/auth/mfa/login/verify',json=body)
    assert repeated.status_code==(400 if after_real_commit else 200)
    assert rt_count(actor)==before+1

def test_missing_encryption_key_cannot_turn_enabled_factor_into_primary_login(mfa_client,monkeypatch):
    from web.settings import get_settings
    client,actor,clock=mfa_client;started,kit=enroll(client,clock);before=rt_count(actor)
    with monkeypatch.context() as patch:
        patch.setattr(get_settings(),'MFA_ENCRYPTION_KEY','')
        response=client.post('/api/auth/login',json={'email':actor['email'],'password':'test123'})
        assert response.status_code==503 and response.json()['detail']['code']=='mfa_service_unavailable'
        assert_opaque(response,[started['secret']]);assert rt_count(actor)==before
    pair,_=authenticate(client,actor,clock,recovery=kit['recovery_codes'][0])
    assert pair.get('token') and rt_count(actor)==before+1

@pytest.mark.parametrize('revocation',['logout','password-reset'])
def test_revocation_invalidates_grants_challenges_proofs_and_refresh_but_keeps_factor(mfa_client,monkeypatch,revocation):
    from web.database.engine import get_engine
    from web.services import password_recovery
    from urllib.parse import urlsplit,parse_qs
    client,actor,clock,started,kit,pair=enroll_login(mfa_client)
    proof=client.post('/api/auth/mfa/reauth',json={'password':'test123'}).json()['reauthentication_token']
    grant=client.post('/api/auth/mfa/step-up',json=ACTION).json()['grant']
    challenge=client.post('/api/auth/login',json={'email':actor['email'],'password':'test123'}).json()['challenge']
    password='test123'
    if revocation=='logout':
        result=client.post('/api/auth/logout');assert result.status_code==200 and result.json()['success'] is True
    else:
        messages=[]
        password_recovery.issue_request(actor['email'],'https://example.invalid',sender=lambda *args:messages.append(args) or True)
        token=parse_qs(urlsplit(messages[0][2]).fragment)['token'][0];password='SyntheticNewPassword42!'
        with Session(get_engine()) as db:password_recovery.consume(db,token,password)
    assert client.post('/api/auth/refresh',json={'refresh_token':pair['refresh_token']}).status_code==401
    assert client.get('/api/auth/mfa/status').status_code==401
    old=client.post('/api/auth/mfa/login/verify',json={'challenge':challenge,'recovery_code':kit['recovery_codes'][1]});assert old.status_code==401
    primary=client.post('/api/auth/login',json={'email':actor['email'],'password':password});assert primary.status_code==202 and 'token'not in primary.json()
    verified=client.post('/api/auth/mfa/login/verify',json={'challenge':primary.json()['challenge'],'recovery_code':kit['recovery_codes'][1]});assert verified.status_code==200
    client.headers['Authorization']='Bearer '+verified.json()['token']
    assert client.get('/api/auth/mfa/status').json()['enabled'] is True
    assert client.post('/api/billing/portal',json=ACTION['body'],headers={'X-MFA-Grant':grant}).status_code==400
    assert client.post('/api/auth/mfa/enroll',json={'reauthentication_token':proof,'recovery_code':kit['recovery_codes'][2]}).status_code==400

def test_google_auth_time_not_iat_is_fresh_primary_and_expiry_is_not_extended(mfa_client,monkeypatch):
    import httpx
    from web.settings import get_settings
    client,actor,clock,started,kit,pair=enroll_login(mfa_client)
    monkeypatch.setattr(get_settings(),'GOOGLE_CLIENT_ID','synthetic-google-client')
    original=httpx.AsyncClient;info={};ports=[]
    def handler(request):
        assert request.url.host=='oauth2.googleapis.com' and request.url.params['id_token']=='synthetic-provider-credential'
        ports.append(True);return httpx.Response(200,json=info)
    monkeypatch.setattr(httpx,'AsyncClient',lambda *args,**kwargs:original(*args,transport=httpx.MockTransport(handler),**kwargs))
    base={'aud':'synthetic-google-client','email_verified':'true','email':actor['email'],'amr':['pwd']}
    for value in [None,int(clock[0].timestamp())-300,int(clock[0].timestamp())+1]:
        info.clear();info.update({**base,'iat':int(clock[0].timestamp())})
        if value is not None:info['auth_time']=value
        response=client.post('/api/auth/mfa/reauth',json={'google_credential':'synthetic-provider-credential'})
        assert response.status_code==403 and response.json()['detail']['code']=='mfa_primary_reauthentication_required'
    info.clear();info.update({**base,'auth_time':int(clock[0].timestamp())-299,'iat':int(clock[0].timestamp())-600})
    primary=client.post('/api/auth/mfa/reauth',json={'google_credential':'synthetic-provider-credential'});assert primary.status_code==200
    # Primary time has one second left; issuing proof must not create five new minutes.
    clock[0]+=timedelta(seconds=2)
    denied=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':primary.json()['reauthentication_token'],'recovery_code':kit['recovery_codes'][1]});assert denied.status_code==400
    info.clear();info.update({**base,'email':'different-synthetic@example.invalid','auth_time':int(clock[0].timestamp())})
    wrong=client.post('/api/auth/mfa/reauth',json={'google_credential':'synthetic-provider-credential'});assert wrong.status_code==400
    assert len(ports)==5
