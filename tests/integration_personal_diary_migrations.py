"""Revision 27 adds only diary snapshots; exact revision 26 stays immutable."""
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration, ROOT
from tests.integration_individual_publication_migrations import seed_previous
from tests.integration_stored_objects_migrations import snapshot
from tests.integration_provider_subjects import application_engine
from web.database.schema_control import verify_runtime_schema

PREVIOUS='20261018_individual_publication'
REVISION='20261019_personal_diary'


@pytest.mark.parametrize('populated',[False,True])
def test_empty_and_populated26_upgrade_preserve_old_rows_and_repeat(migration_database,populated):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    if populated:
        seed_previous(engine)
    columns,before=snapshot(engine)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match='revision'):
        verify_runtime_schema(engine)
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    assert snapshot(engine,columns)[1]==before
    verify_runtime_schema(engine)
    with engine.connect() as db:
        assert len(inspect(db).get_table_names())==27  # 26 business + Alembic.
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==REVISION
        assert db.scalar(text('SELECT count(*) FROM personal_diary_days'))==0
        if engine.dialect.name=='sqlite':
            assert db.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    assert snapshot(engine,columns)[1]==before


def test_source26_drift_rejected_before_diary_ddl(migration_database):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    with engine.begin() as db:
        db.execute(text('ALTER TABLE planes_generados ADD COLUMN unexpected_diary_drift integer'))
    result=subprocess.run([sys.executable,'-X','utf8','db_bootstrap.py'],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url,METODOBASE_TEST_DATABASE_URL=''),capture_output=True,text=True)
    assert result.returncode!=0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==PREVIOUS
        assert 'personal_diary_days' not in inspect(db).get_table_names()


def test_failure_after_real_diary_ddl_rolls_back_table_rows_and_revision(migration_database,monkeypatch):
    import db_bootstrap
    from alembic.operations import Operations
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    seed_previous(engine)
    columns,before=snapshot(engine)
    original=Operations.create_table
    reached=[]
    def create_then_fail(self,name,*args,**kwargs):
        result=original(self,name,*args,**kwargs)
        if name=='personal_diary_days':
            reached.append(name)
            raise RuntimeError('Synthetic failure after actual diary DDL')
        return result
    monkeypatch.setattr(Operations,'create_table',create_then_fail)
    monkeypatch.setattr(db_bootstrap,'_migration_engine',lambda:engine)
    assert db_bootstrap.main()==1
    assert reached==['personal_diary_days']
    assert snapshot(engine,columns)[1]==before
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==PREVIOUS
        assert 'personal_diary_days' not in inspect(db).get_table_names()


@pytest.mark.parametrize('zone',['UTC','America/Mexico_City'])
def test_constraints_restrict_owner_and_preserve_snapshots_without_source_fk(migration_database,zone):
    from web.database.models import PersonalDiaryDay
    from web.database.tenant_context import tenant_scope
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    seed_previous(engine)
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    app=application_engine(url,engine)
    instant=datetime(2026,10,18,7,30,tzinfo=timezone(timedelta(hours=5,minutes=30)))
    try:
        with app.connect() as db:
            if app.dialect.name=='postgresql':
                db.execute(text("SELECT set_config('TimeZone',:zone,false)"),{'zone':zone})
            else:
                db.exec_driver_sql('PRAGMA foreign_keys=ON')
            db.commit()
        with tenant_scope('individual-migration'),Session(app) as db:
            row=PersonalDiaryDay(user_id='individual-migration',local_date=date(2026,10,18),
                created_at=instant,updated_at=instant)
            db.add(row)
            db.commit()
            assert row.created_at==datetime(2026,10,18,2)
            for changes in ({'water_ml':-1},{'water_ml':20001},{'version':0},{'version':2147483648},
                    {'timezone':'UTC'},{'meals_json':'x'*65537}):
                with pytest.raises((IntegrityError,DataError)) as invalid:
                    db.query(PersonalDiaryDay).filter_by(id=row.id).update(changes)
                    db.commit()
                if app.dialect.name=='postgresql':
                    assert invalid.value.orig.pgcode==('22003' if changes.get('version')==2147483648 else '23514')
                db.rollback()
            with pytest.raises(IntegrityError):
                db.add(PersonalDiaryDay(user_id='individual-migration',local_date=date(2026,10,18)))
                db.commit()
            db.rollback()
            db.execute(text('DELETE FROM planes_generados WHERE id=10'))
            db.commit()
            assert db.scalar(select(PersonalDiaryDay.meals_json))=='{}'
        # Privileged DDL owner still cannot delete a referenced account through
        # this RESTRICT FK. This is schema preservation, not a role bypass.
        with engine.connect() as db:
            transaction=db.begin()
            with pytest.raises(IntegrityError):
                db.execute(text("DELETE FROM usuarios WHERE id='individual-migration'"))
            transaction.rollback()
        with engine.connect() as db:
            fks=inspect(db).get_foreign_keys('personal_diary_days')
            assert len(fks)==1 and fks[0]['referred_table']=='usuarios'
            assert fks[0]['options']['ondelete']=='RESTRICT'
    finally:
        if app is not engine:
            app.dispose()
