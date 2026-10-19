"""Revision31-only fixtures: no historical target/expectation is rewritten."""
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pytest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.history_index_contract_v1 import history_index_signature

PREVIOUS = "20261019_personal_history_index"
REVISION = "20261019_mfa"


@pytest.fixture(params=["sqlite", "postgresql"])
def mfa_database(request, tmp_path):
    """Record attribution at creation; never infer ownership from a DB name."""
    from tests.history_index_fixtures import history_migration_database
    owner = history_migration_database.__wrapped__(request, tmp_path)
    url, engine = next(owner)
    try:
        output = os.environ.get("METODOBASE_HISTORY_ORDERED_PROOF_DIR")
        if output and engine.dialect.name == "postgresql":
            with (Path(output) / "mfa31-owned-created.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"database":engine.url.database,"pid":os.getpid(),
                    "attempt":os.environ.get("METODOBASE_MFA31_ATTEMPT", ""),
                    "created_at":datetime.now(timezone.utc).isoformat(),
                    "fixture":"mfa31_fixtures.mfa_database"}) + "\n")
        yield url, engine
    finally:
        owner.close()


def signature(connection):
    return {"signature": schema_signature(connection), "tenant_security": tenant_security_signature(connection),
            "member_link_security": member_link_security_signature(connection),
            "history_order_index": history_index_signature(connection)}


def create_target_tables(engine):
    """One-time author target capture uses the SAME frozen migration DDL.

    It is not runtime or an acceptance fixture: normal tests must execute the
    whole upgrade and compare its output to the reviewed committed target.
    """
    migration = importlib.import_module("web.database.alembic.versions.20261019_mfa")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.create_tables()
        return signature(connection)
