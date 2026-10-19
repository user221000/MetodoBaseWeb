"""Independent retirement32 HTTP: real invitation lineage and bounded authority.

No product edits, fake auth, minted bearer, schema stamp, limiter clear or
provider. SQL only seeds eligible professional fixture and drives parent OFF.
"""
# ruff: noqa: F811 -- pytest fixture parameters register named fixture objects
import base64
from datetime import UTC, datetime, timedelta
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.test_personal_progress_http import (  # noqa: F401
    accepted,
    grant,
    progress_db,
    progress_http,
    shared_path,
)

PASSWORD = 'Synthetic progress password 42!'
METADATA = '/api/auth/progress-retirement/metadata'
WITHDRAW = '/api/auth/progress-retirement/withdraw'


def private(response):
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "default-src 'none'" in response.headers['content-security-policy']
    assert 'accounts.google.com' not in response.headers['content-security-policy']
    assert all(value.split('=', 1)[0] == '_csrf' for value in response.headers.get_list('set-cookie'))


def enroll(case, headers, email):
    from web.services.mfa_crypto import totp
    client = case['client_http']
    proof = client.post('/api/auth/mfa/reauth', headers=headers, json={'password': PASSWORD})
    assert proof.status_code == 200
    start = client.post('/api/auth/mfa/enroll', headers=headers,
        json={'reauthentication_token': proof.json()['reauthentication_token']})
    assert start.status_code == 200
    secret = base64.b32decode(start.json()['secret'])
    confirmed = client.post('/api/auth/mfa/enroll/confirm', headers=headers, json={
        'enrollment_id': start.json()['enrollment_id'], 'code': totp(secret, int(datetime.now(UTC).timestamp()) // 30)})
    assert confirmed.status_code == 200
    codes = confirmed.json()['recovery_codes']
    login = client.post('/api/auth/login', json={'email': email, 'password': PASSWORD})
    assert login.status_code == 202
    verified = client.post('/api/auth/mfa/login/verify', json={'challenge': login.json()['challenge'], 'recovery_code': codes[0]})
    assert verified.status_code == 200
    return {'Authorization': 'Bearer ' + verified.json()['token']}, secret, codes


@pytest.fixture
def legitimate_member(progress_http, monkeypatch):
    if progress_http['factory'] == 'web.main_web':
        return _prepare_legitimate_member(progress_http, monkeypatch)
    # The historical API factory does not mount team creation. Prepare the
    # real supported genealogy through web, keeping the same migrated DB and
    # actual registered accounts; retire only through the target API client.
    from fastapi.testclient import TestClient
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as setup:
        result = _prepare_legitimate_member({**progress_http, 'client_http': setup}, monkeypatch)
    return {**result, 'client_http': progress_http['client_http']}


def _prepare_legitimate_member(progress_http, monkeypatch):
    from web.database.models import Cliente, Subscription, Usuario
    from web.settings import get_settings
    c = progress_http; client = c['client_http']
    monkeypatch.setattr(get_settings(), 'MFA_ENCRYPTION_KEY', base64.urlsafe_b64encode(bytes(range(32))).decode())
    owner, _, _ = enroll(c, c['headers']['gym'], c['emails']['gym'])
    email = uuid.uuid4().hex + '@example.invalid'
    body = {'email': email, 'nombre': 'Independent legitimate member', 'apellido': '', 'role': 'viewer'}
    step = client.post('/api/auth/mfa/step-up', headers=owner,
        json={'method': 'POST', 'path': '/api/gym/team/invite', 'body': body})
    assert step.status_code == 200
    invited = client.post('/api/gym/team/invite', headers={**owner, 'X-MFA-Grant': step.json()['grant']}, json=body)
    assert invited.status_code == 200
    assert client.post('/api/auth/accept-invite', json={'token': invited.json()['invitation_token'], 'password': PASSWORD}).status_code == 200
    login = client.post('/api/auth/login', json={'email': email, 'password': PASSWORD})
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['token']}
    me = client.get('/api/auth/me', headers=headers)
    assert me.status_code == 200 and me.json()['role'] == 'viewer' and me.json()['team_gym_id'] == c['gym']
    member = me.json()['id']
    linked_email = uuid.uuid4().hex + '@example.invalid'
    assert client.post('/api/auth/registro', json={'email': linked_email, 'password': PASSWORD, 'nombre': 'Independent linked professional', 'tipo': 'gym'}).status_code == 200
    linked_login = client.post('/api/auth/login', json={'email': linked_email, 'password': PASSWORD})
    assert linked_login.status_code == 200
    linked_headers = {'Authorization': 'Bearer ' + linked_login.json()['token']}
    linked_me = client.get('/api/auth/me', headers=linked_headers); assert linked_me.status_code == 200
    linked = linked_me.json()['id']; client_id = str(uuid.uuid4()); now = datetime.now(UTC)
    with Session(c['admin']) as db:
        db.add(Cliente(id_cliente=client_id, gym_id=linked, nombre='Explicit linked fixture', activo=True))
        db.add(Subscription(gym_id=linked, plan='clinica', status='active', provider='stripe', max_clientes=0,
            current_period_start=now - timedelta(days=1), current_period_end=now + timedelta(days=2)))
        db.commit()
    case = {**c, 'parent': c['gym'], 'person': member, 'gym': linked, 'client': client_id,
        'headers': {**c['headers'], 'person': headers, 'gym': linked_headers},
        'emails': {**c['emails'], 'person': email, 'gym': linked_email}}
    c['ready'].clear(); link = accepted(case)
    result, _ = grant(case, link, source_profile_id=None,
        categories={'weight': False, 'body_fat': False, 'lean_mass': False, 'completion': True})
    assert result.status_code == 200
    member_headers, secret, codes = enroll(case, headers, email)
    assert client.get('/api/auth/me', headers=member_headers).status_code == 200
    with Session(c['admin']) as db:
        actor = db.get(Usuario, member)
        assert actor.team_gym_id == case['parent'] and actor.activo and actor.invitation_token is None
        before_sv = actor.session_version
        db.get(Usuario, case['parent']).activo = False
        db.commit()
        assert db.get(Usuario, member).session_version == before_sv
    assert client.post('/api/auth/login', json={'email': email, 'password': PASSWORD}).status_code == 401
    assert client.get('/api/auth/me', headers=member_headers).status_code == 401
    return {**case, 'link': link, 'consent': result.json()['consent'], 'member_headers': member_headers,
        'secret': secret, 'codes': codes, 'admission_counter_resets': False}


def command(case, index=None, **changes):
    body = {'primary': {'method': 'password', 'email': case['emails']['person'], 'password': PASSWORD}}
    if index is not None: body['factor'] = {'recovery_code': case['codes'][index]}
    return {**body, **changes}


def withdraw(case, index, **changes):
    return command(case, index, **{'link_id': case['link'], 'expected_consent_id': case['consent']['id'], 'expected_version': 1, **changes})


def authority(case):
    from web.database.models import Cliente, MfaAuthorization, RefreshToken, Usuario
    with Session(case['admin']) as db:
        user = db.get(Usuario, case['person'])
        return {'id': user.id, 'sv': user.session_version, 'role': user.role, 'parent': user.team_gym_id,
            'password': user.password_hash,
            'refresh': db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user.id)),
            'proofs': db.scalar(select(func.count()).select_from(MfaAuthorization).where(MfaAuthorization.user_id == user.id)),
            'profiles': db.scalars(select(Cliente.id_cliente).where(Cliente.gym_id == user.id)).all()}


def test_legitimate_parent_off_requires_fresh_factor_each_call_and_never_issues_session(legitimate_member):
    c = legitimate_member; client = c['client_http']; before = authority(c)
    response = client.post(METADATA, json=command(c, 1), headers=c['headers']['other'])
    assert response.status_code == 200; private(response)
    assert set(response.json()) == {'scope', 'items', 'next_after'}
    assert response.json()['scope'] == 'own_consent_retirement_only'
    row = response.json()['items'][0]
    assert row['link_id'] == c['link'] and row['consent']['id'] == c['consent']['id']
    assert set(row['consent']) == {'id', 'version', 'event', 'protocol', 'link_version', 'categories', 'from_date', 'through_date', 'ongoing', 'created_at'}
    assert client.post(WITHDRAW, json=withdraw(c, 1)).status_code == 401
    result = client.post(WITHDRAW, json=withdraw(c, 2)); assert result.status_code == 200; private(result)
    assert result.json()['consent']['event'] == 'withdraw' and result.json()['consent']['version'] == 2
    assert result.json()['effective'] is False and result.json()['capabilities'] == {'withdraw': False, 'grant': False}
    assert authority(c) == before
    assert client.get('/api/usuario/progreso/consentimientos', headers=c['member_headers']).status_code == 401
    assert client.get('/api/auth/me', headers=c['headers']['other']).status_code == 200
    # Parent restoration cannot revive an explicitly withdrawn event.
    from web.database.models import Usuario
    with Session(c['admin']) as db: db.get(Usuario, c['parent']).activo = True; db.commit()
    assert client.get(shared_path(c, c['link'], c['consent']), headers=c['headers']['gym']).status_code == 409


def test_real_stale_cas_and_commit_ack_loss_require_new_proof_not_substitution(legitimate_member, monkeypatch):
    from web.database import engine as database
    c = legitimate_member; client = c['client_http']
    stale = client.post(WITHDRAW, json=withdraw(c, 1, expected_consent_id=str(uuid.uuid4())))
    assert stale.status_code == 409; private(stale)
    class LostAck(Session):
        def commit(self):
            lost = any(getattr(row, 'event_type', None) == 'progress_retirement_withdraw' for row in self.new)
            super().commit()
            if lost: raise RuntimeError('QA_PRIVATE_RETIREMENT_ACK')
    monkeypatch.setattr(database, '_SessionLocal', sessionmaker(bind=c['engine'], class_=LostAck, expire_on_commit=True))
    result = client.post(WITHDRAW, json=withdraw(c, 1))
    assert result.status_code == 503 and result.json()['detail']['code'] == 'progress_retirement_unconfirmed'; private(result)
    assert client.post(METADATA, json=command(c, 1)).status_code == 401
    observed = client.post(METADATA, json=command(c, 2)); assert observed.status_code == 200
    assert observed.json()['items'][0]['consent']['event'] == 'withdraw'
    assert observed.json()['items'][0]['consent']['version'] == 2


def test_naturally_expired_totp_and_ambient_headers_cannot_replace_fresh_proof(legitimate_member):
    from web.services.mfa_crypto import totp
    c = legitimate_member; client = c['client_http']
    old = totp(c['secret'], int(datetime.now(UTC).timestamp()) // 30 - 3)
    response = client.post(METADATA, json=command(c, factor={'code': old}), headers=c['headers']['other'])
    assert response.status_code == 401; private(response)
    assert 'items' not in response.json()
    assert client.post(METADATA, json={}, headers=c['headers']['other']).status_code == 422
    assert client.post(METADATA, json=command(c, 1, source_profile_id=c['profile'])).status_code == 422
    fresh = client.post(METADATA, json=command(c, 1)); assert fresh.status_code == 200
    for path in (METADATA, WITHDRAW, '/retirar-consentimientos', '/retirar-consentimientos/'):
        result = client.get(path, follow_redirects=False)
        assert result.status_code in {200, 307, 405}; private(result)
    for path in (METADATA + '-neighbor', '/retirar-consentimientos-neighbor'):
        neighbor = client.get(path)
        assert neighbor.status_code == 404 and neighbor.headers['referrer-policy'] == 'strict-origin-when-cross-origin'


def test_real_actor10_and_ip30_limits_accumulate_without_any_reset(legitimate_member):
    from web.database.models import AuthAuditLog
    c = legitimate_member; client = c['client_http']
    for index in range(10):
        body = command(c); body['primary']['password'] = 'Incorrect proof'
        if index % 2: body.update(link_id=c['link'], expected_consent_id=c['consent']['id'], expected_version=1)
        result = client.post(WITHDRAW if index % 2 else METADATA, json=body)
        assert result.status_code == 401
    limited = client.post(METADATA, json=command(c, 1)); assert limited.status_code == 429; private(limited)
    with Session(c['admin']) as db:
        assert db.scalar(select(func.count()).select_from(AuthAuditLog).where(AuthAuditLog.user_id == c['person'], AuthAuditLog.event_type == 'progress_retirement_attempt')) == 10
    for _ in range(19):
        body = {'primary': {'method': 'password', 'email': uuid.uuid4().hex + '@example.invalid', 'password': 'Unknown proof'}}
        assert client.post(METADATA, json=body).status_code == 401
    exhausted = client.post(METADATA, json={'primary': {'method': 'password', 'email': uuid.uuid4().hex + '@example.invalid', 'password': 'Unknown proof'}})
    assert exhausted.status_code == 429; private(exhausted)
