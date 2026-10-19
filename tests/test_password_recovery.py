"""Recovery authority, uncertain commits and public-channel invariants."""
from datetime import datetime,timedelta,timezone
import json
from threading import Event
import time
from types import SimpleNamespace
from urllib.parse import urlsplit,parse_qs

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from tests.test_account_recovery_contract_before import recovery_case

OLD='SyntheticOldPassword123'
NEW='SyntheticNewPassword456'
OWNER='recovery-before-owner'


def wait_idle(client):
    deadline=time.monotonic()+8
    dispatcher=client.app.state.recovery_dispatcher
    while dispatcher.pending and time.monotonic()<deadline:
        time.sleep(.01)
    assert dispatcher.pending==0


@pytest.fixture
def recovery_http(recovery_case,monkeypatch):
    from web import auth
    from web.database.models import Usuario,UserRole
    from web.services import email_service
    client,engine,factory=recovery_case
    messages=[]
    def capture(email,name,link):
        messages.append({'email':email,'name':name,'link':link})
        return True
    monkeypatch.setattr(email_service,'send_password_reset',capture)
    monkeypatch.setattr(email_service,'send_password_changed',lambda *args:True)
    with Session(engine) as db:
        db.get(Usuario,OWNER).password_hash=auth.hash_password(OLD)
        for name,changes in [('other',{}),('inactive',{'activo':False}),
                ('deleted',{'deleted_at':datetime.now(timezone.utc)}),
                ('pending',{'activo':False,'invitation_token':'b'*64,'team_gym_id':OWNER})]:
            db.add(Usuario(id='recovery-'+name,email='recovery-'+name+'@example.invalid',nombre='Synthetic',
                tipo='usuario',role=UserRole.VIEWER,password_hash=auth.hash_password(OLD),**changes))
        db.commit()
    yield SimpleNamespace(client=client,engine=engine,messages=messages,factory=factory)
    wait_idle(client)


def issued(case,email='recovery-before@example.invalid'):
    response=case.client.post('/api/auth/password-reset/request',json={'email':email})
    assert response.status_code==202,response.text
    wait_idle(case.client)
    message=case.messages[-1]
    parsed=urlsplit(message['link'])
    assert parsed.scheme=='https' and parsed.netloc=='recovery.example.invalid' and not parsed.query
    return parse_qs(parsed.fragment)['token'][0]


def confirm(case,token,password=NEW,**kwargs):
    return case.client.post('/api/auth/password-reset/confirm',json={
        'token':token,'new_password':password,'confirm_password':password},**kwargs)


def test_full_cycle_keeps_authority_until_verified_then_revokes_own_sessions(recovery_http):
    from web import auth
    from web.database.models import Usuario,Cliente,RefreshToken,AuthAuditLog
    from web.services.password_recovery import digest
    case=recovery_http
    with Session(case.engine) as db:
        principal=auth.identity_from_user(db.get(Usuario,OWNER),db)
        other=auth.identity_from_user(db.get(Usuario,'recovery-other'),db)
    old_pair=auth.crear_token_pair(principal)
    other_pair=auth.crear_token_pair(other)
    token=issued(case,' RECOVERY-BEFORE@example.invalid ')
    with Session(case.engine) as db:
        user=db.get(Usuario,OWNER)
        assert user.password_reset_hash==digest(token)!=token
        assert user.password_reset_session_version==user.session_version==7
        assert auth.verify_password(OLD,user.password_hash)
        assert user.role.value=='owner' and user.tipo=='gym' and user.team_gym_id is None
    assert auth.verificar_token(old_pair['access_token'])
    response=confirm(case,token)
    assert response.status_code==200,response.text
    assert set(response.json())=={'code','message'} and response.json()['code']=='password_reset_complete'
    # Existing CSRF bootstrap is not an authentication/session cookie.
    assert set(response.cookies.keys()).issubset({'_csrf'}) and token not in response.text
    assert case.client.get('/api/auth/me').status_code==401
    with Session(case.engine) as db:
        user=db.get(Usuario,OWNER)
        assert user.session_version==8 and auth.verify_password(NEW,user.password_hash)
        assert user.password_reset_hash is user.password_reset_expires_at is user.password_reset_session_version is None
        assert user.role.value=='owner' and user.tipo=='gym' and user.team_gym_id is None
        assert db.query(Cliente).filter_by(gym_id=OWNER).count()==1
        assert db.query(RefreshToken).filter_by(user_id=OWNER,revoked=False).count()==0
        assert db.query(AuthAuditLog).filter_by(user_id=OWNER,event_type='password_reset_complete').count()==1
    assert auth.verificar_token(old_pair['access_token']) is None
    assert auth.verificar_refresh_token(old_pair['refresh_token']) is None
    assert auth.verificar_token(other_pair['access_token'])
    assert confirm(case,token).status_code==400
    assert case.client.post('/api/auth/login',json={'email':'recovery-before@example.invalid','password':OLD}).status_code==401
    assert case.client.post('/api/auth/login',json={'email':'recovery-before@example.invalid','password':NEW}).status_code==200


def test_unknown_and_ineligible_requests_share_response_without_mail_or_activation(recovery_http):
    from web.database.models import Usuario
    case=recovery_http
    results=[]
    for kind in ('unknown','inactive','deleted','pending'):
        response=case.client.post('/api/auth/password-reset/request',json={'email':'recovery-'+kind+'@example.invalid'})
        assert response.status_code==202,response.text
        results.append(response.json())
    wait_idle(case.client)
    assert all(result==results[0] for result in results) and case.messages==[]
    with Session(case.engine) as db:
        assert db.query(Usuario).filter(Usuario.password_reset_hash.isnot(None)).count()==0
        assert db.get(Usuario,'recovery-inactive').activo is False
        assert db.get(Usuario,'recovery-pending').invitation_token=='b'*64


@pytest.mark.parametrize('outcome',['false','exception'])
def test_transport_failure_preserves_uniform202_and_valid_digest_without_private_logs(recovery_http,monkeypatch,caplog,outcome):
    from web.services import email_service
    from web.database.models import Usuario
    case=recovery_http
    private=[]
    def sender(email,name,link):
        private.extend((email,link,parse_qs(urlsplit(link).fragment)['token'][0]))
        if outcome=='exception':
            raise RuntimeError('Private transport '+link)
        return False
    monkeypatch.setattr(email_service,'send_password_reset',sender)
    response=case.client.post('/api/auth/password-reset/request',json={'email':'recovery-before@example.invalid'})
    assert response.status_code==202
    wait_idle(case.client)
    assert private and all(value not in response.text+caplog.text for value in private)
    with Session(case.engine) as db:
        row=db.get(Usuario,OWNER)
        assert row.password_reset_hash and row.session_version==7


@pytest.mark.parametrize('reason',['missing_key','bad_origin'])
def test_disabled_configuration_is_uniform_before_lookup_or_admission(recovery_http,monkeypatch,reason):
    from web.settings import get_settings
    case=recovery_http
    if reason=='missing_key': monkeypatch.setattr(get_settings(),'RESEND_API_KEY','')
    else: monkeypatch.setattr(get_settings(),'BASE_URL','https://good.invalid@evil.invalid/path#token')
    for email in ('recovery-before@example.invalid','unknown@example.invalid'):
        response=case.client.post('/api/auth/password-reset/request',json={'email':email})
        assert response.status_code==503
        assert response.json()['detail']['code']=='password_reset_service_unavailable'
    assert case.client.app.state.recovery_dispatcher.pending==0 and case.messages==[]


def test_completion_does_not_require_mail_provider_to_remain_configured(recovery_http,monkeypatch):
    from web.settings import get_settings
    case=recovery_http
    token=issued(case)
    monkeypatch.setattr(get_settings(),'RESEND_API_KEY','')
    assert confirm(case,token).status_code==200


@pytest.mark.parametrize('change',['expired','version','inactive','deleted','invitation'])
def test_confirm_revalidates_current_account_and_uses_same_unavailable_error(recovery_http,change):
    from web.database.models import Usuario
    case=recovery_http
    token=issued(case)
    with Session(case.engine) as db:
        row=db.get(Usuario,OWNER)
        if change=='expired': row.password_reset_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        elif change=='version': row.session_version+=1
        elif change=='inactive': row.activo=False
        elif change=='deleted': row.deleted_at=datetime.now(timezone.utc)
        else: row.invitation_token='c'*64
        db.commit()
    response=confirm(case,token)
    assert response.status_code==400
    assert response.json()['detail']['code']=='password_reset_unavailable'
    with Session(case.engine) as db:
        from web.auth import verify_password
        assert verify_password(OLD,db.get(Usuario,OWNER).password_hash)


def test_new_request_rotates_link_but_does_not_revoke_existing_login(recovery_http):
    from web import auth
    from web.database.models import Usuario
    case=recovery_http
    with Session(case.engine) as db:
        pair=auth.crear_token_pair(auth.identity_from_user(db.get(Usuario,OWNER),db))
    first,second=issued(case),issued(case)
    assert first!=second
    assert confirm(case,first).status_code==400
    assert auth.verificar_token(pair['access_token'])
    assert confirm(case,second).status_code==200


@pytest.mark.parametrize('ack_lost',[False,True])
def test_consume_real_commit_uncertainty_is_visible_and_never_compensates(recovery_http,monkeypatch,caplog,ack_lost):
    from sqlalchemy.exc import StatementError
    from web.database.models import AuthAuditLog,Usuario,RefreshToken
    from web import auth
    case=recovery_http
    token=issued(case)
    original=Session.commit
    def uncertain(db):
        is_consume=any(isinstance(row,AuthAuditLog) and row.event_type=='password_reset_complete' for row in db.new)
        if is_consume:
            if ack_lost: original(db)
            raise StatementError('private-confirm-statement','private-confirm-sql',{'password':NEW,'token':token},RuntimeError())
        return original(db)
    monkeypatch.setattr(Session,'commit',uncertain)
    response=confirm(case,token)
    assert response.status_code==503,response.text
    assert response.json()['detail']['code']=='password_reset_unconfirmed'
    assert all(value not in response.text+caplog.text for value in (NEW,token,'private-confirm-sql','private-confirm-statement'))
    with Session(case.engine) as db:
        row=db.get(Usuario,OWNER)
        assert row.session_version==7+int(ack_lost)
        assert auth.verify_password(NEW if ack_lost else OLD,row.password_hash)
        assert (row.password_reset_hash is None)==ack_lost
        assert db.query(AuthAuditLog).filter_by(event_type='password_reset_complete').count()==int(ack_lost)
        assert db.query(RefreshToken).filter_by(user_id=OWNER,revoked=False).count()==(0 if ack_lost else 1)


def test_issue_lost_commit_ack_does_not_send_or_undo_the_persisted_digest(recovery_http,monkeypatch,caplog):
    from sqlalchemy.exc import StatementError
    from web.database.models import AuthAuditLog,Usuario
    case=recovery_http
    original=Session.commit
    def uncertain(db):
        issue=any(isinstance(row,AuthAuditLog) and row.event_type=='password_reset_request' for row in db.new)
        result=original(db)
        if issue: raise StatementError('private-issue','private-issue-sql',{'email':'private-issue-email'},RuntimeError())
        return result
    monkeypatch.setattr(Session,'commit',uncertain)
    response=case.client.post('/api/auth/password-reset/request',json={'email':'recovery-before@example.invalid'})
    assert response.status_code==202
    wait_idle(case.client)
    assert case.messages==[] and 'private-issue' not in caplog.text
    with Session(case.engine) as db:
        row=db.get(Usuario,OWNER)
        assert row.password_reset_hash and row.session_version==7


def test_request_returns_complete_response_while_sdk_is_blocked(recovery_http,monkeypatch):
    from web.services import email_service
    case=recovery_http
    entered,release=Event(),Event()
    def blocked(*args):
        entered.set()
        assert release.wait(5)
        return True
    monkeypatch.setattr(email_service,'send_password_reset',blocked)
    try:
        response=case.client.post('/api/auth/password-reset/request',json={'email':'recovery-before@example.invalid'})
        assert response.status_code==202 and entered.wait(3)
        assert case.client.get('/health').status_code==200
        assert not release.is_set() and case.client.app.state.recovery_dispatcher.pending==1
    finally:
        release.set()


def test_rate_failure_prevents_any_work_and_keys_never_contain_email(recovery_http,monkeypatch):
    from web import rate_limiter_redis
    case=recovery_http
    keys=[]
    async def unavailable(key,*args,**kwargs):
        keys.append(key)
        raise HTTPException(503,{'code':'rate_limit_backend_unavailable'})
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',unavailable)
    response=case.client.post('/api/auth/password-reset/request',json={'email':'recovery-before@example.invalid'})
    assert response.status_code==503 and case.messages==[]
    assert all('example.invalid' not in key and 'recovery-before' not in key for key in keys)


@pytest.mark.parametrize('payload',[
    {'email':'recovery-before@example.invalid','user_id':OWNER},
    {'token':'a'*43,'new_password':'é'*37,'confirm_password':'é'*37},
    {'token':'a'*43,'new_password':NEW,'confirm_password':'different-password'},
])
def test_mass_assignment_password_bytes_and_confirmation_are_rejected(recovery_http,payload):
    case=recovery_http
    suffix='request' if 'email' in payload else 'confirm'
    response=case.client.post('/api/auth/password-reset/'+suffix,json=payload)
    assert response.status_code==422
    assert NEW not in response.text
