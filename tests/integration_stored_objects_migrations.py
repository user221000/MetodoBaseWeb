"""Private object metadata: real migrations, preservation and tenant/FK gates."""
import os
import subprocess
import sys
from contextlib import contextmanager

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration, _fixture, ROOT
from tests.integration_provider_subjects import application_engine
from web.database.schema_control import verify_runtime_schema

PREVIOUS = '20261018_gym_generation_quota'
REVISION = '20261018_stored_objects'


def seed_previous(engine):
    with engine.begin() as db:
        for owner in ('object-owner-a','object-owner-b'):
            db.execute(text("""INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro)
                VALUES(:id,:email,'synthetic','Synthetic','','gym','OWNER',true,0,'2026-10-01')"""),
                {'id':owner,'email':owner+'@example.invalid'})
        db.execute(text("""INSERT INTO clientes(id_cliente,gym_id,nombre,activo,fecha_registro)
            VALUES('object-client-a','object-owner-a','Synthetic',true,'2026-10-01')"""))
        db.execute(text("""INSERT INTO planes_generados(id,id_cliente,gym_id,fecha_generacion,ruta_pdf,plan_json)
            VALUES(42,'object-client-a','object-owner-a','2026-10-01','legacy/private.pdf',:json)"""),{'json':'{"legacy":true}'})
        db.execute(text("""INSERT INTO gym_profiles(id,gym_id,nombre_negocio,logo_url)
            VALUES(42,'object-owner-a','Synthetic','legacy/logo.png')"""))
        db.execute(text("""INSERT INTO gym_generation_reservations(id,gym_id,client_id,request_key,request_hash,period,local_date,timezone,
            catalog_plan,status,plan_id,persisted_at,result_json,created_at,updated_at)
            VALUES('object-reservation','object-owner-a','object-client-a','synthetic-key',:hash,'2026-10','2026-10-01',
            'America/Mexico_City','free','completed',42,'2026-10-01',:result,'2026-10-01','2026-10-01')"""),{'hash':'a'*64,'result':'{"plan_id":42}'})


def snapshot(engine, columns=None):
    with engine.connect() as db:
        inspector = inspect(db)
        if columns is None:
            columns = {table:[c['name'] for c in inspector.get_columns(table)]
                for table in inspector.get_table_names() if table != 'alembic_version'}
        quote = db.dialect.identifier_preparer.quote
        rows = {table:sorted((tuple(row) for row in db.execute(text('SELECT '+','.join(map(quote,names))+' FROM '+quote(table)))),key=repr)
            for table,names in columns.items()}
        return columns, rows


@pytest.mark.parametrize('origin',['empty','legacy','populated24'])
def test_upgrade_is_repeatable_and_preserves_previous_data(migration_database, origin):
    url, engine = migration_database
    if origin == 'empty':
        run_migration(url,'db_bootstrap.py','--revision','head')
        verify_runtime_schema(engine)
        with engine.connect() as db:
            assert db.scalar(text('SELECT version_num FROM alembic_version')) == REVISION
            assert len(inspect(db).get_table_names()) == 26
        run_migration(url,'db_bootstrap.py','--revision','head')
        return
    if origin == 'legacy':
        _fixture(engine)
        run_migration(url,'db_bootstrap.py','--adopt-verified-legacy','--revision',PREVIOUS)
    else:
        run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    seed_previous(engine)
    columns, before = snapshot(engine)
    run_migration(url,'db_bootstrap.py','--revision','head')
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == REVISION
        assert len(inspect(db).get_table_names()) == 26  # 25 business tables.
        assert db.scalar(text('SELECT count(*) FROM stored_objects')) == 0
        assert db.scalar(text('SELECT pdf_object_id FROM planes_generados WHERE id=42')) is None
        assert db.scalar(text('SELECT logo_object_id FROM gym_profiles WHERE id=42')) is None
        if engine.dialect.name == 'sqlite':
            assert db.exec_driver_sql('PRAGMA foreign_key_check').all() == []
    assert snapshot(engine,columns)[1] == before
    verify_runtime_schema(engine)
    run_migration(url,'db_bootstrap.py','--revision','head')
    assert snapshot(engine,columns)[1] == before


def test_source_drift_aborts_before_object_metadata_ddl(migration_database):
    url,engine = migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    with engine.begin() as db:
        db.execute(text('ALTER TABLE clientes ADD COLUMN unexpected_drift integer'))
    result = subprocess.run([sys.executable,'-X','utf8','db_bootstrap.py'],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url,METODOBASE_TEST_DATABASE_URL=''),capture_output=True,text=True)
    assert result.returncode != 0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
        assert 'stored_objects' not in inspect(db).get_table_names()
        assert 'pdf_object_id' not in {c['name'] for c in inspect(db).get_columns('planes_generados')}


def test_ddl_failure_rolls_back_table_columns_revision_and_rows(migration_database, monkeypatch):
    import db_bootstrap
    from alembic.operations import Operations
    url,engine = migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    seed_previous(engine)
    columns,before = snapshot(engine)
    original = Operations.batch_alter_table
    reached = []
    @contextmanager
    def rebuild_then_fail(self,name,*args,**kwargs):
        with original(self,name,*args,**kwargs) as batch:
            yield batch
        if name == 'planes_generados':
            reached.append(name)
            raise RuntimeError('Synthetic failure after actual plan reference DDL')
    monkeypatch.setattr(db_bootstrap,'_migration_engine',lambda:engine)
    monkeypatch.setattr(Operations,'batch_alter_table',rebuild_then_fail)
    assert db_bootstrap.main() == 1
    assert reached == ['planes_generados']
    assert snapshot(engine,columns)[1] == before
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
        assert 'stored_objects' not in inspect(db).get_table_names()
        assert 'pdf_object_id' not in {c['name'] for c in inspect(db).get_columns('planes_generados')}


def test_metadata_constraints_and_same_owner_composite_references(migration_database):
    from web.database.models import StoredObject
    from web.database.tenant_context import tenant_scope
    url,engine = migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    seed_previous(engine)
    run_migration(url,'db_bootstrap.py','--revision','head')
    app = application_engine(url,engine)
    if app.dialect.name == 'sqlite':
        with app.connect() as db:
            db.exec_driver_sql('PRAGMA foreign_keys=ON')
    def values(identity='a'*32,owner='object-owner-a',**changes):
        return dict(id=identity,gym_id=owner,kind='plan_pdf',key='private/'+identity,
            content_type='application/pdf',byte_size=100,sha256='a'*64,
            storage_backend='local',status='pending',**changes)
    try:
        with tenant_scope('object-owner-a'), Session(app) as db:
            obj = StoredObject(**values())
            db.add(obj)
            db.commit()  # Pending metadata is durable without a published reference.
            assert db.scalar(select(StoredObject.status)) == 'pending'
            obj.status = 'ready'
            db.execute(text("UPDATE planes_generados SET pdf_object_id=:id WHERE id=42"),{'id':obj.id})
            db.execute(text("UPDATE gym_profiles SET logo_object_id=:id WHERE id=42"),{'id':obj.id})
            db.commit()
            with pytest.raises(IntegrityError):
                db.delete(obj)
                db.commit()
            db.rollback()
        for field,bad in [('kind','unknown'),('storage_backend','unknown'),('status','prepared'),
                ('byte_size',0),('byte_size',64*1024*1024+1),('sha256','a'*63),
                ('id','a'*31),('key','x'*513),('content_type','x'*129)]:
            data=values(identity='b'*32)
            data[field]=bad
            with tenant_scope('object-owner-a'), Session(app) as db:
                db.add(StoredObject(**data))
                with pytest.raises(DBAPIError) as invalid:
                    db.commit()
                if engine.dialect.name == 'postgresql':
                    assert invalid.value.orig.pgcode in {'23514','22001'}
                db.rollback()
        with tenant_scope('object-owner-b'), Session(app) as db:
            db.add(StoredObject(**values(identity='b'*32,owner='object-owner-b')))
            db.commit()
        with tenant_scope('object-owner-a'), Session(app) as db:
            for table,column in [('planes_generados','pdf_object_id'),('gym_profiles','logo_object_id')]:
                with pytest.raises(IntegrityError):
                    db.execute(text('UPDATE '+table+' SET '+column+'=:id WHERE id=42'),{'id':'b'*32})
                    db.commit()
                db.rollback()
            duplicate=values(identity='e'*32)
            duplicate['key']='private/'+'a'*32
            db.add(StoredObject(**duplicate))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
            temporary=values(identity='d'*32)
            temporary.pop('id')
            own=StoredObject(**temporary)
            db.add(own)
            db.commit()
            assert len(own.id) == 32
            db.delete(own)
            db.commit()
        if engine.dialect.name == 'postgresql':
            with Session(app) as db:
                assert db.scalars(select(StoredObject)).all() == []
                db.add(StoredObject(**values(identity='c'*32)))
                with pytest.raises(DBAPIError) as absent:
                    db.commit()
                assert absent.value.orig.pgcode == '42501'
                db.rollback()
            with tenant_scope('object-owner-a'), Session(app) as db:
                assert [o.id for o in db.scalars(select(StoredObject))] == ['a'*32]
                assert db.query(StoredObject).filter_by(gym_id='object-owner-b').update({'status':'ready'}) == 0
                assert db.query(StoredObject).filter_by(gym_id='object-owner-b').delete() == 0
                db.rollback()
                foreign=values(identity='c'*32,owner='object-owner-b')
                db.add(StoredObject(**foreign))
                with pytest.raises(DBAPIError) as denied:
                    db.commit()
                assert denied.value.orig.pgcode == '42501'
                db.rollback()
                with pytest.raises(DBAPIError) as move:
                    db.query(StoredObject).filter_by(id='a'*32).update({'gym_id':'object-owner-b'})
                assert move.value.orig.pgcode == '42501'
                db.rollback()
        with engine.begin() as db:
            with pytest.raises(IntegrityError):
                db.execute(text("DELETE FROM usuarios WHERE id='object-owner-a'"))
    finally:
        if app is not engine:
            app.dispose()
