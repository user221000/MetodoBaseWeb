"""Current35 composition of original Google criteria and browser ACK transport.

Real password/subject binding and signed JWKS transport are preserved. The
historical33 database fixture and tokeninfo-only31 canaries remain unchanged.
"""
import uuid

from tests import test_google33_headers as headers33
from tests import test_google33_http as google33
from tests import test_nutrition35_http as current35
from tests.ci_web41 import google_mail_http_fixture as mail_http
from web.settings import get_settings

google_db = current35.followup_db
google_http = google33.google_http
test_real_binding_changes_session_not_contacts_or_personal_space = google33.test_real_binding_changes_session_not_contacts_or_personal_space
test_wrong_password_and_exact_access_binding = google33.test_wrong_password_and_exact_access_binding
test_commit_uncertainty_never_returns_proof_or_session = google33.test_commit_uncertainty_never_returns_proof_or_session
test_active_mfa_cannot_be_removed_by_google_or_link = google33.test_active_mfa_cannot_be_removed_by_google_or_link
test_explicit_unlink_retains_owner_history_and_only_same_owner_can_relink = google33.test_explicit_unlink_retains_owner_history_and_only_same_owner_can_relink
test_link_dependency_closes_before_response_and_never_reports_uncertain_ack = headers33.test_link_dependency_closes_before_response_and_never_reports_uncertain_ack


def test_browser_Google_binding_ACK_and_primary_pair_are_distinct(google_http, monkeypatch):
    c = google_http
    client = c["client"]
    origin = "https://browser.example.invalid"
    monkeypatch.setattr(get_settings(), "BASE_URL", origin)
    client.base_url = origin
    browser = {"Origin": origin, "X-MetodoBase-Browser": "1"}
    login = client.post("/api/auth/login", headers=browser, json={"email": c["email"], "password": google33.PASSWORD})
    assert login.status_code == 200
    assert login.json().get("session_mode") == "browser" and "refresh_token" not in login.json()
    assert client.cookies.get("__Host-mb_refresh")
    authenticated = {**browser, "Authorization": "Bearer "+login.json()["token"]}
    # Each synthetic provider subject must remain independent across factories
    # that share this module's database, as in the original start() helper.
    c["google"]["sub"] = str(int(google33.SUBJECT)+int(uuid.uuid4().hex[:6], 16))
    issued = client.post("/api/auth/google/link/start", headers=authenticated,
        json={"password": google33.PASSWORD, "google_credential": c["credential"]()})
    assert issued.status_code == 200 and "session_mode" not in issued.json()
    confirmed = client.post("/api/auth/google/link/confirm", headers=authenticated,
        json={"intent": issued.json()["intent"], "confirm": True})
    assert confirmed.status_code == 200
    assert all(key not in confirmed.json() for key in ["token", "refresh_token", "session_mode"])
    assert client.cookies.get("__Host-mb_refresh") is None
    # Default browser headers reach both real email stages; no response adapter.
    client.headers.update(browser)
    pending_email = mail_http.begin(c)
    assert pending_email.json().get("session_mode") == "browser"
    assert client.cookies.get("__Host-mb_refresh") is None
    assert "https://accounts.google.com/gsi/client" in pending_email.headers["content-security-policy"]
    before_verification = mail_http.counts(c)
    wrong_origin = client.post("/api/auth/google/verify-email",
        headers={**browser, "Origin": "https://other.example.invalid"},
        json={"challenge": pending_email.json()["challenge"], "code": c["mail_transport"].mail[-1][1]})
    assert wrong_origin.status_code == 403
    assert client.cookies.get("__Host-mb_refresh") is None
    assert mail_http.counts(c) == before_verification
    code = c["mail_transport"].mail[-1][1]
    wrong_code = mail_http.verify(c, pending_email, code="000000" if code != "000000" else "000001")
    assert wrong_code.status_code == 400
    assert wrong_code.json()["detail"]["code"] == "google_email_code_invalid"
    assert not {"token", "access_token", "refresh_token"} & wrong_code.json().keys()
    assert client.cookies.get("__Host-mb_refresh") is None
    assert mail_http.counts(c) == before_verification
    primary = mail_http.verify(c, pending_email)
    assert primary.status_code == 200
    assert primary.json().get("session_mode") == "browser" and "refresh_token" not in primary.json()
    assert client.cookies.get("__Host-mb_refresh")
    assert primary.headers["cache-control"] == "no-store"
    assert primary.headers["referrer-policy"] == "no-referrer"
    assert "https://accounts.google.com/gsi/client" in primary.headers["content-security-policy"]
    before = len(c["calls"])
    rejected = client.post("/api/auth/google", headers={**browser, "Origin": "https://other.example.invalid"},
        json={"credential": c["credential"]()})
    assert rejected.status_code == 403 and len(c["calls"]) == before
    after_pair = mail_http.counts(c)
    replay = mail_http.verify(c, pending_email)
    assert replay.status_code == 400
    assert replay.json()["detail"]["code"] == "google_email_code_invalid"
    assert not {"token", "access_token", "refresh_token"} & replay.json().keys()
    assert client.cookies.get("__Host-mb_refresh") is None
    assert mail_http.counts(c) == after_pair
    for refused in (wrong_origin, wrong_code, replay):
        assert refused.headers["cache-control"] == "no-store"
        assert refused.headers["referrer-policy"] == "no-referrer"


def test_link_boundaries_include_the_public_inert_page_status(google_http):
    client = google_http["client"]
    for method, path in [("GET", "/api/auth/google/link/start"), ("GET", "/api/auth/google/link/confirm"),
            ("GET", "/api/auth/google/link/unlink"), ("POST", "/api/auth/google/link/status"),
            ("POST", "/api/auth/google/link/start"), ("POST", "/api/auth/google/link/confirm"),
            ("POST", "/api/auth/google/link/unlink"), ("GET", "/api/auth/google/link/status"),
            ("GET", "/api/auth/google/link/status/"), ("GET", "/cuenta/google"), ("GET", "/cuenta/google/")]:
        response = client.request(method, path, follow_redirects=False)
        if path == "/cuenta/google":
            assert response.status_code == 200
            assert "<html" in response.text and "token" not in response.headers
        elif path == "/cuenta/google/":
            assert response.status_code == 307
            assert response.headers["location"] == str(client.base_url.join("/cuenta/google"))
        else:
            assert response.status_code in (307, 401, 404, 405, 422)
        assert response.headers["Cache-Control"] == "no-store" and response.headers["Referrer-Policy"] == "no-referrer"
        policy = response.headers["Content-Security-Policy"]
        assert "unsafe-inline" not in policy and "cdn.jsdelivr.net" not in policy and "default-src 'none'" in policy
        assert ("accounts.google.com/gsi/client" in policy) == path.startswith("/cuenta/google")
    for path in ("/cuenta/google-extra", "/api/auth/google/link/status-extra", "/api/auth/google/linker", "/api/auth/google/links"):
        response = client.get(path)
        assert response.status_code == 404 and response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_verified_legacy_Google_primary_failure_retains_private_normal_CSP(google_http, monkeypatch):
    from web.routes import auth
    c = google_http
    issued = google33.start(c)
    assert issued.status_code == 200
    confirmed = c["client"].post("/api/auth/google/link/confirm", headers=c["headers"],
        json={"intent": issued.json()["intent"], "confirm": True})
    assert confirmed.status_code == 200

    seam = []

    def unavailable(*args, **kwargs):
        seam.append(True)
        raise RuntimeError("Synthetic primary failure without private values")

    monkeypatch.setattr(auth, "_primary_result", unavailable)
    pending_email = mail_http.begin(c)
    assert seam == []
    response = mail_http.verify(c, pending_email)
    assert seam == [True]
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "https://accounts.google.com/gsi/client" in response.headers["content-security-policy"]
    assert "Synthetic" not in response.text
