"""Activate the reviewed transaction-local tenant boundary on PostgreSQL.

The fixed table/policy vocabulary belongs to this revision. Unexpected policies
abort instead of silently composing a permissive OR or deleting custom rules.
SQLite remains a development adapter and is forbidden in production runtime.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261018_tenant_isolation"
down_revision = "20261018_provider_subjects"
branch_labels = None
depends_on = None

TENANT_COLUMNS = {
    "clientes": "gym_id", "planes_generados": "gym_id", "client_progress": "gym_id",
    "subscriptions": "gym_id", "payments": "gym_id", "stripe_customers": "gym_id",
    "invoices": "gym_id", "checkout_sessions": "gym_id", "gym_profiles": "gym_id",
    "gym_branding": "gym_id", "gym_settings": "gym_id", "gym_licenses": "gym_id",
    "planes_suscripcion": "gym_id", "audit_log": "gym_id",
    "user_subscriptions": "user_id", "generation_reservations": "user_id",
    "license_activations": "gym_id",
}


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return
    existing = connection.execute(sa.text("SELECT tablename,policyname FROM pg_policies WHERE schemaname=current_schema()")).all()
    expected = {table: "tenant_isolation_planes" if table == "planes_generados" else "tenant_isolation_" + table
                for table in TENANT_COLUMNS}
    for table, policy in existing:
        if table not in expected or policy != expected[table]:
            raise RuntimeError("Unexpected tenant policy requires explicit reconciliation")
    quote = connection.dialect.identifier_preparer.quote
    for table, column in TENANT_COLUMNS.items():
        context = {"table_name": quote(table), "policy_name": quote(expected[table]), "tenant_column": quote(column)}
        connection.execute(sa.DDL("DROP POLICY IF EXISTS %(policy_name)s ON %(table_name)s", context=context))
        connection.execute(sa.DDL("CREATE POLICY %(policy_name)s ON %(table_name)s FOR ALL USING (%(tenant_column)s = NULLIF(current_setting('app.current_tenant', TRUE), '')) WITH CHECK (%(tenant_column)s = NULLIF(current_setting('app.current_tenant', TRUE), ''))", context=context))
        connection.execute(sa.DDL("ALTER TABLE %(table_name)s ENABLE ROW LEVEL SECURITY", context=context))
        connection.execute(sa.DDL("ALTER TABLE %(table_name)s FORCE ROW LEVEL SECURITY", context=context))
    # Replace an already-applied historic SECURITY DEFINER/session-wide helper.
    # This function cannot read business data or establish ambient authority.
    connection.execute(sa.text("""
        CREATE OR REPLACE FUNCTION set_tenant(tenant_id TEXT)
        RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.current_tenant', tenant_id, TRUE);
        END;
        $$ LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog
    """))


def downgrade():
    raise RuntimeError("Tenant boundary rollback requires reviewed application rollback and verified backup/restore")
