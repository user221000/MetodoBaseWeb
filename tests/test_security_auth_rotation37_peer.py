"""Independent cutover hazards and key consumers, using only synthetic keys."""
import base64
import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from tests import account_security37_http
from tests.followup34_http import PASSWORD
from web import auth
from web.middleware.csrf import CSRFMiddleware, generate_csrf_token, verify_csrf_token
from web.services import mfa_service
from web.services.personal_history_cursor import decode_position, encode_position
from web.settings import get_settings

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http
KEY_A = 'inert-peer-rotation-generation-A-' + 'a' * 40
KEY_B = 'inert-peer-rotation-generation-B-' + 'b' * 40


def worker(monkeypatch, key):
    monkeypatch.setattr(get_settings(), 'SECRET_KEY', key)
    monkeypatch.setattr(auth, 'SECRET_KEY', key)


def test_mixed_old_worker_can_rotate_unrevoked_old_refresh_and_new_worker_refuses_it(account_http, monkeypatch):
    """Sequential worker-generation model, not a multi-process/load-balancer claim."""
    from web.database.models import RefreshToken
    case = account_http
    raw = case['raw']
    raw.headers.pop('Authorization', None)
    worker(monkeypatch, KEY_A)
    credentials = {'email': uuid.uuid4().hex + '@example.invalid', 'password': PASSWORD}
    assert raw.post('/api/auth/registro', json={**credentials, 'nombre': 'Synthetic cutover',
                                               'tipo': 'usuario'}).status_code == 200
    old = raw.post('/api/auth/login', json=credentials)
    assert old.status_code == 200
    old_access, old_refresh = old.json()['token'], old.json()['refresh_token']
    old_jti = auth._decode_token(old_refresh)['jti']
    worker(monkeypatch, KEY_B)
    assert raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + old_access}).status_code == 401
    assert raw.post('/api/auth/refresh', json={'refresh_token': old_refresh}).status_code == 401
    with case['factory']() as db:
        assert db.get(RefreshToken, old_jti).revoked is False
    new = raw.post('/api/auth/login', json=credentials)
    assert new.status_code == 200
    new_access = new.json()['token']
    worker(monkeypatch, KEY_A)
    assert raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + old_access}).status_code == 200
    revived = raw.post('/api/auth/refresh', json={'refresh_token': old_refresh})
    assert revived.status_code == 200
    assert raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + new_access}).status_code == 401
    with case['factory']() as db:
        assert db.get(RefreshToken, old_jti).revoked is True
    worker(monkeypatch, KEY_B)
    assert raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + revived.json()['token']}).status_code == 401
    assert raw.post('/api/auth/refresh', json={'refresh_token': revived.json()['refresh_token']}).status_code == 401
    assert raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + new_access}).status_code == 200


def test_settings_only_change_keeps_cached_auth_and_bound_CSRF_until_rebuilt(monkeypatch):
    worker(monkeypatch, KEY_A)
    payload = {'inert_probe': 'not-an-access-token'}
    old = auth._make_token(payload)
    bound = CSRFMiddleware(lambda *_args: None, secret_key=KEY_A)
    old_csrf = generate_csrf_token(KEY_A)
    monkeypatch.setattr(get_settings(), 'SECRET_KEY', KEY_B)
    assert auth._decode_token(old) == payload
    assert verify_csrf_token(old_csrf, bound.secret_key) is True
    worker(monkeypatch, KEY_B)
    fresh = CSRFMiddleware(lambda *_args: None, secret_key=KEY_B)
    assert auth._decode_token(old) is None
    assert verify_csrf_token(old_csrf, fresh.secret_key) is False
    assert verify_csrf_token(generate_csrf_token(KEY_B), fresh.secret_key) is True


def test_current_issued_access_TTL_remains_short_for_both_remember_modes(monkeypatch):
    worker(monkeypatch, KEY_B)
    monkeypatch.setattr(auth.time, 'time', lambda: 1_700_000_000.0)
    monkeypatch.setattr(auth, 'ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    user = {'id': 'inert-subject', 'email': 'subject@example.invalid', 'nombre': 'Synthetic',
            'tipo': 'usuario', 'role': 'viewer', 'session_version': 0}
    for remember in (False, True):
        payload = auth._decode_token(auth.crear_access_token(user, remember_me=remember))
        assert payload['exp'] == 1_700_000_900.0
        assert (payload['iss'], payload['aud'], payload['v'], payload['type']) == (
            'metodobase', 'metodobase-web', 1, 'access')


@pytest.mark.parametrize('form', ['encoded-key', 'decoded-key'])
def test_reusing_MFA_encryption_key_as_signing_key_refuses_configuration(monkeypatch, form):
    raw = b'X' * 32
    encoded = base64.urlsafe_b64encode(raw).decode()
    monkeypatch.setattr(get_settings(), 'MFA_ENCRYPTION_KEY', encoded)
    worker(monkeypatch, encoded if form == 'encoded-key' else raw.decode())
    with pytest.raises(HTTPException) as failure:
        mfa_service.configuration()
    assert failure.value.status_code == 503
    assert failure.value.detail['code'] == 'mfa_service_unavailable'


def test_history_cursor_cutover_requires_restart_of_pagination_not_subject_adoption():
    stamp = datetime(2026, 10, 22, 0, 0)
    values = {'subject': 'inert-owner', 'profile': 'inert-profile'}
    old = encode_position(stamp, 42, secret=KEY_A, **values)
    assert decode_position(old, secret=KEY_A, **values) == (stamp, 42)
    with pytest.raises(ValueError, match='Invalid history cursor'):
        decode_position(old, secret=KEY_B, **values)
    current = encode_position(stamp, 42, secret=KEY_B, **values)
    assert decode_position(current, secret=KEY_B, **values) == (stamp, 42)
    with pytest.raises(ValueError, match='Invalid history cursor'):
        decode_position(current, secret=KEY_B, subject='another-owner', profile=values['profile'])
