"""Revision36: opt-in events, provider observations, fenced outbox and attempts."""
import importlib,json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from web.database.notification_schema_v1 import tables,TABLES
from web.database.notification_policy import install,signature as notification_signature

revision="20261020_notifications"
down_revision="20261020_nutrition_profile"
branch_labels=None
depends_on=None


def signature(connection):
    result=importlib.import_module("web.database.alembic.versions.20261020_nutrition_profile").signature(connection)
    result["notification_security"]=notification_signature(connection)
    return result


def target(connection,name):
    return json.loads((Path(__file__).parent.parent/"schema_targets"/(name+"_"+connection.dialect.name+".json")).read_text(encoding="utf-8"))


def verify(connection,name):
    actual=signature(connection);expected=target(connection,name)
    if "notification_security" not in expected:actual.pop("notification_security")
    if actual!=expected:raise RuntimeError("Notifications require the exact reviewed schema/security contract")


def create_tables():
    connection=op.get_bind();metadata=sa.MetaData()
    op.add_column("usuarios",sa.Column("notification_contact_version",sa.Integer,
        sa.CheckConstraint("notification_contact_version BETWEEN 0 AND 2147483647",name="ck_usuario_notification_contact_version"),
        nullable=False,server_default="0"))
    for name in ("usuarios","subscriptions","provider_subject_associations"):
        sa.Table(name,metadata,autoload_with=connection)
    created=tables(metadata)
    metadata.create_all(connection,tables=list(created),checkfirst=False)
    install(connection)


def begin(connection):
    if connection.dialect.name=="sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def upgrade():
    connection=op.get_bind();begin(connection)
    verify(connection,down_revision);create_tables();verify(connection,revision)


def downgrade():
    connection=op.get_bind();begin(connection);verify(connection,revision)
    if any(connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM "+name+")")) for name in TABLES):
        raise RuntimeError("Notification history requires a reviewed data-preserving restore")
    for name in reversed(TABLES):op.drop_table(name)
    if connection.dialect.name=="sqlite":
        connection.exec_driver_sql("DROP TRIGGER r36_contact_epoch_initial")
        connection.exec_driver_sql("DROP TRIGGER r36_contact_epoch_guard")
        connection.exec_driver_sql("DROP TRIGGER r36_contact_email_change")
    if connection.dialect.name=="postgresql":
        connection.exec_driver_sql("DROP TRIGGER r36_contact_epoch_guard ON public.usuarios")
        connection.exec_driver_sql("DROP FUNCTION public.r36_contact_epoch()")
        for index in range(1,6):connection.exec_driver_sql("DROP FUNCTION public.r36_guard_"+str(index)+"()")
        connection.exec_driver_sql("DROP FUNCTION public.r36_immutable()")
    op.drop_column("usuarios","notification_contact_version")
    verify(connection,down_revision)
