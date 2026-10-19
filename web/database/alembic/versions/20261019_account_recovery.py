"""Account-bound opaque recovery state; no history/identity is inferred."""
import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature

revision='20261019_account_recovery'
down_revision='20261019_personal_diary'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    path=Path(__file__).resolve().parent.parent/'schema_targets'/('20261019_personal_diary_'+connection.dialect.name+'.json')
    expected=json.loads(path.read_text(encoding='utf-8'))
    if schema_signature(connection)!=expected['signature'] or tenant_security_signature(connection)!=expected['tenant_security']:
        raise RuntimeError('Recovery requires exact reviewed personal diary revision27')
    with op.batch_alter_table('usuarios') as batch:
        batch.add_column(sa.Column('password_reset_hash',sa.String(64),nullable=True))
        batch.add_column(sa.Column('password_reset_expires_at',sa.DateTime(),nullable=True))
        batch.add_column(sa.Column('password_reset_session_version',sa.Integer(),nullable=True))
        batch.create_unique_constraint('uq_usuario_password_reset_hash',['password_reset_hash'])
        batch.create_check_constraint('ck_usuario_reset_state',
            '(password_reset_hash IS NULL AND password_reset_expires_at IS NULL AND password_reset_session_version IS NULL) OR (password_reset_hash IS NOT NULL AND length(password_reset_hash) = 64 AND password_reset_expires_at IS NOT NULL AND password_reset_session_version IS NOT NULL AND password_reset_session_version >= 0)')


def downgrade():
    raise RuntimeError('Recovery rollback requires reviewed rollback and verified restore')
