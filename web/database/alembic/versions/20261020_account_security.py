"""Revision37: nullable contact proof/status, never an account activation flag."""
import importlib
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from web.database.account_security_schema_v1 import NAMES, columns

revision = "20261020_account_security"
down_revision = "20261020_notifications"
branch_labels = None
depends_on = None


def signature(connection):
    return importlib.import_module("web.database.alembic.versions.20261020_notifications").signature(connection)


def verify(connection, name):
    path = Path(__file__).parent.parent / "schema_targets" / (name + "_" + connection.dialect.name + ".json")
    if signature(connection) != json.loads(path.read_text(encoding="utf-8")):
        raise RuntimeError("Account security requires the exact reviewed schema/security contract")


def create_columns():
    for column in columns():
        op.add_column("usuarios", column)
    op.create_index("ix_usuarios_email_verification_hash", "usuarios", ["email_verification_hash"], unique=True)


def begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def upgrade():
    connection = op.get_bind()
    begin(connection)
    verify(connection, down_revision)
    create_columns()
    verify(connection, revision)


def downgrade():
    connection = op.get_bind()
    begin(connection)
    verify(connection, revision)
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM usuarios WHERE " +
                                 " OR ".join(name + " IS NOT NULL" for name in NAMES) + ")")):
        raise RuntimeError("Contact evidence requires a reviewed data-preserving restore")
    op.drop_index("ix_usuarios_email_verification_hash", table_name="usuarios")
    for name in reversed(NAMES):
        op.drop_column("usuarios", name)
    verify(connection, down_revision)
