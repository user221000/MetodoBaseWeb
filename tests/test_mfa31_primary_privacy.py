"""Exact primary API privacy policy through real factories and error boundaries.

Only provider transports and failure seams are synthetic. No routes are mounted
for these probes; normal GIS CSP and adjacent paths remain outside the policy.
"""
import httpx
import pytest

from tests.test_mfa31_http import mfa_client, enroll


PRIMARY_PATHS = ("/api/auth/login", "/api/auth/google")
PRIVATE_PARAMETER = "synthetic-primary-private-parameter@example.invalid"


def google_transport(monkeypatch, *, status=200, info=None, fail=False):
    from web.settings import get_settings

    monkeypatch.setattr(get_settings(), "GOOGLE_CLIENT_ID", "synthetic-google-client")
    actual = httpx.AsyncClient

    def handler(request):
        assert request.url.host == "oauth2.googleapis.com"
        assert request.url.path == "/tokeninfo"
        assert request.url.params["id_token"] == "synthetic-google-credential"
        if fail:
            raise RuntimeError(PRIVATE_PARAMETER)
        return httpx.Response(status, json=info or {})

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: actual(
        *args, transport=httpx.MockTransport(handler), **kwargs))


def primary_body(actor, path):
    return ({"email": actor["email"], "password": "test123"}
            if path.endswith("/login") else {"credential": "synthetic-google-credential"})


def assert_private_primary(response):
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    # These APIs retain the existing policy, including the GIS endpoints.
    policy = response.headers["content-security-policy"]
    assert "https://accounts.google.com/gsi/client" in policy
    assert "https://js.stripe.com" in policy
    assert "default-src 'none'" not in policy


@pytest.mark.parametrize("path", PRIMARY_PATHS)
@pytest.mark.parametrize("status", [422, 401, 429, 503, 500])
def test_primary_errors_keep_private_headers(mfa_client, monkeypatch, caplog, path, status):
    client, actor, _ = mfa_client
    body = primary_body(actor, path)
    if status == 422:
        body = {}
    elif status == 401:
        if path.endswith("/login"):
            body["password"] = "synthetic-wrong-password"
        else:
            google_transport(monkeypatch, status=401)
    elif status in (429, 503):
        from web.middleware import rate_limiter
        from web import rate_limiter_redis
        from web.settings import get_settings

        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_ENABLED", True)
        if status == 429:
            async def rejected(*args, **kwargs):
                return False, {"retry_after": 5, "remaining": 0}, "local"

            monkeypatch.setattr(rate_limiter_redis, "check_rate_limit", rejected)
        else:
            async def unavailable(*args, **kwargs):
                raise RuntimeError(PRIVATE_PARAMETER)

            # Real fail-closed Redis error conversion, with only its transport
            # replaced. The already-created app still uses its local middleware.
            monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://synthetic.invalid:6379/0")
            monkeypatch.setattr(rate_limiter_redis, "_is_allowed_redis", unavailable)
    else:
        if path.endswith("/login"):
            from web import auth

            def failed(*args, **kwargs):
                raise RuntimeError(PRIVATE_PARAMETER)

            monkeypatch.setattr(auth, "verificar_credenciales", failed)
        else:
            google_transport(monkeypatch, fail=True)

    response = client.post(path, json=body)
    assert response.status_code == status
    assert_private_primary(response)
    if status == 500:
        assert response.json()["detail"] == "Error interno del servidor"
        assert PRIVATE_PARAMETER not in response.text
        assert PRIVATE_PARAMETER not in caplog.text
    elif status == 503:
        assert response.json()["detail"]["code"] == "rate_limit_backend_unavailable"


@pytest.mark.parametrize("path", PRIMARY_PATHS)
def test_primary_wrong_method_is_private_without_changing_routes(mfa_client, path):
    client, _, _ = mfa_client
    assert path in client.app.openapi()["paths"]
    response = client.get(path)
    assert response.status_code == 405
    assert_private_primary(response)


@pytest.mark.parametrize("path", PRIMARY_PATHS)
def test_primary_factor_challenge_retains_normal_csp(mfa_client, monkeypatch, path):
    client, actor, clock = mfa_client
    if path.endswith("/google"):
        google_transport(monkeypatch, info={"aud": "synthetic-google-client",
            "email_verified": "true", "email": actor["email"]})
    response = client.post(path, json=primary_body(actor, path))
    assert response.status_code == 200
    assert response.json()["mfa_required"] is False
    assert response.json()["token"] and response.json()["refresh_token"]
    assert_private_primary(response)
    enroll(client, clock)
    response = client.post(path, json=primary_body(actor, path))
    assert response.status_code == 202
    assert response.json()["mfa_required"] is True
    assert "token" not in response.json() and "refresh_token" not in response.json()
    assert_private_primary(response)


def test_login_pages_adjacent_and_existing_private_paths_keep_their_policy(mfa_client):
    client, _, _ = mfa_client
    for path in ("/login-gym", "/login-usuario"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "https://accounts.google.com/gsi/client" in response.headers["content-security-policy"]
    for path in ("/api/auth/login-extra", "/api/auth/google-extra", "/api/auth/LOGIN", "/api/auth/google/other"):
        response = client.post(path, json={})
        assert response.status_code == 404
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    response = client.get("/api/auth/mfa/status")
    assert response.status_code == 200
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    response = client.get("/api/usuario/historial", headers={"Authorization": ""})
    assert response.status_code == 401
    assert response.headers["referrer-policy"] == "no-referrer"
    response = client.get("/api/usuario/vinculos", headers={"Authorization": ""})
    assert response.status_code == 401
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
