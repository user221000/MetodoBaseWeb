"""Commercial catalog and persisted entitlement boundary acceptance."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException


@pytest.mark.parametrize("count", [9, 10, 11])
def test_free_client_boundary_uses_real_rows_and_preserves_existing_clients(test_gym_user, count):
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import Cliente
    from web.services.feature_gate import FeatureGate
    with Session(get_engine()) as db:
        db.add_all([Cliente(id_cliente=f"catalog-client-{i}", gym_id=test_gym_user["id"], nombre=f"Synthetic {i}", activo=True)
            for i in range(count)])
        db.commit()
        gate = FeatureGate(db, test_gym_user["id"])
        assert gate.features.max_clientes == 10
        assert gate.get_client_count() == count
        if count < 10:
            gate.check_can_create_client()
        else:
            with pytest.raises(HTTPException) as error:
                gate.check_can_create_client()
            assert error.value.status_code == 402
        assert db.query(Cliente).count() == count


@pytest.mark.parametrize("status,days", [("past_due", 5), ("canceled", 5), ("active", -1), ("trialing", -1)])
def test_inactive_or_expired_paid_row_cannot_grant_features(test_gym_user, status, days):
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import Subscription
    from web.services.feature_gate import FeatureGate
    with Session(get_engine()) as db:
        db.add(Subscription(gym_id=test_gym_user["id"], plan="clinica", status=status,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=days),
            trial_end=datetime.now(timezone.utc) + timedelta(days=days), max_clientes=999999))
        db.commit()
        gate = FeatureGate(db, test_gym_user["id"])
        assert gate.plan == "free"
        assert not gate.features.can_multi_user
        assert gate.features.max_clientes == 10


def test_catalog_copies_keep_personal_monthly_limits_separate_from_gym_daily_limits():
    from core.plan_catalog import get_plan_catalog, get_individual_plan_catalog
    web = get_plan_catalog("web")
    desktop = get_plan_catalog("desktop")
    individual = get_individual_plan_catalog()
    assert web["free"]["max_clientes"] == desktop["free"]["max_clientes"] == 10
    assert web["free"]["max_planes_por_cliente_dia"] == desktop["free"]["max_planes_por_cliente_dia"] == 1
    assert web["free"]["max_planes_diarios"] == desktop["free"]["max_planes_diarios"] == 10
    assert "pro_usuario" not in desktop
    assert individual["pro"]["max_planes_mes"] == 5
    assert individual["starter"]["max_planes_mes"] == 1
    for name in desktop:
        assert desktop[name]["precio_centavos"] == web[name]["precio_mxn"] * 100
        assert desktop[name]["moneda"] == "MXN"
    web["free"]["max_clientes"] = 999
    web["free"]["features"].clear()
    assert get_plan_catalog("web")["free"]["max_clientes"] == 10
    assert get_plan_catalog("web")["free"]["features"]
