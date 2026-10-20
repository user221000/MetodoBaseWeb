"""Public primary identity is independent of an unrelated signed-in Bearer."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db as followup_db
from tests.notifications36_http import notification_http as notification_http


def test_registration_and_password_login_use_the_new_subject(notification_http, monkeypatch):
    from web.database.models import Usuario
    from web.database.tenant_context import current_tenant
    from web.middleware.tenant import TenantMiddleware

    case = notification_http
    manager_header = case["raw"].headers["Authorization"]
    calls = []
    extract = TenantMiddleware._extract_tenant

    async def observed(self, request):
        calls.append((request.method, request.url.path))
        return await extract(self, request)

    monkeypatch.setattr(TenantMiddleware, "_extract_tenant", observed)
    email = uuid.uuid4().hex + "@example.invalid"
    body = {"email": email, "password": "Synthetic Independent Primary 2026!",
            "nombre": "Synthetic independent", "tipo": "gym"}
    registration = case["raw"].post("/api/auth/registro", json=body)
    assert registration.status_code == 200
    assert calls == []
    login = case["raw"].post("/api/auth/login", json={key: body[key] for key in ("email", "password")})
    assert login.status_code == 200 and login.json()["mfa_required"] is False
    assert calls == []
    with Session(case["admin"]) as db:
        account = db.scalar(select(Usuario).where(Usuario.email == email))
        assert account is not None and account.id != case["user"] and account.team_gym_id is None
        new_id = account.id
        assert db.scalar(select(func.count()).select_from(Usuario).where(Usuario.email == email)) == 1
    manager = case["raw"].get("/api/auth/me")
    assert manager.status_code == 200 and manager.json()["id"] == case["user"]
    independent = case["raw"].get("/api/auth/me", headers={"Authorization": "Bearer " + login.json()["token"]})
    assert independent.status_code == 200 and independent.json()["id"] == new_id
    assert case["raw"].headers["Authorization"] == manager_header
    assert current_tenant.get() == ""


def test_primary_isolation_is_finite_and_browser_admission_remains_first(notification_http, monkeypatch):
    from web.database.models import Usuario
    from web.middleware.tenant import TenantMiddleware, _PUBLIC_PRIMARY_POSTS

    case = notification_http
    calls = []
    extract = TenantMiddleware._extract_tenant

    async def observed(self, request):
        calls.append((request.method, request.url.path))
        return await extract(self, request)

    monkeypatch.setattr(TenantMiddleware, "_extract_tenant", observed)
    assert _PUBLIC_PRIMARY_POSTS == frozenset(
        path + suffix for path in ("/api/auth/registro", "/api/auth/login", "/api/auth/google")
        for suffix in ("", "/"))
    with Session(case["admin"]) as db:
        count = db.scalar(select(func.count()).select_from(Usuario))
    rejected = case["raw"].post("/api/auth/registro", json={}, headers={
        "X-MetodoBase-Browser": "1", "Origin": "https://other.example.invalid"})
    assert rejected.status_code == 403 and calls == []
    assert rejected.headers["cache-control"] == "no-store"
    assert rejected.headers["referrer-policy"] == "no-referrer"
    with Session(case["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(Usuario)) == count
    neighbor = case["raw"].post("/api/auth/registro-neighbor", json={})
    assert neighbor.status_code == 404
    wrong_method = case["raw"].get("/api/auth/registro")
    assert wrong_method.status_code == 405
    if case["factory_name"] == "api.app":
        assert calls == [("POST", "/api/auth/registro-neighbor"), ("GET", "/api/auth/registro")]
    else:
        assert calls == []  # SaaS already excludes its public auth prefix.
    me = case["raw"].get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == case["user"]
