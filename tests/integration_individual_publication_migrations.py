"""Individual accounting extends immutable revision 25 without guessing legacy links."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration, ROOT
from tests.integration_stored_objects_migrations import snapshot
from tests.integration_provider_subjects import application_engine
from web.database.schema_control import verify_runtime_schema

PREVIOUS = '20261018_stored_objects'
REVISION = '20261018_individual_publication'


def seed_previous(engine):
    with engine.begin() as db:
        db.execute(text("""INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro)
            VALUES('individual-migration','individual-migration@example.invalid','synthetic','Synthetic','','usuario','VIEWER',true,0,'2026-10-01')"""))
        db.execute(text("""INSERT INTO clientes(id_cliente,gym_id,nombre,activo,fecha_registro)
            VALUES('individual-client','individual-migration','Synthetic',true,'2026-10-01')"""))
        for plan in (10, 11):
            db.execute(text("""INSERT INTO planes_generados(id,id_cliente,gym_id,fecha_generacion,plan_json)
                VALUES(:id,'individual-client','individual-migration','2026-10-01','{}')"""), {'id': plan})
        for identity, status, plan in [('reserved','reserved',None), ('completed','completed',10),
                ('completed-missing','completed',None), ('released','released',None)]:
            db.execute(text("""INSERT INTO generation_reservations(id,user_id,request_key,period,status,plan_id,created_at,updated_at)
                VALUES(:id,'individual-migration',:id,'2026-10',:status,:plan,'2026-10-01','2026-10-01')"""),
                {'id':identity,'status':status,'plan':plan})


@pytest.mark.parametrize('populated', [False, True])
def test_upgrade_preserves_legacy_rows_without_claiming_publication(migration_database, populated):
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    if populated:
        seed_previous(engine)
    columns, before = snapshot(engine)
    with pytest.raises(RuntimeError, match='revision'):
        verify_runtime_schema(engine)
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    assert snapshot(engine, columns)[1] == before
    with engine.connect() as db:
        assert len(inspect(db).get_table_names()) == 26
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == REVISION
        if populated:
            rows = db.execute(text('SELECT publication_protocol,persisted_at FROM generation_reservations')).all()
            assert rows == [(0, None)] * 4
            assert db.scalar(text("SELECT plan_id FROM generation_reservations WHERE id='reserved'")) is None
        if engine.dialect.name == 'sqlite':
            assert db.exec_driver_sql('PRAGMA foreign_key_check').all() == []
    verify_runtime_schema(engine, expected_revision=REVISION)
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    assert snapshot(engine, columns)[1] == before


def test_source_drift_is_rejected_before_new_columns(migration_database):
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    with engine.begin() as db:
        db.execute(text('ALTER TABLE generation_reservations ADD COLUMN unknown_drift integer'))
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py'], cwd=ROOT,
        env=dict(os.environ, DATABASE_URL=url, METODOBASE_TEST_DATABASE_URL=''), capture_output=True, text=True)
    assert result.returncode != 0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
        assert 'persisted_at' not in {c['name'] for c in inspect(db).get_columns('generation_reservations')}


def test_failure_after_actual_ddl_rolls_back_columns_rows_and_revision(migration_database, monkeypatch):
    import db_bootstrap
    from alembic.operations import Operations
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    seed_previous(engine)
    columns, before = snapshot(engine)
    original = Operations.batch_alter_table
    reached = []
    @contextmanager
    def alter_then_fail(self, table, *args, **kwargs):
        with original(self, table, *args, **kwargs) as batch:
            yield batch
        if table == 'generation_reservations':
            reached.append(table)
            raise RuntimeError('Synthetic error after real individual ledger DDL')
    monkeypatch.setattr(db_bootstrap, '_migration_engine', lambda: engine)
    monkeypatch.setattr(Operations, 'batch_alter_table', alter_then_fail)
    assert db_bootstrap.main() == 1
    assert reached == ['generation_reservations']
    assert snapshot(engine, columns)[1] == before
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
        assert 'persisted_at' not in {c['name'] for c in inspect(db).get_columns('generation_reservations')}


@pytest.mark.parametrize('zone', ['UTC', 'America/Mexico_City'])
def test_checks_and_typed_marker_in_utc_and_mexico_sessions(migration_database, zone):
    from web.database.models import GenerationReservation
    from web.database.tenant_context import tenant_scope
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    seed_previous(engine)
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    app = application_engine(url, engine)
    instant = datetime(2026, 10, 18, 7, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    try:
        if app.dialect.name == 'postgresql':
            with app.connect() as db:
                db.execute(text("SELECT set_config('TimeZone',:zone,false)"), {'zone':zone})
                db.commit()
        with tenant_scope('individual-migration'), Session(app) as db:
            for changes in [dict(publication_protocol=2), dict(publication_protocol=0,persisted_at=instant),
                    dict(publication_protocol=1,status='reserved',persisted_at=instant),
                    dict(publication_protocol=1,status='released',persisted_at=instant),
                    dict(publication_protocol=1,status='completed')]:
                with pytest.raises(IntegrityError):
                    db.query(GenerationReservation).filter_by(id='reserved').update(changes)
                    db.commit()
                db.rollback()
            db.query(GenerationReservation).filter_by(id='reserved').update(dict(
                publication_protocol=1, status='completed', persisted_at=instant, plan_id=11))
            db.commit()
            marker = db.get(GenerationReservation, 'reserved').persisted_at
            assert marker == datetime(2026, 10, 18, 2)
            if app.dialect.name == 'sqlite':
                db.execute(text('PRAGMA foreign_keys=ON'))
            db.execute(text('DELETE FROM planes_generados WHERE id=11'))
            db.commit()
            row = db.get(GenerationReservation, 'reserved')
            db.refresh(row)
            assert row.plan_id is None and row.persisted_at == marker and row.status == 'completed'
    finally:
        if app is not engine:
            app.dispose()
