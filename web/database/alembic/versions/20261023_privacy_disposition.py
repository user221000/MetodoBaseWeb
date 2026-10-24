"""Revision39 additive requests/dispositions; no fabricated schema targets."""
import importlib
import json
from pathlib import Path
import sqlalchemy as sa
from alembic import op
from web.database.alembic.schema_contract_v2 import schema_contracts_equal
from web.database.privacy_policy_v1 import install, uninstall, signature as privacy_signature
from web.database.privacy_schema_v1 import REQUESTS, ITEMS, request_table, item_table

revision = '20261023_privacy_disposition'
down_revision = '20261023_product_facts'
branch_labels = depends_on = None


def signature(connection):
    result = importlib.import_module('web.database.alembic.versions.20261023_product_facts').signature(connection)
    result['privacy_security'] = privacy_signature(connection)
    return result


def verify(connection, revision_name):
    actual = signature(connection)
    if revision_name == down_revision:
        actual.pop('privacy_security')
    path = Path(__file__).parent.parent / 'schema_targets' / (revision_name + '_' + connection.dialect.name + '.json')
    if not schema_contracts_equal(actual, json.loads(path.read_bytes())):
        raise RuntimeError('Privacy disposition requires a genuinely captured schema/security target')


def create_tables(connection):
    metadata = sa.MetaData()
    sa.Table('usuarios',metadata,autoload_with=connection)
    request_table(metadata,sa.DateTime()).create(connection,checkfirst=False)
    item_table(metadata,sa.DateTime()).create(connection,checkfirst=False)
    install(connection)


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN IMMEDIATE')
    verify(connection,down_revision)
    create_tables(connection)
    verify(connection,revision)


def downgrade():
    connection = op.get_bind()
    verify(connection,revision)
    if connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM privacy_requests)')):
        raise RuntimeError('Privacy dispositions require a reviewed data-preserving restore')
    uninstall(connection)
    op.drop_table(ITEMS)
    op.drop_table(REQUESTS)
    verify(connection,down_revision)
