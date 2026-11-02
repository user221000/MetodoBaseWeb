"""Revision41: nullable current refund observations; preserve historical unknowns."""
import importlib
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from web.database.alembic.schema_contract_v2 import schema_contracts_equal
from web.database.payment_refund_schema_v1 import columns

revision = "20261102_payment_refund_facts"
down_revision = "20261031_gym_equipment"
branch_labels = depends_on = None


def signature(connection):
    return importlib.import_module(
        "web.database.alembic.versions.20261031_gym_equipment").signature(connection)


def verify(connection, name):
    path = Path(__file__).parent.parent / "schema_targets" / (name + "_" + connection.dialect.name + ".json")
    if not schema_contracts_equal(signature(connection), json.loads(path.read_bytes())):
        raise RuntimeError("Payment refund facts require the genuinely captured schema/security target")


def add_columns(connection):
    # Real additive DDL only. No row update, default, create_all or stamp.
    for column in columns(sa.DateTime()):
        op.add_column("payments", column)


def _begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def upgrade():
    connection = op.get_bind()
    _begin(connection)
    verify(connection, down_revision)
    add_columns(connection)
    verify(connection, revision)


def downgrade():
    connection = op.get_bind()
    _begin(connection)
    verify(connection, revision)
    if connection.dialect.name == "postgresql":
        connection.execute(sa.text("SET LOCAL row_security=off"))
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM payments WHERE refund_amount_cents IS NOT NULL "
        "OR refund_observed_at IS NOT NULL OR stripe_charge_id IS NOT NULL)")):
        raise RuntimeError("Observed refund facts require a reviewed data-preserving recovery")
    for name in ("stripe_charge_id", "refund_observed_at", "refund_amount_cents"):
        op.drop_column("payments", name)
    verify(connection, down_revision)
