"""Canonical parent required again under account locks, at issue and consumption.

Ambiguous parent rows are deliberately synthetic historical DB states. No
legitimate API is claimed to create them; no business invitation/mail is sent.
"""
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate


@pytest.mark.parametrize("actor_role", ["owner", "admin"])
@pytest.mark.parametrize("pending_token", [None, "", "A" * 64])
def test_action_authorizer_uses_the_canonical_owner_predicate(test_gym_user, actor_role, pending_token):
    from web.auth import identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    from web.services.client_link_context import canonical_gym
    from web.services.mfa_actions import authorize

    with Session(get_engine()) as db:
        parent = db.get(Usuario, test_gym_user["id"])
        actor = parent
        if actor_role == "admin":
            identity = str(uuid.uuid4())
            actor = Usuario(id=identity, email=identity + "@example.invalid", nombre="Synthetic admin",
                password_hash=parent.password_hash, tipo="usuario", role=UserRole.ADMIN,
                team_gym_id=parent.id, activo=True, session_version=0)
            db.add(actor)
            db.commit()
        expected = identity_from_user(actor, db)
        # SQLite's write lock is the account-lock analogue used by the service.
        for identity in sorted({parent.id, actor.id}):
            db.execute(update(Usuario).where(Usuario.id == identity).values(id=Usuario.id))
        parent.invitation_token = pending_token
        db.flush()
        assert canonical_gym(parent) is (pending_token is None)
        if pending_token is None:
            assert authorize(db, expected, "team.invite", None) == parent.id
        else:
            with pytest.raises(HTTPException) as rejected:
                authorize(db, expected, "team.invite", None)
            assert rejected.value.status_code == 403
            assert rejected.value.detail["code"] == "mfa_action_forbidden"


@pytest.mark.parametrize("pending_token", ["", "A" * 64])
@pytest.mark.parametrize("mfa_client", ["web.main_web"], indirect=True)
def test_pending_parent_blocks_preissued_grant_without_consuming_it(mfa_client, monkeypatch, pending_token):
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole, MfaAuthorization
    from web.services.mfa_crypto import opaque_digest
    from web.services import team_invitation_service

    client, owner, clock = mfa_client
    assert "/api/gym/team/invite" in client.app.openapi()["paths"]
    identity = str(uuid.uuid4())
    with Session(get_engine()) as db:
        parent = db.get(Usuario, owner["id"])
        admin = Usuario(id=identity, email=identity + "@example.invalid", nombre="Synthetic admin",
            password_hash=parent.password_hash, tipo="usuario", role=UserRole.ADMIN,
            team_gym_id=parent.id, activo=True, session_version=0)
        db.add(admin)
        db.commit()
        bearer = crear_access_token(identity_from_user(admin, db))
        actor = {"id": admin.id, "email": admin.email}
    client.headers["Authorization"] = "Bearer " + bearer
    _, kit = enroll(client, clock)
    authenticate(client, actor, clock, recovery=kit["recovery_codes"][0])
    body = {"email": "synthetic-invite@example.invalid", "nombre": "Synthetic invite", "role": "viewer"}
    issued = client.post("/api/auth/mfa/step-up", json={"method": "POST",
        "path": "/api/gym/team/invite", "body": body})
    assert issued.status_code == 200
    grant = issued.json()["grant"]
    grant_hash = opaque_digest("action", grant)
    with Session(get_engine()) as db:
        count = db.scalar(select(func.count()).select_from(Usuario))
        assert db.get(MfaAuthorization, grant_hash).consumed_at is None
        parent = db.get(Usuario, owner["id"])
        parent.invitation_token = pending_token
        db.commit()
    business_calls = []

    def forbidden(*args, **kwargs):
        business_calls.append(True)
        raise AssertionError("A noncanonical parent cannot reach the invitation business port")

    monkeypatch.setattr(team_invitation_service, "issue", forbidden)
    response = client.post("/api/gym/team/invite", json=body, headers={"X-MFA-Grant": grant})
    assert response.status_code in {401, 403}
    assert response.json()["detail"]["code"] in {"mfa_identity_unavailable", "mfa_action_forbidden"}
    assert "grant" not in response.json() and business_calls == []
    with Session(get_engine()) as db:
        assert db.get(MfaAuthorization, grant_hash).consumed_at is None
        assert db.scalar(select(func.count()).select_from(Usuario)) == count


@pytest.mark.parametrize("actor_role", ["owner", "admin"])
def test_actor_empty_invitation_is_not_a_canonical_authenticated_context(mfa_client, actor_role):
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    from web.services.client_link_context import valid_actor

    client, owner, clock = mfa_client
    actor = owner
    if actor_role == "admin":
        identity = str(uuid.uuid4())
        with Session(get_engine()) as db:
            parent = db.get(Usuario, owner["id"])
            admin = Usuario(id=identity, email=identity + "@example.invalid", nombre="Synthetic admin",
                password_hash=parent.password_hash, tipo="usuario", role=UserRole.ADMIN,
                team_gym_id=parent.id, activo=True, session_version=0)
            db.add(admin)
            db.commit()
            client.headers["Authorization"] = "Bearer " + crear_access_token(identity_from_user(admin, db))
            actor = {"id": admin.id, "email": admin.email}
    _, kit = enroll(client, clock)
    authenticate(client, actor, clock, recovery=kit["recovery_codes"][0])
    action = {"method": "POST", "path": "/api/gym/team/invite",
        "body": {"email": "synthetic-next@example.invalid", "nombre": "Synthetic invite", "role": "viewer"}}
    allowed = client.post("/api/auth/mfa/step-up", json=action)
    assert allowed.status_code == 200
    with Session(get_engine()) as db:
        row = db.get(Usuario, actor["id"])
        row.invitation_token = ""
        db.commit()
        parent = db.get(Usuario, row.team_gym_id) if row.team_gym_id else None
        assert not valid_actor(row, parent)
    denied = client.post("/api/auth/mfa/step-up", json=action)
    status = client.get("/api/auth/mfa/status")
    assert denied.status_code in {401, 403}
    assert "grant" not in denied.json()
    assert status.status_code == 401
