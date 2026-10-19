"""Explicit recipient proof and immutable plan publications; no legacy adoption."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature

revision='20261019_client_account_links'
down_revision='20261019_account_recovery'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    base=Path(__file__).resolve().parent.parent
    expected=json.loads((base/'schema_targets'/('20261019_account_recovery_'+connection.dialect.name+'.json')).read_text(encoding='utf-8'))
    if schema_signature(connection)!=expected['signature'] or tenant_security_signature(connection)!=expected['tenant_security']:
        raise RuntimeError('Member linking requires the exact reviewed recovery revision28')
    for table,name,columns in (
        ('clientes','uq_client_account_owner',['gym_id','id_cliente']),
        ('planes_generados','uq_member_plan_source_owner',['gym_id','id_cliente','id'])):
        with op.batch_alter_table(table) as batch:
            batch.create_unique_constraint(name,columns)
    ddl=(base/'member_link_ddl'/('20261019_'+connection.dialect.name+'.sql')).read_text(encoding='utf-8')
    for statement in ddl.split('-- R12 statement\n'):
        if statement.strip(): connection.exec_driver_sql(statement)
    if connection.dialect.name=='postgresql':
        from web.database.member_link_projection_v1 import projection_sql
        from web.database.member_link_policy_v1 import member_link_sql
        connection.exec_driver_sql(projection_sql())
        connection.exec_driver_sql(member_link_sql())
    elif connection.dialect.name=='sqlite':
        from web.database.member_link_sqlite_v1 import sqlite_statements
        for statement in sqlite_statements(): connection.exec_driver_sql(statement)
    else:
        raise RuntimeError('Member linking requires a reviewed database dialect')


def downgrade():
    raise RuntimeError('Member linking rollback requires reviewed application rollback and verified restore')
