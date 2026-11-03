"""Known billing instants have UTC on the wire without rewriting stored values."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.parametrize("has_period", [True, False])
def test_personal_periods_are_explicit_utc_and_keep_storage_unchanged(
    test_gym_user, has_period,
):
    from web.auth import crear_access_token
    from web.database.engine import get_engine
    from web.database.models import Subscription, UserRole, UserSubscription, Usuario
    from web.services.billing_integrity import current_quota_period

    start = datetime(2030, 11, 3, 2, 12, 57) if has_period else None
    end = datetime(2030, 12, 3, 2, 12, 57) if has_period else None
    actor = {**test_gym_user, "tipo": "usuario", "role": "viewer"}
    with Session(get_engine()) as db:
        user = db.get(Usuario, actor["id"])
        user.tipo = "usuario"
        user.role = UserRole.VIEWER
        db.add(Subscription(
            gym_id=actor["id"], plan="pro_usuario", status="active", provider="stripe",
            current_period_start=start, current_period_end=end,
        ))
        db.add(UserSubscription(
            user_id=actor["id"], plan="pro", status="active", max_planes_mes=5,
            planes_usados_mes=1, mes_actual=current_quota_period(),
        ))
        db.commit()
        stored = db.query(Subscription).filter_by(gym_id=actor["id"]).one()
        assert (stored.current_period_start, stored.current_period_end) == (start, end)
        assert stored.current_period_end is None or stored.current_period_end.tzinfo is None

    from web.main_web import create_app
    token = crear_access_token(actor)
    with TestClient(create_app(), headers={"Authorization": "Bearer " + token}) as client:
        response = client.get("/api/usuario/suscripcion")
    assert response.status_code == 200
    body = response.json()
    assert body["planes_usados"] == 1
    for key, original in (("period_start", start), ("period_end", end)):
        if original is None:
            assert body[key] is None
        else:
            instant = datetime.fromisoformat(body[key])
            assert instant.tzinfo is not None
            assert instant.utcoffset() == timedelta(0)
            assert instant.replace(tzinfo=None) == original
    if has_period:
        local_end = datetime.fromisoformat(body["period_end"]).astimezone(
            ZoneInfo("America/Mexico_City"),
        )
        assert local_end.date() == date(2030, 12, 2)
    with Session(get_engine()) as db:
        stored = db.query(Subscription).filter_by(gym_id=actor["id"]).one()
        assert (stored.current_period_start, stored.current_period_end) == (start, end)
