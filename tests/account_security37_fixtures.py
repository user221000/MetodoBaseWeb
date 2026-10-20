"""Explicit current37 SQLite fixtures; no historical target is retargeted."""
import base64
import uuid

import pytest
from sqlalchemy.orm import sessionmaker

from tests.followup34_fixtures import owned_database
from tests.integration_schema_migrations import run_migration
from web.database.models import UserRole, Usuario

PASSWORD = "Synthetic account security password 42!"
NEW_PASSWORD = "Synthetic changed account password 43!"
REVISION = "20261020_account_security"


@pytest.fixture(scope="module")
def account37_engine(tmp_path_factory):
    with owned_database("sqlite", tmp_path_factory.mktemp("account37")) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        yield engine


@pytest.fixture
def account37(account37_engine, monkeypatch):
    from web.auth import crear_token_pair, hash_password, identity_from_user
    from web.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "RESEND_API_KEY", "synthetic-account37-no-network")
    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"A" * 32).decode())
    factory = sessionmaker(bind=account37_engine, expire_on_commit=True, autoflush=False)
    identity = str(uuid.uuid4())
    with factory() as db:
        user = Usuario(id=identity, email=uuid.uuid4().hex + "@example.invalid", nombre="Synthetic account",
                       password_hash=hash_password(PASSWORD), tipo="usuario", role=UserRole.VIEWER)
        db.add(user)
        db.flush()
        expected = identity_from_user(user, db)
        pair = crear_token_pair(expected, db=db)
        db.commit()
    return {"factory": factory, "engine": account37_engine, "expected": expected,
            "user": identity, "access": pair["access_token"], "refresh": pair["refresh_token"]}
