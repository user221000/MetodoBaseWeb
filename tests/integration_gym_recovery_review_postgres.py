"""Independent gym reservation replay, compensation and post-commit crash."""
from contextlib import contextmanager
import json
import multiprocessing
import os

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from tests.integration_gym_caps_http_postgres import gym_case, QUOTA_NOW
from tests.integration_postgres import owned_postgres_database, TENANT_A


def payload(index=1):
    return {"id_cliente": "qa-gym-cap-client-" + str(index), "plan_numero": 1, "tipo_plan": "menu_fijo"}


@contextmanager
def app_session(case):
    from web.database.tenant_context import configure_tenant_engine, tenant_scope

    engine = configure_tenant_engine(create_engine(case[1], pool_size=1, max_overflow=0))
    try:
        with tenant_scope(TENANT_A), Session(engine, expire_on_commit=False) as db:
            yield db
    finally:
        engine.dispose()


def persisted_plan(db, reservation):
    from web.database.repository import registrar_plan

    plan_id = registrar_plan(db, TENANT_A, reservation.client_id,
        {"plan_json": '{"synthetic":true}', "ruta_pdf": "synthetic-quota-only.pdf"},
        return_id=True, reservation_id=reservation.id)
    assert plan_id
    db.commit()
    return plan_id


def test_completed_request_replays_exact_result_and_rejects_changed_hash(gym_case):
    from fastapi import HTTPException
    from web.database.models import GymGenerationReservation, PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation, complete_gym_generation

    with app_session(gym_case) as db:
        reservation = reserve_gym_generation(db, TENANT_A, payload(), "complete-and-replay", now=QUOTA_NOW)
        plan_id = persisted_plan(db, reservation)
        result = {"success": True, "plan_id": plan_id, "label": "nutrición sintética"}
        assert complete_gym_generation(db, TENANT_A, reservation.id, result) == result
        replay = reserve_gym_generation(db, TENANT_A, dict(reversed(list(payload().items()))),
                                        "complete-and-replay", now=QUOTA_NOW)
        assert replay.id == reservation.id and json.loads(replay.result_json) == result
        with pytest.raises(HTTPException) as failure:
            reserve_gym_generation(db, TENANT_A, payload(2), "complete-and-replay", now=QUOTA_NOW)
        assert failure.value.status_code == 409 and failure.value.detail["code"] == "idempotency_conflict"
        db.rollback()
        assert db.query(GymGenerationReservation).count() == 1
        assert db.query(PlanGenerado).count() == 1


@pytest.mark.parametrize("changed", [False, True])
def test_pending_request_cannot_create_another_reservation(gym_case, changed):
    from fastapi import HTTPException
    from web.database.models import GymGenerationReservation
    from web.services.gym_generation_quota import reserve_gym_generation

    with app_session(gym_case) as db:
        reserve_gym_generation(db, TENANT_A, payload(), "pending-review", now=QUOTA_NOW)
        with pytest.raises(HTTPException) as failure:
            reserve_gym_generation(db, TENANT_A, payload(2) if changed else payload(), "pending-review", now=QUOTA_NOW)
        assert failure.value.status_code == 409
        assert failure.value.detail["code"] == ("idempotency_conflict" if changed else "generation_in_progress")
        db.rollback()
        assert db.query(GymGenerationReservation).count() == 1


def test_failure_without_persisted_plan_releases_once_and_new_key_can_retry(gym_case):
    from web.database.models import GymGenerationReservation
    from web.services.gym_generation_quota import reserve_gym_generation, fail_gym_generation

    with app_session(gym_case) as db:
        first = reserve_gym_generation(db, TENANT_A, payload(), "released-review", now=QUOTA_NOW)
        fail_gym_generation(db, TENANT_A, first.id)
        fail_gym_generation(db, TENANT_A, first.id)
        db.refresh(first)
        assert first.status == "released" and first.persisted_at is None
        second = reserve_gym_generation(db, TENANT_A, payload(), "new-key-review", now=QUOTA_NOW)
        assert second.id != first.id and second.status == "reserved"
        assert db.query(GymGenerationReservation).filter_by(status="released").count() == 1


def _persist_then_crash(url):
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url

    validate_postgres_test_url(url)
    os.environ.pop("_METODOBASE_TEST_ROOT", None)
    os.environ["METODOBASE_TEST_DATABASE_URL"] = url
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from web.database.engine import get_engine
    from web.database.tenant_context import tenant_scope
    from web.services.gym_generation_quota import reserve_gym_generation

    with tenant_scope(TENANT_A), Session(get_engine(), expire_on_commit=False) as db:
        reservation = reserve_gym_generation(db, TENANT_A, payload(), "crash-after-persist", now=QUOTA_NOW)
        persisted_plan(db, reservation)
        os._exit(23)  # Own synthetic child: crash after the real PG commit.


def test_process_crash_after_plan_commit_cannot_refund_even_after_plan_delete(gym_case):
    from fastapi import HTTPException
    from web.database.models import GymGenerationReservation, PlanGenerado
    from web.services.gym_generation_quota import fail_gym_generation, reserve_gym_generation

    process = multiprocessing.get_context("spawn").Process(target=_persist_then_crash, args=(gym_case[1],))
    process.start()
    try:
        process.join(30)
        assert not process.is_alive() and process.exitcode == 23
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)
    with app_session(gym_case) as db:
        reservation = db.query(GymGenerationReservation).filter_by(request_key="crash-after-persist").one()
        assert reservation.plan_id is not None and reservation.persisted_at is not None
        original_plan = reservation.plan_id
        fail_gym_generation(db, TENANT_A, reservation.id)
        db.refresh(reservation)
        assert reservation.status == "reserved"
    with Session(gym_case[0]) as db:
        db.execute(delete(PlanGenerado).where(PlanGenerado.id == original_plan))
        db.commit()
    with app_session(gym_case) as db:
        reservation = db.query(GymGenerationReservation).filter_by(request_key="crash-after-persist").one()
        assert reservation.plan_id is None and reservation.persisted_at is not None
        fail_gym_generation(db, TENANT_A, reservation.id)
        db.refresh(reservation)
        assert reservation.status == "reserved"
        with pytest.raises(HTTPException) as failure:
            reserve_gym_generation(db, TENANT_A, payload(), "must-not-refund", now=QUOTA_NOW)
        assert failure.value.status_code == 403 and failure.value.detail["code"] == "daily_plan_limit"


def test_reservations_keep_local_calendar_period_across_midnight_month_boundary(gym_case):
    from datetime import datetime, timezone
    from web.services.gym_generation_quota import reserve_gym_generation

    with app_session(gym_case) as db:
        before = reserve_gym_generation(db, TENANT_A, payload(), "before-rollover",
            now=datetime(2026, 11, 1, 5, 59, 59, tzinfo=timezone.utc))
        after = reserve_gym_generation(db, TENANT_A, payload(), "after-rollover",
            now=datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc))
        assert (before.period, before.local_date.isoformat()) == ("2026-10", "2026-10-31")
        assert (after.period, after.local_date.isoformat()) == ("2026-11", "2026-11-01")
        assert before.timezone == after.timezone == "America/Mexico_City"


def test_zero_clinica_caps_allow_more_than_free_limit_for_same_client(gym_case):
    from datetime import datetime, timedelta, timezone
    from web.database.models import Subscription
    from web.services.gym_generation_quota import reserve_gym_generation

    with Session(gym_case[0]) as db:
        row = db.query(Subscription).filter_by(gym_id=TENANT_A).one()
        row.plan, row.status = "clinica", "active"
        row.current_period_end = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        db.commit()
    with app_session(gym_case) as db:
        ids = {reserve_gym_generation(db, TENANT_A, payload(), "unlimited-" + str(index), now=QUOTA_NOW).id
               for index in range(21)}
        assert len(ids) == 21
