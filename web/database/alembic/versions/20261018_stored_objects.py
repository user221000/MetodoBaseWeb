"""Track private objects without guessing legacy paths or deleting stored bytes."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature

revision = '20261018_stored_objects'
down_revision = '20261018_gym_generation_quota'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    source = Path(__file__).resolve().parent.parent / 'schema_targets' / ('20261018_gym_quota_' + connection.dialect.name + '.json')
    expected = json.loads(source.read_text(encoding='utf-8'))
    if schema_signature(connection) != expected['signature'] or tenant_security_signature(connection) != expected['tenant_security']:
        raise RuntimeError('Stored object migration requires the exact reviewed quota source schema')
    op.create_table('stored_objects',
        sa.Column('id',sa.String(32),primary_key=True),
        sa.Column('gym_id',sa.String(36),sa.ForeignKey('usuarios.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('kind',sa.String(20),nullable=False),
        sa.Column('key',sa.String(512),nullable=False,unique=True),
        sa.Column('content_type',sa.String(128),nullable=False),
        sa.Column('byte_size',sa.Integer(),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('storage_backend',sa.String(10),nullable=False),
        sa.Column('status',sa.String(10),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False),
        sa.Column('updated_at',sa.DateTime(),nullable=False),
        sa.UniqueConstraint('gym_id','id',name='uq_stored_object_owner_id'),
        sa.CheckConstraint('length(id) = 32',name='ck_stored_object_id'),
        sa.CheckConstraint("kind IN ('plan_pdf', 'gym_logo')",name='ck_stored_object_kind'),
        sa.CheckConstraint('length(key) BETWEEN 1 AND 512',name='ck_stored_object_key'),
        sa.CheckConstraint('length(content_type) BETWEEN 1 AND 128',name='ck_stored_object_content_type'),
        sa.CheckConstraint('byte_size BETWEEN 1 AND 67108864',name='ck_stored_object_size'),
        sa.CheckConstraint('length(sha256) = 64',name='ck_stored_object_sha256'),
        sa.CheckConstraint("storage_backend IN ('local', 's3')",name='ck_stored_object_backend'),
        sa.CheckConstraint("status IN ('pending', 'ready')",name='ck_stored_object_status'))
    op.create_index('ix_stored_objects_gym_id','stored_objects',['gym_id'])
    # SQLite rebuilds run only through the blocking bootstrap transaction with
    # FK enforcement suspended on that connection and foreign_key_check at end.
    for table,column,constraint in (
            ('planes_generados','pdf_object_id','fk_plan_pdf_object_owner'),
            ('gym_profiles','logo_object_id','fk_gym_logo_object_owner')):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column(column,sa.String(32),nullable=True))
            batch.create_foreign_key(constraint,'stored_objects',['gym_id',column],['gym_id','id'],ondelete='RESTRICT')
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text("""CREATE POLICY tenant_isolation_stored_objects ON stored_objects
            FOR ALL USING (gym_id = NULLIF(current_setting('app.current_tenant', TRUE), ''))
            WITH CHECK (gym_id = NULLIF(current_setting('app.current_tenant', TRUE), ''))"""))
        connection.execute(sa.text('ALTER TABLE stored_objects ENABLE ROW LEVEL SECURITY'))
        connection.execute(sa.text('ALTER TABLE stored_objects FORCE ROW LEVEL SECURITY'))


def downgrade():
    raise RuntimeError('Private object rollback requires reviewed application rollback and verified backup/restore')
