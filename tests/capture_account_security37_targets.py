"""Capture only the new37 target; never overwrite a reviewed predecessor."""
import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from tests.followup34_fixtures import owned_database
    from tests.integration_schema_migrations import run_migration
    from tests.isolation import block_external_sockets, prepare_environment
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialect", choices=("sqlite", "postgresql"), default="sqlite")
    dialect = parser.parse_args().dialect
    directory = prepare_environment(discard_inherited=True)
    block_external_sockets()
    migration = importlib.import_module("web.database.alembic.versions.20261020_account_security")
    path = ROOT / ("web/database/alembic/schema_targets/20261020_account_security_" + dialect + ".json")
    if path.exists():
        raise RuntimeError("Never overwrite a captured target")
    if dialect == "postgresql":
        from tests.account_security37_owned import owned_database as pg_lease
        lease = pg_lease
    else:
        lease = owned_database
    with lease(dialect, directory / "capture37") as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", migration.down_revision)
        with engine.begin() as connection:
            if dialect == "sqlite":
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            migration.verify(connection, migration.down_revision)
            with Operations.context(MigrationContext.configure(connection)):
                migration.create_columns()
            value = migration.signature(connection)
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
        print(json.dumps({"dialect": dialect, "tables": len(value["signature"]["tables"]), "target": path.name}))


if __name__ == "__main__":
    main()
