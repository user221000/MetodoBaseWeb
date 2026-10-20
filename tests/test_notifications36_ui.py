"""Own reminder shells and current browser UI against actual SQLite/ASGI/MFA.

No listening socket, browser, provider or PostgreSQL acceptance is claimed.
"""
import base64
import importlib
import json
import queue
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.notifications36_http import followup_db as followup_db, notification_http as notification_http

ROOT = Path(__file__).resolve().parents[1]


def private(response):
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    policy = response.headers["Content-Security-Policy"]
    assert "default-src 'none'" in policy
    assert "unsafe-inline" not in policy and "accounts.google.com" not in policy


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("path,context", [("/recordatorios", "gym"), ("/mis-recordatorios", "personal")])
def test_own_shell_headers_alias_methods_and_adjacent_routes(factory, path, context):
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        for suffix in ("", "/"):
            response = client.get(path + suffix)
            assert response.status_code == 200
            private(response)
            assert f'data-notification-context="{context}"' in response.text
            assert "Los envíos están desactivados" in response.text
            assert "notifications36.js" in response.text and "r27notify1" in response.text
            assert "Registrar intención" not in response.text  # It is created only after validated reads.
        response = client.get(path + "//", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["Location"] == "http://testserver" + path
        private(response)
        response = client.head(path)
        assert response.status_code == 405
        private(response)
        for adjacent in (path + "x", path + "/extra"):
            response = client.get(adjacent)
            assert response.status_code == 404
            assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
def test_exclusion_stays_public_minimal_and_bootstrap_free(factory):
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get("/notificaciones/excluir")
    assert response.status_code == 200
    private(response)
    assert "/static/js/api.js" not in response.text
    assert "localStorage" not in response.text and "sessionStorage" not in response.text
    assert "credentials:'omit'" in response.text


@pytest.mark.parametrize("scenario", ["lost-ack", "late-ack"])
def test_actual_controller_MFA_cookie_preference_replay_and_session_fence(notification_http, monkeypatch, scenario):
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session
    from web.database.models import NotificationOutbox, NotificationPreference
    from web.services import mfa_service
    from web.services.mfa_crypto import totp
    from web.settings import get_settings

    case = notification_http
    raw = case["raw"]
    # Public registration must not inherit the fixture manager's Bearer scope.
    raw.headers.pop("Authorization", None)
    origin = "https://testserver"
    monkeypatch.setattr(get_settings(), "BASE_URL", origin)
    monkeypatch.setattr(raw, "base_url", httpx.URL(origin))
    now = datetime.now(UTC)
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda value=None: actual(now if value is None else value))
    password = "Synthetic-notification-UI-only-2026!"
    email = "notification-ui-" + uuid.uuid4().hex + "@example.invalid"
    registered = raw.post("/api/auth/registro", json={"email": email, "password": password, "nombre": "Synthetic own", "tipo": "gym"})
    assert registered.status_code == 200
    pair = registered.json()
    raw.headers["Authorization"] = "Bearer " + pair["token"]
    principal = raw.get("/api/auth/me").json()["id"]
    proof = raw.post("/api/auth/mfa/reauth", json={"password": password})
    assert proof.status_code == 200
    enrollment = raw.post("/api/auth/mfa/enroll", json={"reauthentication_token": proof.json()["reauthentication_token"]})
    assert enrollment.status_code == 200
    value = enrollment.json()
    confirmed = raw.post("/api/auth/mfa/enroll/confirm", json={"enrollment_id": value["enrollment_id"], "code": totp(base64.b32decode(value["secret"]), int(now.timestamp()) // 30)})
    assert confirmed.status_code == 200
    recovery = confirmed.json()["recovery_codes"][0]
    raw.headers.pop("Authorization", None)
    boot = {"origin": origin, "email": email, "password": password, "recovery": recovery, "scenario": scenario}
    process = subprocess.Popen(["node", "tests/e2e/notifications36_http_worker.cjs"], cwd=ROOT,
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
    lost = False
    try:
        while True:
            line = incoming.get(timeout=45)
            assert line is not None, "Worker closed before its safe typed result"
            request = json.loads(line)
            if request["type"] == "result":
                result = request
                break
            if request["command"] == "bootstrap":
                data = boot
            else:
                assert request["command"] == "http"
                assert request["url"].startswith("/api/") and ":" not in request["url"]
                options = request["options"]
                response = raw.request(options["method"], request["url"], content=options.get("body"), headers=options.get("headers"))
                status, body = response.status_code, response.text
                if scenario == "lost-ack" and not lost and options["method"] == "PUT" and "/notificaciones/preferencias/" in request["url"]:
                    assert status == 200
                    lost = True
                    status, body = 503, json.dumps({"detail": {"code": "notification_unconfirmed"}})
                data = {"status": status, "body": body, "headers": dict(response.headers)}
            process.stdin.write(json.dumps({"id": request["id"], "ok": True, "data": data}) + "\n")
            process.stdin.flush()
        process.stdin.close()
        assert process.wait(timeout=5) == 0, "Safe worker outcome: " + json.dumps(result)
        assert result and result.get("passed") is True
        assert lost is (scenario == "lost-ack")
        with Session(case["admin"]) as db:
            count = db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id == principal))
            assert count == (2 if scenario == "lost-ack" else 1)
            assert db.scalar(select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.user_id == principal)) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()
        reader.join(timeout=5)
