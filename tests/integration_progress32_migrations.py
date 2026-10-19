"""Independent32 targets, legacy preservation and transaction-safe rollback."""
import importlib
import os
import subprocess
import sys

from alembic import command
from alembic.operations import Operations
import pytest
from sqlalchemy import inspect, text

from tests.progress32_fixtures import owned_database, PREVIOUS, REVISION
from tests.integration_schema_migrations import run_migration, ROOT
from tests.integration_client_link_migrations import populate28
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import verify_runtime_schema, alembic_config


@pytest.fixture(params=["sqlite","postgresql"])
def progress_database(request,tmp_path):
    if request.param=="postgresql" and not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("Explicit synthetic PostgreSQL profile required")
    with owned_database(request.param,tmp_path) as value:yield value


@pytest.mark.parametrize("populated",[False,True])
def test_empty_populated_repeat_and_safe_rollback_preserve31(progress_database,populated):
    url,engine=progress_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    if populated:
        populate28(engine)
        with engine.begin() as db:
            # Core SQL is deliberately the exact historical31 column set.
            db.execute(text("INSERT INTO client_progress(id_cliente,gym_id,fecha,peso_kg,notas) SELECT id_cliente,gym_id,'2020-01-02',71.5,'Legacy notes preserved' FROM clientes ORDER BY id LIMIT 1"))
    columns,rows=snapshot(engine)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match="revision"):verify_runtime_schema(engine)
    run_migration(url,"db_bootstrap.py","--revision",REVISION);verify_runtime_schema(engine)
    assert snapshot(engine,columns)[1]==rows
    with engine.connect() as db:
        assert len(inspect(db).get_table_names())==34
        assert db.scalar(text("SELECT count(*) FROM progress_consents"))==0
        legacy=db.execute(text("SELECT source_kind,record_key,measured_on,recorded_by_id,recorded_at,updated_at,withdrawn_at,version FROM client_progress")).all()
        assert all(tuple(row)==("legacy_unverified",None,None,None,None,None,None,1) for row in legacy)
        if engine.dialect.name=="sqlite":assert db.exec_driver_sql("PRAGMA foreign_key_check").all()==[]
    run_migration(url,"db_bootstrap.py","--revision",REVISION)
    assert snapshot(engine,columns)[1]==rows
    run_migration(url,"-m","alembic","downgrade",PREVIOUS);verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows
    run_migration(url,"db_bootstrap.py","--revision",REVISION);verify_runtime_schema(engine)


def test_predecessor_drift_is_rejected_before_any32_change(progress_database):
    url,engine=progress_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    with engine.begin() as db:db.exec_driver_sql("ALTER TABLE client_progress ADD COLUMN unexpected_progress_drift INTEGER")
    result=subprocess.run([sys.executable,"-X","utf8","db_bootstrap.py","--revision",REVISION],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    with engine.connect() as db:
        assert "progress_consents" not in inspect(db).get_table_names()
        assert db.scalar(text("SELECT version_num FROM alembic_version"))==PREVIOUS


def test_mid_migration_failure_does_not_leave_provenance_or_table(progress_database,monkeypatch):
    url,engine=progress_database;run_migration(url,"db_bootstrap.py","--revision",PREVIOUS)
    columns,rows=snapshot(engine);original=Operations.create_table
    def fail_after(self,name,*args,**kwargs):
        value=original(self,name,*args,**kwargs)
        if name=="progress_consents":raise RuntimeError("Synthetic32 table interruption")
        return value
    monkeypatch.setattr(Operations,"create_table",fail_after)
    with pytest.raises(RuntimeError,match="Synthetic32"):
        with engine.begin() as db:
            config=alembic_config();config.attributes["connection"]=db;command.upgrade(config,REVISION)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows


def test_authored_measurement_refuses_destructive_rollback(progress_database):
    url,engine=progress_database;run_migration(url,"db_bootstrap.py","--revision",REVISION)
    # A PostgreSQL admin seed explicitly binds its synthetic personal subject;
    # its final INSERT still exercises the invoker guard, not a disabled policy.
    with engine.begin() as db:
        db.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro) VALUES ('32-subject','32-subject@example.invalid','synthetic','Synthetic','','usuario','VIEWER',true,0,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO clientes(id_cliente,gym_id,nombre,activo) VALUES ('32-profile','32-subject','Synthetic',true)"))
        if engine.dialect.name=="postgresql":db.execute(text("SELECT set_config('app.current_tenant','32-subject',true)"))
        db.execute(text("INSERT INTO client_progress(id_cliente,gym_id,record_key,source_kind,measured_on,recorded_by_id,recorded_at,updated_at,fecha,peso_kg,version,notas) VALUES ('32-profile','32-subject','00000000-0000-0000-0000-000000000032','self_reported','2020-01-02','32-subject','2026-10-19','2026-10-19','2026-10-19',71.5,1,'')"))
    columns,rows=snapshot(engine)
    result=subprocess.run([sys.executable,"-X","utf8","-m","alembic","downgrade",PREVIOUS],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url),capture_output=True)
    assert result.returncode!=0
    verify_runtime_schema(engine);assert snapshot(engine,columns)[1]==rows
