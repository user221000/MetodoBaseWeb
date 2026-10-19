"""Exact revision30→31 security-state migration, disposable SQLite/PG only."""
from datetime import datetime, timezone
import os
import subprocess
import sys

from alembic import command
from alembic.operations import Operations
import pytest
from sqlalchemy import inspect, text

from tests.mfa31_fixtures import mfa_database as migration_database
from tests.integration_schema_migrations import run_migration, ROOT
from tests.integration_client_link_migrations import populate28
from tests.integration_stored_objects_migrations import snapshot
from tests.mfa31_fixtures import PREVIOUS, REVISION
from web.database.schema_control import alembic_config, verify_runtime_schema


@pytest.mark.parametrize("populated", [False, True])
def test_empty_populated_upgrade_repeat_and_empty_mfa_rollback_preserve30(migration_database, populated):
    url, engine = migration_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    if populated:
        populate28(engine)
    columns, rows = snapshot(engine)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError, match="revision"):
        verify_runtime_schema(engine)
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    assert snapshot(engine, columns)[1] == rows
    with engine.connect() as db:
        assert len(inspect(db).get_table_names()) == 33
        assert db.scalar(text("SELECT count(*) FROM mfa_credentials")) == 0
        if engine.dialect.name == "postgresql":
            flags = db.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relname LIKE 'mfa_%' ORDER BY relname")).all()
            protected = [row for row in flags if row[0] in {"mfa_credentials", "mfa_recovery_codes"}]
            assert [tuple(row[1:]) for row in protected] == [(True, True)] * 2
    run_migration(url, "-m", "alembic", "downgrade", PREVIOUS)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    verify_runtime_schema(engine)


def test_unknown30_drift_rejected_before_mfa_ddl(migration_database):
    url, engine = migration_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    with engine.begin() as db:
        db.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN unknown_mfa_drift integer")
    result = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py", "--revision", REVISION],
        cwd=ROOT, env=dict(os.environ, DATABASE_URL=url), capture_output=True, text=True)
    assert result.returncode != 0
    with engine.connect() as db:
        assert "mfa_credentials" not in inspect(db).get_table_names()
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == PREVIOUS


def test_mid_ddl_failure_rolls_back_all_new_tables_and_revision(migration_database, monkeypatch):
    url, engine = migration_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    columns, rows = snapshot(engine)
    original = Operations.create_table
    def fail_after_first(self, name, *args, **kwargs):
        value = original(self, name, *args, **kwargs)
        if name == "mfa_credentials":
            raise RuntimeError("Synthetic interruption after first table")
        return value
    monkeypatch.setattr(Operations, "create_table", fail_after_first)
    with pytest.raises(RuntimeError, match="Synthetic interruption"):
        with engine.begin() as db:
            config = alembic_config()
            config.attributes["connection"] = db
            command.upgrade(config, REVISION)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows
    with engine.connect() as db:
        assert not set(inspect(db).get_table_names()) & {"mfa_credentials", "mfa_recovery_codes", "mfa_authorizations"}


def test_security_state_prevents_destructive_downgrade(migration_database):
    url, engine = migration_database
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    with engine.begin() as db:
        db.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro) VALUES ('mfa-rollback','mfa-rollback@example.invalid','synthetic','Synthetic','','usuario','VIEWER',true,0,:now)"),
            {"now": datetime.now(timezone.utc).replace(tzinfo=None)})
        db.execute(text("INSERT INTO mfa_credentials(user_id,factor_id,created_at) VALUES ('mfa-rollback','0123456789abcdef0123456789abcdef',:now)"),
            {"now": datetime.now(timezone.utc).replace(tzinfo=None)})
    columns, rows = snapshot(engine)
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "alembic", "downgrade", PREVIOUS],
        cwd=ROOT, env=dict(os.environ, DATABASE_URL=url), capture_output=True, text=True)
    assert result.returncode != 0
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
