"""enable_rls_policies_multi_tenant

Revision ID: c4f8e9d2a3b1
Revises: 936af15af980
Create Date: 2026-03-24 10:30:00.000000

Row Level Security (RLS) policies para aislamiento multi-tenant en PostgreSQL.
Estas políticas garantizan que cada gym solo puede ver sus propios datos.

NOTA: Solo aplica para PostgreSQL. SQLite no soporta RLS.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'c4f8e9d2a3b1'
down_revision: Union[str, Sequence[str], None] = '936af15af980'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def is_postgres() -> bool:
    """Check if we're running on PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == 'postgresql'


def upgrade() -> None:
    """Define policies; activation is a separate, tested R04 rollout.

    Historic repair: new installations must not enable FORCE RLS before every
    transaction/worker receives tenant context. Already enabled policies remain
    untouched; no downgrade of an existing database's protection occurs here.
    """
    if not is_postgres():
        # SQLite no soporta RLS - skip silently
        return
    
    conn = op.get_bind()
    
    # ── Habilitar RLS en tablas con gym_id ────────────────────────────────────
    
    # Tabla: clientes
    conn.execute(text("""
        CREATE POLICY tenant_isolation_clientes ON clientes
        FOR ALL
        USING (gym_id = current_setting('app.current_tenant', TRUE))
        WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))
    """))
    
    # Tabla: planes_generados
    conn.execute(text("""
        CREATE POLICY tenant_isolation_planes ON planes_generados
        FOR ALL
        USING (gym_id = current_setting('app.current_tenant', TRUE))
        WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))
    """))
    
    # Tabla: subscriptions (si existe)
    conn.execute(text("""
            CREATE POLICY tenant_isolation_subscriptions ON subscriptions
            FOR ALL
            USING (gym_id = current_setting('app.current_tenant', TRUE))
            WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))
        """))
    
    # Tabla: payments (si existe)
    conn.execute(text("""
            CREATE POLICY tenant_isolation_payments ON payments
            FOR ALL
            USING (gym_id = current_setting('app.current_tenant', TRUE))
            WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))
        """))
    
    # ── Crear función helper para set tenant ──────────────────────────────────
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION set_tenant(tenant_id TEXT)
        RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.current_tenant', tenant_id, TRUE);
        END;
        $$ LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog
    """))
    
    # Role provisioning is external to schema migration. A dedicated database
    # owner has NOCREATEROLE; the configured runtime role receives explicit DML
    # grants from the deployment contract, independently of this historic name.
    # Do not create a cluster-global role or grant it access opportunistically.
    # Existing roles/ACLs and already-applied revisions remain untouched.


def downgrade() -> None:
    """Remove RLS policies."""
    if not is_postgres():
        return
    
    conn = op.get_bind()
    
    # Eliminar políticas
    for table, policy in [
        ('clientes', 'tenant_isolation_clientes'),
        ('planes_generados', 'tenant_isolation_planes'),
        ('subscriptions', 'tenant_isolation_subscriptions'),
        ('payments', 'tenant_isolation_payments'),
    ]:
        conn.execute(text(f"DROP POLICY IF EXISTS {policy} ON {table}"))
        conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    
    # Eliminar función helper
    conn.execute(text("DROP FUNCTION IF EXISTS set_tenant(TEXT)"))
