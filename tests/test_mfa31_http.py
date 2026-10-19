"""Current31 MFA contracts, with real identities and synthetic external ports."""
import pytest
import base64
from datetime import datetime, timedelta, timezone
import importlib
import uuid
from fastapi.testclient import TestClient


@pytest.fixture(params=["api.app", "web.main_web"])
def mfa_client(request, monkeypatch, test_gym_user):
    from web.services import mfa_service
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"synthetic-key-for-mfa-tests-only!!"[:32]).decode())
    clock = [datetime.now(timezone.utc)]
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda now=None: actual(clock[0] if now is None else now))
    # Distinct synthetic source IP: exercise the real limiter without sharing
    # a process-local test bucket with a different independent account.
    number = int(uuid.uuid4().hex[:4], 16)
    application = importlib.import_module(request.param).create_app()
    with TestClient(application, raise_server_exceptions=False,
            headers=test_gym_user["auth_headers"], client=(f"127.1.{number // 256}.{number % 256}", 50000)) as client:
        yield client, test_gym_user, clock


def enroll(client, clock):
    from web.services.mfa_crypto import totp
    proof = client.post("/api/auth/mfa/reauth", json={"password": "test123"})
    assert proof.status_code == 200, proof.text
    start = client.post("/api/auth/mfa/enroll", json={"reauthentication_token": proof.json()["reauthentication_token"]})
    assert start.status_code == 200, start.text
    source = start.json()
    seed = base64.b32decode(source["secret"])
    done = client.post("/api/auth/mfa/enroll/confirm", json={"enrollment_id": source["enrollment_id"],
        "code": totp(seed, int(clock[0].timestamp()) // 30)})
    assert done.status_code == 200, done.text
    return source, done.json()


def authenticate(client, actor, clock, *, seed=None, recovery=None):
    from web.services.mfa_crypto import totp
    primary = client.post("/api/auth/login", json={"email": actor["email"], "password": "test123"})
    assert primary.status_code == 202, primary.text
    challenge = primary.json()["challenge"]
    assert "token" not in primary.json() and "refresh_token" not in primary.json()
    body = {"challenge": challenge}
    if recovery:
        body["recovery_code"] = recovery
    else:
        body["code"] = totp(seed, int(clock[0].timestamp()) // 30)
    result = client.post("/api/auth/mfa/login/verify", json=body)
    assert result.status_code == 200, result.text
    client.headers["Authorization"] = "Bearer " + result.json()["token"]
    return result.json(), body


@pytest.mark.parametrize("client_fixture", ["auth_client", "web_auth_client"])
def test_primary_only_owner_cannot_open_billing_portal(request, monkeypatch, client_fixture):
    from web.services import stripe_service
    calls = []
    monkeypatch.setattr(stripe_service, "create_portal_session", lambda **kw: calls.append(kw) or {"url": "https://provider.example.invalid/portal"})
    client = request.getfixturevalue(client_fixture)
    response = client.post("/api/billing/portal", json={"return_url": "/dashboard"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "mfa_enrollment_required"
    assert calls == []


def test_enrollment_login_one_use_and_status_never_repeats_secrets(mfa_client):
    client, actor, clock = mfa_client
    from web.auth import verificar_token, verificar_refresh_token
    original = actor["access_token"]
    start, done = enroll(client, clock)
    assert done["reauthenticate"] is True and len(set(done["recovery_codes"])) == 8
    assert verificar_token(original) is None
    clock[0] += timedelta(seconds=31)
    pair, body = authenticate(client, actor, clock, seed=base64.b32decode(start["secret"]))
    assert pair["token"].count(".") == 1
    assert verificar_token(pair["token"])["amr"] == ["pwd", "otp"]
    assert verificar_refresh_token(pair["refresh_token"])
    replay = client.post("/api/auth/mfa/login/verify", json=body)
    assert replay.status_code == 400
    state = client.get("/api/auth/mfa/status")
    assert state.status_code == 200
    assert state.json()["enabled"] is True and state.json()["recovery_codes_remaining"] == 8
    assert start["secret"] not in state.text
    assert all(code not in state.text for code in done["recovery_codes"])
    assert state.headers["Cache-Control"] == "no-store"
    assert state.headers["Referrer-Policy"] == "no-referrer"


def test_recent_mfa_grant_exact_body_action_access_and_one_use(mfa_client, monkeypatch):
    client, actor, clock = mfa_client
    from web.services import stripe_service
    calls = []
    monkeypatch.setattr(stripe_service, "create_portal_session", lambda **kw: calls.append(kw) or {"url": "https://provider.example.invalid/portal"})
    _, done = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=done["recovery_codes"][0])
    action = {"method": "POST", "path": "/api/billing/portal", "body": {"return_url": "/dashboard"}}
    issued = client.post("/api/auth/mfa/step-up", json=action)
    assert issued.status_code == 200, issued.text
    grant = issued.json()["grant"]
    mismatch = client.post(action["path"], json={"return_url": "/suscripciones"}, headers={"X-MFA-Grant": grant})
    assert mismatch.status_code == 403 and calls == []
    valid = client.post(action["path"], json=action["body"], headers={"X-MFA-Grant": grant})
    assert valid.status_code == 200 and len(calls) == 1
    replay = client.post(action["path"], json=action["body"], headers={"X-MFA-Grant": grant})
    assert replay.status_code in (400,409) and len(calls) == 1
    second = client.post("/api/auth/mfa/step-up", json=action)
    assert second.status_code == 200  # Recent MFA, distinct grant, no OTP replay.
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    client.headers["Authorization"] = "Bearer " + refreshed.json()["token"]
    bound = client.post(action["path"], json=action["body"], headers={"X-MFA-Grant": second.json()["grant"]})
    assert bound.status_code == 400 and len(calls) == 1


def test_recovery_one_use_and_password_reset_does_not_disable_factor(mfa_client):
    client, actor, clock = mfa_client
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services.password_recovery import issue_request, consume
    from urllib.parse import urlsplit, parse_qs
    _, done = enroll(client, clock)
    authenticate(client, actor, clock, recovery=done["recovery_codes"][0])
    another = client.post("/api/auth/login", json={"email": actor["email"], "password": "test123"})
    replay = client.post("/api/auth/mfa/login/verify", json={"challenge": another.json()["challenge"],
        "recovery_code": done["recovery_codes"][0]})
    assert replay.status_code == 400
    messages = []
    issue_request(actor["email"], "https://example.invalid", sender=lambda *args: messages.append(args) or True)
    token = parse_qs(urlsplit(messages[0][2]).fragment)["token"][0]
    with Session(get_engine()) as db:
        consume(db, token, "SyntheticNewPassword123")
    login = client.post("/api/auth/login", json={"email": actor["email"], "password": "SyntheticNewPassword123"})
    assert login.status_code == 202 and "token" not in login.json()


def test_failed_factor_budget_survives_new_challenges(mfa_client):
    client, actor, clock = mfa_client
    start, _ = enroll(client, clock)
    # A password-verified challenge is not permission to reset the actor budget.
    from web.services import mfa_service
    from web.database.engine import SessionLocal
    from web.auth import _get_user_by_id
    identity = _get_user_by_id(actor["id"])
    from web.services.mfa_crypto import totp
    actual_code = totp(base64.b32decode(start["secret"]), int(clock[0].timestamp()) // 30)
    wrong_code = str((int(actual_code) + 1) % 1000000).zfill(6)
    for attempt in range(10):
        with SessionLocal() as db:
            proof = mfa_service.login(db, identity)["challenge"]
        with SessionLocal() as db:
            with pytest.raises(Exception) as caught:
                mfa_service.verify_login(db, proof, code=wrong_code)
        assert caught.value.status_code == 400
    with SessionLocal() as db:
        with pytest.raises(Exception) as caught:
            mfa_service.login(db, identity)
    assert caught.value.status_code == 429  # No fresh challenge after exhaustion.


@pytest.mark.parametrize("path", ["status", "enroll", "login/verify", "step-up", "revoke"])
def test_mfa_wrong_methods_have_final_private_headers(mfa_client, path):
    client, _, _ = mfa_client
    response = client.put("/api/auth/mfa/" + path)
    assert response.status_code == 405
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
