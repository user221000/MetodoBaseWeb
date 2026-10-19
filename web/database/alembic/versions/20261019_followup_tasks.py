"""Revision34 operational declarations; never contact/payment/retention facts."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.history_index_contract_v1 import history_index_signature
from web.database.progress_policy import signature as progress_signature
from web.database.google_identity_policy import signature as google_signature
from web.database.followup_policy import install, signature as followup_signature
from web.database.followup_schema_v1 import tables

revision = "20261019_followup_tasks"
down_revision = "20261019_google_subjects"
branch_labels = None
depends_on = None


def _target(connection, name):
    return json.loads((Path(__file__).parent.parent/"schema_targets"/(name+"_"+connection.dialect.name+".json")).read_text(encoding="utf-8"))


def signature(connection):
    return {"signature": schema_signature(connection), "tenant_security": tenant_security_signature(connection),
        "member_link_security": member_link_security_signature(connection), "history_order_index": history_index_signature(connection),
        "progress_security": progress_signature(connection), "google_identity_security": google_signature(connection),
        "followup_security": followup_signature(connection)}


def _verify(connection, target):
    actual = signature(connection)
    if "followup_security" not in target:
        actual.pop("followup_security")
    if actual != target:
        raise RuntimeError("Follow-up requires the exact reviewed predecessor/schema/security contract")


def create_tables():
    connection = op.get_bind()
    metadata = sa.MetaData()
    # Resolve only existing FK targets; never import evolving ORM/defaults here.
    sa.Table("usuarios", metadata, autoload_with=connection)
    sa.Table("clientes", metadata, autoload_with=connection)
    task, event = tables(metadata)
    metadata.create_all(connection, tables=[task, event], checkfirst=False)
    install(connection)


def _begin(connection):
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")


def upgrade():
    connection = op.get_bind()
    _begin(connection)
    _verify(connection, _target(connection, down_revision))
    create_tables()
    _verify(connection, _target(connection, revision))


def downgrade():
    connection = op.get_bind()
    _begin(connection)
    _verify(connection, _target(connection, revision))
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM followup_tasks) OR EXISTS(SELECT 1 FROM followup_task_events)")):
        raise RuntimeError("Follow-up history rollback requires reviewed whole-scope restore")
    if connection.dialect.name == "postgresql":
        op.drop_constraint("fk_followup_current_event", "followup_tasks", type_="foreignkey")
    op.drop_table("followup_task_events")
    op.drop_table("followup_tasks")
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("DROP FUNCTION r34_event_apply()")
        connection.exec_driver_sql("DROP FUNCTION r34_task_guard()")
        connection.exec_driver_sql("DROP FUNCTION r34_event_guard()")
    _verify(connection, _target(connection, down_revision))
