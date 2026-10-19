"""Personal encrypted MFA and purpose-bound one-use authorization, revision31."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.history_index_contract_v1 import history_index_signature
from web.database.mfa_policy import install_policies

revision = "20261019_mfa"
down_revision = "20261019_personal_history_index"
branch_labels = None
depends_on = None


def _target(connection, name):
    path = Path(__file__).resolve().parent.parent / "schema_targets" / (name + "_" + connection.dialect.name + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


def _verify(connection, target):
    if (schema_signature(connection) != target["signature"]
            or tenant_security_signature(connection) != target["tenant_security"]
            or member_link_security_signature(connection) != target["member_link_security"]
            or history_index_signature(connection) != target["history_order_index"]):
        raise RuntimeError("MFA requires the exact reviewed schema/security/index contract")


def create_tables():
    """Frozen DDL, independent of later ORM classes and their Python defaults."""
    op.create_table("mfa_credentials",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("factor_id", sa.String(32), nullable=False, unique=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("secret_ciphertext", sa.Text()), sa.Column("enabled_at", sa.DateTime()),
        sa.Column("last_counter", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("pending_id", sa.String(32)), sa.Column("pending_ciphertext", sa.Text()),
        sa.Column("pending_expires_at", sa.DateTime()),
        sa.Column("attempts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("generation >= 0 AND last_counter >= -1", name="ck_mfa_credential_counters"),
        sa.CheckConstraint("(secret_ciphertext IS NULL AND enabled_at IS NULL) OR (secret_ciphertext IS NOT NULL AND enabled_at IS NOT NULL AND generation > 0)", name="ck_mfa_credential_active"),
        sa.CheckConstraint("(pending_id IS NULL AND pending_ciphertext IS NULL AND pending_expires_at IS NULL) OR (pending_id IS NOT NULL AND pending_ciphertext IS NOT NULL AND pending_expires_at IS NOT NULL)", name="ck_mfa_credential_pending"))
    op.create_table("mfa_recovery_codes",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("mfa_credentials.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("used_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("generation > 0 AND length(code_hash) = 64", name="ck_mfa_recovery_state"))
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])
    op.create_table("mfa_authorizations",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False), sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False), sa.Column("access_hash", sa.String(64)),
        sa.Column("action_binding", sa.String(64)), sa.Column("primary_method", sa.String(16), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=False), sa.Column("consumed_at", sa.DateTime()),
        sa.Column("factor_verified_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("CAST(purpose AS TEXT) IN (CAST('login' AS TEXT),CAST('reauth' AS TEXT),CAST('action' AS TEXT)) AND CAST(primary_method AS TEXT) IN (CAST('password' AS TEXT),CAST('google' AS TEXT))", name="ck_mfa_authorization_purpose"),
        sa.CheckConstraint("session_version >= 0 AND generation >= 0 AND attempts >= 0 AND length(token_hash) = 64", name="ck_mfa_authorization_counters"),
        sa.CheckConstraint("(purpose = 'login' AND access_hash IS NULL AND action_binding IS NULL AND ((consumed_at IS NULL AND factor_verified_at IS NULL) OR (consumed_at IS NOT NULL AND factor_verified_at IS NOT NULL AND factor_verified_at = consumed_at AND factor_verified_at >= created_at))) OR (purpose = 'reauth' AND access_hash IS NOT NULL AND length(access_hash) = 64 AND action_binding IS NULL AND factor_verified_at IS NULL) OR (purpose = 'action' AND access_hash IS NOT NULL AND length(access_hash) = 64 AND action_binding IS NOT NULL AND length(action_binding) = 64 AND factor_verified_at IS NOT NULL AND factor_verified_at <= created_at)", name="ck_mfa_authorization_binding"))
    op.create_index("ix_mfa_authorizations_user_id", "mfa_authorizations", ["user_id"])
    op.create_index("ix_mfa_authorizations_recent", "mfa_authorizations", ["user_id", "access_hash", "factor_verified_at"])
    install_policies(op.get_bind())


def upgrade():
    connection = op.get_bind()
    # sqlite3 defers BEGIN for SELECT/DDL; start a real transaction so a
    # post-DDL contract/constraint failure cannot leave half an upgrade.
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")
    _verify(connection, _target(connection, down_revision))
    create_tables()
    _verify(connection, _target(connection, revision))


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")
    _verify(connection, _target(connection, revision))
    # Never remove a factor/used-code history to turn MFA into primary-only.
    for table in ("mfa_authorizations", "mfa_recovery_codes", "mfa_credentials"):
        if connection.scalar(sa.select(sa.exists().select_from(sa.table(table)))):
            raise RuntimeError("MFA rollback with security state requires verified recovery/restore")
    for table in ("mfa_authorizations", "mfa_recovery_codes", "mfa_credentials"):
        op.drop_table(table)
    _verify(connection, _target(connection, down_revision))
