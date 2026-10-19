"""Nullable account auth state added from exact27, preserving historical data."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect,select,text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database,run_migration,ROOT
from tests.integration_individual_publication_migrations import seed_previous
from tests.integration_stored_objects_migrations import snapshot
from tests.integration_provider_subjects import application_engine
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.schema_control import verify_runtime_schema

PREVIOUS='20261019_personal_diary'
REVISION='20261019_account_recovery'
COLUMNS={'password_reset_hash','password_reset_expires_at','password_reset_session_version'}


def populate27(engine):
    # Use reviewed SQL/reflection, not current Usuario ORM against an old revision.
    seed_previous(engine)
    with engine.begin() as db:
        db.execute(text("""INSERT INTO personal_diary_days(id,user_id,local_date,timezone,water_ml,version,meals_json,created_at,updated_at)
            VALUES('recovery-history','individual-migration','2026-10-18','America/Mexico_City',750,3,'{}','2026-10-18','2026-10-18')"""))


@pytest.mark.parametrize('populated',[False,True])
def test_empty_and_populated27_upgrade_repeat_and_preserve_authority(migration_database,populated):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    if populated: populate27(engine)
    columns,before=snapshot(engine)
    with engine.connect() as db:
        security_before=tenant_security_signature(db)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match='revision'):
        verify_runtime_schema(engine)
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    verify_runtime_schema(engine,expected_revision=REVISION)
    assert snapshot(engine,columns)[1]==before
    with engine.connect() as db:
        assert len(inspect(db).get_table_names())==27  # 26 business tables, no new authority table.
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==REVISION
        assert tenant_security_signature(db)==security_before
        assert COLUMNS.issubset({column['name'] for column in inspect(db).get_columns('usuarios')})
        assert db.execute(text('SELECT password_reset_hash,password_reset_expires_at,password_reset_session_version FROM usuarios')).all()==([(None,None,None)] if populated else [])
        if engine.dialect.name=='sqlite': assert db.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    assert snapshot(engine,columns)[1]==before


def test_unknown27_drift_rejected_before_account_columns(migration_database):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    with engine.begin() as db: db.execute(text('ALTER TABLE usuarios ADD COLUMN unknown_recovery_drift integer'))
    result=subprocess.run([sys.executable,'-X','utf8','db_bootstrap.py'],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url,METODOBASE_TEST_DATABASE_URL=''),capture_output=True,text=True)
    assert result.returncode!=0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==PREVIOUS
        assert COLUMNS.isdisjoint({column['name'] for column in inspect(db).get_columns('usuarios')})


def test_failure_after_actual_parent_rebuild_rolls_back_rows_constraints_and_revision(migration_database,monkeypatch):
    import db_bootstrap
    from alembic.operations import Operations
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    populate27(engine)
    columns,before=snapshot(engine)
    original=Operations.batch_alter_table
    reached=[]
    @contextmanager
    def altered(self,name,*args,**kwargs):
        with original(self,name,*args,**kwargs) as batch: yield batch
        if name=='usuarios':
            reached.append(True)
            raise RuntimeError('Synthetic failure after actual recovery parent DDL')
    monkeypatch.setattr(db_bootstrap,'_migration_engine',lambda:engine)
    monkeypatch.setattr(Operations,'batch_alter_table',altered)
    assert db_bootstrap.main()==1 and reached==[True]
    assert snapshot(engine,columns)[1]==before
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==PREVIOUS
        assert COLUMNS.isdisjoint({column['name'] for column in inspect(db).get_columns('usuarios')})
        if engine.dialect.name=='sqlite': assert db.exec_driver_sql('PRAGMA foreign_key_check').all()==[]


@pytest.mark.parametrize('zone',['UTC','America/Mexico_City'])
def test_all_or_none_digest_unique_and_expiry_utc_type(migration_database,zone):
    from web.database.models import Usuario
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    populate27(engine)
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    app=application_engine(url,engine)
    instant=datetime(2026,10,19,11,30,tzinfo=timezone(timedelta(hours=5,minutes=30)))
    try:
        with app.connect() as db:
            if app.dialect.name=='postgresql': db.execute(text("SELECT set_config('TimeZone',:zone,false)"),{'zone':zone})
            db.commit()
        with Session(app) as db:
            for changes in ({'password_reset_hash':'a'*64},
                    {'password_reset_hash':'a'*63,'password_reset_expires_at':instant,'password_reset_session_version':0},
                    {'password_reset_hash':'a'*64,'password_reset_expires_at':instant,'password_reset_session_version':-1}):
                with pytest.raises(IntegrityError):
                    db.query(Usuario).filter_by(id='individual-migration').update(changes); db.commit()
                db.rollback()
            db.query(Usuario).filter_by(id='individual-migration').update({'password_reset_hash':'a'*64,
                'password_reset_expires_at':instant,'password_reset_session_version':0})
            db.commit()
            row=db.get(Usuario,'individual-migration')
            assert row.password_reset_expires_at==datetime(2026,10,19,6)
            db.add(Usuario(id='recovery-second',email='second@example.invalid',password_hash='synthetic',nombre='Synthetic',
                password_reset_hash='a'*64,password_reset_expires_at=instant,password_reset_session_version=0))
            with pytest.raises(IntegrityError): db.commit()
            db.rollback()
            assert db.scalar(select(Usuario.session_version).where(Usuario.id=='individual-migration'))==0
    finally:
        if app is not engine: app.dispose()
