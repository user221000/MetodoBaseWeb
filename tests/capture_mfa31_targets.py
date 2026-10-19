"""Author-only one-time target capture in a disposable owned test database.

This utility cannot adopt an unknown database, run against a supplied URL or
overwrite a historical target. Acceptance subsequently uses normal Alembic.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialect", choices=["sqlite", "postgresql"], required=True)
    parser.add_argument("--private-config", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    from tests.isolation import prepare_environment, block_external_sockets
    temporary = prepare_environment(discard_inherited=True)
    block_external_sockets()
    if not args.evidence.is_dir():
        raise ValueError("Explicit evidence directory required")
    if args.dialect == "postgresql":
        if args.private_config is None:
            raise ValueError("Explicit synthetic configuration required")
        config = json.loads(args.private_config.read_text(encoding="utf-8"))
        for key in ("METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL"):
            os.environ[key] = config[key]
    os.environ["METODOBASE_HISTORY_ORDERED_PROOF_DIR"] = str(args.evidence)
    target = ROOT / "web/database/alembic/schema_targets" / ("20261019_mfa_" + args.dialect + ".json")
    if target.exists():
        raise ValueError("Target already exists; do not overwrite reviewed bytes")
    from tests.mfa31_fixtures import mfa_database
    from tests.integration_schema_migrations import run_migration
    from tests.mfa31_fixtures import PREVIOUS, create_target_tables
    os.environ["METODOBASE_MFA31_ATTEMPT"] = "target-capture-textcast-" + args.dialect
    owner = mfa_database.__wrapped__(SimpleNamespace(param=args.dialect), temporary)
    url, engine = next(owner)
    try:
        run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
        value = create_target_tables(engine)
        target.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"dialect": args.dialect, "target": target.name, "tables": len(value["signature"]["tables"])}))
    finally:
        owner.close()


if __name__ == "__main__":
    main()
