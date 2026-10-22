"""Original privacy assertions with signed Google transport and real linking."""
import uuid

import pytest

from tests.ci_web37.composition import fixture_function
from tests.ci_web37.legacy_current import namespace

_literal = namespace("tests/test_mfa31_primary_privacy.py", __name__)
_base_client = fixture_function(_literal["mfa_client"])


@pytest.fixture(params=["api.app", "web.main_web"])
def current_primary_client(request, monkeypatch, test_gym_user):
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
