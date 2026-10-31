"""Exact auth router, signed provider JWTs and current-schema RAM SQLite.

Only provider HTTP, Redis wire and email delivery are synthetic. MFA and token
minting execute unchanged; no real provider or mailbox is contacted.
"""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from tests.google33_signed_provider import SignedProvider
from tests.test_google_email_login import (
    database_schema, isolated_database, otp_case, counts, seed,
)


@pytest.fixture
def google_http(otp_case, monkeypatch):
    from web.routes.auth import router
    from web.settings import get_settings

    case = otp_case
    client_id = "synthetic-google-email.apps.googleusercontent.com"
    monkeypatch.setattr(get_settings(), "GOOGLE_CLIENT_ID", client_id)
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {**case.info, "aud": client_id, "email_verified": True, "iat": now, "exp": now + 3600}
    provider = SignedProvider(monkeypatch, claims)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app, raise_server_exceptions=False) as client:
        yield case, client, provider


@pytest.mark.parametrize("kind,role", [("usuario", "viewer"), ("gym", "owner")])
def test_signed_google_primary_requires_email_before_new_account_or_tokens(google_http, kind, role):
    from web import auth
    from web.database.models import GymProfile, PlanSuscripcion

    case, client, provider = google_http
    issued = client.post("/api/auth/google", json={"credential": provider.credential(), "tipo": kind})
    assert issued.status_code == 202
    stage = issued.json()
    assert set(stage) == {"email_verification_required", "challenge", "expires_at", "masked_email"}
    assert stage["email_verification_required"] is True and counts(case) == (0, 0, 0)
    assert "no-store" in issued.headers["cache-control"]
    verified = client.post("/api/auth/google/verify-email",
        json={"challenge": stage["challenge"], "code": case.mail[-1][1]})
    assert verified.status_code == 200
    result = verified.json()
    assert result["mfa_required"] is False and result["role"] == role
    assert counts(case) == (1, 1, 1)
    identity = auth.verificar_token(result["token"])
    assert identity["email"] == case.info["email"] and identity["tipo"] == kind
    with case.sessions() as db:
        assert db.scalar(select(func.count()).select_from(GymProfile)) == int(kind == "gym")
        assert db.scalar(select(func.count()).select_from(PlanSuscripcion)) == 5 * int(kind == "gym")
    replay = client.post("/api/auth/google/verify-email",
        json={"challenge": stage["challenge"], "code": case.mail[-1][1]})
    assert replay.status_code == 400
    assert all(key not in replay.json() for key in ("token", "refresh_token", "challenge"))


@pytest.mark.parametrize("factor_enabled", [False, True])
def test_legacy_mail_proof_keeps_the_existing_account_and_its_mfa(google_http, factor_enabled):
    from web import auth

    case, client, provider = google_http
    owner = seed(case, mfa=factor_enabled)
    issued = client.post("/api/auth/google", json={"credential": provider.credential(), "tipo": "gym"})
    assert issued.status_code == 202 and counts(case) == (1, 0, 0)
    stage = issued.json()
    verified = client.post("/api/auth/google/verify-email",
        json={"challenge": stage["challenge"], "code": case.mail[-1][1]})
    assert verified.status_code == (202 if factor_enabled else 200)
    body = verified.json()
    assert body["mfa_required"] is factor_enabled
    if factor_enabled:
        assert body["methods"] == ["totp", "recovery_code"]
        assert body["challenge"] != stage["challenge"]
        assert all(key not in body for key in ("token", "refresh_token"))
        assert counts(case) == (1, 0, 0)
    else:
        identity = auth.verificar_token(body["token"])
        assert identity["id"] == owner and identity["tipo"] == "usuario"
        assert counts(case) == (1, 0, 1)


def test_a_wrong_google_audience_never_sends_mail_or_stores_an_otp(google_http):
    case, client, provider = google_http
    bad_claims = {**provider.claims, "aud": "another-application"}
    response = client.post("/api/auth/google", json={"credential": provider.credential(claims=bad_claims)})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "google_identity_invalid"
    assert case.mail == [] and case.cache.rows == {} and counts(case) == (0, 0, 0)


def test_missing_email_configuration_cannot_fall_back_to_the_old_google_login(google_http, monkeypatch):
    case, client, provider = google_http
    seed(case)
    monkeypatch.setattr(case.settings, "RESEND_API_KEY", "")
    response = client.post("/api/auth/google", json={"credential": provider.credential()})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "google_email_unavailable"
    assert case.mail == [] and case.cache.rows == {} and counts(case) == (1, 0, 0)
