"""Current37 migration companions; predecessors22–36 remain byte immutable."""
import importlib
import os
import subprocess
import sys

import pytest
from alembic import command
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.followup34_fixtures import owned_database
from tests.integration_client_link_migrations import populate28
from tests.integration_schema_migrations import ROOT, run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import alembic_config, verify_runtime_schema

PREVIOUS = "20261020_notifications"
REVISION = "20261020_account_security"


@pytest.fixture
def account_database(tmp_path):
    with owned_database("sqlite", tmp_path) as value:
        yield value


@pytest.mark.parametrize("populated", [False, True])
def test_exact36_preserves_rows_repeat_and_empty37_downgrade(account_database, populated):
    url, engine = account_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    if populated:
        populate28(engine)
    columns, rows = snapshot(engine)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
    with engine.connect() as connection:
        assert len(inspect(connection).get_table_names()) == 42
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert connection.scalar(text("SELECT count(*) FROM usuarios WHERE email_verified_at IS NOT NULL OR email_verification_hash IS NOT NULL")) == 0
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    assert snapshot(engine, columns)[1] == rows
    run_migration(url, "-m", "alembic", "downgrade", PREVIOUS)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows


def test_predecessor_drift_refuses_before_addition(account_database):
    url, engine = account_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN unexpected37 INTEGER")
    result = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py", "--revision", REVISION],
                            cwd=ROOT, env=dict(os.environ, DATABASE_URL=url), capture_output=True, check=False)
    assert result.returncode != 0
    with engine.connect() as connection:
        assert "email_verified_at" not in {c["name"] for c in inspect(connection).get_columns("usuarios")}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PREVIOUS


def test_interrupted_install_rolls_back_all_metadata_and_revision(account_database):
    url, engine = account_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    columns, rows = snapshot(engine)
    def interrupted(connection, cursor, statement, parameters, context, many):
        if statement.startswith("ALTER TABLE usuarios ADD COLUMN email_verification_expires_at"):
            raise RuntimeError("Synthetic37 interruption")
    event.listen(engine, "after_cursor_execute", interrupted)
    try:
        with pytest.raises(RuntimeError, match="Synthetic37"), engine.begin() as connection:
            config = alembic_config()
            config.attributes["connection"] = connection
            command.upgrade(config, REVISION)
    finally:
        event.remove(engine, "after_cursor_execute", interrupted)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows


@pytest.mark.parametrize("state", ["pending", "verified"])
def test_any_contact_evidence_refuses_destructive_downgrade(account_database, state):
    url, engine = account_database
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    populate28(engine)
    with engine.begin() as connection:
        identity = connection.scalar(text("SELECT id FROM usuarios LIMIT 1"))
        assert identity is not None
        if state == "pending":
            connection.execute(text("UPDATE usuarios SET email_verification_hash=:digest, email_verification_issued_at='2026-10-20 00:00:00', "
                "email_verification_expires_at='2026-10-20 00:30:00', email_verification_session_version=session_version, "
                "email_verification_contact_version=notification_contact_version WHERE id=:id"), {"digest": "a" * 64, "id": identity})
        else:
            connection.execute(text("UPDATE usuarios SET email_verified_at='2026-10-20 00:00:00', "
                                    "email_verified_contact_version=notification_contact_version WHERE id=:id"), {"id": identity})
    columns, rows = snapshot(engine)
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "alembic", "downgrade", PREVIOUS],
                            cwd=ROOT, env=dict(os.environ, DATABASE_URL=url), capture_output=True, check=False)
    assert result.returncode != 0
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows


@pytest.mark.parametrize("clause", ["email_verified_at='2026-10-20 00:00:00'", "email_verified_contact_version=1",
    "email_verification_hash='short'", "email_verification_contact_version=1", "email_verification_expires_at='2026-10-20 00:00:00'"])
def test_partial_malformed_contact_metadata_is_rejected(account_database, clause):
    url, engine = account_database
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    populate28(engine)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.exec_driver_sql("UPDATE usuarios SET " + clause)
    verify_runtime_schema(engine)


def test_predecessor_security_components_are_identical(account_database):
    url, engine = account_database
    previous = importlib.import_module("web.database.alembic.versions.20261020_notifications")
    current = importlib.import_module("web.database.alembic.versions.20261020_account_security")
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    with engine.connect() as connection:
        before = previous.signature(connection)
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    with engine.connect() as connection:
        after = current.signature(connection)
    assert {k: v for k, v in before.items() if k != "signature"} == {k: v for k, v in after.items() if k != "signature"}
