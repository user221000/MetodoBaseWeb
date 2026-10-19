"""Author-only33 capture using the new additive binding DDL; no old target writes."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--dialect",choices=["sqlite","postgresql"],required=True)
    parser.add_argument("--private-config",type=Path)
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    from tests.isolation import prepare_environment,block_external_sockets
    temporary=prepare_environment(discard_inherited=True);block_external_sockets()
    if not args.evidence.is_dir():raise ValueError("Existing own evidence directory required")
    if args.dialect=="postgresql":
        if args.private_config is None:raise ValueError("Explicit synthetic configuration required")
        config=json.loads(args.private_config.read_text(encoding="utf-8"))
        for key in ("METODOBASE_TEST_MIGRATOR_URL","METODOBASE_TEST_POSTGRES_URL"):os.environ[key]=config[key]
    os.environ["GOOGLE33_PRIVATE_LEASES"]=str(args.evidence)
    path=ROOT/"web/database/alembic/schema_targets"/("20261019_google_subjects_"+args.dialect+".json")
    if path.exists():raise ValueError("Never overwrite a captured target silently")
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from tests.google33_fixtures import PREVIOUS,owned_database,signature
    from tests.integration_schema_migrations import run_migration
    with owned_database(args.dialect,temporary/"capture33") as (url,engine):
        run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
        migration=importlib.import_module("web.database.alembic.versions.20261019_google_subjects")
        with engine.begin() as connection:
            if args.dialect=="sqlite" and not connection.connection.driver_connection.in_transaction:connection.exec_driver_sql("BEGIN")
            with Operations.context(MigrationContext.configure(connection)):migration.create_tables()
            value=signature(connection)
        path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8",newline="\n")
        print(json.dumps({"dialect":args.dialect,"tables":len(value["signature"]["tables"]),"target":path.name}))


if __name__=="__main__":main()
