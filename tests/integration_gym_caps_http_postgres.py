"""B2B caps through real HTTP/JWT/RLS and processes, with synthetic compute.

Only nutrition/PDF computation is replaced. The route's quota, repository,
transactions and durable plan rows are real. Each module owns a UUID database.
"""
from datetime import datetime, timedelta, timezone
import importlib
import multiprocessing
import os
import time

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from tests.integration_postgres import owned_postgres_database, TENANT_A

QUOTA_NOW = datetime(2026, 10, 18, 18, tzinfo=timezone.utc)


class _QuotaClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return QUOTA_NOW.astimezone(tz) if tz is not None else QUOTA_NOW.replace(tzinfo=None)


def _worker(url, factory_module, action, index, barrier, output):
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url

    validate_postgres_test_url(url)
    os.environ.pop("_METODOBASE_TEST_ROOT", None)
    os.environ["METODOBASE_TEST_DATABASE_URL"] = url
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from fastapi.testclient import TestClient
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario, PlanGenerado
    from web.database import repository

    adapter = importlib.import_module("web.routes.planes" if factory_module == "web.main_web" else "api.routes.planes")
    # Freeze only the quota clock. Auth expiry, principal lookup, DB and locks
    # remain real; this also makes monthly tests valid on the first CI day.
    import web.subscription_guard as guard
    guard.datetime = _QuotaClock
    for module_name in ("web.services.quota_calendar", "web.services.gym_generation_quota"):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name != module_name:
                raise
        else:
            module.datetime = _QuotaClock

    def synthetic_compute(*args, **kwargs):
        if factory_module == "web.main_web":
            client_id, _, gym_id, *remaining = args
            # Existing SaaS signature includes tipo_plan before any reservation.
            reservation = kwargs.get("reservation_id") or (remaining[1] if len(remaining) > 1 else None)
        else:
            gym_id, client_id, _, *remaining = args
            reservation = kwargs.get("reservation_id") or (remaining[0] if remaining else None)
        time.sleep(0.4)
        with Session(get_engine()) as db:
            arguments = {"reservation_id": reservation} if reservation is not None else {}
            plan_id = repository.registrar_plan(db, gym_id, client_id,
                {"plan_json": '{"synthetic":true}', "ruta_pdf": "synthetic-quota-only.pdf"},
                return_id=True, **arguments)
            assert plan_id
            db.get(PlanGenerado, plan_id).fecha_generacion = QUOTA_NOW.replace(tzinfo=None)
            db.commit()
        return {"success": True, "plan_id": plan_id, "id_cliente": client_id,
                "nombre": "Synthetic quota client", "ruta_pdf": None}

    adapter._generar_plan_sync = synthetic_compute
    try:
        with TestClient(importlib.import_module(factory_module).create_app(), raise_server_exceptions=False) as client:
            with Session(get_engine()) as db:
                token = crear_access_token(identity_from_user(db.get(Usuario, TENANT_A), db))
            barrier.wait(30)
            headers = {"Authorization": "Bearer " + token, "Idempotency-Key": action + "-" + str(index)}
            if action == "create-client":
                payload = {"nombre": "Synthetic candidate " + str(index), "edad": 30, "peso_kg": 75,
                    "estatura_cm": 175, "grasa_corporal_pct": 20, "sexo": "M",
                    "nivel_actividad": "moderada", "objetivo": "mantenimiento"}
                response = client.post("/api/clientes", json=payload, headers=headers)
            else:
                target = 1 if action == "client-day" else index + 1
                response = client.post("/api/generar-plan", headers=headers,
                    json={"id_cliente": "qa-gym-cap-client-" + str(target),
                          "plan_numero": 1, "tipo_plan": "menu_fijo"})
            body = response.json()
            detail = body.get("detail", {}) if isinstance(body, dict) else {}
            output.put({"status": response.status_code, "success": response.status_code in {200, 201},
                        "code": detail.get("code") if isinstance(detail, dict) else None})
    except Exception as error:
        output.put({"error": type(error).__name__})
    finally:
        get_engine().dispose()


def _run(url, factory_module, action, count):
    context = multiprocessing.get_context("spawn")
    barrier, output = context.Barrier(count), context.Queue()
    workers = [context.Process(target=_worker, args=(url, factory_module, action, index, barrier, output))
               for index in range(count)]
    for worker in workers:
        worker.start()
    try:
        for worker in workers:
            worker.join(45)
            assert not worker.is_alive(), "Owned synthetic B2B worker exceeded deadline"
            assert worker.exitcode == 0
        results = [output.get(timeout=5) for _ in workers]
        assert all("error" not in item for item in results), results
        return results
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(5)
        output.close()


@pytest.fixture
def gym_case(owned_postgres_database):
    from web.database.models import Base, Cliente, PlanGenerado, Subscription

    admin, url = owned_postgres_database
    now = QUOTA_NOW.replace(tzinfo=None)
    with Session(admin) as db:
        reservations = Base.metadata.tables.get("gym_generation_reservations")
        if reservations is not None:
            db.execute(reservations.delete().where(reservations.c.gym_id == TENANT_A))
        db.execute(delete(PlanGenerado).where(PlanGenerado.gym_id == TENANT_A))
        db.execute(delete(Cliente).where(Cliente.gym_id == TENANT_A))
        subscription = db.scalars(select(Subscription).where(Subscription.gym_id == TENANT_A)).one()
        subscription.plan, subscription.status = "free", "active"
        db.commit()
        for index in range(9):
            db.add(Cliente(id_cliente="qa-gym-cap-client-" + str(index), gym_id=TENANT_A,
                nombre="Synthetic cap client " + str(index), edad=30, peso_kg=75, estatura_cm=175,
                grasa_corporal_pct=20, sexo="M", nivel_actividad="moderada", objetivo="mantenimiento",
                activo=True, fecha_registro=now - timedelta(days=1)))
        db.commit()
    return admin, url, now


@pytest.mark.parametrize("factory_module", ["web.main_web", "api.app"])
@pytest.mark.parametrize("cap", ["gym-day", "client-day"])
def test_three_processes_cannot_exceed_last_gym_or_client_daily_credit(gym_case, factory_module, cap):
    from web.database.models import PlanGenerado

    admin, url, now = gym_case
    existing = 9 if cap == "gym-day" else 0
    with Session(admin) as db:
        for _ in range(existing):
            db.add(PlanGenerado(gym_id=TENANT_A, id_cliente="qa-gym-cap-client-0", fecha_generacion=now))
        db.commit()
    results = _run(url, factory_module, cap, 3)
    assert sum(item["success"] for item in results) == 1, results
    assert all(item["status"] in {200, 402, 403} for item in results), results
    expected = "daily_plan_limit_gym" if cap == "gym-day" else "daily_plan_limit"
    assert [item["code"] for item in results if not item["success"]] == [expected, expected], results
    with Session(admin) as db:
        assert db.scalar(select(func.count()).select_from(PlanGenerado).where(PlanGenerado.gym_id == TENANT_A)) == existing + 1


@pytest.mark.parametrize("factory_module", ["web.main_web", "api.app"])
def test_two_processes_cannot_create_client_eleven_when_only_one_slot_remains(gym_case, factory_module):
    from web.database.models import Cliente

    admin, url, _ = gym_case
    results = _run(url, factory_module, "create-client", 2)
    assert sum(item["success"] for item in results) == 1, results
    assert all(item["status"] in {201, 402, 403} for item in results), results
    assert [item["code"] for item in results if not item["success"]] == ["client_limit_reached"], results
    with Session(admin) as db:
        assert db.scalar(select(func.count()).select_from(Cliente).where(Cliente.gym_id == TENANT_A, Cliente.activo.is_(True))) == 10


@pytest.mark.parametrize("factory_module", ["web.main_web", "api.app"])
def test_monthly_free_cap_blocks_new_generation_before_compute(gym_case, factory_module):
    from web.database.models import PlanGenerado

    admin, url, now = gym_case
    # Twenty plans across five earlier days do not exhaust today's daily cap.
    month_start = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    with Session(admin) as db:
        for index in range(20):
            db.add(PlanGenerado(gym_id=TENANT_A, id_cliente="qa-gym-cap-client-" + str(index % 9),
                               fecha_generacion=month_start + timedelta(days=index // 4)))
        db.commit()
    results = _run(url, factory_module, "month", 1)
    assert results[0]["status"] in {402, 403}, results
    assert results[0]["code"] == "monthly_plan_limit_gym", results
    with Session(admin) as db:
        assert db.scalar(select(func.count()).select_from(PlanGenerado).where(PlanGenerado.gym_id == TENANT_A)) == 20
