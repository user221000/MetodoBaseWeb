"""Actual SaaS/API factories, current37 schema and provider SDK doubles only."""
import json
import re
from datetime import timedelta
from html import unescape
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy.orm import Session

from tests import account_security37_http
from tests.account_security37_fixtures import NEW_PASSWORD
from tests.followup34_http import PASSWORD
from web.database.models import MfaCredential, Usuario
from web.services import mfa_service as mfa

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http

PREFIX = "/api/account/security"


def headers(case):
    from web.settings import get_settings
    result = {"Origin": get_settings().BASE_URL, "X-MetodoBase-Browser": "1"}
    if case["raw"].cookies.get("_csrf"):
        result["X-CSRF-Token"] = case["raw"].cookies.get("_csrf")
    return result


def provider(monkeypatch):
    import resend

    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-account37-no-send")
    packets = []
    monkeypatch.setattr(resend.Emails, "send", lambda params: packets.append(dict(params)) or {"id": "synthetic-provider-ack"})
    return packets


def token_from_packet(packet):
    link = unescape(re.search('href="([^"]+)"', packet["html"]).group(1))
    parsed = urlsplit(link)
    assert parsed.path == "/auth/verify-email" and not parsed.query
    return parse_qs(parsed.fragment)["token"][0]


def private(response):
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "accounts.google.com" not in response.headers["content-security-policy"]


def test_explicit_contact_request_provider_ack_public_confirmation_and_replay(account_http, monkeypatch):
    case = account_http
    packets = provider(monkeypatch)
    status = case["raw"].get(PREFIX)
    assert status.status_code == 200 and status.json()["email_verified"] is False
    private(status)
    response = case["raw"].post(PREFIX + "/email/request", json={}, headers=headers(case))
    assert response.status_code == 200 and response.json()["delivery"] == "provider_accepted"
    private(response)
    assert len(packets) == 1
    token = token_from_packet(packets[0])
    assert token not in response.text
    case["raw"].headers.pop("Authorization")
    # Token possession alone confirms contact, without an auth session/cookie.
    case["raw"].cookies.clear()
    response = case["raw"].post(PREFIX + "/email/confirm", json={"token": token}, headers=headers(case))
    assert response.status_code == 200 and response.json() == {"code": "account_email_confirmed", "email_verified": True}
    private(response)
    assert not any("mb_refresh" in value for value in response.headers.get_list("set-cookie"))
    assert token not in response.text
    assert case["raw"].post(PREFIX + "/email/confirm", json={"token": token}, headers=headers(case)).status_code == 400
    assert case["raw"].get("/api/auth/me").status_code == 401


def test_public_get_does_not_consume_and_contains_no_auth_bootstrap(account_http, monkeypatch):
    case = account_http
    packets = provider(monkeypatch)
    assert case["raw"].post(PREFIX + "/email/request", json={}, headers=headers(case)).status_code == 200
    token = token_from_packet(packets[0])
    with Session(case["admin"]) as db:
        before = db.get(Usuario, case["user"]).email_verification_hash
    page = case["raw"].get("/auth/verify-email")
    assert page.status_code == 200
    private(page)
    assert "email-verification37.js" in page.text and "api.js" not in page.text
    assert token not in page.text and "Synthetic manager" not in page.text
    with Session(case["admin"]) as db:
        assert db.get(Usuario, case["user"]).email_verification_hash == before


def test_foreign_bearer_cannot_retarget_email_confirmation(account_http, monkeypatch):
    case = account_http
    packets = provider(monkeypatch)
    assert case["raw"].post(PREFIX + "/email/request", json={}, headers=headers(case)).status_code == 200
    token = token_from_packet(packets[0])
    # The persisted member has its own real password login, independent of A.
    with Session(case["admin"]) as db:
        email = db.get(Usuario, case["member"]).email
    response = case["raw"].post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    case["raw"].headers["Authorization"] = "Bearer " + response.json()["token"]
    response = case["raw"].post(PREFIX + "/email/confirm", json={"token": token}, headers=headers(case))
    assert response.status_code == 200
    assert case["raw"].get("/api/auth/me").json()["id"] == case["member"]
    with Session(case["admin"]) as db:
        assert db.get(Usuario, case["user"]).email_verified_at is not None
        assert db.get(Usuario, case["member"]).email_verified_at is None


@pytest.mark.parametrize("raw", ['{"token":"AAA","token":"BBB"}', '{"token":NaN}', '{"token":"AAA","email":"private-marker"}', '[]'])
def test_closed_duplicate_nonfinite_body_is_not_reflected(account_http, raw):
    case = account_http
    response = case["raw"].post(PREFIX + "/email/confirm", content=raw,
                               headers={**headers(case), "Content-Type": "application/json"})
    assert response.status_code == 422
    private(response)
    assert "private-marker" not in response.text and "AAA" not in response.text and "BBB" not in response.text


def test_admission_precedes_optional_bearer_lookup_and_finite_neighbors(account_http, monkeypatch):
    from web import auth
    case = account_http
    calls = []
    monkeypatch.setattr(auth, "verificar_token", lambda *args: calls.append(True))
    for path in (PREFIX + "/email/request", PREFIX + "/password", PREFIX + "/email/confirm"):
        response = case["raw"].post(path, json={}, headers={"Origin": "https://foreign.example.invalid", "X-MetodoBase-Browser": "1"})
        assert response.status_code == 403
        private(response)
    assert calls == []
    # The new finite path does not admit neighboring prefixes or mutate cookies.
    from web.account_security_paths import (
        is_account_security_post,
        is_account_security_private,
    )
    assert not is_account_security_private(PREFIX + "/email/confirm-extra")
    assert not is_account_security_post(PREFIX + "/password-extra")


def test_body_limit_and_missing_header_do_not_touch_provider(account_http, monkeypatch):
    case = account_http
    packets = provider(monkeypatch)
    response = case["raw"].post(PREFIX + "/email/request", json={}, headers={"Origin": "http://127.0.0.1:8765"})
    assert response.status_code == 403
    response = case["raw"].post(PREFIX + "/email/confirm", content=json.dumps({"token": "A" * 9000}),
                               headers={**headers(case), "Content-Type": "application/json"})
    assert response.status_code == 413
    assert packets == []


def test_password_uses_real_primary_proof_current_totp_and_revokes_cookie(account_http, monkeypatch):
    from web.services.mfa_crypto import decrypt, totp
    case = account_http
    # Advance only this explicit test clock beyond setup's already used TOTP.
    original_clock = mfa.instant
    now = original_clock() + timedelta(seconds=31)
    monkeypatch.setattr(mfa, "instant", lambda value=None: original_clock(now if value is None else value))
    proof = case["raw"].post("/api/auth/mfa/reauth", json={"password": PASSWORD}, headers=headers(case))
    assert proof.status_code == 200
    with Session(case["admin"]) as db:
        row = db.get(MfaCredential, case["user"])
        secret = decrypt(row.secret_ciphertext, mfa.configuration(), mfa._aad(row, row.generation, "active"))
    response = case["raw"].post(PREFIX + "/password", headers=headers(case), json={
        "reauthentication_token": proof.json()["reauthentication_token"], "new_password": NEW_PASSWORD,
        "confirm_password": NEW_PASSWORD, "code": totp(secret, int(now.timestamp()) // 30)})
    assert response.status_code == 200 and response.json()["sessions_revoked"] is True
    assert "token" not in response.json() and "refresh_token" not in response.json()
    private(response)
    assert any("mb_refresh_dev=" in value and "Max-Age=0" in value for value in response.headers.get_list("set-cookie"))
    assert case["raw"].get("/api/auth/me").status_code == 401
    with Session(case["admin"]) as db:
        user = db.get(Usuario, case["user"])
        assert user.session_version == 2 and db.get(MfaCredential, case["user"]).enabled_at is not None
