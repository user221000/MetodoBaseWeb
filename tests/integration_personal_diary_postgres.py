"""Migrated UUID PostgreSQL: restricted roles, real HTTP and process CAS."""
from datetime import date, datetime, timedelta, timezone
import importlib
import multiprocessing

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine

pytestmark=pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
NOW=datetime(2026,10,19,18,tzinfo=timezone.utc)
DAY=date(2026,10,19)


@pytest.fixture
def diary_pg(migration_database):
    from web.database.models import Usuario,UserRole
    url,admin=migration_database
    run_migration(url,'db_bootstrap.py','--revision','head')
    with Session(admin) as db:
        for identity,kind,role,parent in [('diary-owner','gym',UserRole.OWNER,None),
                ('diary-person','usuario',UserRole.VIEWER,None),('diary-other','usuario',UserRole.VIEWER,None),
                ('diary-member','gym',UserRole.NUTRIOLOGO,'diary-owner')]:
            db.add(Usuario(id=identity,email=identity+'@example.invalid',nombre='Synthetic',
                password_hash='synthetic',tipo=kind,role=role,team_gym_id=parent,activo=True))
            db.flush()
        db.commit()
    app=application_engine(url,admin)
    try:
        yield admin,app
    finally:
        app.dispose()


def test_force_rls_own_dml_foreign_absent_and_pool_reuse(diary_pg):
    from web.database.models import PersonalDiaryDay
    from web.database.tenant_context import tenant_scope
    from web.services.personal_diary_persistence import patch_diary_day,read_diary_day
    from web.personal_diary_schemas import WaterOperation
    admin,app=diary_pg
    for subject in ('diary-person','diary-other'):
        with Session(app) as db:
            result=patch_diary_day(db,subject,DAY,WaterOperation(operation='water',expected_version=0,water_ml=500),now=NOW)
            assert result['version']==1
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
        assert db.scalar(text('SELECT count(*) FROM personal_diary_days'))==0
    with tenant_scope('diary-person'),Session(app) as db:
        assert db.scalars(select(PersonalDiaryDay.user_id)).all()==['diary-person']
        assert db.query(PersonalDiaryDay).filter_by(user_id='diary-other').update({'water_ml':999})==0
        assert db.query(PersonalDiaryDay).filter_by(user_id='diary-other').delete()==0
        assert db.query(PersonalDiaryDay).filter_by(user_id='diary-person').update({'water_ml':600})==1
        db.commit()
        with pytest.raises(DBAPIError) as denied:
            db.query(PersonalDiaryDay).update({'user_id':'diary-other'})
        assert denied.value.orig.pgcode=='42501'
        db.rollback()
        assert db.query(PersonalDiaryDay).delete()==1
        db.rollback()
        db.add(PersonalDiaryDay(user_id='diary-person',local_date=DAY-timedelta(days=1)))
        db.commit()
    with Session(app) as db,pytest.raises(DBAPIError) as denied:
        db.add(PersonalDiaryDay(user_id='diary-person',local_date=DAY-timedelta(days=2)))
        db.commit()
    assert denied.value.orig.pgcode=='42501'
    for subject,water in [('diary-other',500),('diary-person',600)]:
        with Session(app) as db:
            assert read_diary_day(db,subject,DAY,now=NOW)['water_ml']==water
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''


def _cas_worker(url,expected,start,ready,output,water):
    from tests.isolation import block_external_sockets,validate_postgres_test_url
    from web.database.tenant_context import configure_tenant_engine
    from web.personal_diary_schemas import WaterOperation
    from web.services.personal_diary_persistence import patch_diary_day
    validate_postgres_test_url(url)
    block_external_sockets()
    engine=configure_tenant_engine(create_engine(url,pool_size=1,max_overflow=0))
    try:
        ready.put(True)
        if not start.wait(20):
            raise RuntimeError('Synthetic process coordination timed out')
        with Session(engine) as db:
            result=patch_diary_day(db,'diary-person',DAY,
                WaterOperation(operation='water',expected_version=expected,water_ml=water),now=NOW)
            output.put(('saved',result['version'],result['water_ml']))
    except HTTPException as error:
        output.put(('denied',error.status_code,error.detail.get('code')))
    except Exception as error:
        output.put(('error',type(error).__name__))
    finally:
        engine.dispose()


@pytest.mark.parametrize('existing',[False,True])
def test_two_processes_have_one_winner_for_absent_and_existing_day(diary_pg,existing):
    from web.personal_diary_schemas import WaterOperation
    from web.services.personal_diary_persistence import patch_diary_day
    from web.database.models import PersonalDiaryDay
    admin,app=diary_pg
    if existing:
        with Session(app) as db:
            patch_diary_day(db,'diary-person',DAY,WaterOperation(operation='water',expected_version=0,water_ml=1),now=NOW)
    context=multiprocessing.get_context('spawn')
    start,ready,output=context.Event(),context.Queue(),context.Queue()
    processes=[context.Process(target=_cas_worker,args=(app.url.render_as_string(hide_password=False),
        int(existing),start,ready,output,water)) for water in (500,1000)]
    try:
        for process in processes: process.start()
        assert ready.get(timeout=20) and ready.get(timeout=20)
        start.set()
        results=[output.get(timeout=30),output.get(timeout=30)]
        assert sorted(row[0] for row in results)==['denied','saved'],results
        assert next(row for row in results if row[0]=='denied')==('denied',409,'diary_version_conflict')
        saved=next(row for row in results if row[0]=='saved')
        assert saved[1]==int(existing)+1
        with Session(admin) as db:
            row=db.scalars(select(PersonalDiaryDay)).one()
            assert (row.version,row.water_ml)==saved[1:]
    finally:
        for process in processes:
            process.join(5)
            if process.is_alive():
                process.terminate(); process.join(5)
        assert all(process.exitcode==0 for process in processes)


@pytest.mark.parametrize('zone',['UTC','America/Mexico_City'])
def test_mexico_midnight_and_typed_utc_are_independent_of_session_timezone(diary_pg,zone):
    from web.personal_diary_schemas import WaterOperation
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_persistence import patch_diary_day
    from web.services.personal_diary_service import local_today
    admin,app=diary_pg
    with app.connect() as db:
        db.execute(text("SELECT set_config('TimeZone',:zone,false)"),{'zone':zone}); db.commit()
    before=datetime(2026,10,19,5,59,tzinfo=timezone.utc)
    after=datetime(2026,10,19,6,0,tzinfo=timezone.utc)
    assert local_today(before)==date(2026,10,18) and local_today(after)==DAY
    with Session(app) as db,pytest.raises(HTTPException) as future:
        patch_diary_day(db,'diary-person',DAY,WaterOperation(operation='water',expected_version=0,water_ml=1),now=before)
    assert future.value.status_code==422
    offset=timezone(timedelta(hours=5,minutes=30))
    with Session(app) as db:
        result=patch_diary_day(db,'diary-person',DAY,
            WaterOperation(operation='water',expected_version=0,water_ml=1),now=after.astimezone(offset))
    assert result['today']=='2026-10-19' and result['created_at']=='2026-10-19T06:00:00+00:00'
    with Session(admin) as db:
        assert db.scalars(select(PersonalDiaryDay.created_at)).one()==datetime(2026,10,19,6)


@pytest.mark.parametrize('factory',['web.main_web','api.app'])
def test_http_member_personal_scope_export_and_foreign_source_under_force_rls(diary_pg,monkeypatch,factory):
    from web.auth import crear_access_token,identity_from_user
    from web.database import engine as database
    from web.database.models import Usuario
    from tests.test_personal_diary_persistence import seed_plan,meal_patch
    from web.services.personal_diary_service import local_today
    admin,app=diary_pg
    monkeypatch.setattr(database,'_engine',app)
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=app,autoflush=False))
    application=importlib.import_module(factory).create_app()
    with Session(app) as db:
        headers={key:{'Authorization':'Bearer '+crear_access_token(identity_from_user(db.get(Usuario,key),db))}
            for key in ('diary-member','diary-other','diary-owner')}
    foreign=seed_plan(admin,owner='diary-other')
    mixed=seed_plan(admin,owner='diary-member',client_owner='diary-other')
    own=seed_plan(admin,owner='diary-member',active=False)
    with TestClient(application,raise_server_exceptions=False) as client:
        assert client.get('/api/auth/me',headers=headers['diary-member']).status_code==200
        url='/api/usuario/diario/'+local_today().isoformat()
        for source in (foreign,mixed):
            response=client.patch(url,headers=headers['diary-member'],json=meal_patch(source,0))
            assert response.status_code==404,response.text
        saved=client.patch(url,headers=headers['diary-member'],json=meal_patch(own,0))
        assert saved.status_code==200,saved.text
        assert saved.json()['totals']['kcal']==140 and saved.json()['version']==1
        assert client.get(url,headers=headers['diary-other']).json()['version']==0
        assert client.get(url,headers=headers['diary-owner']).status_code==403
        exported=client.get('/api/usuario/privacidad/exportar',headers=headers['diary-member'])
        assert exported.status_code==200,exported.text
        assert exported.json()['personal_diary']['records'][0]['meals']==saved.json()['meals']
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''


@pytest.mark.parametrize('ack_lost',[False,True])
def test_rollback_and_real_commit_ack_uncertainty_are_visible_and_recoverable(diary_pg,monkeypatch,caplog,ack_lost):
    from sqlalchemy.exc import StatementError
    from web.database.models import PersonalDiaryDay
    from web.personal_diary_schemas import WaterOperation
    from web.services.personal_diary_persistence import patch_diary_day,read_diary_day
    admin,app=diary_pg
    with Session(app) as db:
        original=db.commit
        def uncertain():
            if ack_lost:
                original()
            raise StatementError('private-diary-statement','private-sql',{'private-water-note':'secret'},RuntimeError())
        monkeypatch.setattr(db,'commit',uncertain)
        with pytest.raises(HTTPException) as failure:
            patch_diary_day(db,'diary-person',DAY,
                WaterOperation(operation='water',expected_version=0,water_ml=1800),now=NOW)
    assert failure.value.status_code==503
    assert failure.value.detail['code']=='diary_save_unconfirmed'
    assert all(value not in caplog.text for value in ('private-diary-statement','private-sql','private-water-note','secret'))
    with Session(admin) as db:
        assert db.query(PersonalDiaryDay).count()==int(ack_lost)
    with Session(app) as db:
        state=read_diary_day(db,'diary-person',DAY,now=NOW)
        assert state['version']==int(ack_lost)
        assert state['water_ml']==(1800 if ack_lost else 0)
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
