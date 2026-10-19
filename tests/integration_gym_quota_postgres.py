"""New ledger RLS and UTC storage semantics on owned migrated PostgreSQL DBs."""
from datetime import datetime, timezone

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine


@pytest.fixture
def gym_ledger(migration_database):
    from web.database.models import Usuario, UserRole, Cliente
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    with Session(admin) as db:
        for suffix in ('a','b'):
            db.add(Usuario(id='quota-' + suffix, email='quota-' + suffix + '@example.test', nombre='Synthetic',
                tipo='gym', role=UserRole.OWNER, password_hash='unused-synthetic'))
        db.commit()
        for suffix in ('a','b'):
            db.add(Cliente(id_cliente='client-' + suffix, gym_id='quota-' + suffix, nombre='Synthetic'))
        db.commit()
    app = application_engine(url, admin)
    try:
        yield admin, app
    finally:
        app.dispose()


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
def test_new_ledger_enforces_own_foreign_and_absent_subject_for_real_dml(gym_ledger):
    from web.database.models import GymGenerationReservation
    from web.database.tenant_context import tenant_scope
    from web.services.gym_generation_quota import reserve_gym_generation
    _, app = gym_ledger
    for suffix in ('a','b'):
        with tenant_scope('quota-' + suffix), Session(app) as db:
            reserve_gym_generation(db, 'quota-' + suffix, {'id_cliente':'client-' + suffix}, 'same-key')
    with Session(app) as db:
        assert db.scalars(select(GymGenerationReservation)).all() == []
    with tenant_scope('quota-a'), Session(app) as db:
        original = dict(db.execute(select(GymGenerationReservation.__table__)).mappings().one())
        assert original['gym_id'] == 'quota-a'
        assert db.query(GymGenerationReservation).filter_by(gym_id='quota-b').update({'request_key':'foreign'}) == 0
        assert db.query(GymGenerationReservation).filter_by(gym_id='quota-b').delete() == 0
        assert db.query(GymGenerationReservation).filter_by(gym_id='quota-a').update({'request_key':'own'}) == 1
        db.rollback()
        savepoint = db.begin_nested()
        assert db.query(GymGenerationReservation).filter_by(gym_id='quota-a').delete() == 1
        db.execute(GymGenerationReservation.__table__.insert().values(**original))
        assert db.query(GymGenerationReservation).filter_by(gym_id='quota-a').count() == 1
        savepoint.rollback()
        db.rollback()
        with pytest.raises(DBAPIError) as failure:
            db.query(GymGenerationReservation).filter_by(gym_id='quota-a').update({'gym_id':'quota-b'})
        assert failure.value.orig.pgcode == '42501'
        db.rollback()
    original['id'], original['request_key'] = 'anonymous-insert', 'anonymous'
    with Session(app) as db, pytest.raises(DBAPIError) as absent:
        db.execute(GymGenerationReservation.__table__.insert().values(**original))
    assert absent.value.orig.pgcode == '42501'


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('database_timezone', ['UTC','America/Mexico_City'])
def test_reservation_plan_storage_and_local_bounds_do_not_depend_on_database_timezone(gym_ledger, database_timezone):
    from web.database import repository
    from web.database.models import PlanGenerado
    from web.database.tenant_context import tenant_scope
    from web.services.gym_generation_quota import reserve_gym_generation, fail_gym_generation
    admin, app = gym_ledger
    with app.connect() as connection:
        connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {'zone': database_timezone})
        connection.commit()
    now = datetime(2026,10,18,5,59,tzinfo=timezone.utc)
    with tenant_scope('quota-a'), Session(app) as db:
        reservation = reserve_gym_generation(db, 'quota-a', {'id_cliente':'client-a'}, 'before-midnight', now=now)
        assert reservation.created_at == datetime(2026,10,18,5,59)
        assert reservation.local_date.isoformat() == '2026-10-17'
        fail_gym_generation(db, 'quota-a', reservation.id)
    with Session(admin) as db:
        db.add(PlanGenerado(gym_id='quota-a',id_cliente='client-a',fecha_generacion=datetime(2026,10,18,6,1)))
        db.commit()
    with tenant_scope('quota-a'), Session(app) as db:
        accepted = reserve_gym_generation(db, 'quota-a', {'id_cliente':'client-a'}, 'day-17', now=now)
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        plan_id = repository.registrar_plan(db, 'quota-a', 'client-a', {}, return_id=True, reservation_id=accepted.id)
        db.commit()
        stored = db.get(PlanGenerado, plan_id).fecha_generacion
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        assert before <= stored <= after
        with pytest.raises(HTTPException) as next_day:
            reserve_gym_generation(db, 'quota-a', {'id_cliente':'client-a'}, 'day-18',
                now=datetime(2026,10,18,6,1,tzinfo=timezone.utc))
        assert next_day.value.detail['code'] == 'daily_plan_limit'
