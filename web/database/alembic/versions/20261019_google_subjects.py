"""Explicit stable Google authentication bindings, never inferred from email."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.history_index_contract_v1 import history_index_signature
from web.database.progress_policy import signature as progress_signature
from web.database.google_identity_policy import install, signature as google_signature

revision = "20261019_google_subjects"
down_revision = "20261019_personal_progress"
branch_labels = None
depends_on = None


def _target(connection, name):
    return json.loads((Path(__file__).parent.parent/"schema_targets"/(name+"_"+connection.dialect.name+".json")).read_text(encoding="utf-8"))


def _verify(connection, target):
    actual = {"signature":schema_signature(connection),"tenant_security":tenant_security_signature(connection),
        "member_link_security":member_link_security_signature(connection),"history_order_index":history_index_signature(connection),
        "progress_security":progress_signature(connection)}
    if "google_identity_security" in target:
        actual["google_identity_security"] = google_signature(connection)
    if actual != target:
        raise RuntimeError("Google binding requires the exact reviewed predecessor/schema/security contract")


def create_tables():
    op.create_table("auth_external_identities",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("issuer",sa.String(64),nullable=False),sa.Column("subject",sa.String(255),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("revoked_at",sa.DateTime()),sa.Column("version",sa.Integer(),nullable=False),
        sa.UniqueConstraint("issuer","subject",name="uq_auth_external_subject"),
        sa.CheckConstraint("CAST(issuer AS TEXT) = CAST('https://accounts.google.com' AS TEXT) AND length(subject) BETWEEN 1 AND 255",name="ck_auth_external_google"),
        sa.CheckConstraint("version BETWEEN 1 AND 2147483647 AND (revoked_at IS NULL OR revoked_at >= created_at)",name="ck_auth_external_state"))
    op.create_index("ix_auth_external_user","auth_external_identities",["user_id"])
    op.create_table("google_link_intents",
        sa.Column("token_hash",sa.String(64),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("issuer",sa.String(64),nullable=False),sa.Column("subject",sa.String(255),nullable=False),
        sa.Column("purpose",sa.String(32),nullable=False),sa.Column("access_hash",sa.String(64),nullable=False),
        sa.Column("session_version",sa.Integer(),nullable=False),sa.Column("generation",sa.Integer(),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("expires_at",sa.DateTime(),nullable=False),sa.Column("consumed_at",sa.DateTime()),
        sa.CheckConstraint("CAST(issuer AS TEXT) = CAST('https://accounts.google.com' AS TEXT) AND length(subject) BETWEEN 1 AND 255",name="ck_google_link_subject"),
        sa.CheckConstraint("CAST(purpose AS TEXT) = CAST('google_link' AS TEXT)",name="ck_google_link_purpose"),
        sa.CheckConstraint("session_version BETWEEN 0 AND 2147483647 AND generation BETWEEN 0 AND 2147483647",name="ck_google_link_versions"),
        sa.CheckConstraint("expires_at > created_at AND (consumed_at IS NULL OR (consumed_at >= created_at AND consumed_at < expires_at))",name="ck_google_link_instants"))
    op.create_index("ix_google_link_user","google_link_intents",["user_id"])
    install(op.get_bind())


def _begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")


def upgrade():
    connection=op.get_bind();_begin(connection)
    _verify(connection,_target(connection,down_revision))
    create_tables()
    _verify(connection,_target(connection,revision))


def downgrade():
    connection=op.get_bind();_begin(connection)
    _verify(connection,_target(connection,revision))
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM auth_external_identities) OR EXISTS(SELECT 1 FROM google_link_intents)")):
        raise RuntimeError("Google binding rollback with authentication history requires reviewed restore")
    op.drop_table("google_link_intents");op.drop_table("auth_external_identities")
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("DROP FUNCTION r33_intent_immutable()")
        connection.exec_driver_sql("DROP FUNCTION r33_identity_immutable()")
    _verify(connection,_target(connection,down_revision))
