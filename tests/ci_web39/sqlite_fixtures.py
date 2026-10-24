"""Current39 SQLite providers; no historical source or assertion is edited."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from tests.followup34_fixtures import owned_database
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from web.database.schema_control import expected_head, verify_runtime_schema
from web.database.tenant_context import configure_tenant_engine

REVISION = "20261023_privacy_disposition"


def foreign_keys(engine):
    @event.listens_for(engine, "connect")
    def enforce(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    engine.dispose()


def current_schema(engine):
    assert expected_head() == REVISION
    verify_runtime_schema(engine, expected_revision=REVISION)
    with engine.connect() as db:
        from web.database.models import Base
        assert set(inspect(db).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
        assert db.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    with owned_database("sqlite", tmp_path_factory.mktemp("current39-runtime")) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        foreign_keys(engine)
        current_schema(engine)
        yield engine


# Pytest binds these explicit exported names separately in each companion
# namespace. The fixture body, factory scope, real password/MFA and original
# business functions remain shared; no credential or repository double is added.
google_db = followup_db
progress_db = followup_db


@pytest.fixture(scope="module", params=["sqlite"])
def link_db(request, tmp_path_factory):
    assert request.param == "sqlite"
    with owned_database("sqlite", tmp_path_factory.mktemp("current39-publication")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        foreign_keys(admin)
        app = configure_tenant_engine(application_engine(url, admin))
        try:
            current_schema(app)
            yield admin, app
        finally:
            if app is not admin:
                app.dispose()


@pytest.fixture(scope="module")
def ledger_template(tmp_path_factory):
    """Same three actors/client as the34 mechanism fixture, on migrations39.

    The original manually installed two34 tables atop33. Here the accepted
    migration chain installs those tables and their policies before seeding.
    All original mechanism test functions and ledger copying remain identical.
    """
    from web.database.models import Cliente, UserRole, Usuario

    path = tmp_path_factory.mktemp("current39-mechanisms") / "template.db"
    url = "sqlite:///" + path.as_posix()
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    engine = create_engine(url)
    try:
        foreign_keys(engine)
        current_schema(engine)
        with Session(engine) as db:
            db.add_all([
                Usuario(id="gym-a", email="a@example.invalid", password_hash="synthetic",
                        nombre="A", tipo="gym", role=UserRole.OWNER),
                Usuario(id="gym-b", email="b@example.invalid", password_hash="synthetic",
                        nombre="B", tipo="gym", role=UserRole.OWNER),
                Usuario(id="nutri-a", email="n@example.invalid", password_hash="synthetic", nombre="N",
                        tipo="usuario", role=UserRole.NUTRIOLOGO, team_gym_id="gym-a"),
            ])
            db.flush()
            db.add(Cliente(id_cliente="client-a", gym_id="gym-a", nombre="Synthetic"))
            db.commit()
    finally:
        engine.dispose()
    return path

# Preserve consumer fixture names while using one actual39 migration provider.
account37_engine = followup_db
origin38_engine = followup_db
