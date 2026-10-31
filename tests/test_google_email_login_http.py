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
    from web.routes.mfa import router as mfa_router
    from web.settings import get_settings

    case = otp_case
    client_id = "synthetic-google-email.apps.googleusercontent.com"
    monkeypatch.setattr(get_settings(), "GOOGLE_CLIENT_ID", client_id)
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {**case.info, "aud": client_id, "email_verified": True, "iat": now, "exp": now + 3600}
    provider = SignedProvider(monkeypatch, claims)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(mfa_router, prefix="/api")
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


BROWSER_ORIGIN = "https://browser.example.invalid"
BROWSER_HEADERS = {"Origin": BROWSER_ORIGIN, "X-MetodoBase-Browser": "1"}
BROWSER_COOKIE = "__Host-mb_refresh"


def browser_transport(case, client, monkeypatch):
    """Use the real BrowserAuthRoute with a synthetic HTTPS cookie jar."""
    monkeypatch.setattr(case.settings, "BASE_URL", BROWSER_ORIGIN)
    client.base_url = BROWSER_ORIGIN
    assert client.cookies.get(BROWSER_COOKIE) is None


def assert_pending_browser(response, client, flag):
    assert response.status_code == 202
    result = response.json()
    assert result[flag] is True and result["session_mode"] == "browser"
    assert all(name not in result for name in ("token", "access_token", "refresh_token"))
    assert client.cookies.get(BROWSER_COOKIE) is None
    # A pending primary stage may only expire the previous cookie.
    cookies = response.headers.get_list("set-cookie")
    assert cookies and all("max-age=0" in item.lower() for item in cookies)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    return result


def assert_confirmed_browser(response, client, owner, actual_kind, role):
    from web import auth
    assert response.status_code == 200
    result = response.json()
    assert result["session_mode"] == "browser"
    assert result["tipo"] == actual_kind and result["role"] == role
    assert "refresh_token" not in result
    assert client.cookies.get(BROWSER_COOKIE)
    cookie_headers = response.headers.get_list("set-cookie")
    assert len(cookie_headers) == 1
    attributes = {part.strip().lower() for part in cookie_headers[0].split(";")[1:]}
    assert {"httponly", "secure", "samesite=strict", "path=/"}.issubset(attributes)
    assert not any(attribute.startswith("domain=") for attribute in attributes)
    assert not any(attribute == "max-age=0" for attribute in attributes)
    identity = auth.verificar_token(result["token"])
    assert identity["id"] == owner and identity["tipo"] == actual_kind and identity["role"] == role
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    return identity


@pytest.mark.parametrize("actual_kind,role,portal_kind", [
    ("usuario", "viewer", "gym"), ("gym", "owner", "usuario"),
])
@pytest.mark.parametrize("bound", [False, True], ids=["legacy", "bound"])
def test_browser_google_email_login_preserves_account_across_opposite_portals(
        google_http, monkeypatch, actual_kind, role, portal_kind, bound):
    """The portal's requested audience never changes the proven account."""
    from web.database.models import Usuario, UserRole

    case, client, provider = google_http
    owner = seed(case, binding=case.info["sub"] if bound else None)
    with case.sessions() as db:
        row = db.get(Usuario, owner)
        row.tipo = actual_kind
        row.role = UserRole(role)
        db.commit()
    browser_transport(case, client, monkeypatch)
    before = (1, int(bound), 0)
    issued = client.post("/api/auth/google", headers=BROWSER_HEADERS,
        json={"credential": provider.credential(), "tipo": portal_kind})
    stage = assert_pending_browser(issued, client, "email_verification_required")
    assert counts(case) == before
    verified = client.post("/api/auth/google/verify-email", headers=BROWSER_HEADERS,
        json={"challenge": stage["challenge"], "code": case.mail[-1][1]})
    assert_confirmed_browser(verified, client, owner, actual_kind, role)
    assert counts(case) == (1, int(bound), 1)
    with case.sessions() as db:
        persisted = db.get(Usuario, owner)
        assert persisted.tipo == actual_kind and persisted.role == UserRole(role)
    replay = client.post("/api/auth/google/verify-email", headers=BROWSER_HEADERS,
        json={"challenge": stage["challenge"], "code": case.mail[-1][1]})
    assert replay.status_code == 400
    assert replay.json()["detail"]["code"] == "google_email_code_invalid"
    assert all(name not in replay.json() for name in ("token", "access_token", "refresh_token"))
    assert counts(case) == (1, int(bound), 1)


def test_browser_google_email_login_waits_for_the_real_personal_factor(google_http, monkeypatch):
    """Email proof alone cannot create the refresh cookie when MFA is active."""
    from web.database.models import MfaCredential
    from web.services import mfa_service as mfa

    case, client, provider = google_http
    owner = seed(case, mfa=True)
    instant = datetime.now(timezone.utc).replace(microsecond=0)
    original_instant = mfa.instant
    monkeypatch.setattr(mfa, "instant", lambda now=None: instant if now is None else original_instant(now))
    factor_secret = b"S" * 20
    with case.sessions() as db:
        factor = db.get(MfaCredential, owner)
        factor.secret_ciphertext = mfa.encrypt(factor_secret, mfa.configuration(), mfa._aad(factor, factor.generation, "active"))
        db.commit()
    browser_transport(case, client, monkeypatch)
    issued = client.post("/api/auth/google", headers=BROWSER_HEADERS,
        json={"credential": provider.credential(), "tipo": "gym"})
    stage = assert_pending_browser(issued, client, "email_verification_required")
    verified = client.post("/api/auth/google/verify-email", headers=BROWSER_HEADERS,
        json={"challenge": stage["challenge"], "code": case.mail[-1][1]})
    pending_factor = assert_pending_browser(verified, client, "mfa_required")
    assert counts(case) == (1, 0, 0)

    async def synthetic_mfa_rate_limit(key, limit, window, **kwargs):
        # Only the transport budget is synthetic; factor verification and its
        # persisted proof/counter/token transactions execute unchanged.
        assert key.startswith("rl:mfa31:/api/auth/mfa/login/verify:")
        assert kwargs == {"use_redis": True, "sensitive": True}
        assert (limit, window) == (30, 300)
        return True, {"retry_after": 0}, True

    monkeypatch.setattr("web.rate_limiter_redis.check_rate_limit", synthetic_mfa_rate_limit)
    result = client.post("/api/auth/mfa/login/verify", headers=BROWSER_HEADERS,
        json={"challenge": pending_factor["challenge"],
              "code": mfa.totp(factor_secret, int(instant.timestamp()) // 30)})
    identity = assert_confirmed_browser(result, client, owner, "usuario", "viewer")
    assert identity["amr"] == ["google", "otp"] and identity["mfa_generation"] == 1
    assert counts(case) == (1, 0, 1)
