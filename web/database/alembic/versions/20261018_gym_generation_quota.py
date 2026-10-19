"""Add durable gym quota/publication ledger after the accepted R04 boundary."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature

revision = "20261018_gym_generation_quota"
down_revision = "20261018_tenant_isolation"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    source = Path(__file__).resolve().parent.parent / 'schema_targets' / ('20261018_isolated_' + connection.dialect.name + '.json')
    expected = json.loads(source.read_text(encoding='utf-8'))
    if schema_signature(connection) != expected['signature'] or tenant_security_signature(connection) != expected['tenant_security']:
        raise RuntimeError('Gym quota migration requires the exact reviewed R04 source schema')
    op.create_table('gym_generation_reservations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('gym_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', sa.String(36), sa.ForeignKey('clientes.id_cliente', ondelete='SET NULL'), nullable=True),
        sa.Column('request_key', sa.String(128), nullable=False),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('period', sa.String(7), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.Column('timezone', sa.String(64), nullable=False),
        sa.Column('catalog_plan', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('planes_generados.id', ondelete='SET NULL'), nullable=True, unique=True),
        sa.Column('persisted_at', sa.DateTime(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('gym_id', 'request_key', name='uq_gym_generation_request_key'),
        sa.CheckConstraint("status IN ('reserved', 'completed', 'released')", name='ck_gym_generation_status'),
        sa.CheckConstraint('length(request_hash) = 64', name='ck_gym_generation_request_hash'),
        sa.CheckConstraint("status <> 'released' OR persisted_at IS NULL", name='ck_gym_generation_no_persisted_refund'),
        sa.CheckConstraint("status <> 'completed' OR result_json IS NOT NULL", name='ck_gym_generation_completed_result'))
    op.create_index('ix_gym_generation_reservations_gym_id', 'gym_generation_reservations', ['gym_id'])
    op.create_index('ix_gym_generation_reservations_client_id', 'gym_generation_reservations', ['client_id'])
    op.create_index('ix_gym_generation_period_status', 'gym_generation_reservations', ['gym_id','period','status'])
    op.create_index('ix_gym_generation_day_client', 'gym_generation_reservations', ['gym_id','local_date','client_id','status'])
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text("""CREATE POLICY tenant_isolation_gym_generation_reservations ON gym_generation_reservations
            FOR ALL USING (gym_id = NULLIF(current_setting('app.current_tenant', TRUE), ''))
            WITH CHECK (gym_id = NULLIF(current_setting('app.current_tenant', TRUE), ''))"""))
        connection.execute(sa.text('ALTER TABLE gym_generation_reservations ENABLE ROW LEVEL SECURITY'))
        connection.execute(sa.text('ALTER TABLE gym_generation_reservations FORCE ROW LEVEL SECURITY'))


def downgrade():
    raise RuntimeError('Quota publication rollback requires reviewed application rollback and verified backup/restore')
