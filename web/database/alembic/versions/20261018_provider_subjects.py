"""Prepare minimal historical provider associations before RLS rollout.

No RLS flags or rights change here. A collision across subjects aborts; existing
canonical subscription/customer IDs are the only legacy backfill authority.
"""
from datetime import datetime, timezone
import hashlib
from alembic import op
import sqlalchemy as sa

revision = "20261018_provider_subjects"
down_revision = "20261018_schema_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("provider_subject_associations",
        sa.Column("provider", sa.String(20), primary_key=True),
        sa.Column("resource_type", sa.String(30), primary_key=True),
        sa.Column("resource_id", sa.String(255), primary_key=True),
        sa.Column("subject_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provenance", sa.String(30), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("provider IN ('stripe','mercadopago')", name="ck_provider_subject_provider"),
        sa.CheckConstraint("resource_type IN ('customer','subscription','payment','preference')", name="ck_provider_subject_resource"),
        sa.CheckConstraint("provenance IN ('legacy_subscription','legacy_customer','verified_purchase')", name="ck_provider_subject_provenance"))
    op.create_index("ix_provider_subject_associations_subject_id", "provider_subject_associations", ["subject_id"])
    with op.batch_alter_table("license_activations") as batch:
        batch.add_column(sa.Column("gym_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("issued_license_id", sa.Integer(), nullable=True))
        batch.alter_column("expira", existing_type=sa.DateTime(), existing_nullable=False, nullable=True)
        batch.create_foreign_key("fk_activation_gym", "usuarios", ["gym_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_activation_issued_license", "gym_licenses", ["issued_license_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_license_activations_gym_id", ["gym_id"])
        batch.create_index("ix_license_activations_issued_license_id", ["issued_license_id"])
    connection = op.get_bind()
    links = sa.table("provider_subject_associations", sa.column("provider"), sa.column("resource_type"),
                     sa.column("resource_id"), sa.column("subject_id"), sa.column("provenance"),
                     sa.column("source_ref"), sa.column("created_at"))
    users = sa.table("usuarios", sa.column("id"))
    subscriptions = sa.table("subscriptions", sa.column("id"), sa.column("gym_id"),
                             sa.column("stripe_subscription_id"), sa.column("stripe_customer_id"))
    customers = sa.table("stripe_customers", sa.column("id"), sa.column("gym_id"), sa.column("stripe_customer_id"))
    issued = sa.table("gym_licenses", sa.column("id"), sa.column("gym_id"), sa.column("license_key"))
    activations = sa.table("license_activations", sa.column("clave_hash"), sa.column("gym_id"), sa.column("issued_license_id"))

    def add(subject, kind, resource, provenance, source):
        if not resource:
            return
        where = (links.c.provider == "stripe", links.c.resource_type == kind, links.c.resource_id == resource)
        previous = connection.execute(sa.select(links.c.subject_id).where(*where)).scalar_one_or_none()
        if previous is not None:
            if previous != subject:
                raise RuntimeError("Conflicting historical provider associations require explicit reconciliation")
            return
        connection.execute(links.insert().values(provider="stripe", resource_type=kind, resource_id=resource,
            subject_id=subject, provenance=provenance, source_ref=str(source), created_at=datetime.now(timezone.utc)))

    # Existing FORCE RLS need not be disabled or bypassed for this backfill.
    # Visit canonical account IDs individually, under transaction-local context.
    postgres = connection.dialect.name == "postgresql"
    previous_context = connection.execute(sa.text("SELECT current_setting('app.current_tenant', TRUE)")).scalar_one() if postgres else None
    try:
        for subject in connection.execute(sa.select(users.c.id)).scalars().all():
            if postgres:
                connection.execute(sa.text("SELECT set_config('app.current_tenant', :tenant, TRUE)"), {"tenant": subject})
            for row in connection.execute(sa.select(subscriptions).where(subscriptions.c.gym_id == subject)).mappings():
                add(subject, "subscription", row["stripe_subscription_id"], "legacy_subscription", row["id"])
                add(subject, "customer", row["stripe_customer_id"], "legacy_subscription", row["id"])
            for row in connection.execute(sa.select(customers).where(customers.c.gym_id == subject)).mappings():
                add(subject, "customer", row["stripe_customer_id"], "legacy_customer", row["id"])
            for row in connection.execute(sa.select(issued).where(issued.c.gym_id == subject)).mappings():
                digest = hashlib.sha256(row["license_key"].encode("utf-8")).hexdigest()
                connection.execute(activations.update().where(activations.c.clave_hash == digest).values(
                    gym_id=subject, issued_license_id=row["id"]))
    finally:
        if postgres:
            connection.execute(sa.text("SELECT set_config('app.current_tenant', :tenant, TRUE)"), {"tenant": previous_context or ""})


def downgrade():
    raise RuntimeError("Provider identity preparation rollback requires verified backup/restore")
