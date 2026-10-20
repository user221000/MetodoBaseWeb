"""Revision35: bounded declarations, preserving unknown legacy profiles."""
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from web.database.alembic.history_index_contract_v1 import history_index_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.followup_policy import signature as followup_signature
from web.database.google_identity_policy import signature as google_signature
from web.database.progress_policy import signature as progress_signature

revision = "20261020_nutrition_profile"
down_revision = "20261019_followup_tasks"
branch_labels = None
depends_on = None


def signature(connection):
    """Retain every predecessor security component; only schema columns change."""
    return {"signature": schema_signature(connection), "tenant_security": tenant_security_signature(connection),
        "member_link_security": member_link_security_signature(connection), "history_order_index": history_index_signature(connection),
        "progress_security": progress_signature(connection), "google_identity_security": google_signature(connection),
        "followup_security": followup_signature(connection)}


def _target(connection, name):
    path = Path(__file__).parent.parent/"schema_targets"/(name+"_"+connection.dialect.name+".json")
    return json.loads(path.read_text(encoding="utf-8"))


def _verify(connection, name):
    if signature(connection) != _target(connection, name):
        raise RuntimeError("Nutrition declaration requires the exact reviewed schema/security contract")


def _begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def create_declaration_column():
    """Add one nullable column and its inline bound without rebuilding clients.

    A SQLite table rebuild could remove existing guards or affect referenced
    history. The literal additive DDL has no user input. SQL NULL remains the
    unknown legacy declaration; no row is backfilled as allergy-free.
    """
    connection = op.get_bind()
    connection.exec_driver_sql("ALTER TABLE clientes ADD COLUMN nutrition_restrictions_json TEXT "
        "CONSTRAINT ck_cliente_nutrition_declaration_bound CHECK "
        "(nutrition_restrictions_json IS NULL OR length(nutrition_restrictions_json) BETWEEN 2 AND 16384)")


def upgrade():
    connection = op.get_bind()
    _begin(connection)
    _verify(connection, down_revision)
    create_declaration_column()
    _verify(connection, revision)


def downgrade():
    connection = op.get_bind()
    _begin(connection)
    _verify(connection, revision)
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM clientes WHERE nutrition_restrictions_json IS NOT NULL)")):
        raise RuntimeError("Nutrition declarations require a reviewed data-preserving restore before rollback")
    op.drop_column("clientes", "nutrition_restrictions_json")
    _verify(connection, down_revision)
