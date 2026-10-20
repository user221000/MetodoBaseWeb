"""Own security shells and real ASGI browser/MFA UI, current37 SQLite only."""
import base64
import importlib
import json
import queue
import re
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.account_security37_http import account37_engine, account_http, followup_db

__all__ = ["account37_engine", "account_http", "followup_db"]
ROOT = Path(__file__).resolve().parents[1]


def private(response, *, gis=False):
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    policy = response.headers["Content-Security-Policy"]
    assert "default-src 'none'" in policy and "unsafe-inline" not in policy
    assert ("accounts.google.com/gsi/client" in policy) is gis
    assert "cdn.jsdelivr.net" not in policy


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("path", ["/cuenta/seguridad", "/mi-seguridad"])
def test_own_shell_finite_GIS_privacy_alias_methods_and_neighbors(factory, path):
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        for suffix in ("", "/"):
            response = client.get(path + suffix)
            assert response.status_code == 200
            private(response, gis=True)
            assert "data-account-security37" in response.text and "r37account1" in response.text
            assert "account-security37.js" in response.text
        response = client.head(path)
        assert response.status_code == 405
        private(response, gis=True)
        response = client.get(path + "//", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["Location"] == "http://testserver" + path
        private(response)
        for adjacent in (path + "x", path + "/extra"):
            response = client.get(adjacent)
            assert response.status_code == 404
            assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
            # The preexisting global policy is retained on neighbors, rather
            # than granting the new fixed GIS shell policy to another route.
            assert "cdn.jsdelivr.net" in response.headers["Content-Security-Policy"]
        for endpoint in ("/api/account/security", "/api/account/security/password", "/auth/verify-email"):
            response = client.get(endpoint)
            private(response)
        response = client.get("/auth/verify-email")
        assert "api.js" not in response.text and "email-verification37.js" in response.text


@pytest.mark.parametrize("scenario", ["success", "lost-ack", "late-ack"])
def test_actual_UI_MFA_cookie_email_password_commit_and_late_ACK(account_http, monkeypatch, scenario):
    import resend

    from web.auth import verify_password
    from web.database.models import MfaCredential, Usuario
    from web.services import mfa_service
    from web.services.mfa_crypto import totp
    from web.settings import get_settings

    case = account_http
    raw = case["raw"]
    raw.headers.pop("Authorization", None)
    raw.cookies.clear()
    origin = "https://testserver"
    monkeypatch.setattr(get_settings(), "BASE_URL", origin)
    monkeypatch.setattr(raw, "base_url", httpx.URL(origin))
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-no-send-account37-ui")
    packets = []
    monkeypatch.setattr(resend.Emails, "send", lambda params: packets.append(True) or {"id": "synthetic-account-ui-ack"})
    now = datetime.now(UTC)
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda value=None: actual(now if value is None else value))
    password, new_password = "Synthetic own account UI password 37!", "Synthetic changed account UI password 37!"
    email = "account-ui-" + uuid.uuid4().hex + "@example.invalid"
    registered = raw.post("/api/auth/registro", json={"email": email, "password": password, "nombre": "Synthetic own", "tipo": "usuario"})
    assert registered.status_code == 200
    raw.headers["Authorization"] = "Bearer " + registered.json()["token"]
    principal = raw.get("/api/auth/me").json()["id"]
    proof = raw.post("/api/auth/mfa/reauth", json={"password": password})
    enrollment = raw.post("/api/auth/mfa/enroll", json={"reauthentication_token": proof.json()["reauthentication_token"]})
    value = enrollment.json()
    confirmed = raw.post("/api/auth/mfa/enroll/confirm", json={"enrollment_id": value["enrollment_id"], "code": totp(base64.b32decode(value["secret"]), int(now.timestamp()) // 30)})
    assert confirmed.status_code == 200
    recovery = confirmed.json()["recovery_codes"]
    raw.headers.pop("Authorization", None)
    raw.cookies.clear()
    shell = raw.get("/cuenta/seguridad")
    csrf = unescape(re.search('name="csrf-token" content="([^"]*)"', shell.text).group(1))
    boot = {"origin": origin, "csrf": csrf, "email": email, "password": password, "new_password": new_password,
            "login_recovery": recovery[0], "change_recovery": recovery[1], "scenario": scenario}
    # Existing registration welcome mail belongs to setup, not this UI request.
    setup_packets = len(packets)
    assert setup_packets == 1
    process = subprocess.Popen(["node", "tests/e2e/account_security37_http_worker.cjs"], cwd=ROOT,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding="utf8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    incoming = queue.Queue()
    def read_lines():
        for line in process.stdout:
            incoming.put(line)
        incoming.put(None)
    reader = threading.Thread(target=read_lines, daemon=True)
    reader.start()
    result = None
    try:
        while True:
            line = incoming.get(timeout=45)
            assert line is not None, "Worker stopped without its safe result"
            request = json.loads(line)
            if request["type"] == "result":
                result = request
                break
            if request["command"] == "bootstrap":
                data = boot
            else:
                assert request["command"] == "http" and request["url"].startswith("/api/") and ":" not in request["url"]
                options = request["options"]
                response = raw.request(options["method"], request["url"], content=options.get("body"), headers=options.get("headers"))
                status, response_body = response.status_code, response.text
                if scenario == "lost-ack" and request["url"] in {"/api/account/security/email/request", "/api/account/security/password"}:
                    assert status == 200
                    status, response_body = 503, json.dumps({"detail": {"code": "account_email_delivery_unconfirmed" if request["url"].endswith("request") else "account_security_unconfirmed"}})
                data = {"status": status, "body": response_body, "headers": dict(response.headers)}
            process.stdin.write(json.dumps({"id": request["id"], "ok": True, "data": data}) + "\n")
            process.stdin.flush()
        process.stdin.close()
        assert process.wait(timeout=5) == 0, "Safe bridge outcome: " + json.dumps(result)
        assert result and result.get("passed") is True
        assert len(packets) == setup_packets + 1
        with Session(case["admin"]) as db:
            user = db.get(Usuario, principal)
            assert user.session_version == 2 and verify_password(new_password, user.password_hash)
            assert db.get(MfaCredential, principal).enabled_at is not None
            assert user.email_verified_at is None and user.email_verification_hash is None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()
        reader.join(timeout=5)
