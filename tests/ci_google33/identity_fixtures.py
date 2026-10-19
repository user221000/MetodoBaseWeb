"""Exact shared identity fixtures, independent of test modules and import order."""
import uuid
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

@pytest.fixture
def identity_db(monkeypatch):
    from web import auth
    from web.database import engine as database
    from web.database.models import Base, Usuario, UserRole

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(auth, "_get_session", factory)
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-security-test-key-with-no-external-use")
    monkeypatch.setattr(database, "_engine", engine)
    monkeypatch.setattr(database, "_SessionLocal", factory)
    password = "SyntheticPassword123!"
    owner_id, member_id = str(uuid.uuid4()), str(uuid.uuid4())
    with factory() as db:
        db.add(Usuario(id=owner_id, email=f"{owner_id}@example.invalid", password_hash=auth.hash_password(password), nombre="Owner", tipo="gym", role=UserRole.OWNER, activo=True))
        db.commit()
        db.add(Usuario(id=member_id, email=f"{member_id}@example.invalid", password_hash=auth.hash_password(password), nombre="Member", tipo="usuario", role=UserRole.NUTRIOLOGO, team_gym_id=owner_id, activo=True))
        db.commit()
    yield factory, owner_id, member_id, password
    engine.dispose()


def principal(factory, user_id):
    from web.database.models import Usuario
    with factory() as db:
        user = db.get(Usuario, user_id)
        return {"id": user.id, "email": user.email, "nombre": user.nombre, "apellido": user.apellido, "tipo": user.tipo, "role": user.role.value, "team_gym_id": user.team_gym_id, "session_version": getattr(user, "session_version", 0)}


def auth_client(monkeypatch):
    from web.routes import auth as routes
    from web.services import auth_audit
    monkeypatch.setattr(auth_audit, "log_auth_event_from_request", AsyncMock())
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    return TestClient(app)

