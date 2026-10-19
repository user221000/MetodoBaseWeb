"""Explicit self reports and versioned, revocable progress consent, revision32."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.history_index_contract_v1 import history_index_signature
from web.database.progress_policy import PROVENANCE_CHECK, SELF_REPORT_CHECK, install, signature

revision = "20261019_personal_progress"
down_revision = "20261019_mfa"
branch_labels = None
depends_on = None


def _target(connection, name):
    return json.loads((Path(__file__).parent.parent / "schema_targets" / (name+"_"+connection.dialect.name+".json")).read_text(encoding="utf-8"))


def _verify(connection, target):
    actual = {"signature":schema_signature(connection),"tenant_security":tenant_security_signature(connection),
        "member_link_security":member_link_security_signature(connection),"history_order_index":history_index_signature(connection)}
    if "progress_security" in target:
        actual["progress_security"] = signature(connection)
    if actual != target:
        raise RuntimeError("Progress requires the exact reviewed predecessor/schema/security contract")


def create_tables():
    """Add metadata only; never reinterpret legacy dates, notes or numbers."""
    with op.batch_alter_table("client_progress") as batch:
        for column in [sa.Column("record_key",sa.String(36)),
                sa.Column("source_kind",sa.String(24),nullable=False,server_default="legacy_unverified"),
                sa.Column("measured_on",sa.Date()),sa.Column("recorded_by_id",sa.String(36)),
                sa.Column("recorded_at",sa.DateTime()),sa.Column("updated_at",sa.DateTime()),
                sa.Column("version",sa.Integer(),nullable=False,server_default="1"),sa.Column("withdrawn_at",sa.DateTime())]:
            batch.add_column(column)
        batch.create_foreign_key("fk_progress_author","usuarios",["recorded_by_id"],["id"],ondelete="RESTRICT")
        batch.create_unique_constraint("uq_progress_record_key",["record_key"])
        batch.create_check_constraint("ck_progress_provenance",PROVENANCE_CHECK)
        batch.create_check_constraint("ck_progress_self_report",SELF_REPORT_CHECK)
    op.create_table("progress_consents",
        sa.Column("id",sa.String(36),primary_key=True),sa.Column("link_id",sa.String(36),nullable=False),
        sa.Column("gym_id",sa.String(36),nullable=False),sa.Column("client_id",sa.String(36),nullable=False),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("version",sa.Integer(),nullable=False),sa.Column("link_version",sa.Integer(),nullable=False),
        sa.Column("event",sa.String(8),nullable=False),sa.Column("protocol",sa.String(32),nullable=False),
        sa.Column("source_profile_id",sa.String(36)),sa.Column("share_weight",sa.Boolean(),nullable=False),
        sa.Column("share_body_fat",sa.Boolean(),nullable=False),sa.Column("share_lean_mass",sa.Boolean(),nullable=False),
        sa.Column("share_completion",sa.Boolean(),nullable=False),sa.Column("from_date",sa.Date(),nullable=False),
        sa.Column("through_date",sa.Date()),sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.ForeignKeyConstraint(["link_id","gym_id","client_id","user_id"],["client_account_links.id","client_account_links.gym_id","client_account_links.client_id","client_account_links.user_id"],name="fk_progress_consent_link",ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id","source_profile_id"],["clientes.gym_id","clientes.id_cliente"],name="fk_progress_consent_profile",ondelete="RESTRICT"),
        sa.UniqueConstraint("link_id","version",name="uq_progress_consent_version"),
        sa.CheckConstraint("version BETWEEN 1 AND 2147483647 AND link_version BETWEEN 1 AND 2147483647",name="ck_progress_consent_versions"),
        sa.CheckConstraint("CAST(event AS TEXT) IN (CAST('grant' AS TEXT),CAST('withdraw' AS TEXT)) AND CAST(protocol AS TEXT) = CAST('progress_share_v1' AS TEXT)",name="ck_progress_consent_protocol"),
        sa.CheckConstraint("through_date IS NULL OR through_date >= from_date",name="ck_progress_consent_dates"),
        sa.CheckConstraint("(share_weight OR share_body_fat OR share_lean_mass OR share_completion) AND (NOT (share_weight OR share_body_fat OR share_lean_mass) OR source_profile_id IS NOT NULL)",name="ck_progress_consent_categories"))
    op.create_index("ix_progress_consent_subject","progress_consents",["user_id","id"])
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
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM progress_consents)")) or connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM client_progress WHERE source_kind<>'legacy_unverified')")):
        raise RuntimeError("Progress rollback with authored data requires reviewed restore/export")
    if connection.dialect.name=="postgresql":
        connection.exec_driver_sql("DROP TRIGGER r25_measurement ON client_progress")
        connection.exec_driver_sql("DROP FUNCTION r25_guard_measurement()")
    else:
        connection.exec_driver_sql("DROP TRIGGER r25_measurement_insert")
        connection.exec_driver_sql("DROP TRIGGER r25_measurement_update")
    op.drop_table("progress_consents")
    if connection.dialect.name=="postgresql":
        connection.exec_driver_sql("DROP FUNCTION r25_guard_consent()")
        connection.exec_driver_sql("DROP FUNCTION r25_personal(text)")
        connection.exec_driver_sql("DROP FUNCTION r25_account(text)")
    with op.batch_alter_table("client_progress") as batch:
        batch.drop_constraint("fk_progress_author",type_="foreignkey")
        batch.drop_constraint("uq_progress_record_key",type_="unique")
        batch.drop_constraint("ck_progress_provenance",type_="check")
        batch.drop_constraint("ck_progress_self_report",type_="check")
        for name in ("record_key","source_kind","measured_on","recorded_by_id","recorded_at","updated_at","version","withdrawn_at"):
            batch.drop_column(name)
    _verify(connection,_target(connection,down_revision))
