"""Independent registration boundaries; local SQLite and mail sink only."""
import uuid
from pathlib import Path
from types import SimpleNamespace
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.test_registration_validation import (
    HEADERS, database_schema, isolated_database, otp_case, registration_http,
)

__all__ = ["database_schema", "isolated_database", "otp_case", "registration_http"]


@pytest.mark.parametrize("kind", ["gym", "usuario"])
@pytest.mark.parametrize("password", ["Qr8!Zx7", "🌿" * 7])
def test_browser_seven_characters_register_login_and_reject_duplicate(
    registration_http, monkeypatch, kind, password,
):
    from web import auth
    from web.database.models import Usuario

    case, client = registration_http
    monkeypatch.setattr(auth, "SECRET_KEY", case.settings.SECRET_KEY)
    mail = []
    monkeypatch.setattr("web.services.email_service.send_welcome",
                        lambda email, name: mail.append((email, name)))
    payload = {"email": uuid.uuid4().hex + "@example.invalid", "nombre": "QA account",
               "tipo": kind, "password": password}
    rejected = client.post("/api/auth/registro", headers=HEADERS,
                           json={**payload, "password": "q7R!x2"})
    assert rejected.status_code == 400
    assert "q7R!x2" not in rejected.text
    with case.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Usuario)) == 0
    assert mail == []

    created = client.post("/api/auth/registro", headers=HEADERS, json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["tipo"] == kind
    assert created.json()["session_mode"] == "browser"
    assert "refresh_token" not in created.json()
    assert client.cookies.get("__Host-mb_refresh")
    identity = auth.verificar_token(created.json()["token"])
    with case.sessions() as db:
        user = db.get(Usuario, identity["id"])
        assert user.tipo == kind and auth.verify_password(password, user.password_hash)
    duplicate = client.post("/api/auth/registro", headers=HEADERS, json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["code"] == "registration_invalid"
    assert password not in duplicate.text
    assert mail == [(payload["email"], payload["nombre"])]
    login = client.post("/api/auth/login", headers=HEADERS,
                        json={"email": payload["email"], "password": password})
    assert login.status_code == 200, login.text
    assert auth.verificar_token(login.json()["token"])["id"] == identity["id"]


@pytest.mark.parametrize("kind", ["gym", "usuario"])
@pytest.mark.parametrize("patch", [{"email": "bad@@example.invalid"}, {"nombre": " "},
                                    {"password": "1234567"}, {"password": "🌿" * 19}])
def test_invalid_registration_still_creates_no_account(registration_http, kind, patch):
    from web.database.models import Usuario

    case, client = registration_http
    payload = {"email": uuid.uuid4().hex + "@example.invalid", "nombre": "QA account",
               "tipo": kind, "password": "Qr8!Zx7", **patch}
    result = client.post("/api/auth/registro", headers=HEADERS, json=payload)
    assert result.status_code == 400
    assert payload["password"] not in result.text
    assert "registration_invalid" in result.text
    with case.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Usuario)) == 0


@pytest.mark.parametrize("kind", ["gym", "usuario"])
@pytest.mark.parametrize("configured", [True, False])
def test_render_actual_registration_for_independent_browser(monkeypatch, kind, configured):
    from config import settings
    from web.routes import pages

    monkeypatch.setattr(settings, "Settings", lambda: SimpleNamespace(
        GOOGLE_CLIENT_ID="synthetic-qa.apps.googleusercontent.com" if configured else ""))
    app = FastAPI()

    @app.middleware("http")
    async def nonce(request, call_next):
        request.state.csp_nonce = "synthetic-qa-nonce"
        return await call_next(request)

    app.include_router(pages.router)
    with TestClient(app) as client:
        response = client.get("/registro", params={"tipo": kind})
    assert response.status_code == 200
    assert 'minlength="7"' in response.text
    output = os.environ.get("REGISTRATION_QA_OUTPUT")
    if output:
        target = Path(output).resolve()
        assert target.drive.upper() in {"E:", "F:"}
        target.mkdir(parents=True, exist_ok=True)
        (target / (kind + ("-configured" if configured else "-unconfigured") + ".html")).write_text(
            response.text, encoding="utf-8")
