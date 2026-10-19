"""R16 proposed contract baseline: actual factories, offline synthetic accounts.

These failures establish missing capabilities, not account enumeration or an
observed production incident. Product files remain exactly at423296f.
"""
import importlib
import json
from pathlib import Path
import time
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


@pytest.fixture(params=['web.main_web','api.app'])
def recovery_case(request,monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole,Cliente,RefreshToken
    from web.services import email_service
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(),'RESEND_API_KEY','synthetic-no-provider-use')
    monkeypatch.setattr(get_settings(),'BASE_URL','https://recovery.example.invalid')
    from web.rate_limiter import _buckets,_bucket_windows
    for key in list(_buckets):
        if key.startswith('rl:recovery-v1:'):
            _buckets.pop(key,None); _bucket_windows.pop(key,None)
    def forbidden(*args,**kwargs):
        raise AssertionError('Baseline cannot dispatch email')
    monkeypatch.setattr(email_service,'_send',forbidden)
    application=importlib.import_module(request.param).create_app()
    with Session(get_engine()) as db:
        db.add(Usuario(id='recovery-before-owner',email='recovery-before@example.invalid',
            nombre='Synthetic',password_hash='synthetic-hash-not-a-credential',
            tipo='gym',role=UserRole.OWNER,activo=True,session_version=7))
        db.flush()
        db.add(Cliente(id_cliente='recovery-before-client',gym_id='recovery-before-owner',nombre='Synthetic'))
        db.add(RefreshToken(jti=str(uuid.uuid4()),user_id='recovery-before-owner',created_at=time.time(),
            expires_at=time.time()+3600,revoked=False))
        db.commit()
    with TestClient(application,raise_server_exceptions=False) as client:
        yield client,get_engine(),request.param
        deadline=time.monotonic()+5
        while application.state.recovery_dispatcher.pending and time.monotonic()<deadline:
            time.sleep(.01)
        assert application.state.recovery_dispatcher.pending==0


def _observation(tmp_path,name,value):
    (Path(tmp_path)/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def test_public_recovery_request_is_uniform_and_keeps_existing_authority(recovery_case,tmp_path):
    from web.database.models import Usuario,Cliente,RefreshToken
    client,engine,factory=recovery_case
    with Session(engine) as db:
        user=db.get(Usuario,'recovery-before-owner')
        before=(user.password_hash,user.role,user.tipo,user.team_gym_id,user.session_version,user.activo)
    known=client.post('/api/auth/password-reset/request',json={'email':'recovery-before@example.invalid'})
    unknown=client.post('/api/auth/password-reset/request',json={'email':'unknown-recovery-before@example.invalid'})
    with Session(engine) as db:
        user=db.get(Usuario,'recovery-before-owner')
        after=(user.password_hash,user.role,user.tipo,user.team_gym_id,user.session_version,user.activo)
        assert after==before
        assert db.query(Cliente).filter_by(gym_id=user.id).count()==1
        assert db.query(RefreshToken).filter_by(user_id=user.id,revoked=False).count()==1
    _observation(tmp_path,'request-before',{'factory':factory,'known_status':known.status_code,
        'unknown_status':unknown.status_code,'same_response':known.json()==unknown.json(),
        'account_authority_and_existing_session_unchanged':after==before})
    assert known.status_code==unknown.status_code==202
    assert known.json()==unknown.json()=={'code':'password_reset_request_received',
        'message':'Si la cuenta puede recuperarse, se intentara enviar un enlace.'}


def test_unavailable_recovery_token_has_generic_public_error(recovery_case,tmp_path):
    client,_,factory=recovery_case
    response=client.post('/api/auth/password-reset/confirm',json={
        'token':'a'*43,'new_password':'SyntheticRecoveryPassword123','confirm_password':'SyntheticRecoveryPassword123'})
    _observation(tmp_path,'confirm-before',{'factory':factory,'status':response.status_code})
    assert response.status_code==400
    assert response.json()['detail']['code']=='password_reset_unavailable'


def test_web_has_readonly_recovery_form_without_bearer_in_request():
    from web.main_web import create_app
    with TestClient(create_app(),raise_server_exceptions=False) as client:
        response=client.get('/auth/reset-password')
    assert response.status_code==200
    assert response.headers['referrer-policy']=='no-referrer'
    assert response.headers['cache-control']=='no-store'
