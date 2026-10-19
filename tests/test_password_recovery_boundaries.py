import asyncio
from threading import Event
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from tests.test_account_recovery_contract_before import recovery_case


def test_public_form_csp_has_no_third_party_or_unsafe_sources(recovery_case):
    client,_,_=recovery_case
    response=client.get('/auth/reset-password')
    assert response.status_code==200
    policy=response.headers['content-security-policy']
    assert 'https:' not in policy and "'unsafe-" not in policy,policy
    assert "script-src 'self'" in policy and "'nonce-" in policy
    assert "frame-ancestors 'none'" in policy and "base-uri 'none'" in policy
    assert response.headers['referrer-policy']=='no-referrer'
    assert response.headers['cache-control']=='no-store'
    ordinary=client.get('/login-usuario').headers['content-security-policy']
    assert 'https://accounts.google.com' in ordinary
    for path in ('/login-usuario','/login-gym'):
        assert 'href="/auth/reset-password"' in client.get(path).text
    for suffix,payload in [('request',{'email':'invalid'}),('confirm',{
            'token':'a'*43,'new_password':'SyntheticPassword123','confirm_password':'SyntheticPassword123'})]:
        rejected=client.post('/api/auth/password-reset/'+suffix,json=payload)
        assert rejected.status_code in {400,422}
        assert rejected.headers['cache-control']=='no-store'
        assert rejected.headers['referrer-policy']=='no-referrer'


def test_body_stops_stream_at_limit_before_parse(monkeypatch):
    from web.routes import password_recovery as routes
    calls=[]
    class Parser:
        def validate_json(self,raw):
            raise AssertionError('Oversized body reached DTO parse')
    monkeypatch.setattr(routes,'TypeAdapter',lambda model:Parser())
    async def receive():
        calls.append(True)
        return {'type':'http.request','body':b'x'*(4096 if len(calls)==1 else 1),'more_body':True}
    request=Request({'type':'http','method':'POST','path':'/',
        'headers':[(b'content-type',b'application/json')]},receive)
    with pytest.raises(HTTPException) as failure:
        asyncio.run(routes.bounded_body(routes.RecoveryRequest)(request))
    assert failure.value.status_code==413 and len(calls)==2


def test_dispatcher_is_bounded_and_does_not_inherit_authenticated_context():
    from web.services.recovery_dispatcher import RecoveryDispatcher
    from web.database.tenant_context import current_tenant,tenant_scope
    entered,release,finished=Event(),Event(),Event()
    observed=[]
    def work():
        try:
            observed.append(current_tenant.get()); entered.set()
            assert release.wait(5)
        finally: finished.set()
    dispatcher=RecoveryDispatcher(workers=1,capacity=1)
    try:
        with tenant_scope('caller-must-not-authorize-mail'):
            assert dispatcher.submit(work)
        assert entered.wait(2) and observed==['']
        assert dispatcher.pending==1 and dispatcher.submit(lambda:None) is False
        release.set(); assert finished.wait(2)
    finally:
        release.set(); dispatcher.close()
    assert dispatcher.submit(lambda:None) is False


@pytest.mark.parametrize('origin',['https://user:secret@example.invalid','https://example.invalid/path',
    'https://example.invalid?token=forbidden','https://example.invalid#forbidden',
    'http://example.invalid','https://example.invalid\\evil','https://example.invalid/%2f',
    'https://example.invalid\n','https://example.invalid:99999'])
def test_only_configured_pure_origin_is_accepted(origin):
    from web.services.password_recovery import public_origin
    with pytest.raises(HTTPException) as failure:
        public_origin(SimpleNamespace(BASE_URL=origin,is_production=True))
    assert failure.value.status_code==503


def test_new_credentials_share_registration_and_invitation_policy():
    from web.account_values import validate_new_password
    from web.routes.team import AcceptInviteRequest
    from web.auth import crear_usuario
    from pydantic import ValidationError
    password='é'*37
    with pytest.raises(ValueError): validate_new_password(password)
    with pytest.raises(ValueError): crear_usuario('byte-policy@example.invalid',password,'Synthetic')
    with pytest.raises(ValidationError): AcceptInviteRequest(token='a'*43,password=password)
    assert validate_new_password('é'*36)=='é'*36


def test_recovery_authority_metadata_never_enters_personal_export():
    from datetime import datetime,timezone
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole
    from web.services.privacy_export import export_personal_data
    with Session(get_engine()) as db:
        db.add(Usuario(id='recovery-export',email='export@example.invalid',nombre='Synthetic',
            password_hash='synthetic',tipo='usuario',role=UserRole.VIEWER,
            password_reset_hash='e'*64,password_reset_expires_at=datetime.now(timezone.utc),
            password_reset_session_version=0))
        db.commit()
        result=export_personal_data(db,'recovery-export')
    assert result['scope']['personal_space'] is True
    assert all('password' not in key and 'reset' not in key and 'session' not in key for key in result['account'])
    assert 'credentials_and_tokens' in result['scope']['excluded_categories']
