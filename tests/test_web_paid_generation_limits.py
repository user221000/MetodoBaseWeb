"""Paid SaaS limits at the durable reservation and public billing boundaries."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session


NOW = datetime(2026, 10, 18, 18, tzinfo=timezone.utc)


@pytest.fixture(params=[('standard', 25, 1), ('gym_comercial', 75, 3)])
def paid_quota_case(request, test_gym_user):
    from web.database.engine import get_engine
    from web.database.models import Cliente
    from web.services.subscription_service import activate_subscription

    plan, daily_limit, per_client_limit = request.param
    engine, owner = get_engine(), test_gym_user['id']
    clients = [f'paid-quota-{index}' for index in range(daily_limit)]
    with Session(engine) as db:
        activate_subscription(db, owner, plan, provider='mercadopago',
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30))
        db.add_all(Cliente(id_cliente=client, gym_id=owner, nombre='Synthetic client')
            for client in clients)
        db.commit()
    return SimpleNamespace(engine=engine, owner=owner, plan=plan, clients=clients,
                           daily_limit=daily_limit, per_client_limit=per_client_limit,
                           user=test_gym_user)


def payload(client):
    return {'id_cliente': client, 'plan_numero': 1, 'tipo_plan': 'menu_fijo'}


def test_paid_daily_boundary_counts_historical_plans_and_pending_reservations(paid_quota_case):
    from web.database.models import GymGenerationReservation, PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation

    case = paid_quota_case
    with Session(case.engine) as db:
        db.add_all(PlanGenerado(gym_id=case.owner, id_cliente=client,
            fecha_generacion=NOW.replace(tzinfo=None)) for client in case.clients[:-1])
        db.commit()
        final = reserve_gym_generation(db, case.owner, payload(case.clients[-1]), 'last-allowed', now=NOW)
        assert final.status == 'reserved' and final.catalog_plan == case.plan
        assert db.query(PlanGenerado).filter_by(gym_id=case.owner).count() == case.daily_limit - 1
        assert db.query(GymGenerationReservation).filter_by(gym_id=case.owner).count() == 1
        with pytest.raises(HTTPException) as exhausted:
            reserve_gym_generation(db, case.owner, payload(case.clients[0]), 'over-daily', now=NOW)
        assert exhausted.value.status_code == 403
        assert exhausted.value.detail['code'] == 'daily_plan_limit_gym'
        assert exhausted.value.detail['current'] == exhausted.value.detail['limit'] == case.daily_limit


def test_paid_per_client_cap_still_counts_pending_work(paid_quota_case):
    from web.services.gym_generation_quota import reserve_gym_generation

    case = paid_quota_case
    with Session(case.engine) as db:
        for index in range(case.per_client_limit):
            reserve_gym_generation(db, case.owner, payload(case.clients[0]), f'client-{index}', now=NOW)
        with pytest.raises(HTTPException) as exhausted:
            reserve_gym_generation(db, case.owner, payload(case.clients[0]), 'client-over', now=NOW)
        assert exhausted.value.detail['code'] == 'daily_plan_limit'
        assert exhausted.value.detail['limit'] == case.per_client_limit
        assert exhausted.value.detail['current'] == case.per_client_limit


def test_legacy_daily_guard_reads_the_same_paid_total(paid_quota_case):
    from web.database.models import PlanGenerado
    from web.subscription_guard import check_daily_plan_limit

    case = paid_quota_case
    stamp = datetime.now(timezone.utc).replace(tzinfo=None)
    with Session(case.engine) as db:
        db.add_all(PlanGenerado(gym_id=case.owner, id_cliente=client, fecha_generacion=stamp)
                   for client in case.clients[:-1])
        db.commit()
        check_daily_plan_limit(db, case.owner, case.clients[-1], case.plan)
        db.add(PlanGenerado(gym_id=case.owner, id_cliente=case.clients[-1], fecha_generacion=stamp))
        db.commit()
        with pytest.raises(HTTPException) as exhausted:
            check_daily_plan_limit(db, case.owner, case.clients[0], case.plan)
        assert exhausted.value.detail['code'] == 'daily_plan_limit_gym'
        assert exhausted.value.detail['current'] == exhausted.value.detail['limit'] == case.daily_limit


def test_upgrade_accepts_more_work_without_erasing_free_usage(paid_quota_case):
    from web.database.models import GymGenerationReservation, Subscription
    from web.services.gym_generation_quota import _usage, reserve_gym_generation
    from web.services.quota_calendar import quota_calendar
    from web.services.subscription_service import activate_subscription

    case = paid_quota_case
    with Session(case.engine) as db:
        db.query(Subscription).filter_by(gym_id=case.owner).update({'plan': 'free'})
        db.commit()
        first = [reserve_gym_generation(db, case.owner, payload(client), f'free-{index}', now=NOW).id
                 for index, client in enumerate(case.clients[:10])]
        assert _usage(db, case.owner, quota_calendar(NOW)) == 10
        with pytest.raises(HTTPException) as exhausted:
            reserve_gym_generation(db, case.owner, payload(case.clients[10]), 'free-over', now=NOW)
        assert exhausted.value.detail['limit'] == 10
        db.rollback()
        activate_subscription(db, case.owner, case.plan, provider='mercadopago',
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30))
        db.commit()
        reserve_gym_generation(db, case.owner, payload(case.clients[10]), 'paid-next', now=NOW)
        assert _usage(db, case.owner, quota_calendar(NOW)) == 11
        assert _usage(db, case.owner, quota_calendar(NOW), monthly=True) == 11
        rows = db.query(GymGenerationReservation).filter(GymGenerationReservation.id.in_(first)).all()
        assert len(rows) == 10 and all(row.catalog_plan == 'free' and row.status == 'reserved' for row in rows)


def test_standard_monthly_hundredth_reservation_remains_available_then_blocks(test_gym_user):
    from web.database.engine import get_engine
    from web.database.models import Cliente, PlanGenerado
    from web.services.gym_generation_quota import reserve_gym_generation
    from web.services.subscription_service import activate_subscription

    owner = test_gym_user['id']
    with Session(get_engine()) as db:
        activate_subscription(db, owner, 'standard', provider='mercadopago',
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30))
        db.add_all([Cliente(id_cliente='monthly-old', gym_id=owner, nombre='Synthetic old'),
                    Cliente(id_cliente='monthly-next', gym_id=owner, nombre='Synthetic next'),
                    Cliente(id_cliente='monthly-over', gym_id=owner, nombre='Synthetic over')])
        db.add_all(PlanGenerado(gym_id=owner, id_cliente='monthly-old',
            fecha_generacion=(NOW - timedelta(days=2)).replace(tzinfo=None)) for _ in range(99))
        db.commit()
        assert reserve_gym_generation(db, owner, payload('monthly-next'), 'hundredth', now=NOW).status == 'reserved'
        with pytest.raises(HTTPException) as exhausted:
            reserve_gym_generation(db, owner, payload('monthly-over'), 'hundred-first', now=NOW)
        assert exhausted.value.detail['code'] == 'monthly_plan_limit_gym'
        assert exhausted.value.detail['current'] == exhausted.value.detail['limit'] == 100


def test_billing_config_exposes_paid_daily_totals_without_price_change(paid_quota_case):
    from fastapi.testclient import TestClient
    from web.main_web import create_app

    case = paid_quota_case
    with TestClient(create_app(), headers=case.user['auth_headers']) as client:
        response = client.get('/api/billing/config')
    assert response.status_code == 200
    plans = response.json()['plans']
    assert plans[case.plan]['max_planes_diarios'] == case.daily_limit
    assert plans[case.plan]['precio_mxn'] == (159 if case.plan == 'standard' else 479)


def test_web_catalog_tiers_are_progressive_and_free_personal_limits_are_preserved():
    from core.plan_catalog import get_individual_plan_catalog, get_plan_catalog
    from web.constants import PLANES_LICENCIA

    catalog = get_plan_catalog('web')
    assert [catalog[key]['max_planes_diarios'] for key in ('free', 'standard', 'gym_comercial')] == [10, 25, 75]
    assert catalog['clinica']['max_planes_diarios'] == 0
    assert catalog['free']['max_planes_mes'] == 20
    assert catalog['free']['max_planes_por_cliente_dia'] == 1
    assert catalog['standard']['max_planes_mes'] == 100
    assert catalog['gym_comercial']['max_planes_mes'] == 0
    assert get_individual_plan_catalog()['starter']['max_planes_mes'] == 1
    assert get_individual_plan_catalog()['pro']['max_planes_mes'] == 5
    assert PLANES_LICENCIA['standard']['max_planes_diarios'] == 25
    assert PLANES_LICENCIA['gym_comercial']['max_planes_diarios'] == 75
    catalog['standard']['max_planes_diarios'] = 999
    assert get_plan_catalog('web')['standard']['max_planes_diarios'] == 25
