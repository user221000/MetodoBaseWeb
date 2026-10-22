"""Explicit37 PG transports for unchanged234 legacy domain criteria.

All CREATE/DROP operations belong to the original account37 UUID primitive.
The historical33 fixtures, numbers, helpers and assertion bodies stay intact.
"""
from __future__ import annotations

import base64
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from tests.account_security37_owned import owned_database
from tests.ci_web37.physical import REVISION, blank_pool, physical_contract
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration


@contextmanager
def current_database(directory):
    with owned_database("postgresql", directory) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        application = application_engine(url, admin)
        try:
            physical_contract(application)
            yield url, admin, application
            physical_contract(application)
        finally:
            application.dispose()


@pytest.fixture(params=["postgresql"])
def migration_database(request, tmp_path):
    assert request.param == "postgresql"
    with current_database(tmp_path) as (url, admin, _application):
        yield url, admin


@pytest.fixture(scope="module", params=["postgresql"])
def link_db(request, tmp_path_factory):
    assert request.param == "postgresql"
    with current_database(tmp_path_factory.mktemp("current37-member")) as (_url, admin, application):
        yield admin, application


@pytest.fixture(scope="module", params=["postgresql"])
def race_link_db(request, tmp_path_factory):
    """One original R24 criterion requires simultaneous holder/worker/revoke."""
    from web.database.tenant_context import configure_tenant_engine

    assert request.param == "postgresql"
    with current_database(tmp_path_factory.mktemp("current37-r24-race")) as (_url, admin, small):
        app = configure_tenant_engine(create_engine(small.url, pool_size=6, max_overflow=0,
            pool_timeout=5, connect_args={"options": "-c statement_timeout=8000"}))
        try:
            # Schema/role/FORCE/FK witness on the base pool1 and explicitly on
            # the real six-connection race engine; this is never labeled pool1.
            physical_contract(app, expected_pool=6)
            yield admin, app
            physical_contract(app, expected_pool=6)
        finally:
            app.dispose()


@pytest.fixture(scope="module")
def progress_db(tmp_path_factory):
    with current_database(tmp_path_factory.mktemp("current37-progress")) as (_url, admin, application):
        yield admin, application


@pytest.fixture(scope="module")
def google_db(tmp_path_factory):
    with current_database(tmp_path_factory.mktemp("current37-google")) as (_url, admin, application):
        yield admin, application


@pytest.fixture
def mfa_pg(migration_database, monkeypatch):
    """Same four ordinary legacy actors; current37 transport and real factors."""
    from tests.integration_current33_mfa_postgres import PASSWORD
    from web import auth
    from web.database import engine as database
    from web.database.models import UserRole, Usuario
    from web.settings import get_settings

    url, admin = migration_database
    ids = [str(uuid.uuid4()) for _ in range(4)]
    with Session(admin) as db:
        for index, identity in enumerate(ids):
            db.add(Usuario(id=identity, email=identity + "@example.invalid", password_hash=auth.hash_password(PASSWORD),
                nombre="Synthetic", apellido="", tipo="gym" if index < 2 else "usuario",
                role=UserRole.OWNER if index < 2 else (UserRole.ADMIN if index == 2 else UserRole.VIEWER),
                team_gym_id=ids[0] if index == 2 else None, activo=True, session_version=0))
            db.flush()
        db.commit()
    app = application_engine(url, admin)

    @event.listens_for(app, "connect")
    def timeout(connection, record):
        with connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='12000ms'")
        connection.commit()

    monkeypatch.setattr(database, "_engine", app)
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=app, autoflush=False, expire_on_commit=False))
    monkeypatch.setattr(get_settings(), "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"mfa31-synthetic-isolated-key-00000"[:32]).decode())
    auth.init_auth()
    try:
        physical_contract(app)
        yield admin, app, ids
        physical_contract(app)
    finally:
        app.dispose()


@pytest.fixture(scope="module")
def owned_postgres_database(tmp_path_factory):
    from tests.ci_web37.pg_rls_seed import seed_original_rls_rows

    with current_database(tmp_path_factory.mktemp("current37-rls")) as (_url, admin, application):
        seed_original_rls_rows(admin)
        # The original RLS/domain fixtures construct their real restricted
        # pool1 from this URL. No owner URL or extra grant reaches that engine.
        yield admin, application.url.render_as_string(hide_password=False)


@pytest.fixture(autouse=True)
def current37_legacy_pool_witness(request):
    """Observe the selected actual engine before/after each business test."""
    engine = None
    expected = 1
    for name in ("mfa_pg", "diary_pg", "postgres_case", "link_db", "progress_db", "google_db"):
        if name in request.fixturenames:
            value = request.getfixturevalue(name)
            engine = value[0] if name == "postgres_case" else value[1]
            if name == "link_db" and request.module.__name__.endswith("_r24_race"):
                expected = 6
            break
    if engine is not None:
        physical_contract(engine, expected_pool=expected)
    yield
    if engine is not None:
        blank_pool(engine)
        physical_contract(engine, expected_pool=expected)
