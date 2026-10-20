"""Independent actual cookie/MFA HTTP401 after SQLite session-version revocation."""
import base64
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
from sqlalchemy.orm import Session

from tests.account_security37_http import account37_engine, account_http, followup_db

__all__ = ["account37_engine", "account_http", "followup_db"]
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("operation", ["status", "email", "password"])
def test_actual_persisted_401_retires_UI_actor_without_refresh(account_http, monkeypatch, operation):
    import resend

    from web.auth import verify_password
    from web.database.models import Usuario
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
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-no-send-independent37")
    monkeypatch.setattr(resend.Emails, "send", lambda params: {"id": "synthetic-independent37"})
    now = datetime.now(UTC)
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda value=None: actual(now if value is None else value))
    password = "Synthetic independent old password37!"
    new_password = "Synthetic independent changed password37!"
    email = "independent-ui37-" + uuid.uuid4().hex + "@example.invalid"
    registration = raw.post("/api/auth/registro", json={"email": email, "password": password, "nombre": "Synthetic independent", "tipo": "usuario"})
    assert registration.status_code == 200
    raw.headers["Authorization"] = "Bearer " + registration.json()["token"]
    principal = raw.get("/api/auth/me").json()["id"]
    proof = raw.post("/api/auth/mfa/reauth", json={"password": password})
    enrollment = raw.post("/api/auth/mfa/enroll", json={"reauthentication_token": proof.json()["reauthentication_token"]}).json()
    confirmed = raw.post("/api/auth/mfa/enroll/confirm", json={"enrollment_id": enrollment["enrollment_id"], "code": totp(base64.b32decode(enrollment["secret"]), int(now.timestamp()) // 30)})
    assert confirmed.status_code == 200
    recovery = confirmed.json()["recovery_codes"]
    raw.headers.pop("Authorization", None)
    raw.cookies.clear()
    shell = raw.get("/cuenta/seguridad")
    csrf = unescape(re.search('name="csrf-token" content="([^"]*)"', shell.text).group(1))
    boot = {"origin": origin, "csrf": csrf, "email": email, "password": password, "new_password": new_password,
            "login_recovery": recovery[0], "change_recovery": recovery[1], "operation": operation}
    worker = subprocess.Popen(["node", "tests/e2e/security_account37_unauthorized_http_peer.cjs"], cwd=ROOT,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, encoding="utf8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    incoming = queue.Queue()

    def read_lines():
        for line in worker.stdout:
            incoming.put(line)
        incoming.put(None)

    reader = threading.Thread(target=read_lines, daemon=True)
    reader.start()
    revoked = False
    result = None
    try:
        while True:
            line = incoming.get(timeout=45)
            assert line is not None, "Private worker stopped before its safe result"
            request = json.loads(line)
            if request["type"] == "result":
                result = request
                break
            if request["command"] == "bootstrap":
                data = boot
            elif request["command"] == "revoke-persisted-session":
                assert not revoked
                with Session(case["admin"]) as db:
                    user = db.get(Usuario, principal)
                    assert user.session_version == 1
                    user.session_version += 1
                    db.commit()
                revoked = True
                data = {"revoked": True}
            else:
                assert request["command"] == "http" and request["url"].startswith("/api/") and ":" not in request["url"]
                options = request["options"]
                response = raw.request(options["method"], request["url"], content=options.get("body"), headers=options.get("headers"))
                data = {"status": response.status_code, "body": response.text, "headers": dict(response.headers)}
            worker.stdin.write(json.dumps({"id": request["id"], "ok": True, "data": data}) + "\n")
            worker.stdin.flush()
        worker.stdin.close()
        exit_code = worker.wait(timeout=5)
        assert revoked and result and result.get("target_HTTP_status") == 401
        assert result["checks"]["no_refresh_retry"] and result["checks"]["only_epoch_persisted"]
        with Session(case["admin"]) as db:
            user = db.get(Usuario, principal)
            assert user.session_version == 2 and verify_password(password, user.password_hash)
            assert not verify_password(new_password, user.password_hash)
        assert exit_code == 0 and result.get("passed") is True, "Safe bridge outcome: " + json.dumps(result)
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=5)
        worker.stdout.close()
        if not worker.stdin.closed:
            worker.stdin.close()
        reader.join(timeout=5)
