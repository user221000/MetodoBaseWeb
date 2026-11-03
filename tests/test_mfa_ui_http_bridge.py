"""Actual UI modules ↔ both actual factories via private pipes and ASGI HTTP.

No listening socket, browser, PostgreSQL migration, provider or public fixture
endpoint. Bodies containing ephemeral MFA material stay in private process RAM.
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

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("scenario", ["lifecycle", "late-ack"])
def test_real_ui_mfa_modules_against_current31(monkeypatch, test_gym_user, factory, scenario):
    from sqlalchemy.orm import Session

    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import UserRole, Usuario
    from web.services import mfa_service, stripe_service
    from web.services.mfa_crypto import totp
    from web.settings import get_settings

    # Only the external payment capability is doubled, never auth/MFA/DB.
    port_calls = []
    monkeypatch.setattr(stripe_service, "create_portal_session", lambda **kwargs:
                        port_calls.append(True) or {"url": "https://billing.stripe.com/synthetic-no-provider"})
    monkeypatch.setattr(get_settings(), "MFA_ENCRYPTION_KEY",
                        base64.urlsafe_b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode())
    browser_origin = "https://testserver"
    monkeypatch.setattr(get_settings(), "BASE_URL", browser_origin)
    now = datetime.now(UTC)
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda value=None: actual(now if value is None else value))
    # This downstream lifecycle starts with a persisted, confirmed contact.
    # The separate negative cases retain admission for unconfirmed/stale contacts.
    if scenario == "lifecycle":
        from tests.test_mfa31_http import verify_billing_contact
        verify_billing_contact(test_gym_user)
    other_id = str(uuid.uuid4())
    other_email = "mfa-ui-" + uuid.uuid4().hex + "@example.invalid"
    password = "Synthetic-MFA-UI-not-live-2026!"
    with Session(get_engine()) as db:
        db.add(Usuario(id=other_id, email=other_email, nombre="Synthetic other",
                       apellido="", password_hash=hash_password(password), tipo="gym",
                       role=UserRole.OWNER, activo=True, session_version=0, fecha_registro=now))
        db.commit()
    app = importlib.import_module(factory).create_app()
    source_ip = "127.2." + str(int(uuid.uuid4().hex[:2], 16)) + "." + str(int(uuid.uuid4().hex[:2], 16))
    root = Path(__file__).resolve().parents[1]
    with TestClient(app, base_url=browser_origin, raise_server_exceptions=False,
                    client=(source_ip, 50000)) as client:
        primary = client.post("/api/auth/login", json={"email": test_gym_user["email"], "password": "test123"})
        assert primary.status_code == 200
        replacement = client.post("/api/auth/login", json={"email": other_email, "password": password})
        assert replacement.status_code == 200
        boot = {"pair": primary.json(), "other": replacement.json(), "other_id": other_id,
                "actor_id": test_gym_user["id"], "email": test_gym_user["email"],
                "password": "test123", "scenario": scenario, "origin": browser_origin}
        process = subprocess.Popen(["node", "tests/e2e/browser_mfa_http_worker31.cjs"], cwd=root,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, encoding="utf8",
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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
                line = incoming.get(timeout=60)
                assert line is not None, "UI worker closed before its safe report"
                request = json.loads(line)
                if request["type"] == "result":
                    result = request
                    break
                command = request["command"]
                if command == "bootstrap":
                    data = boot
                elif command == "totp":
                    data = totp(base64.b32decode(request["seed"]), int(now.timestamp()) // 30)
                elif command == "http":
                    options = request["options"]
                    assert request["url"].startswith("/api/") and ":" not in request["url"]
                    response = client.request(options["method"], request["url"],
                                              content=options.get("body"), headers=options.get("headers"))
                    data = {"status": response.status_code, "body": response.text,
                            "headers": dict(response.headers)}
                else:
                    raise AssertionError("Unknown private bridge command")
                process.stdin.write(json.dumps({"id": request["id"], "ok": True, "data": data}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            assert process.wait(timeout=5) == 0, "Safe worker state: " + json.dumps(result)
            assert result and result.get("passed") is True, "UI/HTTP flow failed without disclosing private values"
            assert len(port_calls) == (1 if scenario == "lifecycle" else 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()
            reader.join(timeout=5)


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("contact_state", ["unconfirmed", "stale"])
def test_mfa_login_without_current_contact_confirmation_cannot_open_portal(
        monkeypatch, test_gym_user, factory, contact_state):
    from sqlalchemy.orm import Session

    from tests.test_mfa31_http import authenticate, enroll, verify_billing_contact
    from web.auth import verificar_token
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services import mfa_service, stripe_service
    from web.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY",
                        base64.urlsafe_b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode())
    # Providers are deliberately unavailable: no missing confirmation may fall
    # back to a portal, even after genuine account MFA has been completed.
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    now = datetime.now(UTC)
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda value=None: actual(now if value is None else value))
    if contact_state == "stale":
        verify_billing_contact(test_gym_user)
    with Session(get_engine()) as db:
        user = db.get(Usuario, test_gym_user["id"])
        if contact_state == "stale":
            assert user.email_verified_at is not None
            assert user.email_verified_contact_version == user.notification_contact_version
            user.notification_contact_version += 1
            db.commit()
            assert user.email_verified_contact_version != user.notification_contact_version
        else:
            assert user.email_verified_at is None
    port_calls = []
    monkeypatch.setattr(stripe_service, "create_portal_session", lambda **kwargs:
                        port_calls.append(True) or {"url": "https://billing.stripe.com/synthetic-no-provider"})
    source_ip = "127.3." + str(int(uuid.uuid4().hex[:2], 16)) + "." + str(int(uuid.uuid4().hex[:2], 16))
    with TestClient(importlib.import_module(factory).create_app(),
                    headers=test_gym_user["auth_headers"], raise_server_exceptions=False,
                    client=(source_ip, 50000)) as client:
        _, kit = enroll(client, [now])
        pair, _ = authenticate(client, test_gym_user, [now], recovery=kit["recovery_codes"][0])
        assert verificar_token(pair["token"])["amr"] == ["pwd", "recovery"]
        state = client.get("/api/auth/mfa/status")
        assert state.status_code == 200 and state.json()["enabled"] is True
        assert state.json()["recovery_codes_remaining"] == 7
        pending = client.post("/api/billing/email-verification/request",
                              json={"action": "gym_stripe_portal", "plan": "manage"})
        assert pending.status_code == 503
        assert pending.json()["detail"]["code"] == "billing_email_unavailable"
        assert not {"email_verified", "verification_token", "url"} & pending.json().keys()
        blocked = client.post("/api/billing/portal", json={"return_url": "/dashboard"})
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["code"] == "billing_email_required"
        assert "url" not in blocked.json()
        for response in (pending, blocked):
            assert "no-store" in {item.strip().lower() for item in response.headers["Cache-Control"].split(",")}
            assert response.headers["Referrer-Policy"] == "no-referrer"
        assert port_calls == []
