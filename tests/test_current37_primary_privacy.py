"""Original privacy assertions with signed Google transport and real linking."""
import uuid

import pytest

from tests.ci_web37.composition import fixture_function
from tests.ci_web37.legacy_current import namespace
from tests.ci_web41 import google_mail_http_fixture as mail_http

_literal = namespace("tests/test_mfa31_primary_privacy.py", __name__)
_base_client = fixture_function(_literal["mfa_client"])


@pytest.fixture
def primary_mail_transport(monkeypatch):
    from web.settings import get_settings
    return mail_http.install(monkeypatch, get_settings())


@pytest.fixture(params=["api.app", "web.main_web"])
def current_primary_client(request, monkeypatch, test_gym_user, primary_mail_transport):
    from tests.google33_signed_provider import SignedProvider
    from web.settings import get_settings

    original = _base_client(request, monkeypatch, test_gym_user)
    client, actor, clock = next(original)
    try:
        monkeypatch.setattr(get_settings(), "GOOGLE_CLIENT_ID", "synthetic-google-client")
        claims = {"aud": "synthetic-google-client", "iss": "https://accounts.google.com",
                  "sub": "privacy37-" + uuid.uuid4().hex, "email": actor["email"],
                  "email_verified": True, "iat": int(clock[0].timestamp()),
                  "auth_time": int(clock[0].timestamp()), "exp": int(clock[0].timestamp()) + 3600}
        provider = SignedProvider(monkeypatch, claims)
        started = client.post("/api/auth/google/link/start", json={
            "password": "test123", "google_credential": provider.credential()})
        assert started.status_code == 200, "Real current37 association start failed"
        linked = client.post("/api/auth/google/link/confirm", json={
            "intent": started.json()["intent"], "confirm": True})
        assert linked.status_code == 200, "Real current37 association confirm failed"
        login = client.post("/api/auth/login", json={"email": actor["email"], "password": "test123"})
        assert login.status_code == 200, "Real current37 password renewal failed"
        client.headers["Authorization"] = "Bearer " + login.json()["token"]
        seam = []
        before_primary = []

        def body(current_actor, path):
            assert current_actor is actor
            before_primary[:] = [len(provider.calls)]
            return ({"email": actor["email"], "password": "test123"}
                    if path.endswith("/login") else {"credential": provider.credential()})

        def transport(patch, *, status=200, info=None, fail=False):
            assert patch is monkeypatch
            if info is not None:
                assert info["aud"] == claims["aud"] and info["email"] == actor["email"]
            provider.status = status
            if fail:
                from web.routes import auth

                def failed(identity, *, remember=False, method="password"):
                    assert method == "google" and remember is True
                    assert identity["id"] == actor["id"]
                    assert len(provider.calls) > before_primary[0]
                    seam.append(True)
                    raise RuntimeError(_literal["PRIVATE_PARAMETER"])

                monkeypatch.setattr(auth, "_primary_result", failed)

        monkeypatch.setitem(_literal, "primary_body", body)
        monkeypatch.setitem(_literal, "google_transport", transport)
        yield client, actor, clock
        if request.node.callspec.params.get("path") == "/api/auth/google" and request.node.callspec.params.get("status") == 500:
            assert seam == [True], "The real resolved subject must reach the private500 seam exactly once"
    finally:
        original.close()


_literal["mfa_client"] = current_primary_client
globals().update({name: value for name, value in _literal.items() if not name.startswith("__")})


# Explicit current successors retain all historical assertion calls and IDs.
# Only Google final authentication moves after the real mailbox proof stage.
PRIMARY_PATHS = _literal["PRIMARY_PATHS"]
PRIVATE_PARAMETER = _literal["PRIVATE_PARAMETER"]
assert_private_primary = _literal["assert_private_primary"]
enroll = _literal["enroll"]


def _complete_google_primary(client, actor, transport, body):
    from web.database.engine import get_engine
    case = {"client": client, "admin": get_engine(), "mail_transport": transport,
            "google": {"email": actor["email"]}}
    pending = mail_http.begin(case, credential=body["credential"])
    assert_private_primary(pending)
    return mail_http.verify(case, pending)


@pytest.mark.parametrize("path", PRIMARY_PATHS)
@pytest.mark.parametrize("status", [422, 401, 429, 503, 500])
def test_primary_errors_keep_private_headers(mfa_client, monkeypatch, caplog, path, status, primary_mail_transport):
    client, actor, _ = mfa_client
    body = _literal["primary_body"](actor, path)
    if status == 422:
        body = {}
    elif status == 401:
        if path.endswith("/login"):
            body["password"] = "synthetic-wrong-password"
        else:
            _literal["google_transport"](monkeypatch, status=401)
    elif status in (429, 503):
        from web import rate_limiter_redis
        from web.middleware import rate_limiter
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
            _literal["google_transport"](monkeypatch, fail=True)

    if path == "/api/auth/google" and status == 500:
        response = _complete_google_primary(client, actor, primary_mail_transport, body)
    else:
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
def test_primary_factor_challenge_retains_normal_csp(mfa_client, monkeypatch, path, primary_mail_transport):
    client, actor, clock = mfa_client
    if path.endswith("/google"):
        _literal["google_transport"](monkeypatch, info={"aud": "synthetic-google-client",
            "email_verified": "true", "email": actor["email"]})
    body = _literal["primary_body"](actor, path)
    response = (_complete_google_primary(client, actor, primary_mail_transport, body)
                if path == "/api/auth/google" else client.post(path, json=body))
    assert response.status_code == 200
    assert response.json()["mfa_required"] is False
    assert response.json()["token"] and response.json()["refresh_token"]
    assert_private_primary(response)
    enroll(client, clock)
    body = _literal["primary_body"](actor, path)
    response = (_complete_google_primary(client, actor, primary_mail_transport, body)
                if path == "/api/auth/google" else client.post(path, json=body))
    assert response.status_code == 202
    assert response.json()["mfa_required"] is True
    assert "token" not in response.json() and "refresh_token" not in response.json()
    assert_private_primary(response)



def test_current_google_mail_unavailable_never_falls_back_to_a_primary_pair(
        mfa_client, monkeypatch, primary_mail_transport):
    from web.database.engine import get_engine
    from web.settings import get_settings

    client, actor, _ = mfa_client
    case = {"admin": get_engine()}
    before = mail_http.counts(case)
    mail_before = len(primary_mail_transport.mail)
    cache_before = len(primary_mail_transport.cache.rows)
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "")
    response = client.post("/api/auth/google", json=_literal["primary_body"](actor, "/api/auth/google"))
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "google_email_unavailable"
    assert not {"token", "access_token", "refresh_token", "challenge"} & response.json().keys()
    assert mail_http.counts(case) == before
    assert len(primary_mail_transport.mail) == mail_before
    assert len(primary_mail_transport.cache.rows) == cache_before
    assert_private_primary(response)
