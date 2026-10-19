"""Reviewed R04 tenant families; importing this module never executes DDL.

Authentication, purchase identity and replay inbox tables form a documented
control plane. This contract deliberately does not claim universal RLS.
"""
from sqlalchemy import DDL, text
from web.database.alembic.security_contract_v1 import tenant_security_signature  # noqa: F401

TENANT_COLUMNS = {
    "clientes": "gym_id", "planes_generados": "gym_id", "client_progress": "gym_id",
    "subscriptions": "gym_id", "payments": "gym_id", "stripe_customers": "gym_id",
    "invoices": "gym_id", "checkout_sessions": "gym_id", "gym_profiles": "gym_id",
    "gym_branding": "gym_id", "gym_settings": "gym_id", "gym_licenses": "gym_id",
    "planes_suscripcion": "gym_id", "audit_log": "gym_id",
    "user_subscriptions": "user_id", "generation_reservations": "user_id",
    "license_activations": "gym_id",
    "gym_generation_reservations": "gym_id",
}
CONTROL_PLANE = frozenset({"usuarios", "refresh_tokens", "purchase_intents",
    "stripe_webhook_events", "auth_audit_log", "provider_subject_associations"})


def policy_name(table: str) -> str:
    if table not in TENANT_COLUMNS:
        raise ValueError("Unknown tenant policy table")
    return "tenant_isolation_planes" if table == "planes_generados" else "tenant_isolation_" + table


def policy_ddl(dialect):
    """Describe only fixed reviewed identifiers; callers own rollout/transaction."""
    if dialect.name != "postgresql":
        return
    quote = dialect.identifier_preparer.quote
    for table, column in TENANT_COLUMNS.items():
        context = {"table_name": quote(table), "policy_name": quote(policy_name(table)), "tenant_column": quote(column)}
        yield DDL("DROP POLICY IF EXISTS %(policy_name)s ON %(table_name)s", context=context)
        yield DDL("CREATE POLICY %(policy_name)s ON %(table_name)s FOR ALL USING (%(tenant_column)s = NULLIF(current_setting('app.current_tenant', TRUE), '')) WITH CHECK (%(tenant_column)s = NULLIF(current_setting('app.current_tenant', TRUE), ''))", context=context)
        yield DDL("ALTER TABLE %(table_name)s ENABLE ROW LEVEL SECURITY", context=context)
        yield DDL("ALTER TABLE %(table_name)s FORCE ROW LEVEL SECURITY", context=context)


def verify_application_database_role(engine) -> None:
    """An application PostgreSQL connection must never bypass FORCE RLS."""
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as connection:
        superuser, bypass = connection.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
        if superuser or bypass:
            raise RuntimeError("Application database role must be NOSUPERUSER and NOBYPASSRLS")
        # FORCE RLS constrains an owner only until that owner issues ALTER TABLE.
        # MEMBER also rejects indirect access to the migration/DDL owner role.
        from web.database.models import Base
        owns_ddl = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_class c WHERE c.relnamespace=current_schema()::regnamespace
                AND c.relkind IN ('r','p') AND c.relname=ANY(:tables)
                AND pg_has_role(current_user,c.relowner,'MEMBER')
            )
        """), {"tables": sorted(Base.metadata.tables)}).scalar_one()
        if owns_ddl:
            raise RuntimeError("Application database role must not be a table DDL owner or member of its role")


