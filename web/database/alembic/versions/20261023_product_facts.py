"""Revision38: future-only data-origin declarations and typed product facts.

There is deliberately no reconstruction INSERT from old business rows. Empty
downgrade is reversible; nonempty downgrade refuses to discard retained facts.
"""
import importlib
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from web.database.product_analytics_policy_v2 import install, signature as product_signature, uninstall
from web.database.product_analytics_schema_v2 import TABLE, fact_table

revision = "20261023_product_facts"
down_revision = "20261020_account_security"
branch_labels = None
depends_on = None


def signature(connection):
    result = importlib.import_module("web.database.alembic.versions.20261020_account_security").signature(connection)
    result["product_analytics_security"] = product_signature(connection)
    return result


def verify(connection, name):
    actual = signature(connection)
    if name == down_revision:
        actual.pop("product_analytics_security")
    path = Path(__file__).parent.parent / "schema_targets" / (name + "_" + connection.dialect.name + ".json")
    if actual != json.loads(path.read_text(encoding="utf-8")):
        raise RuntimeError("Product facts require the reviewed schema/security contract")


def begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def create_table(connection):
    metadata = sa.MetaData()
    for name in ("usuarios", "clientes"):
        sa.Table(name, metadata, autoload_with=connection)
    fact_table(metadata, sa.DateTime()).create(connection, checkfirst=False)
    install(connection)


def upgrade():
    connection = op.get_bind()
    begin(connection)
    verify(connection, down_revision)
    create_table(connection)
    verify(connection, revision)


def downgrade():
    connection = op.get_bind()
    begin(connection)
    verify(connection, revision)
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM product_analytics_facts)")):
        raise RuntimeError("Product facts require a reviewed data-preserving restore")
    uninstall(connection)
    op.drop_table(TABLE)
    verify(connection, down_revision)
