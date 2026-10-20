"""Real SQLite35 migration/rollback; PostgreSQL has its own explicit gate."""
import importlib
import json
import os
import subprocess
import sys

import pytest
from alembic import command
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import Session

from tests.followup34_fixtures import owned_database
from tests.integration_schema_migrations import ROOT, run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.models import UserRole, Usuario
from web.database.schema_control import alembic_config, verify_runtime_schema

PREVIOUS = "20261019_followup_tasks"
REVISION = "20261020_nutrition_profile"


@pytest.fixture
def database35(tmp_path):
    with owned_database("sqlite", tmp_path) as value:
        yield value


@pytest.mark.parametrize("populated", [False, True])
def test_exact34_rows_survive_upgrade_repeat_and_null_only_downgrade(database35, populated):
    url, engine = database35
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    if populated:
        with Session(engine) as db:
            db.add(Usuario(id="nutrition35-migration", email="migration35@example.invalid", nombre="Synthetic",
                           password_hash="synthetic", tipo="gym", role=UserRole.OWNER))
            db.commit()
        with engine.begin() as c:
            c.execute(text("INSERT INTO clientes(gym_id,id_cliente,nombre,activo) VALUES(:g,:i,:n,1)"),
                      {"g": "nutrition35-migration", "i": "LEGACY35", "n": "Synthetic"})
    columns, rows = snapshot(engine)
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM clientes WHERE nutrition_restrictions_json IS NOT NULL")) == 0
        assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    run_migration(url, "-m", "alembic", "downgrade", PREVIOUS)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows


def test_nonnull_declaration_refuses_data_loss_on_downgrade(database35):
    from tests.test_nutrition35_profile_contract import declaration
    from web.database.models import Cliente
    from web.services.nutrition_profiles import encode_declaration

    url, engine = database35
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    with Session(engine) as db:
        db.add(Usuario(id="facts35", email="facts35@example.invalid", nombre="Synthetic", password_hash="synthetic",
                       tipo="gym", role=UserRole.OWNER))
        db.flush()
        db.add(Cliente(id_cliente="facts35", gym_id="facts35", nombre="Synthetic",
                       nutrition_restrictions_json=encode_declaration(declaration(reported=True))))
        db.commit()
    columns, rows = snapshot(engine)
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "alembic", "downgrade", PREVIOUS],
        cwd=ROOT, env=dict(os.environ, DATABASE_URL=url), capture_output=True, check=False)
    assert result.returncode != 0
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows


def test_drift_or_interrupted_DDL_cannot_advance_the_revision(database35):
    url, engine = database35
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    columns, rows = snapshot(engine)

    def interrupted(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("ALTER TABLE clientes ADD COLUMN nutrition_restrictions_json"):
            raise RuntimeError("Synthetic35 DDL interruption")

    event.listen(engine, "after_cursor_execute", interrupted)
    try:
        with pytest.raises(RuntimeError, match="Synthetic35"), engine.begin() as c:
            config = alembic_config()
            config.attributes["connection"] = c
            command.upgrade(config, REVISION)
    finally:
        event.remove(engine, "after_cursor_execute", interrupted)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows
    with engine.begin() as c:
        c.exec_driver_sql("ALTER TABLE clientes ADD COLUMN unexpected35 INTEGER")
    result = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py", "--revision", REVISION],
        cwd=ROOT, env=dict(os.environ, DATABASE_URL=url), capture_output=True, check=False)
    assert result.returncode != 0
    with engine.connect() as c:
        assert "nutrition_restrictions_json" not in {v["name"] for v in inspect(c).get_columns("clientes")}
        assert c.scalar(text("SELECT version_num FROM alembic_version")) == PREVIOUS


def test_target35_changes_only_one_bounded_nullable_client_column():
    migration = importlib.import_module("web.database.alembic.versions."+REVISION)
    folder = ROOT/"web/database/alembic/schema_targets"
    old = json.loads((folder/(PREVIOUS+"_sqlite.json")).read_bytes())
    current = json.loads((folder/(REVISION+"_sqlite.json")).read_bytes())
    table = current["signature"]["tables"]["clientes"]
    column = next(c for c in table["columns"] if c["name"] == "nutrition_restrictions_json")
    assert column["nullable"] is True and column["type"] == "TEXT" and column["default"] is None
    table["columns"].remove(column)
    check = next(c for c in table["checks"] if c["name"] == "ck_cliente_nutrition_declaration_bound")
    assert check["sql"] == "nutrition_restrictions_json IS NULL OR length(nutrition_restrictions_json) BETWEEN 2 AND 16384"
    table["checks"].remove(check)
    assert old == current
    assert migration.down_revision == PREVIOUS


def test_database_rejects_oversized_or_empty_declarations(database35):
    from sqlalchemy.exc import IntegrityError

    url, engine = database35
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    with Session(engine) as db:
        db.add(Usuario(id="bound35", email="bound35@example.invalid", nombre="Synthetic", password_hash="synthetic",
                       tipo="gym", role=UserRole.OWNER))
        db.commit()
    with engine.begin() as c:
        c.execute(text("INSERT INTO clientes(gym_id,id_cliente,nombre,activo) VALUES(:g,:i,:n,1)"),
                  {"g": "bound35", "i": "BOUND35", "n": "Synthetic"})
    for invalid in ("", "{", "x"*16385):
        with pytest.raises(IntegrityError), engine.begin() as c:
            c.execute(text("UPDATE clientes SET nutrition_restrictions_json=:v WHERE id_cliente=:i"),
                      {"v": invalid, "i": "BOUND35"})
    with engine.connect() as c:
        assert c.scalar(text("SELECT nutrition_restrictions_json FROM clientes WHERE id_cliente='BOUND35'")) is None
