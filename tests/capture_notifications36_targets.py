"""Explicit author capture36; frozen targets22-35 are never rewritten."""
import argparse,importlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from tests.isolation import prepare_environment,block_external_sockets
    from tests.notifications36_fixtures import owned_database
    from tests.integration_schema_migrations import run_migration
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    parser=argparse.ArgumentParser();parser.add_argument("--dialect",choices=("sqlite","postgresql"),default="sqlite")
    dialect=parser.parse_args().dialect
    directory=prepare_environment(discard_inherited=True);block_external_sockets()
    migration=importlib.import_module("web.database.alembic.versions.20261020_notifications")
    path=ROOT/("web/database/alembic/schema_targets/20261020_notifications_"+dialect+".json")
    if path.exists():raise RuntimeError("Never overwrite a captured target")
    with owned_database(dialect,directory/"capture36") as (url,engine):
        run_migration(url,"db_bootstrap.py","--revision",migration.down_revision)
        with engine.begin() as connection:
            if dialect=="sqlite":connection.exec_driver_sql("BEGIN IMMEDIATE")
            migration.verify(connection,migration.down_revision)
            with Operations.context(MigrationContext.configure(connection)):
                migration.create_tables()
            value=migration.signature(connection)
        with path.open("xb") as f:f.write((json.dumps(value,sort_keys=True,indent=2)+"\n").encode())
        print(json.dumps({"dialect":dialect,"tables":len(value["signature"]["tables"]),"target":path.name}))


if __name__=="__main__":main()
