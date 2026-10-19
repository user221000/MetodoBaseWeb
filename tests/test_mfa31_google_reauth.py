"""Provider auth_time, not refresh iat or a supplied email, proves fresh primary."""
from datetime import timedelta
import httpx
import pytest

from tests.test_mfa31_http import mfa_client


def google_transport(monkeypatch, actor, clock, *, freshness="fresh", email=None):
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), "GOOGLE_CLIENT_ID", "synthetic-mfa-google-client")
    info = {"aud":"synthetic-mfa-google-client", "email_verified":"true",
        "email":email or actor["email"], "iat":int(clock[0].timestamp()),
        "auth_time":int(clock[0].timestamp())}
    if freshness == "stale": info["auth_time"] -= 3600
    if freshness == "missing": info.pop("auth_time")
    if freshness == "future": info["auth_time"] += 60
    if freshness == "boolean": info["auth_time"] = True
    calls = []
    class Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            calls.append((url,kwargs))
            return httpx.Response(200,json=info)
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    return calls


@pytest.mark.parametrize("freshness", ["stale", "missing", "future", "boolean"])
def test_google_primary_reauth_rejects_stale_or_absent_auth_time_despite_new_iat(mfa_client, monkeypatch, freshness):
    client, actor, clock = mfa_client
    calls = google_transport(monkeypatch, actor, clock, freshness=freshness)
    response = client.post("/api/auth/mfa/reauth", json={"google_credential":"synthetic-verified-provider-credential"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "mfa_primary_reauthentication_required"
    assert len(calls) == 1 and calls[0][0] == "https://oauth2.googleapis.com/tokeninfo"


def test_fresh_google_primary_reauth_accepts_only_matching_persisted_account(mfa_client, monkeypatch):
    client, actor, clock = mfa_client
    google_transport(monkeypatch, actor, clock)
    response = client.post("/api/auth/mfa/reauth", json={"google_credential":"synthetic-verified-provider-credential"})
    assert response.status_code == 200, response.text
    assert "reauthentication_token" in response.json()


def test_google_primary_cannot_reauthenticate_a_different_persisted_account(mfa_client, monkeypatch):
    client, actor, clock = mfa_client
    google_transport(monkeypatch,actor,clock,email="different-account@example.invalid")
    response = client.post("/api/auth/mfa/reauth",json={"google_credential":"synthetic-provider-credential"})
    assert response.status_code == 400


def test_google_primary_admission_budget_survives_credential_rotation(mfa_client, monkeypatch):
    client, actor, clock = mfa_client
    calls = google_transport(monkeypatch,actor,clock,freshness="stale")
    for attempt in range(10):
        response = client.post("/api/auth/mfa/reauth",json={"google_credential":"synthetic-credential-"+str(attempt)})
        assert response.status_code == 403
    blocked = client.post("/api/auth/mfa/reauth",json={"google_credential":"new-synthetic-credential"})
    assert blocked.status_code == 429 and len(calls) == 10
