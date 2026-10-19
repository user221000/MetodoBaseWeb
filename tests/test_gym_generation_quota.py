"""Durable B2B quota/idempotency and publication/compensation invariants."""
from datetime import datetime, timedelta, timezone
import json

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def gym_quota_case(test_gym_user):
    from web.database.engine import get_engine
    from web.database.models import Cliente
    engine = get_engine()
    with Session(engine) as db:
        for index in range(10):
            db.add(Cliente(id_cliente='quota-client-' + str(index), gym_id=test_gym_user['id'],
                nombre='Synthetic client', fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=2)))
        db.commit()
    return engine, test_gym_user['id']


def payload(index=0, number=1):
    return {'id_cliente': 'quota-client-' + str(index), 'plan_numero': number, 'tipo_plan': 'menu_fijo'}


def test_pending_reservation_consumes_per_client_day_and_retry_cannot_start_again(gym_quota_case):
    from web.services.gym_generation_quota import reserve_gym_generation
    engine, owner = gym_quota_case
    with Session(engine) as db:
        reserve_gym_generation(db, owner, payload(), 'first')
        with pytest.raises(HTTPException) as duplicate:
            reserve_gym_generation(db, owner, payload(), 'first')
        assert duplicate.value.status_code == 409
        db.rollback()
        with pytest.raises(HTTPException) as second:
            reserve_gym_generation(db, owner, payload(), 'second')
        assert second.value.detail['code'] == 'daily_plan_limit'


def test_global_daily_cap_counts_historical_plans_and_pending_reservation(gym_quota_case):
    from web.database.models import PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation
    engine, owner = gym_quota_case
    with Session(engine) as db:
        for index in range(9):
            db.add(PlanGenerado(gym_id=owner, id_cliente='quota-client-' + str(index),
                fecha_generacion=datetime.now(timezone.utc).replace(tzinfo=None)))
        db.commit()
        reserve_gym_generation(db, owner, payload(9), 'tenth')
        with pytest.raises(HTTPException) as exhausted:
            reserve_gym_generation(db, owner, payload(0), 'eleventh')
        assert exhausted.value.detail['code'] == 'daily_plan_limit_gym'
        assert exhausted.value.detail['limit'] == 10


def test_monthly_cap_includes_historical_previous_days(gym_quota_case):
    from web.database.models import PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation
    engine, owner = gym_quota_case
    now = datetime(2026, 10, 18, 18, tzinfo=timezone.utc)
    with Session(engine) as db:
        for _ in range(20):
            db.add(PlanGenerado(gym_id=owner, id_cliente='quota-client-0', fecha_generacion=datetime(2026,10,10,18)))
        db.commit()
        with pytest.raises(HTTPException) as exhausted:
            reserve_gym_generation(db, owner, payload(1), 'monthly', now=now)
        assert exhausted.value.detail['code'] == 'monthly_plan_limit_gym'
        assert exhausted.value.detail['limit'] == 20


def test_complete_replays_exact_response_and_rejects_changed_payload(gym_quota_case):
    from web.database import repository
    from web.database.models import PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation, complete_gym_generation, fail_gym_generation, _usage
    from web.services.quota_calendar import quota_calendar
    engine, owner = gym_quota_case
    with Session(engine) as db:
        reservation = reserve_gym_generation(db, owner, payload(), 'completed')
        plan_id = repository.registrar_plan(db, owner, payload()['id_cliente'], {'plan_json':'{"breakfast":{}}'},
            return_id=True, reservation_id=reservation.id)
        db.commit()
        result = {'success':True,'plan_id':plan_id,'nombre':'Synthetic','macros':{'kcal_real':1995.5},'plan':{'breakfast':{}}}
        assert complete_gym_generation(db, owner, reservation.id, result) == result
        replay = reserve_gym_generation(db, owner, payload(), 'completed')
        assert json.loads(replay.result_json) == result
        assert db.query(PlanGenerado).count() == 1
        assert _usage(db, owner, quota_calendar(), monthly=True) == 1
        fail_gym_generation(db, owner, reservation.id)
        assert replay.status == 'completed'
        with pytest.raises(HTTPException) as conflict:
            reserve_gym_generation(db, owner, payload(number=2), 'completed')
        assert conflict.value.status_code == 409 and conflict.value.detail['code'] == 'idempotency_conflict'


def test_failure_releases_once_and_allows_new_key(gym_quota_case):
    from web.services.gym_generation_quota import reserve_gym_generation, fail_gym_generation
    engine, owner = gym_quota_case
    with Session(engine) as db:
        reservation = reserve_gym_generation(db, owner, payload(), 'failure')
        fail_gym_generation(db, owner, reservation.id)
        fail_gym_generation(db, owner, reservation.id)
        assert reservation.status == 'released'
        with pytest.raises(HTTPException):
            reserve_gym_generation(db, owner, payload(), 'failure')
        db.rollback()
        assert reserve_gym_generation(db, owner, payload(), 'replacement').status == 'reserved'


@pytest.mark.parametrize('delete_plan', [False, True])
def test_crash_after_plan_commit_never_refunds_even_after_reference_deleted(gym_quota_case, delete_plan):
    from web.database import repository
    from web.database.models import PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation, fail_gym_generation
    engine, owner = gym_quota_case
    with Session(engine) as db:
        reservation = reserve_gym_generation(db, owner, payload(), 'crash')
        plan_id = repository.registrar_plan(db, owner, payload()['id_cliente'], {'plan_json':'{}'},
            return_id=True, reservation_id=reservation.id)
        db.commit()
        if delete_plan:
            db.query(PlanGenerado).filter_by(id=plan_id).delete()
            db.commit()
        fail_gym_generation(db, owner, reservation.id)
        assert reservation.status == 'reserved' and reservation.persisted_at is not None
        with pytest.raises(HTTPException) as retry:
            reserve_gym_generation(db, owner, payload(), 'replacement')
        assert retry.value.detail['code'] == 'daily_plan_limit'


def test_plan_link_requires_the_reserved_client_and_transaction_rolls_back(gym_quota_case):
    from web.database import repository
    from web.database.models import PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation
    engine, owner = gym_quota_case
    with Session(engine) as db:
        reservation = reserve_gym_generation(db, owner, payload(), 'bound-client')
        with pytest.raises(ValueError):
            repository.registrar_plan(db, owner, payload(1)['id_cliente'], {}, reservation_id=reservation.id)
        db.rollback()
        assert db.query(PlanGenerado).count() == 0


def test_client_capacity_is_enforced_in_repository_for_every_adapter(gym_quota_case):
    from web.database import repository
    from web.database.models import Cliente
    engine, owner = gym_quota_case
    with Session(engine) as db:
        with pytest.raises(HTTPException) as cap:
            repository.crear_cliente(db, owner, {'nombre':'Over limit'})
        assert cap.value.detail['code'] == 'client_limit_reached' and cap.value.detail['limit'] == 10
        db.rollback()
        assert db.query(Cliente).count() == 10


def test_inactive_client_cannot_reserve_or_start_worker(gym_quota_case):
    from web.database.models import Cliente
    from web.services.gym_generation_quota import reserve_gym_generation
    from web.services.plan_generation import build_plan
    engine, owner = gym_quota_case
    with Session(engine) as db:
        db.query(Cliente).filter_by(id_cliente='quota-client-0').update({'activo':False})
        db.commit()
        with pytest.raises(HTTPException) as inactive:
            reserve_gym_generation(db, owner, payload(), 'inactive')
        assert inactive.value.status_code == 404
    with pytest.raises(ValueError):
        build_plan('quota-client-0', 1, owner)


def test_deactivated_client_keeps_completed_replay_and_existing_job_can_publish(gym_quota_case):
    from web.database import repository
    from web.database.models import Cliente
    from web.services.gym_generation_quota import reserve_gym_generation, complete_gym_generation
    engine, owner = gym_quota_case
    with Session(engine) as db:
        reservation = reserve_gym_generation(db, owner, payload(), 'accepted-before-deactivation')
        db.query(Cliente).filter_by(id_cliente='quota-client-0').update({'activo':False})
        db.commit()
        # The worker already loaded/authorized the client before CPU work.
        plan_id = repository.registrar_plan(db, owner, 'quota-client-0', {}, return_id=True, reservation_id=reservation.id)
        db.commit()
        result = {'success':True,'plan_id':plan_id}
        complete_gym_generation(db, owner, reservation.id, result)
        replay = reserve_gym_generation(db, owner, payload(), 'accepted-before-deactivation')
        assert replay.status == 'completed' and json.loads(replay.result_json) == result
