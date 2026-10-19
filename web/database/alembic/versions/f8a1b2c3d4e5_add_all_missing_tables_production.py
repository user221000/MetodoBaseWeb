"""add all missing tables and columns for production

Revision ID: f8a1b2c3d4e5
Revises: 77162ee0e00c
Create Date: 2026-04-01 02:30:00.000000

Comprehensive migration that adds all tables and columns defined in models.py
but missing from previous migrations. Safe to run on fresh or existing databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = '77162ee0e00c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """Inspect the active dialect instead of querying PostgreSQL-only catalogs."""
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    return any(item["name"] == column_name for item in sa.inspect(op.get_bind()).get_columns(table_name))


def _add_column(table: str, column) -> None:
    """Rebuild SQLite constraints explicitly when adding legacy foreign keys."""
    if op.get_bind().dialect.name == "sqlite":
        foreign_keys = list(column.foreign_keys)
        unique = column.unique
        plain_column = sa.Column(column.name, column.type, nullable=column.nullable,
                                 server_default=column.server_default)
        with op.batch_alter_table(table, naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s"}) as batch:
            batch.add_column(plain_column)
            for foreign_key in foreign_keys:
                referenced_table, referenced_column = foreign_key.target_fullname.rsplit(".", 1)
                batch.create_foreign_key("fk_" + table + "_" + column.name + "_" + referenced_table,
                    referenced_table, [column.name], [referenced_column], ondelete=foreign_key.ondelete)
            if unique:
                batch.create_unique_constraint("uq_" + table + "_" + column.name, [column.name])
    else:
        op.add_column(table, column)


def upgrade() -> None:
    # ── Missing columns on 'usuarios' (RBAC) ─────────────────────────────
    if not _column_exists('usuarios', 'role'):
        _add_column('usuarios', sa.Column('role', sa.String(20), nullable=False, server_default='VIEWER'))
    if not _column_exists('usuarios', 'team_gym_id'):
        _add_column('usuarios', sa.Column('team_gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=True))
    if not _column_exists('usuarios', 'invited_by'):
        _add_column('usuarios', sa.Column('invited_by', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True))
    if not _column_exists('usuarios', 'invitation_token'):
        _add_column('usuarios', sa.Column('invitation_token', sa.String(64), nullable=True, unique=True))
    if not _column_exists('usuarios', 'invitation_expires'):
        _add_column('usuarios', sa.Column('invitation_expires', sa.DateTime, nullable=True))
    if not _column_exists('usuarios', 'invitation_role'):
        _add_column('usuarios', sa.Column('invitation_role', sa.String(20), nullable=True))

    # ── Missing columns on 'clientes' ────────────────────────────────────
    if not _column_exists('clientes', 'fecha_suscripcion'):
        _add_column('clientes', sa.Column('fecha_suscripcion', sa.DateTime, nullable=True))
    if not _column_exists('clientes', 'fecha_fin_suscripcion'):
        _add_column('clientes', sa.Column('fecha_fin_suscripcion', sa.DateTime, nullable=True))
    if not _column_exists('clientes', 'alimentos_excluidos'):
        _add_column('clientes', sa.Column('alimentos_excluidos', sa.Text, nullable=True))

    # ── refresh_tokens (was only in SQLite web_usuarios.db, never in Alembic) ─
    if not _table_exists('refresh_tokens'):
        op.create_table('refresh_tokens',
            sa.Column('jti', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
            sa.Column('expires_at', sa.Float, nullable=False),
            sa.Column('revoked', sa.Boolean, nullable=False, server_default='false'),
            sa.Column('created_at', sa.Float, nullable=False),
        )
        op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])

    # ── stripe_customers ─────────────────────────────────────────────────
    if not _table_exists('stripe_customers'):
        op.create_table('stripe_customers',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('stripe_customer_id', sa.String(255), nullable=False, unique=True),
            sa.Column('email', sa.String(255)),
            sa.Column('name', sa.String(255)),
            sa.Column('default_payment_method', sa.String(255)),
            sa.Column('currency', sa.String(3), server_default='usd'),
            sa.Column('tax_exempt', sa.String(20), server_default='none'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index('ix_stripe_customers_gym_id', 'stripe_customers', ['gym_id'])
        op.create_index('ix_stripe_customers_stripe_id', 'stripe_customers', ['stripe_customer_id'])

    # ── invoices ─────────────────────────────────────────────────────────
    if not _table_exists('invoices'):
        op.create_table('invoices',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
            sa.Column('stripe_invoice_id', sa.String(255), nullable=False, unique=True),
            sa.Column('stripe_subscription_id', sa.String(255)),
            sa.Column('amount_due', sa.Integer, nullable=False),
            sa.Column('amount_paid', sa.Integer, nullable=False, server_default='0'),
            sa.Column('amount_remaining', sa.Integer, nullable=False, server_default='0'),
            sa.Column('subtotal', sa.Integer),
            sa.Column('tax', sa.Integer, server_default='0'),
            sa.Column('total', sa.Integer, nullable=False),
            sa.Column('currency', sa.String(3), nullable=False, server_default='usd'),
            sa.Column('status', sa.String(30), nullable=False),
            sa.Column('paid', sa.Boolean, server_default='false'),
            sa.Column('hosted_invoice_url', sa.String(500)),
            sa.Column('invoice_pdf', sa.String(500)),
            sa.Column('period_start', sa.DateTime),
            sa.Column('period_end', sa.DateTime),
            sa.Column('due_date', sa.DateTime),
            sa.Column('paid_at', sa.DateTime),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index('ix_invoices_gym_created', 'invoices', ['gym_id', 'created_at'])

    # ── stripe_webhook_events ────────────────────────────────────────────
    if not _table_exists('stripe_webhook_events'):
        op.create_table('stripe_webhook_events',
            sa.Column('event_id', sa.String(255), primary_key=True),
            sa.Column('event_type', sa.String(100), nullable=False),
            sa.Column('processed_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column('result', sa.String(255)),
        )
        op.create_index('ix_stripe_webhook_events_processed_at', 'stripe_webhook_events', ['processed_at'])

    # ── gym_profiles ─────────────────────────────────────────────────────
    if not _table_exists('gym_profiles'):
        op.create_table('gym_profiles',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('nombre_negocio', sa.String(255), server_default=''),
            sa.Column('telefono', sa.String(50), server_default=''),
            sa.Column('direccion', sa.Text, server_default=''),
            sa.Column('ciudad', sa.String(150), server_default=''),
            sa.Column('estado', sa.String(100), server_default=''),
            sa.Column('pais', sa.String(100), server_default='México'),
            sa.Column('logo_url', sa.String(500), server_default=''),
            sa.Column('color_primario', sa.String(7), server_default='#E5B800'),
            sa.Column('color_secundario', sa.String(7), server_default='#292524'),
            sa.Column('sitio_web', sa.String(500), server_default=''),
            sa.Column('rfc', sa.String(20), server_default=''),
            sa.Column('razon_social', sa.String(255), server_default=''),
            sa.Column('regimen_fiscal', sa.String(10), server_default=''),
            sa.Column('codigo_postal_fiscal', sa.String(5), server_default=''),
            sa.Column('uso_cfdi', sa.String(10), server_default='G03'),
            sa.Column('instagram', sa.String(255), server_default=''),
            sa.Column('facebook', sa.String(255), server_default=''),
            sa.Column('tiktok', sa.String(255), server_default=''),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('horarios_comidas', sa.JSON, nullable=True),
        )
        op.create_index('ix_gym_profiles_gym_id', 'gym_profiles', ['gym_id'])

    # ── planes_suscripcion ───────────────────────────────────────────────
    if not _table_exists('planes_suscripcion'):
        op.create_table('planes_suscripcion',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
            sa.Column('nombre', sa.String(100), nullable=False),
            sa.Column('duracion_dias', sa.Integer, nullable=False),
            sa.Column('precio', sa.Float, nullable=False, server_default='0.0'),
            sa.Column('moneda', sa.String(10), nullable=False, server_default='MXN'),
            sa.Column('activo', sa.Boolean, nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index('ix_planes_sub_gym', 'planes_suscripcion', ['gym_id', 'activo'])

    # ── client_progress ──────────────────────────────────────────────────
    if not _table_exists('client_progress'):
        op.create_table('client_progress',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('id_cliente', sa.String(36), sa.ForeignKey('clientes.id_cliente', ondelete='CASCADE'), nullable=False),
            sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
            sa.Column('fecha', sa.DateTime, server_default=sa.func.now()),
            sa.Column('peso_kg', sa.Float),
            sa.Column('grasa_corporal_pct', sa.Float),
            sa.Column('masa_magra_kg', sa.Float),
            sa.Column('notas', sa.Text, server_default=''),
        )
        op.create_index('ix_progress_cliente_fecha', 'client_progress', ['id_cliente', 'fecha'])

    # ── audit_log ────────────────────────────────────────────────────────
    if not _table_exists('audit_log'):
        op.create_table('audit_log',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True),
            sa.Column('accion', sa.String(50), nullable=False),
            sa.Column('entidad', sa.String(50)),
            sa.Column('entidad_id', sa.String(36)),
            sa.Column('detalle', sa.Text, server_default=''),
            sa.Column('ip', sa.String(45)),
            sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index('ix_audit_log_gym_id', 'audit_log', ['gym_id'])
        op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])

    # ── user_subscriptions ───────────────────────────────────────────────
    if not _table_exists('user_subscriptions'):
        op.create_table('user_subscriptions',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('plan', sa.String(20), nullable=False, server_default='starter'),
            sa.Column('max_planes_mes', sa.Integer, nullable=False, server_default='1'),
            sa.Column('planes_usados_mes', sa.Integer, nullable=False, server_default='0'),
            sa.Column('mes_actual', sa.String(7), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index('ix_user_subscriptions_user_id', 'user_subscriptions', ['user_id'])

    # ── Safe indexes (IF NOT EXISTS not supported by Alembic, use try/except) ──
    conn = op.get_bind()
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS ix_usuarios_team_gym ON usuarios (team_gym_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_invitation_token ON usuarios (invitation_token)",
        "CREATE INDEX IF NOT EXISTS ix_clientes_fecha_fin_suscripcion ON clientes (fecha_fin_suscripcion)",
    ]:
        conn.execute(sa.text(idx_sql))


def downgrade() -> None:
    # Drop tables in reverse order
    for table in [
        'user_subscriptions', 'audit_log', 'client_progress',
        'planes_suscripcion', 'gym_profiles', 'stripe_webhook_events',
        'invoices', 'stripe_customers',
    ]:
        op.drop_table(table)

    # Drop columns
    op.drop_column('clientes', 'alimentos_excluidos')
    op.drop_column('clientes', 'fecha_fin_suscripcion')
    op.drop_column('clientes', 'fecha_suscripcion')
    op.drop_column('usuarios', 'invitation_role')
    op.drop_column('usuarios', 'invitation_expires')
    op.drop_column('usuarios', 'invitation_token')
    op.drop_column('usuarios', 'invited_by')
    op.drop_column('usuarios', 'team_gym_id')
    op.drop_column('usuarios', 'role')
