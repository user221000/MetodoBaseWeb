"""Revision40: optional per-gym training inventory; no inferred legacy stock."""
import importlib
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from web.database.alembic.schema_contract_v2 import schema_contracts_equal

revision = "20261031_gym_equipment"
down_revision = "20261023_privacy_disposition"
branch_labels = depends_on = None


def signature(connection):
    # The predecessor captures all schema and security components dynamically;
    # retain every policy/function/role component, not a hand-copied subset.
    return importlib.import_module(
        "web.database.alembic.versions.20261023_privacy_disposition").signature(connection)


def verify(connection, name):
    path = Path(__file__).parent.parent / "schema_targets" / (name + "_" + connection.dialect.name + ".json")
    if not schema_contracts_equal(signature(connection), json.loads(path.read_bytes())):
        raise RuntimeError("Gym equipment requires the genuinely captured schema/security target")


def add_inventory_column(connection):
    """Add one bounded nullable column; leave all existing rows and RLS intact."""
    connection.exec_driver_sql("ALTER TABLE gym_settings ADD COLUMN training_equipment_json TEXT "
        "CONSTRAINT ck_gym_training_equipment_bound CHECK "
        "(training_equipment_json IS NULL OR length(training_equipment_json) BETWEEN 2 AND 16384)")


def _begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def upgrade():
    connection = op.get_bind()
    _begin(connection)
    verify(connection, down_revision)
    add_inventory_column(connection)
    verify(connection, revision)


def downgrade():
    connection = op.get_bind()
    _begin(connection)
    verify(connection, revision)
    if connection.dialect.name == "postgresql":
        # This does not grant a bypass. PostgreSQL must reject a guard query
        # that would otherwise silently hide tenant rows from its DDL owner.
        connection.execute(sa.text("SET LOCAL row_security=off"))
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM gym_settings WHERE training_equipment_json IS NOT NULL)")):
        raise RuntimeError("Saved gym inventories require a reviewed data-preserving recovery")
    op.drop_column("gym_settings", "training_equipment_json")
    verify(connection, down_revision)
