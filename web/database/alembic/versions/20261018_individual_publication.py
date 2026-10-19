"""Keep individual consumption atomic with a physically published plan."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature

revision = '20261018_individual_publication'
down_revision = '20261018_stored_objects'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    source = Path(__file__).resolve().parent.parent / 'schema_targets' / (
        '20261018_stored_objects_' + connection.dialect.name + '.json')
    expected = json.loads(source.read_text(encoding='utf-8'))
    if (schema_signature(connection) != expected['signature']
            or tenant_security_signature(connection) != expected['tenant_security']):
        raise RuntimeError('Individual publication requires the exact reviewed object source schema')
    # Existing requests remain protocol 0. A historical timestamp or nearby Plan
    # is not evidence that a previously failed worker did not publish.
    with op.batch_alter_table('generation_reservations') as batch:
        batch.add_column(sa.Column('publication_protocol', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('persisted_at', sa.DateTime(), nullable=True))
        batch.create_check_constraint('ck_generation_publication_protocol', 'publication_protocol IN (0, 1)')
        batch.create_check_constraint('ck_generation_publication_marker',
            "persisted_at IS NULL OR (publication_protocol = 1 AND status = 'completed')")
        batch.create_check_constraint('ck_generation_completed_publication',
            "publication_protocol = 0 OR status <> 'completed' OR persisted_at IS NOT NULL")


def downgrade():
    raise RuntimeError('Individual publication rollback requires reviewed application rollback and verified restore')
