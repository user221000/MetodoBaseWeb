"""Exercise signing-key cutover on the unchanged real schema37 auth paths."""
import importlib
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from tests import account_security37_http
from tests.followup34_http import PASSWORD
from web import auth
from web.services import mfa_crypto

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http


def rotate_worker(monkeypatch):
    """Change synthetic settings and cached signing state; not a worker restart."""
    from web.settings import get_settings
    key = 'synthetic-rotation37-new-signing-key-' + uuid.uuid4().hex
    monkeypatch.setattr(get_settings(), 'SECRET_KEY', key)
    monkeypatch.setattr(auth, 'SECRET_KEY', key)


def personal(case):
    raw = case['raw']
    raw.headers.pop('Authorization', None)
    email = uuid.uuid4().hex + '@example.invalid'
    made = raw.post('/api/auth/registro', json={
        'email': email, 'password': PASSWORD, 'nombre': 'Synthetic rotation account', 'tipo': 'usuario'})
    assert made.status_code == 200
    return {'email': email, 'password': PASSWORD}


def browser_headers(raw):
    from web.settings import get_settings
    values = {'Origin': get_settings().BASE_URL, 'X-MetodoBase-Browser': '1'}
    if raw.cookies.get('_csrf'):
        values['X-CSRF-Token'] = raw.cookies.get('_csrf')
    return values


def test_cutover_rejects_old_access_and_both_refresh_transports_then_allows_new_login(account_http, monkeypatch):
    from web import browser_session
    case = account_http
    raw = case['raw']
    credentials = personal(case)
    legacy = raw.post('/api/auth/login', json=credentials)
    assert legacy.status_code == 200
    old_access, old_refresh = legacy.json()['token'], legacy.json()['refresh_token']
    before = raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + old_access})
    assert before.status_code == 200
    browser = raw.post('/api/auth/login', json=credentials, headers=browser_headers(raw))
    assert browser.status_code == 200 and browser.json()['session_mode'] == 'browser'
    assert 'refresh_token' not in browser.json()
    _, cookie_name, _ = browser_session.configuration()
    old_cookie = raw.cookies.get(cookie_name)
    assert old_cookie
    old_csrf = raw.cookies.get('_csrf')
    assert old_csrf
    rotate_worker(monkeypatch)

    # Build the actual factory again: CSRF captures its key when middleware is
    # constructed. Mutating auth globals on the original app cannot prove this.
    application = importlib.import_module(case['factory_name']).create_app()
    with TestClient(application, raise_server_exceptions=False) as renewed:
        renewed.cookies.update(raw.cookies)
        # A non-exempt HTML path exercises real CSRF before route dispatch.
        blocked = renewed.post('/login-usuario', json={}, headers={'X-CSRF-Token': old_csrf})
        assert blocked.status_code == 403
        assert blocked.json()['detail'] == 'CSRF token invalid or expired'
        page = renewed.get('/login-usuario')
        assert page.status_code == 200
        new_csrf = renewed.cookies.get('_csrf')
        from web.middleware.csrf import verify_csrf_token
        assert new_csrf != old_csrf and verify_csrf_token(new_csrf, auth.SECRET_KEY)
        assert not verify_csrf_token(old_csrf, auth.SECRET_KEY)
        # These auth routes have their own explicit browser admission. Their
        # 401s below are token rejection, not the HTML CSRF denial above.
        assert renewed.get('/api/auth/me', headers={'Authorization': 'Bearer ' + old_access}).status_code == 401
        assert renewed.post('/api/auth/refresh', json={'refresh_token': old_refresh}).status_code == 401
        expired = renewed.post('/api/auth/refresh', json={}, headers=browser_headers(renewed))
        assert expired.status_code == 401
        assert old_cookie not in expired.text and old_refresh not in expired.text
        assert expired.headers['cache-control'] == 'no-store'

        fresh = renewed.post('/api/auth/login', json=credentials, headers=browser_headers(renewed))
        assert fresh.status_code == 200 and fresh.json()['session_mode'] == 'browser'
        assert renewed.cookies.get(cookie_name) != old_cookie
        current = renewed.get('/api/auth/me', headers={'Authorization': 'Bearer ' + fresh.json()['token']})
        assert current.status_code == 200 and current.json()['id'] == before.json()['id']
        assert current.json()['session_version'] == before.json()['session_version']
        refreshed = renewed.post('/api/auth/refresh', json={}, headers=browser_headers(renewed))
        assert refreshed.status_code == 200 and refreshed.json()['session_mode'] == 'browser'


def test_key_only_rollback_resurrects_a_token_so_application_rollback_must_keep_new_key(account_http, monkeypatch):
    raw = account_http['raw']
    credentials = personal(account_http)
    login = raw.post('/api/auth/login', json=credentials)
    assert login.status_code == 200
    token = login.json()['token']
    headers = {'Authorization': 'Bearer ' + token}
    assert raw.get('/api/auth/me', headers=headers).status_code == 200
    with monkeypatch.context() as cutover:
        rotate_worker(cutover)
        assert raw.get('/api/auth/me', headers=headers).status_code == 401
    # Demonstrate the operational hazard, not an authorized rollback strategy.
    assert raw.get('/api/auth/me', headers=headers).status_code == 200


@pytest.mark.parametrize('field,value', [('iss', 'other-issuer'), ('aud', 'other-audience'),
    ('type', 'refresh'), ('exp', 0), ('exp', True), ('v', 2)])
def test_current_key_still_rejects_invalid_access_claims_before_database(field, value, monkeypatch):
    rotate_worker(monkeypatch)
    claims = {'id': 'synthetic-subject', 'type': 'access', 'iss': 'metodobase',
              'aud': 'metodobase-web', 'v': 1, 'exp': 9999999999, 'sv': 0}
    claims[field] = value
    calls = []
    def forbidden(*_args):
        calls.append(True)
        raise AssertionError('Rejected claims reached identity lookup')
    monkeypatch.setattr(auth, '_get_user_by_id', forbidden)
    assert auth.verificar_token(auth._make_token(claims)) is None
    assert not calls


def test_signing_cutover_keeps_previously_enrolled_factor_working(account_http, monkeypatch):
    from web.database.models import MfaCredential, Usuario
    from web.services import mfa_service
    case = account_http
    raw = case['raw']
    with case['factory']() as db:
        factor = db.get(MfaCredential, case['user'])
        account = db.get(Usuario, case['user'])
        email = account.email
        ciphertext, generation = factor.secret_ciphertext, factor.generation
        seed = mfa_crypto.decrypt(ciphertext, mfa_service.configuration(),
                                  mfa_service._aad(factor, generation, 'active'))
        counter = max(factor.last_counter + 1, int(datetime.now(timezone.utc).timestamp()) // 30 + 1)
    # Advance the synthetic server and authenticator together to an unused TOTP
    # step, rather than waiting for the wall clock or bypassing factor checks.
    observed = datetime.fromtimestamp(counter * 30 + 1, timezone.utc)
    clock = mfa_service.instant
    monkeypatch.setattr(mfa_service, 'instant', lambda now=None: clock(observed if now is None else now))
    rotate_worker(monkeypatch)
    raw.headers.pop('Authorization', None)
    primary = raw.post('/api/auth/login', json={'email': email, 'password': PASSWORD})
    assert primary.status_code == 202 and primary.json()['mfa_required'] is True
    confirmed = raw.post('/api/auth/mfa/login/verify', json={
        'challenge': primary.json()['challenge'], 'code': mfa_crypto.totp(seed, counter)})
    assert confirmed.status_code == 200
    access = confirmed.json()['token']
    current = raw.get('/api/auth/me', headers={'Authorization': 'Bearer ' + access})
    assert current.status_code == 200 and current.json()['id'] == case['user']
    with case['factory']() as db:
        factor = db.get(MfaCredential, case['user'])
        assert factor.secret_ciphertext == ciphertext and factor.generation == generation
        assert factor.last_counter == counter
