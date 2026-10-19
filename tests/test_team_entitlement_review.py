"""Independent R11 contract: new memberships need persisted multi-user rights.

This tests the existing catalog boolean; it introduces no team/device maximum.
The real web factory, JWT verifier and database run without auth overrides.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session


def entitlement(owner, *, plan="clinica", status="active", expired=False):
    from web.database.engine import get_engine
    from web.database.models import Subscription

    now = datetime.now(timezone.utc)
    with Session(get_engine()) as db:
        row = db.execute(select(Subscription).where(Subscription.gym_id == owner["id"])).scalar_one_or_none()
        if row is None:
            row = Subscription(gym_id=owner["id"], plan=plan)
            db.add(row)
        row.plan, row.status, row.provider = plan, status, "stripe"
        row.current_period_start = now - timedelta(days=1)
        row.current_period_end = now + timedelta(days=-1 if expired else 29)
        db.commit()


def invitation(client):
    return client.post("/api/gym/team/invite", json={"email": "entitlement-professional@example.invalid",
        "nombre": "Synthetic Professional", "role": "nutriologo"})


@pytest.mark.parametrize("plan", ["free", "standard", "gym_comercial"])
def test_catalog_without_multi_user_rejects_new_invitation(web_auth_client, test_gym_user, plan):
    from core.plan_catalog import get_plan_catalog
    from web.database.engine import get_engine
    from web.database.models import Usuario

    assert get_plan_catalog("web")[plan]["multi_usuario"] is False
    entitlement(test_gym_user, plan=plan)
    response = invitation(web_auth_client)
    assert response.status_code == 402
    with Session(get_engine()) as db:
        assert db.execute(select(Usuario).where(Usuario.team_gym_id == test_gym_user["id"])).first() is None


@pytest.mark.parametrize("lost", ["free", "gym_comercial", "past_due", "expired"])
def test_invitation_cannot_be_consumed_after_persisted_rights_are_lost(web_auth_client, test_gym_user, lost):
    from web.database.engine import get_engine
    from web.database.models import Usuario

    entitlement(test_gym_user)
    offered = invitation(web_auth_client)
    assert offered.status_code == 200, offered.text
    token = offered.json()["invitation_token"]
    entitlement(test_gym_user, plan=lost if lost in {"free", "gym_comercial"} else "clinica",
                status="past_due" if lost == "past_due" else "active", expired=lost == "expired")
    response = web_auth_client.post("/api/auth/accept-invite", json={
        "token": token, "password": "Synthetic-Entitlement-Password-2026!"})
    assert response.status_code == 402
    with Session(get_engine()) as db:
        member = db.execute(select(Usuario).where(Usuario.team_gym_id == test_gym_user["id"])).scalar_one()
        assert member.activo is False and member.invitation_token is not None


def test_active_clinica_can_create_and_consume_new_membership(web_auth_client, test_gym_user):
    from web.auth import verificar_token

    entitlement(test_gym_user)
    offered = invitation(web_auth_client)
    assert offered.status_code == 200, offered.text
    accepted = web_auth_client.post("/api/auth/accept-invite", json={
        "token": offered.json()["invitation_token"], "password": "Synthetic-Entitlement-Password-2026!"})
    assert accepted.status_code == 200, accepted.text
    identity = verificar_token(accepted.json()["access_token"])
    assert identity["team_gym_id"] == test_gym_user["id"] and identity["role"] == "nutriologo"
