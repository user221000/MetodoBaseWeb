"""Independent browser admission regression for the protected mailbox proof.

Actual composed factories, SQLAlchemy and BrowserAuthRoute execute unchanged.
The imported fixture substitutes Google JWKS, email transport and Redis wire;
real Redis/browser end-to-end acceptance is a separate gate.
"""
import pytest

from tests.test_google_mfa_email_reauthentication import (
    database_schema, isolated_database, reauth_case, reauth_http,
)

ORIGIN = 'https://incident-qa.example.invalid'
PATHS = ('/api/auth/mfa/google-email/request', '/api/auth/mfa/google-email/verify')


def auth_cookie_writes(response):
    # The composed CSRF middleware may issue its own independent cookie.
    # Reauth must preserve only the existing HttpOnly refresh authority.
    return [value for value in response.headers.get_list('set-cookie')
            if value.startswith(('__Host-mb_refresh=', 'mb_refresh_dev='))]


def setup_browser(case, client, monkeypatch):
    monkeypatch.setattr(case.settings, 'BASE_URL', ORIGIN)
    client.base_url = ORIGIN
    return {'Origin': ORIGIN, 'X-MetodoBase-Browser': '1'}


def test_protected_google_mailbox_paths_do_not_become_primary_or_revoking():
    from web.browser_session import COOKIE_POSTS, PRIMARY, REVOKING
    assert set(PATHS) <= COOKIE_POSTS
    assert not set(PATHS) & (PRIMARY | REVOKING)


def test_browser_uses_existing_actor_for_mailbox_proof_without_rotating_or_issuing_a_session(
        reauth_http, monkeypatch):
    from sqlalchemy import func, select
    from web.database.models import RefreshToken
    case, client = reauth_http
    headers = setup_browser(case, client, monkeypatch)
    # An existing browser proof must not be cleared or replaced by reauth.
    client.cookies.set('__Host-mb_refresh', 'synthetic-cookie-not-general-authority', domain='incident-qa.example.invalid', path='/')
    with case.sessions() as db:
        before = db.scalar(select(func.count()).select_from(RefreshToken))
    issued = client.post(PATHS[0], headers=headers,
                         json={'google_credential': case.provider.credential()})
    assert issued.status_code == 202
    assert len(case.mail) == 1
    assert not auth_cookie_writes(issued)
    stage = issued.json()
    assert set(stage) == {'email_verification_required', 'challenge', 'expires_at', 'masked_email', 'resend_after_seconds'}
    verified = client.post(PATHS[1], headers=headers,
        json={'challenge': stage['challenge'], 'code': case.mail[-1][1]})
    assert verified.status_code == 200
    assert set(verified.json()) == {'reauthentication_token', 'expires_at'}
    assert not auth_cookie_writes(verified)
    assert verified.headers['cache-control'] == 'no-store'
    assert verified.headers['referrer-policy'] == 'no-referrer'
    assert client.cookies.get('__Host-mb_refresh') == 'synthetic-cookie-not-general-authority'
    with case.sessions() as db:
        assert db.scalar(select(func.count()).select_from(RefreshToken)) == before
    replay = client.post(PATHS[1], headers=headers,
        json={'challenge': stage['challenge'], 'code': case.mail[-1][1]})
    assert replay.status_code == 400
    assert 'reauthentication_token' not in replay.json()


@pytest.mark.parametrize('path', PATHS)
@pytest.mark.parametrize('change', ['origin', 'header', 'query', 'duplicate_origin'])
def test_browser_origin_header_and_query_admission_precede_any_mailbox_operation(
        reauth_http, monkeypatch, path, change):
    case, client = reauth_http
    headers = setup_browser(case, client, monkeypatch)
    if change == 'origin':
        headers['Origin'] = 'https://outside.example.invalid'
    elif change == 'header':
        headers['X-MetodoBase-Browser'] = '0'
    elif change == 'query':
        path += '?unexpected=1'
    else:
        headers = [('Origin', ORIGIN), ('Origin', 'https://outside.example.invalid'), ('X-MetodoBase-Browser', '1')]
    body = {'google_credential': case.provider.credential()} if '/request' in path else {'challenge': 'A' * 43, 'code': '123456'}
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'browser_origin_invalid'
    assert case.mail == [] and not case.cache.rows
    assert not auth_cookie_writes(response)


@pytest.mark.parametrize('path', PATHS)
def test_admitted_browser_still_requires_a_bearer_actor_before_proof_or_mail(
        reauth_http, monkeypatch, path):
    case, client = reauth_http
    headers = setup_browser(case, client, monkeypatch)
    del client.headers['Authorization']
    body = {'google_credential': case.provider.credential()} if path.endswith('/request') else {'challenge': 'A' * 43, 'code': '123456'}
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 401
    assert case.mail == [] and not case.cache.rows
    assert not auth_cookie_writes(response)


def test_admitted_code_stays_bound_to_the_actor_and_exact_access(reauth_http, monkeypatch):
    case, client = reauth_http
    headers = setup_browser(case, client, monkeypatch)
    issued = client.post(PATHS[0], headers=headers,
                         json={'google_credential': case.provider.credential()})
    assert issued.status_code == 202
    before = len(case.mail)
    headers['Authorization'] = 'Bearer ' + case.tokens['b']
    denied = client.post(PATHS[1], headers=headers,
        json={'challenge': issued.json()['challenge'], 'code': case.mail[-1][1]})
    assert denied.status_code == 400
    assert set(denied.json()) == {'detail'}
    assert len(case.mail) == before
    # A rejected cross-account attempt cannot consume account A's valid proof.
    headers['Authorization'] = 'Bearer ' + case.tokens['a']
    accepted = client.post(PATHS[1], headers=headers,
        json={'challenge': issued.json()['challenge'], 'code': case.mail[-1][1]})
    assert accepted.status_code == 200
    assert set(accepted.json()) == {'reauthentication_token', 'expires_at'}
