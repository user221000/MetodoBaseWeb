"""Personal consumption snapshots with explicit ownership and no inferred import."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature

revision = '20261019_personal_diary'
down_revision = '20261018_individual_publication'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    path = Path(__file__).resolve().parent.parent / 'schema_targets' / (
        '20261018_individual_publication_' + connection.dialect.name + '.json')
    expected = json.loads(path.read_text(encoding='utf-8'))
    if (schema_signature(connection) != expected['signature']
            or tenant_security_signature(connection) != expected['tenant_security']):
        raise RuntimeError('Personal diary requires the exact reviewed individual publication schema')
    op.create_table('personal_diary_days',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('usuarios.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.Column('timezone', sa.String(64), nullable=False, server_default='America/Mexico_City'),
        sa.Column('water_ml', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('meals_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'local_date', name='uq_personal_diary_user_date'),
        sa.CheckConstraint("timezone = 'America/Mexico_City'", name='ck_personal_diary_timezone'),
        sa.CheckConstraint('water_ml BETWEEN 0 AND 20000', name='ck_personal_diary_water'),
        sa.CheckConstraint('version BETWEEN 1 AND 2147483647', name='ck_personal_diary_version'),
        sa.CheckConstraint('length(meals_json) BETWEEN 2 AND 65536', name='ck_personal_diary_content_size'))
    op.create_index('ix_personal_diary_days_user_id', 'personal_diary_days', ['user_id'])
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text("""CREATE POLICY tenant_isolation_personal_diary_days ON personal_diary_days
            FOR ALL USING (user_id = NULLIF(current_setting('app.current_tenant', TRUE), ''))
            WITH CHECK (user_id = NULLIF(current_setting('app.current_tenant', TRUE), ''))"""))
        connection.execute(sa.text('ALTER TABLE personal_diary_days ENABLE ROW LEVEL SECURITY'))
        connection.execute(sa.text('ALTER TABLE personal_diary_days FORCE ROW LEVEL SECURITY'))


def downgrade():
    raise RuntimeError('Personal diary rollback requires reviewed application rollback and verified restore')
