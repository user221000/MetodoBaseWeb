"""Actual browser transport in both factories, with persisted identity and MFA.

Synthetic HTTPS TestClient traffic never contacts an external origin/provider.
Tokens remain local test variables and never become assertion diagnostics.
"""
import base64
import time
import uuid

import pytest

from tests import followup34_http as historical
from tests import test_nutrition35_http as current
from web import auth
from web.settings import get_settings

followup_db = current.followup_db
followup_http = historical.followup_http
ORIGIN = "https://browser.example.invalid"
HEADERS = {"Origin": ORIGIN, "X-MetodoBase-Browser": "1"}


@pytest.fixture
def browser(followup_http, monkeypatch):
    raw = followup_http["raw"]
    monkeypatch.setattr(get_settings(), "BASE_URL", ORIGIN)
    raw.base_url = ORIGIN
    return followup_http


def private(response):
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"


def account(case, *, browser_mode=False):
    email = uuid.uuid4().hex+"@example.invalid"
    response = case["raw"].post("/api/auth/registro", json={"email": email, "password": historical.PASSWORD,
        "nombre": "Synthetic browser account", "tipo": "usuario"}, headers=HEADERS if browser_mode else {})
    assert response.status_code == 200
    return email, response


def post(case, path, payload=None, **kwargs):
    return case["raw"].post(path, json={} if payload is None else payload, headers=HEADERS, **kwargs)


def cookie(case):
    value = case["raw"].cookies.get("__Host-mb_refresh")
    assert isinstance(value, str) and value
    return value


def pair(response):
    assert response.status_code == 200
    data = response.json()
    assert data.get("session_mode") == "browser"
    assert isinstance(data.get("token"), str) and data["token"]
    assert "refresh_token" not in data
    private(response)
    return data["token"]


def test_actual_cookie_rotation_preserves_resource_bearer_boundary(browser):
    email, _ = account(browser)
    login = post(browser, "/api/auth/login", {"email": email, "password": historical.PASSWORD})
    access = pair(login)
    initial = cookie(browser)
    header = login.headers["set-cookie"].lower()
    assert "secure" in header and "httponly" in header and "samesite=strict" in header and "path=/" in header
    assert "domain=" not in header
    browser["raw"].headers.pop("Authorization", None)
    assert browser["raw"].get("/api/auth/me").status_code == 401
    assert browser["raw"].get("/api/auth/me", headers={"Authorization": "Bearer "+access}).status_code == 200
    rotated = post(browser, "/api/auth/refresh")
    renewed = pair(rotated)
    assert cookie(browser) != initial
    assert auth.verificar_refresh_token(initial) is None
    assert auth.verificar_token(renewed) is not None


def test_migration_is_explicit_and_legacy_JSON_contract_is_unchanged(browser):
    _, registered = account(browser)
    legacy = registered.json()
    assert legacy.get("refresh_token") and "session_mode" not in legacy
    old = legacy["refresh_token"]
    assert all(not value.startswith("__Host-mb_refresh=") for value in registered.headers.get_list("set-cookie"))
    # Cookie refresh never accepts a legacy proof in its body.
    denied = post(browser, "/api/auth/refresh", {"refresh_token": old})
    assert denied.status_code == 422
    assert auth.verificar_refresh_token(old) is not None
    migrated = post(browser, "/api/auth/browser/migrate", {"refresh_token": old})
    pair(migrated)
    assert auth.verificar_refresh_token(old) is None
    assert auth.verificar_refresh_token(cookie(browser)) is not None


def test_actual_logout_confirms_revocation_and_absence_is_truthful(browser):
    _, registered = account(browser, browser_mode=True)
    access = pair(registered)
    proof = cookie(browser)
    browser["raw"].headers.pop("Authorization", None)
    response = post(browser, "/api/auth/browser/logout")
    assert response.status_code == 200
    assert response.json() == {"success": True, "server_confirmed": True, "session_mode": "browser"}
    private(response)
    assert auth.verificar_token(access) is None and auth.verificar_refresh_token(proof) is None
    assert browser["raw"].cookies.get("__Host-mb_refresh") is None
    again = post(browser, "/api/auth/browser/logout")
    assert again.status_code == 200 and again.json()["server_confirmed"] is False


@pytest.mark.parametrize("variant", ["origin", "header", "content-type", "query", "duplicate-origin"])
def test_rejected_browser_boundaries_precede_authentication_and_cookie_mutation(browser, monkeypatch, variant):
    _, registered = account(browser, browser_mode=True)
    pair(registered)
    proof = cookie(browser)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Rejected browser boundary reached authentication")

    monkeypatch.setattr(auth, "verificar_credenciales", forbidden)
    headers = {**HEADERS, "Content-Type": "application/json"}
    path = "/api/auth/login"
    if variant == "origin":
        headers["Origin"] = "https://other.example.invalid"
    elif variant == "header":
        headers["X-MetodoBase-Browser"] = "0"
    elif variant == "content-type":
        headers["Content-Type"] = "text/plain"
    elif variant == "query":
        path += "?unexpected=1"
    else:
        headers = list(headers.items())+[("Origin", ORIGIN)]
    response = browser["raw"].post(path, content='{}', headers=headers)
    assert response.status_code == (415 if variant == "content-type" else 403)
    assert calls == []
    private(response)
    assert all(not value.startswith("__Host-mb_refresh=") for value in response.headers.get_list("set-cookie"))
    assert cookie(browser) == proof


def test_unavailable_cookie_is_distinct_from_unconfirmed_rotation(browser, monkeypatch):
    browser["raw"].cookies.clear()
    missing = post(browser, "/api/auth/refresh")
    assert missing.status_code == 401 and missing.json()["detail"]["code"] == "browser_session_unavailable"
    private(missing)
    _, registered = account(browser, browser_mode=True)
    pair(registered)

    def unavailable(*args, **kwargs):
        raise RuntimeError("Synthetic transport unavailable")

    monkeypatch.setattr(auth, "rotar_refresh_token", unavailable)
    response = post(browser, "/api/auth/refresh")
    assert response.status_code == 503 and response.json()["detail"]["code"] == "browser_session_unconfirmed"
    assert "server_confirmed" not in response.json() and "Synthetic" not in response.text
    private(response)


def test_MFA_challenge_has_no_pair_and_expires_old_cookie(browser):
    _, registered = account(browser, browser_mode=True)
    pair(registered)
    email = browser["client"].principal["email"]
    response = post(browser, "/api/auth/login", {"email": email, "password": historical.PASSWORD})
    assert response.status_code == 202
    data = response.json()
    assert set(data) == {"mfa_required", "challenge", "expires_at", "methods", "session_mode"}
    assert data["mfa_required"] is True and data["session_mode"] == "browser"
    assert browser["raw"].cookies.get("__Host-mb_refresh") is None
    private(response)


def test_duplicate_cookie_does_not_choose_a_proof(browser):
    _, registered = account(browser, browser_mode=True)
    pair(registered)
    proof = cookie(browser)
    headers = {**HEADERS, "Cookie": "__Host-mb_refresh="+proof+"; __Host-mb_refresh="+proof}
    response = browser["raw"].post("/api/auth/refresh", json={}, headers=headers)
    assert response.status_code == 401 and response.json()["detail"]["code"] == "browser_session_unavailable"
    assert auth.verificar_refresh_token(proof) is not None


def test_closed_JSON_does_not_echo_input_or_accept_browser_body_refresh(browser):
    sentinel = "synthetic-private-body-sentinel"
    response = post(browser, "/api/auth/login", [{"password": sentinel}])
    assert response.status_code == 422 and sentinel not in response.text
    private(response)
    response = browser["raw"].post("/api/auth/browser/migrate", content='{"refresh_token":"x","refresh_token":"y"}',
                                  headers={**HEADERS, "Content-Type": "application/json"})
    assert response.status_code == 422
    private(response)


def test_actual_MFA_enrollment_ACK_and_factor_pair_use_the_same_transport(browser):
    from web.services.mfa_crypto import totp

    email, registered = account(browser, browser_mode=True)
    access = pair(registered)
    raw = browser["raw"]
    raw.headers["Authorization"] = "Bearer "+access
    reauth = post(browser, "/api/auth/mfa/reauth", {"password": historical.PASSWORD})
    assert reauth.status_code == 200 and "session_mode" not in reauth.json()
    enrollment = post(browser, "/api/auth/mfa/enroll", {"reauthentication_token": reauth.json()["reauthentication_token"]})
    assert enrollment.status_code == 200 and "session_mode" not in enrollment.json()
    data = enrollment.json()
    code = totp(base64.b32decode(data["secret"]), int(time.time())//30)
    confirmed = post(browser, "/api/auth/mfa/enroll/confirm", {"enrollment_id": data["enrollment_id"], "code": code})
    assert confirmed.status_code == 200
    kit = confirmed.json()
    assert "session_mode" not in kit and "token" not in kit and "refresh_token" not in kit
    assert raw.cookies.get("__Host-mb_refresh") is None
    assert auth.verificar_token(access) is None
    challenge = post(browser, "/api/auth/login", {"email": email, "password": historical.PASSWORD})
    assert challenge.status_code == 202
    verified = post(browser, "/api/auth/mfa/login/verify", {"challenge": challenge.json()["challenge"],
                                                          "recovery_code": kit["recovery_codes"][0]})
    renewed = pair(verified)
    assert auth.verificar_token(renewed)["amr"] == ["pwd", "recovery"]
    assert auth.verificar_refresh_token(cookie(browser))["amr"] == ["pwd", "recovery"]


def test_legacy_refresh_still_rotates_JSON_and_never_issues_a_refresh_cookie(browser):
    _, registered = account(browser)
    result = browser["raw"].post("/api/auth/refresh", json={"refresh_token": registered.json()["refresh_token"]})
    assert result.status_code == 200
    data = result.json()
    assert set(data) == {"token", "refresh_token"}
    assert auth.verificar_refresh_token(data["refresh_token"]) is not None
    assert all(not value.startswith("__Host-mb_refresh=") for value in result.headers.get_list("set-cookie"))


def test_unknown_commit_logout_never_claims_confirmed_revocation(browser, monkeypatch):
    _, registered = account(browser, browser_mode=True)
    access = pair(registered)
    original = auth.revocar_refresh_tokens_usuario

    def lost_ack(identity):
        original(identity)
        raise RuntimeError("Synthetic revocation commit acknowledgement unavailable")

    monkeypatch.setattr(auth, "revocar_refresh_tokens_usuario", lost_ack)
    response = post(browser, "/api/auth/browser/logout")
    assert response.status_code == 503 and response.json()["detail"]["code"] == "browser_session_unconfirmed"
    assert "server_confirmed" not in response.json() and "Synthetic" not in response.text
    assert auth.verificar_token(access) is None
    assert browser["raw"].cookies.get("__Host-mb_refresh") is None
    private(response)


def test_insecure_nonlocal_configuration_stops_before_authentication(browser, monkeypatch):
    monkeypatch.setattr(get_settings(), "BASE_URL", "http://nonlocal.example.invalid")
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Insecure configuration reached authentication")

    monkeypatch.setattr(auth, "verificar_credenciales", forbidden)
    response = post(browser, "/api/auth/login", {"email": "synthetic@example.invalid", "password": historical.PASSWORD})
    assert response.status_code == 503 and calls == []
    assert all(not value.startswith("__Host-mb_refresh=") for value in response.headers.get_list("set-cookie"))
    private(response)
