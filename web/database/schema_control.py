"""Read-only schema signatures and startup gates; never repair schema at runtime."""
import json
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from web.database.alembic.schema_contract_v1 import schema_signature

ROOT = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    """Resolve migration paths independently of the process working directory."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "web" / "database" / "alembic"))
    return config


def expected_head() -> str:
    """Require one migration head, failing explicitly on an unresolved branch."""
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    if len(heads) != 1:
        raise RuntimeError("Migration history must have exactly one head")
    return heads[0]


def verify_legacy_signature(connection) -> None:
    """Accept only the exact frozen legacy schema before assigning its revision."""
    path = Path(__file__).parent / "schema_baselines" / ("20260402_orm_" + connection.dialect.name + ".json")
    if not path.is_file():
        raise RuntimeError("No reviewed legacy schema baseline for this dialect")
    expected = json.loads(path.read_text(encoding="utf-8"))
    if schema_signature(connection) != expected["signature"]:
        raise RuntimeError("Legacy schema differs from reviewed baseline; reconcile drift before adoption")


def verify_runtime_schema(engine, *, require_revision: bool = True) -> None:
    """Fail before traffic when migrations or required application columns are missing.

    Only isolated unit SQLite fixtures may opt out of revision bookkeeping. They
    still require all application columns. PostgreSQL always requires exact head.
    """
    from web.database.models import Base
    with engine.connect() as connection:
        inspector = inspect(connection)
        if require_revision or connection.dialect.name == "postgresql":
            actual = MigrationContext.configure(connection).get_current_heads()
            if actual != (expected_head(),):
                raise RuntimeError("Database revision does not match application; run reviewed migrations")
            target_path = Path(__file__).parent / "alembic" / "schema_targets" / ("20261018_reconciled_" + connection.dialect.name + ".json")
            target = json.loads(target_path.read_text(encoding="utf-8"))["signature"]
            if schema_signature(connection) != target:
                raise RuntimeError("Database structure differs from the reviewed application schema")
        available = set(inspector.get_table_names())
        for table in Base.metadata.sorted_tables:
            if table.name not in available:
                raise RuntimeError("Database is missing an application table")
            actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
            if not set(table.columns.keys()).issubset(actual_columns):
                raise RuntimeError("Database is missing application columns")
