"""Author-only additive35 capture; no writes to reviewed predecessor targets."""
import argparse
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialect", choices=["sqlite", "postgresql"], required=True)
    parser.add_argument("--private-config", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    from tests.isolation import block_external_sockets, prepare_environment

    temporary = prepare_environment(discard_inherited=True)
    block_external_sockets()
    if not args.evidence.is_dir():
        raise ValueError("Existing own evidence directory required")
    if args.dialect == "postgresql":
        if args.private_config is None:
            raise ValueError("Explicit synthetic profile required")
        config = json.loads(args.private_config.read_text(encoding="utf-8"))
        for key in ("METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL"):
            os.environ[key] = config[key]
    # Reuse the reviewed ownership/normal-close primitive without retargeting it.
    os.environ["FOLLOWUP34_PRIVATE_LEASES"] = str(args.evidence)
    path = ROOT/"web/database/alembic/schema_targets"/("20261020_nutrition_profile_"+args.dialect+".json")
    if path.exists():
        raise ValueError("Never overwrite a captured target silently")
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from tests.followup34_fixtures import owned_database
    from tests.integration_schema_migrations import run_migration

    migration = importlib.import_module("web.database.alembic.versions.20261020_nutrition_profile")
    with owned_database(args.dialect, temporary/"capture35") as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", migration.down_revision)
        with engine.begin() as connection:
            if args.dialect == "sqlite" and not connection.connection.driver_connection.in_transaction:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            with Operations.context(MigrationContext.configure(connection)):
                migration.create_declaration_column()
            value = migration.signature(connection)
        path.write_bytes((json.dumps(value, sort_keys=True, indent=2)+"\n").encode())
        print(json.dumps({"dialect": args.dialect, "tables": len(value["signature"]["tables"]), "target": path.name}))


if __name__ == "__main__":
    main()
