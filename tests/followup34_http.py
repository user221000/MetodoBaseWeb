"""Current34 authentic HTTP fixtures. No principal/MFA dependency overrides."""
import base64
import importlib
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from tests.followup34_fixtures import owned_database, REVISION
from tests.integration_schema_migrations import run_migration
from tests.mfa31_contract_client import MfaContractClient

PASSWORD = "Synthetic operational tasks password 42!"


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    with owned_database("sqlite", tmp_path_factory.mktemp("followup34-http")) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
        engine.dispose()
        yield engine


@pytest.fixture(params=["api.app", "web.main_web"])
def followup_http(followup_db, request, monkeypatch):
    from web.database import engine as database
    from web.settings import get_settings
    from web.database.models import Cliente, Usuario, UserRole
    from web.auth import hash_password
    settings = get_settings()
    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"F"*32).decode())
    admin, application = followup_db if isinstance(followup_db, tuple) else (followup_db, followup_db)
    monkeypatch.setattr(database, "_engine", application)
    factory = sessionmaker(bind=application, expire_on_commit=True, autoflush=False)
    monkeypatch.setattr(database, "_SessionLocal", factory)
    number = int(uuid.uuid4().hex[:4], 16)
    with TestClient(importlib.import_module(request.param).create_app(), raise_server_exceptions=False,
                    client=(f"127.5.{number//256}.{number%256}", 50000)) as raw:
        email = uuid.uuid4().hex+"@example.invalid"
        made = raw.post("/api/auth/registro", json={"email": email, "password": PASSWORD, "nombre": "Synthetic manager", "tipo": "gym"})
        assert made.status_code == 200, "Real34 owner registration"
        login = raw.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert login.status_code == 200, "Real34 password login"
        raw.headers["Authorization"] = "Bearer "+login.json()["token"]
        me = raw.get("/api/auth/me")
        assert me.status_code == 200
        user = me.json()["id"]
        client = MfaContractClient(raw, {"id": user}, factory, PASSWORD)
        client.authenticate()
        profile, member = str(uuid.uuid4()), str(uuid.uuid4())
        with Session(admin) as db:
            db.add(Usuario(id=member, email=uuid.uuid4().hex+"@example.invalid", password_hash=hash_password(PASSWORD),
                nombre="Synthetic assigned professional", tipo="usuario", role=UserRole.NUTRIOLOGO, team_gym_id=user))
            db.add(Cliente(id_cliente=profile, gym_id=user, nombre="Synthetic task client"))
            db.commit()
        yield {"client": client, "raw": raw, "user": user, "member": member, "profile": profile,
            "factory": factory, "engine": application, "admin": admin, "factory_name": request.param}


def candidate(case):
    response = case["raw"].get("/api/seguimiento/clientes/"+case["profile"]+"/candidatos")
    assert response.status_code == 200, "Authorised34 candidate"
    return next(c for c in response.json()["candidates"] if c["cause"] == "no_saved_plan")


def create(case, *, key=None, **changes):
    evidence = candidate(case)
    body = {"client_id": case["profile"], "cause": "no_saved_plan", "cause_evidence_hash": evidence["cause_evidence_hash"],
        "next_step": "review_plan_history", "assignee_id": case["member"], "expected_active_task_id": None, "confirm": True, **changes}
    key = str(uuid.uuid4()) if key is None else key
    response = case["raw"].post("/api/seguimiento/tareas", json=body, headers={"Idempotency-Key": key})
    return response, body, key
