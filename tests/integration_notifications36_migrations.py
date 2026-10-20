"""New36 exact predecessor, rollback and repeat; no historical retargeting."""
import os,subprocess,sys
from alembic import command
import pytest
from sqlalchemy import event,inspect,text
from sqlalchemy.orm import Session,sessionmaker

from tests.notifications36_fixtures import owned_database
from tests.integration_client_link_migrations import populate28
from tests.integration_schema_migrations import ROOT,run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import alembic_config,verify_runtime_schema

PREVIOUS="20261020_nutrition_profile"
REVISION="20261020_notifications"


@pytest.fixture(params=["sqlite","postgresql"])
def notification_database(request,tmp_path):
    if request.param=="postgresql" and not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("An explicit own PostgreSQL lease profile is required")
    with owned_database(request.param,tmp_path) as value:yield value


@pytest.mark.parametrize("populated",[False,True])
def test_exact35_rows_repeat_and_empty36_downgrade(notification_database,populated):
    url,engine=notification_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    if populated:populate28(engine)
    columns,rows=snapshot(engine)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match="revision"):verify_runtime_schema(engine)
    run_migration(url,"db_bootstrap.py","--revision",REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine,columns)[1]==rows
    with engine.connect() as connection:
        assert len(inspect(connection).get_table_names())==42
        assert connection.scalar(text("SELECT count(*) FROM notification_preferences"))==0
        assert connection.scalar(text("SELECT count(*) FROM notification_billing_facts"))==0
        assert connection.scalar(text("SELECT count(*) FROM notification_outbox"))==0
        assert connection.scalar(text("SELECT count(*) FROM notification_attempts"))==0
        if engine.dialect.name=="sqlite":assert connection.exec_driver_sql("PRAGMA foreign_key_check").all()==[]
    run_migration(url,"db_bootstrap.py","--revision",REVISION)
    assert snapshot(engine,columns)[1]==rows
    run_migration(url,"-m","alembic","downgrade",PREVIOUS)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows


def test_predecessor_drift_refuses_new_tables(notification_database):
    url,engine=notification_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    with engine.begin() as c:c.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN unexpected_notification INTEGER")
    result=subprocess.run([sys.executable,"-X","utf8","db_bootstrap.py","--revision",REVISION],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    with engine.connect() as c:
        assert "notification_outbox" not in inspect(c).get_table_names()
        assert c.scalar(text("SELECT version_num FROM alembic_version"))==PREVIOUS


def test_interrupted_install_preserves35_rows_schema_and_revision(notification_database):
    url,engine=notification_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    columns,rows=snapshot(engine)
    def interrupted(connection,cursor,statement,parameters,context,many):
        if statement.lstrip().upper().startswith("CREATE TABLE NOTIFICATION_OUTBOX"):
            raise RuntimeError("Synthetic36 install interruption")
    event.listen(engine,"after_cursor_execute",interrupted)
    try:
        with pytest.raises(RuntimeError,match="Synthetic36"):
            with engine.begin() as connection:
                config=alembic_config();config.attributes["connection"]=connection;command.upgrade(config,REVISION)
    finally:event.remove(engine,"after_cursor_execute",interrupted)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows


def test_nonempty_history_refuses_destructive_rollback(notification_database):
    from web.database.models import Usuario,UserRole
    from web.notification_schemas import PreferenceWrite
    from web.services.notifications import set_preference
    url,engine=notification_database;run_migration(url,"db_bootstrap.py","--revision",REVISION)
    with Session(engine) as db:
        db.add(Usuario(id="notification-migration-owner",email="migration@example.invalid",password_hash="synthetic",
            nombre="Synthetic migration",tipo="gym",role=UserRole.OWNER,session_version=0));db.commit()
    import uuid
    set_preference({"id":"notification-migration-owner","session_version":0},"gym","account_period_end",
        PreferenceWrite(expected_version=0,enabled=True,confirm=True),str(uuid.uuid4()),factory=sessionmaker(bind=engine,autoflush=False))
    columns,rows=snapshot(engine)
    result=subprocess.run([sys.executable,"-X","utf8","-m","alembic","downgrade",PREVIOUS],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    verify_runtime_schema(engine)
    assert snapshot(engine,columns)[1]==rows
