"""Durable billing/quota identities and compatible session revocation.

Revision ID: 20261018_billing_integrity
Revises: 20260402_plan_json

Additive preparation only: no live rights reconciliation, no RLS activation and
no stamp. Existing individual Pro rows remain pending provider reconciliation.
Downgrade refuses to discard financial/generation records or paid Pro mappings;
restore the verified backup when those records exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261018_billing_integrity"
down_revision = "20260402_plan_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply additive schema and normalize the ORM's existing enum contract."""
    op.add_column("usuarios", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    conn = op.get_bind()
    # The established model makes a gym without a parent its own owner. Never
    # promote individuals or team members when fixing the historic viewer default.
    conn.execute(sa.text("UPDATE usuarios SET role='OWNER' WHERE tipo='gym' AND team_gym_id IS NULL AND lower(role)='viewer'"))
    invalid = conn.execute(sa.text("SELECT count(*) FROM usuarios WHERE upper(role) NOT IN ('OWNER','ADMIN','NUTRIOLOGO','VIEWER') OR (invitation_role IS NOT NULL AND upper(invitation_role) NOT IN ('OWNER','ADMIN','NUTRIOLOGO','VIEWER'))")).scalar_one()
    if invalid:
        raise RuntimeError("Unknown persisted roles require explicit reconciliation")
    conn.execute(sa.text("UPDATE usuarios SET role=upper(role), invitation_role=upper(invitation_role)"))
    conn.execute(sa.text("UPDATE subscriptions SET stripe_subscription_id=NULL WHERE stripe_subscription_id=''"))
    conn.execute(sa.text("UPDATE subscriptions SET stripe_customer_id=NULL WHERE stripe_customer_id=''"))
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_constraint("ck_subscription_plan", type_="check")
        batch.create_check_constraint("ck_subscription_plan", "plan IN ('free','standard','gym_comercial','clinica','pro_usuario')")
        batch.add_column(sa.Column("provider", sa.String(20), nullable=True))
        batch.add_column(sa.Column("provider_payment_id", sa.String(255), nullable=True))
        batch.create_unique_constraint("uq_subscription_provider_payment", ["provider_payment_id"])
    op.create_table("purchase_intents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("operation", sa.String(30), nullable=False),
        sa.Column("request_key", sa.String(128), nullable=False),
        sa.Column("plan", sa.String(30), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("provider_customer_id", sa.String(255)),
        sa.Column("provider_reference_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("subject_id", "provider", "operation", "request_key", name="uq_purchase_operation_key"),
        sa.CheckConstraint("amount_cents > 0", name="ck_purchase_positive_amount"))
    op.create_index("ix_purchase_intents_subject_id", "purchase_intents", ["subject_id"])
    op.create_index("ix_purchase_intents_provider_reference_id", "purchase_intents", ["provider_reference_id"])
    op.create_table("generation_reservations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_key", sa.String(128), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("planes_generados.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "request_key", name="uq_generation_request_key"),
        sa.CheckConstraint("status IN ('reserved','completed','released')", name="ck_generation_reservation_status"))
    op.create_index("ix_generation_reservations_user_id", "generation_reservations", ["user_id"])


def downgrade() -> None:
    """Refuse irreversible loss of billing/generation state during rollback."""
    conn = op.get_bind()
    for table in ("purchase_intents", "generation_reservations"):
        if conn.execute(sa.select(sa.func.count()).select_from(sa.table(table))).scalar_one():
            raise RuntimeError("Rollback requires a verified restore; durable operation records exist")
    if conn.execute(sa.text("SELECT count(*) FROM subscriptions WHERE plan='pro_usuario'")).scalar_one():
        raise RuntimeError("Rollback cannot discard individual paid subscriptions")
    op.drop_table("generation_reservations")
    op.drop_table("purchase_intents")
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_constraint("uq_subscription_provider_payment", type_="unique")
        batch.drop_column("provider_payment_id")
        batch.drop_column("provider")
        batch.drop_constraint("ck_subscription_plan", type_="check")
        batch.create_check_constraint("ck_subscription_plan", "plan IN ('free','standard','gym_comercial','clinica')")
    op.drop_column("usuarios", "session_version")
