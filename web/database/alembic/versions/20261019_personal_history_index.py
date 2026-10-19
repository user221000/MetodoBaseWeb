"""Index bounded personal history without changing rows or prior contracts."""
import json
from pathlib import Path

from alembic import op

from web.database.alembic.history_index_contract_v1 import (
    INDEX_NAME, create_history_index, expected_history_index, history_index_signature,
)
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.tenant_policy import tenant_security_signature

revision = '20261019_personal_history_index'
down_revision = '20261019_client_account_links'
branch_labels = None
depends_on = None


def _target(connection, name):
    path = Path(__file__).resolve().parent.parent / 'schema_targets'
    return json.loads((path / (name + '_' + connection.dialect.name + '.json')).read_text(encoding='utf-8'))


def _verify(connection, expected):
    """Require the exact predecessor/current target before transactional DDL."""
    if (schema_signature(connection) != expected['signature']
            or tenant_security_signature(connection) != expected['tenant_security']
            or member_link_security_signature(connection) != expected['member_link_security']):
        raise RuntimeError('History index migration requires the exact reviewed schema')
    if 'history_order_index' in expected and history_index_signature(connection) != expected['history_order_index']:
        raise RuntimeError('History index migration found unexpected ordering')


def upgrade():
    connection = op.get_bind()
    _verify(connection, _target(connection, down_revision))
    create_history_index(connection)
    if history_index_signature(connection) != expected_history_index(connection.dialect.name):
        raise RuntimeError('History index did not acquire the reviewed physical ordering')
    _verify(connection, _target(connection, revision))


def downgrade():
    connection = op.get_bind()
    _verify(connection, _target(connection, revision))
    # The index owns no rows and has no dependants; rollback leaves revision29 intact.
    connection.exec_driver_sql('DROP INDEX ' + INDEX_NAME)
    _verify(connection, _target(connection, down_revision))
