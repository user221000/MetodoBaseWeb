"""Browser admission and cookie boundaries for the Google email-code stage."""
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from web.browser_session import BrowserAuthRoute, COOKIE_POSTS
from web.settings import get_settings

ORIGIN = "https://browser.example.invalid"
HEADERS = {"Origin": ORIGIN, "X-MetodoBase-Browser": "1"}


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setattr(get_settings(), "BASE_URL", ORIGIN)
    app = FastAPI()
    router = APIRouter(route_class=BrowserAuthRoute)
    calls = []

    @router.post("/api/auth/google")
    async def start():
        calls.append("start")
        return JSONResponse({"email_verification_required": True,
            "challenge": "A" * 43, "expires_at": "2099-01-01T00:00:00Z",
            "masked_email": "p***@example.invalid"}, status_code=202)

    @router.post("/api/auth/google/verify-email")
    async def verify():
        calls.append("verify")
        return JSONResponse({"mfa_required": True, "challenge": "B" * 43,
            "expires_at": "2099-01-01T00:00:00Z", "methods": ["totp", "recovery_code"]},
            status_code=202)

    app.include_router(router)
    with TestClient(app, base_url=ORIGIN) as client:
        yield client, calls


@pytest.mark.parametrize("path,flag", [
    ("/api/auth/google", "email_verification_required"),
    ("/api/auth/google/verify-email", "mfa_required"),
])
def test_each_pending_stage_expires_the_old_cookie_without_issuing_a_session(transport, path, flag):
    client, calls = transport
    response = client.post(path, headers={**HEADERS, "Cookie": "__Host-mb_refresh=obsolete"}, json={})
    assert response.status_code == 202
    assert response.json()[flag] is True
    assert response.json()["session_mode"] == "browser"
    assert all(key not in response.json() for key in ("token", "access_token", "refresh_token"))
    cookie = response.headers["set-cookie"].lower()
    assert "max-age=0" in cookie and "httponly" in cookie and "secure" in cookie
    assert "samesite=strict" in cookie
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert calls == (["start"] if path.endswith("google") else ["verify"])


@pytest.mark.parametrize("path", ["/api/auth/google", "/api/auth/google/verify-email"])
def test_cross_origin_cannot_reach_credentials_mail_or_change_cookies(transport, path):
    client, calls = transport
    response = client.post(path, headers={**HEADERS, "Origin": "https://other.example.invalid"}, json={})
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert calls == []


def test_email_confirmation_uses_the_same_closed_browser_admission_list():
    assert "/api/auth/google/verify-email" in COOKIE_POSTS


def test_nonbrowser_email_challenge_keeps_legacy_cookie_free_transport(transport):
    client, _ = transport
    response = client.post("/api/auth/google", json={})
    assert response.status_code == 202
    assert response.json()["email_verification_required"] is True
    assert "session_mode" not in response.json()
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("variant,status", [
    ("query", 403), ("marker", 403), ("duplicate_origin", 403),
    ("content_type", 415), ("get", 405), ("slash", 307), ("neighbor", 404),
])
def test_confirmation_rejects_ambiguous_or_wrong_requests_before_handler_work(transport, variant, status):
    client, calls = transport
    path = "/api/auth/google/verify-email"
    headers = list(HEADERS.items())
    method = "POST"
    if variant == "query":
        path += "?untrusted=1"
    elif variant == "marker":
        headers = [(key, "0" if key == "X-MetodoBase-Browser" else value) for key, value in headers]
    elif variant == "duplicate_origin":
        headers.append(("Origin", ORIGIN))
    elif variant == "content_type":
        headers.append(("Content-Type", "text/plain"))
    elif variant == "get":
        method = "GET"
    elif variant == "slash":
        path += "/"
    elif variant == "neighbor":
        path += "-extra"
    response = client.request(method, path, headers=headers, json={}, follow_redirects=False)
    assert response.status_code == status
    assert calls == []
    assert "set-cookie" not in response.headers
