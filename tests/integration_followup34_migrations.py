"""Current34 upgrade/rollback; frozen22-33 signatures and rows stay unchanged."""
import os
import subprocess
import sys

from alembic import command
import pytest
from sqlalchemy import event, inspect, text

from tests.followup34_fixtures import PREVIOUS, REVISION, owned_database
from tests.integration_client_link_migrations import populate28
from tests.integration_schema_migrations import ROOT, run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import alembic_config, verify_runtime_schema


@pytest.fixture(params=["sqlite","postgresql"])
def followup_database(request,tmp_path):
    if request.param=="postgresql" and not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("Explicit own PostgreSQL lease profile required")
    with owned_database(request.param,tmp_path) as value:yield value


@pytest.mark.parametrize("populated",[False,True])
def test_exact33_rows_upgrade_repeat_and_empty34_downgrade(followup_database,populated):
    url,engine=followup_database
    run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    if populated:populate28(engine)
    columns,rows=snapshot(engine)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match="revision"):verify_runtime_schema(engine)
    run_migration(url,"db_bootstrap.py","--revision",REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine,columns)[1]==rows
    with engine.connect() as c:
        assert len(inspect(c).get_table_names())==38
        assert c.scalar(text("SELECT count(*) FROM followup_tasks"))==0
        assert c.scalar(text("SELECT count(*) FROM followup_task_events"))==0
        if engine.dialect.name=="sqlite":assert c.exec_driver_sql("PRAGMA foreign_key_check").all()==[]
    run_migration(url,"db_bootstrap.py","--revision",REVISION)
    assert snapshot(engine,columns)[1]==rows
    run_migration(url,"-m","alembic","downgrade",PREVIOUS)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows


def test_predecessor_drift_refuses_any34_ddl(followup_database):
    url,engine=followup_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    with engine.begin() as c:c.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN unexpected_followup INTEGER")
    result=subprocess.run([sys.executable,"-X","utf8","db_bootstrap.py","--revision",REVISION],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    with engine.connect() as c:
        assert "followup_tasks" not in inspect(c).get_table_names()
        assert c.scalar(text("SELECT version_num FROM alembic_version"))==PREVIOUS


def test_mid34_install_failure_rolls_back_both_tables(followup_database,monkeypatch):
    url,engine=followup_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    columns,rows=snapshot(engine)
    def interrupted(connection,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith("CREATE TABLE FOLLOWUP_TASK_EVENTS"):
            raise RuntimeError("Synthetic34 install interruption")
    # Alembic loads its own migration module namespace; intercept actual DDL
    # after the second table instead of patching an unused import copy.
    event.listen(engine,"after_cursor_execute",interrupted)
    try:
        with pytest.raises(RuntimeError,match="Synthetic34"):
            with engine.begin() as c:
                config=alembic_config();config.attributes["connection"]=c;command.upgrade(config,REVISION)
    finally:event.remove(engine,"after_cursor_execute",interrupted)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows


def test_nonempty_history_refuses_destructive_downgrade(followup_database):
    from sqlalchemy.orm import Session
    from web.database.models import Usuario, UserRole, Cliente, FollowupTaskEvent
    from tests.test_followup34_mechanisms import creation
    url,engine=followup_database;run_migration(url,"db_bootstrap.py","--revision",REVISION)
    with Session(engine) as db:
        db.add(Usuario(id="gym-a",email="a@example.invalid",password_hash="synthetic",nombre="A",tipo="gym",role=UserRole.OWNER))
        db.flush();db.add(Cliente(id_cliente="client-a",gym_id="gym-a",nombre="Synthetic"));db.commit()
    from web.database.tenant_context import tenant_scope
    with tenant_scope("gym-a"),Session(engine) as db:
        value=creation(assignee_id=None)
        db.add(FollowupTaskEvent(**value));db.commit()
    columns,rows=snapshot(engine)
    result=subprocess.run([sys.executable,"-X","utf8","-m","alembic","downgrade",PREVIOUS],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    verify_runtime_schema(engine)
    assert snapshot(engine,columns)[1]==rows
