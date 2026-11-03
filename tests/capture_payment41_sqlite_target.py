"""Capture new41 from genuine migrations and additive DDL in owned SQLite RAM."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from tests.isolation import prepare_environment, block_external_sockets
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from alembic import command
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine
    from web.database.schema_control import alembic_config

    path = ROOT / "web/database/alembic/schema_targets/20261102_payment_refund_facts_sqlite.json"
    if path.exists():
        raise RuntimeError("Never overwrite a captured target")
    migration = importlib.import_module("web.database.alembic.versions.20261102_payment_refund_facts")
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            config = alembic_config()
            config.attributes["connection"] = connection
            command.upgrade(config, migration.down_revision)
            migration.verify(connection, migration.down_revision)
            with Operations.context(MigrationContext.configure(connection)):
                migration.add_columns(connection)
            value = migration.signature(connection)
            connection.commit()
            if connection.exec_driver_sql("PRAGMA foreign_key_check").all():
                raise RuntimeError("Captured schema has a foreign key violation")
        raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
        with path.open("xb") as output:
            output.write(raw)
        print(json.dumps({"dialect": "sqlite", "target": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "tables": len(value["signature"]["tables"]),
            "scope": "actual_migration40_then_additive41_DDL_in_owned_memory_database"}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
