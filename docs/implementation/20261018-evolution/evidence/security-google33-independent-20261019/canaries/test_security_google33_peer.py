"""Independent33 attacks with real local proofs, RSA JWTs and transport only."""
import asyncio
import base64
from datetime import datetime, timezone
import json
import time
import urllib.request
import uuid

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.test_google33_http import google_db, google_http, PASSWORD


def issue(c, *, fresh=True, **extra):
    if fresh:
        c['google']['sub'] = str(uuid.uuid4().int)
    c['google']['iat'] = c['google']['auth_time']
    return c['client'].post('/api/auth/google/link/start', headers=c['headers'],
        json={'password': PASSWORD, 'google_credential': c['credential'](), **extra})


def confirm(c, intent):
    return c['client'].post('/api/auth/google/link/confirm', headers=c['headers'],
        json={'intent': intent, 'confirm': True})


def login(c, recovery=None):
    reply = c['client'].post('/api/auth/login', json={'email': c['email'], 'password': PASSWORD})
    if recovery is not None:
        assert reply.status_code == 202
        reply = c['client'].post('/api/auth/mfa/login/verify',
            json={'challenge': reply.json()['challenge'], 'recovery_code': recovery})
    assert reply.status_code == 200
    c['headers'] = {'Authorization': 'Bearer ' + reply.json()['token']}
    return reply


def bind(c):
    prepared = issue(c)
    assert prepared.status_code == 200
    assert confirm(c, prepared.json()['intent']).status_code == 200
    login(c)
    state = c['client'].get('/api/auth/google/link/status', headers=c['headers'])
    assert state.status_code == 200 and len(state.json()['items']) == 1
    return state.json()['items'][0]


def factor(c):
    from web.services.mfa_crypto import totp
    client = c['client']
    primary = client.post('/api/auth/mfa/reauth', headers=c['headers'], json={'password': PASSWORD})
    assert primary.status_code == 200
    pending = client.post('/api/auth/mfa/enroll', headers=c['headers'],
        json={'reauthentication_token': primary.json()['reauthentication_token']})
    assert pending.status_code == 200
    ready = client.post('/api/auth/mfa/enroll/confirm', headers=c['headers'],
        json={'enrollment_id': pending.json()['enrollment_id'],
              'code': totp(base64.b32decode(pending.json()['secret']), int(c['clock'][0].timestamp()) // 30)})
    assert ready.status_code == 200
    codes = ready.json()['recovery_codes']
    assert len(codes) == 8
    login(c, codes[0])
    return codes


def test_bound_subject_ignores_another_existing_owners_contact_and_issuer_alias(google_http):
    from web.database.models import Usuario, AuthExternalIdentity
    c = google_http
    bind(c)
    other = uuid.uuid4().hex + '@example.invalid'
    registered = c['client'].post('/api/auth/registro', json={
        'email': other, 'password': PASSWORD, 'nombre': 'Other real owner', 'tipo': 'gym'})
    assert registered.status_code == 200
    c['google'].update(email=other, iss='accounts.google.com')
    response = c['client'].post('/api/auth/google', json={'credential': c['credential'](), 'tipo': 'gym',
        'id': 'untrusted-owner', 'gym_id': 'untrusted-owner'})
    assert response.status_code == 200 and response.json()['role'] == 'viewer'
    me = c['client'].get('/api/auth/me', headers={'Authorization': 'Bearer ' + response.json()['token']})
    assert me.status_code == 200 and me.json()['id'] == c['user'] and me.json()['email'] == c['email']
    with Session(c['admin']) as db:
        assert db.get(Usuario, c['user']).team_gym_id is None
        binding = db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.subject == c['google']['sub']))
        assert binding.issuer == 'https://accounts.google.com' and binding.user_id == c['user']


@pytest.mark.parametrize('state', ['disabled', 'deleted', 'invited', 'parent_off', 'parent_role'])
def test_bound_identity_reloads_persisted_gates_without_recreation(google_http, state):
    from web.database.models import Usuario, UserRole, AuthExternalIdentity
    c = google_http
    bind(c)
    parent = None
    if state.startswith('parent_'):
        other = uuid.uuid4().hex + '@example.invalid'
        made = c['client'].post('/api/auth/registro', json={'email': other, 'password': PASSWORD,
            'nombre': 'Persisted parent gate', 'tipo': 'gym'})
        assert made.status_code == 200
        parent = c['client'].get('/api/auth/me', headers={'Authorization': 'Bearer ' + made.json()['token']}).json()['id']
    with Session(c['admin']) as db:
        before = db.scalar(select(func.count()).select_from(Usuario))
        user = db.get(Usuario, c['user'])
        if state == 'disabled': user.activo = False
        elif state == 'deleted': user.deleted_at = c['clock'][0]
        elif state == 'invited': user.invitation_token = uuid.uuid4().hex
        else:
            user.team_gym_id = parent
            user.role = UserRole.NUTRIOLOGO
            if state == 'parent_off': db.get(Usuario, parent).activo = False
            else: db.get(Usuario, parent).role = UserRole.ADMIN
        db.commit()
    denied = c['client'].post('/api/auth/google', json={'credential': c['credential']()})
    assert denied.status_code == 401 and not {'token', 'refresh_token', 'challenge'} & denied.json().keys()
    with Session(c['admin']) as db:
        assert db.scalar(select(func.count()).select_from(Usuario)) == before
        assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.subject == c['google']['sub'])) == c['user']


def test_foreign_actor_cannot_consume_a_real_intent_and_owner_can_still_confirm(google_http):
    from web.database.models import GoogleLinkIntent, Usuario
    c = google_http
    prepared = issue(c)
    assert prepared.status_code == 200
    other = uuid.uuid4().hex + '@example.invalid'
    made = c['client'].post('/api/auth/registro', json={'email': other, 'password': PASSWORD, 'nombre': 'Other actor'})
    assert made.status_code == 200
    failed = c['client'].post('/api/auth/google/link/confirm', headers={'Authorization': 'Bearer ' + made.json()['token']},
        json={'intent': prepared.json()['intent'], 'confirm': True})
    assert failed.status_code == 409
    with Session(c['admin']) as db:
        row = db.scalar(select(GoogleLinkIntent).where(GoogleLinkIntent.user_id == c['user']))
        assert row.consumed_at is None and db.get(Usuario, c['user']).session_version == 0
    assert confirm(c, prepared.json()['intent']).status_code == 200
    assert confirm(c, prepared.json()['intent']).status_code == 401


@pytest.mark.parametrize('after_commit', [False, True])
def test_start_factor_and_intent_are_atomic_across_before_or_after_ack_fault(google_http, monkeypatch, caplog, after_commit):
    from web.routes import google_link
    from web.database.models import GoogleLinkIntent, MfaRecoveryCode, MfaCredential, AuthAuditLog
    from web.services.mfa_crypto import opaque_digest
    c = google_http
    codes = factor(c)
    class Fault(Session):
        def commit(self):
            if any(isinstance(row, GoogleLinkIntent) for row in self.new):
                if after_commit: super().commit()
                raise RuntimeError('PRIVATE_START_ACK_SENTINEL')
            super().commit()
    monkeypatch.setattr(google_link, 'SessionLocal', sessionmaker(bind=c['engine'], class_=Fault, expire_on_commit=True, autoflush=False))
    result = issue(c, recovery_code=codes[1])
    assert result.status_code == 503 and 'intent' not in result.json()
    assert 'PRIVATE_START_ACK_SENTINEL' not in result.text + caplog.text
    with Session(c['admin']) as db:
        used = db.scalar(select(MfaRecoveryCode.used_at).where(MfaRecoveryCode.code_hash == opaque_digest('recovery', codes[1])))
        intent = db.scalar(select(GoogleLinkIntent).where(GoogleLinkIntent.user_id == c['user']))
        audit = db.scalar(select(AuthAuditLog.id).where(AuthAuditLog.user_id == c['user'], AuthAuditLog.event_type == 'google_link_intent'))
        assert (used is not None) is after_commit and (intent is not None) is after_commit and (audit is not None) is after_commit
        assert db.get(MfaCredential, c['user']).attempts['google_link:start']['count'] == 1
    assert c['engine'].pool.checkedout() == 0


def test_max_minus_one_reaches_max_and_google_still_requires_real_factor(google_http):
    from web.database.models import Usuario, MfaRecoveryCode, GoogleLinkIntent
    c = google_http
    codes = factor(c)
    first = issue(c, recovery_code=codes[1])
    assert first.status_code == 200 and confirm(c, first.json()['intent']).status_code == 200
    original_subject = c['google']['sub']
    with Session(c['admin']) as db:
        db.get(Usuario, c['user']).session_version = 2147483646
        db.commit()
    login(c, codes[2])
    last = issue(c, recovery_code=codes[3])
    assert last.status_code == 200 and confirm(c, last.json()['intent']).status_code == 200
    c['google']['sub'] = original_subject
    primary = c['client'].post('/api/auth/google', json={'credential': c['credential']()})
    assert primary.status_code == 202 and not {'token', 'refresh_token'} & primary.json().keys()
    verified = c['client'].post('/api/auth/mfa/login/verify', json={'challenge': primary.json()['challenge'], 'recovery_code': codes[4]})
    assert verified.status_code == 200
    c['headers'] = {'Authorization': 'Bearer ' + verified.json()['token']}
    assert c['client'].get('/api/auth/me', headers=c['headers']).status_code == 200
    with Session(c['admin']) as db:
        before = [(r.id, r.used_at) for r in db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == c['user']).order_by(MfaRecoveryCode.id))]
        intents = db.scalar(select(func.count()).select_from(GoogleLinkIntent).where(GoogleLinkIntent.user_id == c['user']))
    calls = len(c['calls'])
    denied = issue(c, recovery_code=codes[5])
    assert denied.status_code == 409 and denied.json()['detail']['code'] == 'google_link_session_version_exhausted'
    assert len(c['calls']) == calls
    state = c['client'].get('/api/auth/google/link/status', headers=c['headers'])
    assert state.status_code == 200 and state.json()['can_link'] is False
    with Session(c['admin']) as db:
        assert db.get(Usuario, c['user']).session_version == 2147483647
        assert before == [(r.id, r.used_at) for r in db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == c['user']).order_by(MfaRecoveryCode.id))]
        assert db.scalar(select(func.count()).select_from(GoogleLinkIntent).where(GoogleLinkIntent.user_id == c['user'])) == intents


def test_jku_x5u_and_library_cannot_open_a_secondary_network(google_http, monkeypatch):
    c = google_http
    c['google'].update(email=c['email'], iat=c['google']['auth_time'],
        jku='https://unapproved.example.invalid/jwks', x5u='https://unapproved.example.invalid/cert')
    attempts = []
    def prohibited(*args, **kwargs):
        attempts.append(True)
        raise RuntimeError('Secondary network is forbidden')
    monkeypatch.setattr(urllib.request, 'urlopen', prohibited)
    result = c['client'].post('/api/auth/google', json={'credential': c['credential']()})
    assert result.status_code == 409 and result.json()['detail']['code'] == 'google_link_required'
    assert len(c['calls']) == 1 and attempts == []


def test_jwks_redirect_is_not_followed(google_http, monkeypatch):
    c = google_http
    actual = httpx._client.AsyncClient
    calls = []
    def transport(request):
        calls.append(str(request.url))
        assert str(request.url) == 'https://www.googleapis.com/oauth2/v3/certs'
        return httpx.Response(302, headers={'Location': 'https://unapproved.example.invalid/keys'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda *a, **kw: actual(*a, **dict(kw, transport=httpx.MockTransport(transport))))
    result = c['client'].post('/api/auth/google', json={'credential': c['credential']()})
    assert result.status_code == 401 and len(calls) == 1
    assert not {'token', 'refresh_token', 'challenge'} & result.json().keys()


@pytest.mark.parametrize('length,expected,calls', [(16384, 401, 1), (16385, 422, 0)])
def test_google_credential_cap_is_enforced_before_or_at_real_verifier(google_http, length, expected, calls):
    c = google_http
    result = c['client'].post('/api/auth/google', json={'credential': 'x' * length})
    assert result.status_code == expected and len(c['calls']) == calls
    assert not {'token', 'refresh_token', 'challenge'} & result.json().keys()


@pytest.mark.parametrize('auth_time', [None, True, 1.5, 'future', 'stale'])
def test_link_rejects_unfresh_auth_time_without_iat_fallback_and_keeps_admission(google_http, auth_time):
    from web.database.models import MfaCredential, GoogleLinkIntent
    c = google_http
    c['google']['iat'] = int(time.time())
    if auth_time is None: c['google'].pop('auth_time')
    elif auth_time == 'future': c['google']['auth_time'] = int(time.time()) + 60
    elif auth_time == 'stale': c['google']['auth_time'] = int(time.time()) - 300
    else: c['google']['auth_time'] = auth_time
    result = c['client'].post('/api/auth/google/link/start', headers=c['headers'],
        json={'password': PASSWORD, 'google_credential': c['credential']()})
    assert result.status_code == 403 and 'intent' not in result.json()
    with Session(c['admin']) as db:
        assert db.get(MfaCredential, c['user']).attempts['google_link:start']['count'] == 1
        assert db.scalar(select(GoogleLinkIntent).where(GoogleLinkIntent.user_id == c['user'])) is None


def test_exact_ssr_get_and_api_error_boundaries_keep_distinct_private_policies(google_http):
    from fastapi import HTTPException
    from fastapi.routing import APIRoute
    c = google_http
    for path, method, expected in [('/cuenta/google', 'GET', 200), ('/cuenta/google', 'HEAD', 405),
            ('/cuenta/google/', 'GET', 307), ('/cuenta/google/', 'HEAD', 307)]:
        result = c['client'].request(method, path, follow_redirects=False)
        assert result.status_code == expected
        assert result.headers['Cache-Control'] == 'no-store' and result.headers['Referrer-Policy'] == 'no-referrer'
        assert 'accounts.google.com/gsi/client' in result.headers['Content-Security-Policy']
        assert 'unsafe-inline' not in result.headers['Content-Security-Policy']
        if expected == 307: assert result.headers['Location'] == str(result.request.url).removesuffix('/')
    for route in ['status', 'start', 'confirm', 'unlink']:
        for suffix in ['', '/']:
            for method in ['GET', 'HEAD', 'POST', 'OPTIONS']:
                result = c['client'].request(method, '/api/auth/google/link/' + route + suffix, follow_redirects=False)
                assert result.status_code in {307, 401, 405, 422}
                assert result.headers['Cache-Control'] == 'no-store' and result.headers['Referrer-Policy'] == 'no-referrer'
                policy = result.headers['Content-Security-Policy']
                assert "default-src 'none'" in policy and 'accounts.google.com' not in policy and 'unsafe-inline' not in policy
    async def synthetic_error(): raise HTTPException(500, 'synthetic-private-boundary')
    own = APIRoute('/api/auth/google/link/status', synthetic_error, methods=['GET'])
    c['client'].app.router.routes.insert(0, own)
    try:
        error = c['client'].get('/api/auth/google/link/status')
        assert error.status_code == 500 and error.headers['Cache-Control'] == 'no-store' and error.headers['Referrer-Policy'] == 'no-referrer'
        assert 'accounts.google.com' not in error.headers['Content-Security-Policy']
    finally: c['client'].app.router.routes.remove(own)
    for path in ['/cuenta/google-extra', '/api/auth/google/link/status-extra', '/api/auth/google/linker']:
        result = c['client'].get(path)
        assert result.status_code == 404 and result.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'


@pytest.mark.parametrize('fault', ['constructor', 'before_close'])
def test_owned_google_resolution_restores_ambient_context_even_when_cleanup_fails(google_http, monkeypatch, fault):
    from fastapi import HTTPException
    from starlette.requests import Request
    from web.database import engine as database
    from web.database.tenant_context import current_tenant
    from web.routes.auth import google_login
    from web.services import google_link
    c = google_http
    bind(c)
    held = []
    seen = []
    real = google_link.resolve_or_register
    class BeforeClose(Session):
        def close(self):
            if self.info.get('independent_owned_resolution'):
                held.append(self)
                raise RuntimeError('PRIVATE_PEER_RESOLUTION_CLOSE')
            super().close()
    def resolve(db, *a, **kw):
        assert current_tenant.get() == ''
        seen.append(True)
        db.info['independent_owned_resolution'] = True
        return real(db, *a, **kw)
    def unavailable(): raise RuntimeError('PRIVATE_PEER_RESOLUTION_CONSTRUCTOR')
    monkeypatch.setattr(google_link, 'resolve_or_register', resolve)
    monkeypatch.setattr(database, '_SessionLocal', unavailable if fault == 'constructor' else
        sessionmaker(bind=c['engine'], class_=BeforeClose, expire_on_commit=True, autoflush=False))
    raw = json.dumps({'credential': c['credential']()}).encode()
    async def receive(): return {'type': 'http.request', 'body': raw, 'more_body': False}
    request = Request({'type': 'http', 'method': 'POST', 'path': '/api/auth/google', 'headers': [], 'client': ('127.0.0.1', 50000)}, receive)
    marker = 'independent-ambient-tenant'
    token = current_tenant.set(marker)
    try:
        with pytest.raises(HTTPException) as failure: asyncio.run(google_login(request))
        assert failure.value.status_code == 503
        assert current_tenant.get() == marker and c['engine'].pool.checkedout() == 0
        assert seen == ([] if fault == 'constructor' else [True])
    finally:
        current_tenant.reset(token)
        for db in held: Session.close(db)
