"""Safe test composition and committed-data cleanup for each synthetic case.

SQLite metadata is for unit/API tests only; migration acceptance is separate.
"""
from pathlib import Path
import os
import random
import sys
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from tests.isolation import block_external_sockets, prepare_environment

try:
    _TEST_ROOT = prepare_environment()
except ValueError as exc:
    raise pytest.UsageError(str(exc)) from None
block_external_sockets()


def pytest_collection_modifyitems(items):
    """Apply the same explicit order in controller and isolated xdist workers."""
    if os.environ.get("_METODOBASE_TEST_REVERSE") == "1":
        items.reverse()
    seed = os.environ.get("_METODOBASE_TEST_SHUFFLE_SEED", "")
    if seed:
        random.Random(int(seed)).shuffle(items)


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    """Prepare unit SQLite once; PostgreSQL must already be migrated."""
    from sqlalchemy import inspect
    from web.database.engine import get_engine
    from web.database.models import Base

    engine = get_engine()
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
    elif "usuarios" not in inspect(engine).get_table_names():
        pytest.fail("PostgreSQL test database is not migrated; run the migration acceptance setup")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def isolated_database(database_schema):
    """Clean independent route commits as rollback-only fixtures cannot.

    Every worker owns a separate SQLite file. Cleanup failures fail the case.
    Tables are deleted in FK order, preserving the prepared schema.
    """
    from web.database.engine import get_engine
    from web.database.models import Base

    def clear():
        with get_engine().begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

    clear()
    yield
    clear()


@pytest.fixture
def test_gym_user():
    """Persist an explicit owner; issue its token after a successful commit."""
    from datetime import datetime, timezone
    from sqlalchemy.orm import Session
    from web.auth import crear_access_token, hash_password, init_auth
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole

    init_auth()
    uid = str(uuid.uuid4())
    user = {"id": uid, "email": f"gym-{uid}@example.test", "nombre": "Synthetic Gym", "tipo": "gym", "role": "owner"}
    with Session(get_engine()) as session:
        session.add(Usuario(id=uid, email=user["email"], password_hash=hash_password("test123"),
                            nombre=user["nombre"], apellido="", tipo="gym", activo=True,
                            role=UserRole.OWNER, session_version=0,
                            fecha_registro=datetime.now(timezone.utc)))
        session.commit()
        assert session.get(Usuario, uid) is not None
    token = crear_access_token(user)
    return {**user, "access_token": token, "auth_headers": {"Authorization": f"Bearer {token}"}}


def _authenticated_client(app, user):
    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=False, headers=user["auth_headers"])


@pytest.fixture
def auth_client(test_gym_user):
    """Standalone API adapter with a fresh synthetic account per case."""
    from api.app import create_app
    with _authenticated_client(create_app(), test_gym_user) as client:
        yield client


@pytest.fixture
def web_auth_client(test_gym_user):
    """Real SaaS composition used by web/main_web.py."""
    from web.main_web import create_app
    with _authenticated_client(create_app(), test_gym_user) as client:
        yield client
