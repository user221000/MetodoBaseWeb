"""Explicit33 binding targets and rollback; historical22-32 criteria stay immutable."""
import importlib
import os
import subprocess
import sys

from alembic import command
from alembic.operations import Operations
import pytest
from sqlalchemy import inspect, text

from tests.google33_fixtures import owned_database, PREVIOUS, REVISION
from tests.integration_schema_migrations import run_migration, ROOT
from tests.integration_client_link_migrations import populate28
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import verify_runtime_schema, alembic_config


@pytest.fixture(params=["sqlite","postgresql"])
def google_database(request,tmp_path):
    if request.param=="postgresql" and not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("Explicit synthetic PostgreSQL profile required")
    with owned_database(request.param,tmp_path) as value:yield value


@pytest.mark.parametrize("populated",[False,True])
def test_empty_populated_repeat_and_safe_rollback_preserve32(google_database,populated):
    url,engine=google_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    if populated:
        populate28(engine)
    columns,rows=snapshot(engine)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match="revision"):verify_runtime_schema(engine)
    run_migration(url,"db_bootstrap.py","--revision",REVISION);verify_runtime_schema(engine)
    assert snapshot(engine,columns)[1]==rows
    with engine.connect() as db:
        assert len(inspect(db).get_table_names())==36
        assert db.scalar(text("SELECT count(*) FROM auth_external_identities"))==0
        assert db.scalar(text("SELECT count(*) FROM google_link_intents"))==0
        if engine.dialect.name=="sqlite":assert db.exec_driver_sql("PRAGMA foreign_key_check").all()==[]
    run_migration(url,"db_bootstrap.py","--revision",REVISION)
    assert snapshot(engine,columns)[1]==rows
    run_migration(url,"-m","alembic","downgrade",PREVIOUS);verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows
    run_migration(url,"db_bootstrap.py","--revision",REVISION);verify_runtime_schema(engine)


def test_predecessor_drift_is_rejected_before_any33_change(google_database):
    url,engine=google_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    with engine.begin() as db:db.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN unexpected_google_binding_drift INTEGER")
    result=subprocess.run([sys.executable,"-X","utf8","db_bootstrap.py","--revision",REVISION],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    with engine.connect() as db:
        assert "auth_external_identities" not in inspect(db).get_table_names()
        assert db.scalar(text("SELECT version_num FROM alembic_version"))==PREVIOUS


def test_mid_migration_failure_does_not_leave_binding_or_intent(google_database,monkeypatch):
    url,engine=google_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    columns,rows=snapshot(engine);original=Operations.create_table
    def fail_after(self,name,*args,**kwargs):
        value=original(self,name,*args,**kwargs)
        if name=="auth_external_identities":raise RuntimeError("Synthetic33 table interruption")
        return value
    monkeypatch.setattr(Operations,"create_table",fail_after)
    with pytest.raises(RuntimeError,match="Synthetic33"):
        with engine.begin() as db:
            config=alembic_config();config.attributes["connection"]=db;command.upgrade(config,REVISION)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows


def test_binding_history_refuses_destructive_rollback(google_database):
    url,engine=google_database;run_migration(url,"db_bootstrap.py","--revision",REVISION)
    with engine.begin() as db:
        db.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro) VALUES ('33-subject','33-subject@example.invalid','synthetic','Synthetic','','usuario','VIEWER',true,0,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO auth_external_identities(id,user_id,issuer,subject,created_at,version) VALUES ('00000000-0000-0000-0000-000000000033','33-subject','https://accounts.google.com','104000000000000000033',CURRENT_TIMESTAMP,1)"))
    columns,rows=snapshot(engine)
    result=subprocess.run([sys.executable,"-X","utf8","-m","alembic","downgrade",PREVIOUS],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    verify_runtime_schema(engine);assert snapshot(engine,columns)[1]==rows
