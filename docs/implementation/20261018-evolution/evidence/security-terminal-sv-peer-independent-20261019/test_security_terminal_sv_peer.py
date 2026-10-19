"""Independent SEC15 canaries; SQL states are synthetic, requests authenticate over HTTP."""
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate  # noqa: F401
from tests.test_mfa31_terminal_session_version import password_login, version, snapshot


@pytest.mark.parametrize("bad", [True, False, -1, 2147483648, None, 1.0, "1"])
def test_identity_and_capacity_do_not_coerce_invalid_versions(test_gym_user, bad):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services import mfa_service as service
    with Session(get_engine(), autoflush=False) as db:
        actor = db.get(Usuario, test_gym_user["id"])
        actor.session_version = bad
        with pytest.raises(HTTPException) as identity:
            service.current_identity(db, actor)
        assert identity.value.status_code == 401
        with pytest.raises(HTTPException) as capacity:
            service._require_session_capacity(actor)
        assert capacity.value.status_code == 409
        assert actor.session_version is bad


@pytest.mark.parametrize("field,value", [
    ("activo", False), ("deleted_at", datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ("invitation_token", ""), ("invitation_token", "synthetic-pending"),
])
def test_terminal_identity_retains_eligibility_guards(test_gym_user, field, value):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services import mfa_service as service
    with Session(get_engine(), autoflush=False) as db:
        actor = db.get(Usuario, test_gym_user["id"])
        actor.session_version = service.MAX_SV
        setattr(actor, field, value)
        with pytest.raises(HTTPException) as denied:
            service.current_identity(db, actor)
        assert denied.value.status_code == 401


@pytest.mark.parametrize("state", ["null", "empty", "pending", "inactive", "nonowner", "nested"])
def test_terminal_team_identity_requires_canonical_parent(test_gym_user, state):
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    from web.services import mfa_service as service
    with Session(get_engine()) as db:
        parent = db.get(Usuario, test_gym_user["id"])
        actor = Usuario(id=str(uuid.uuid4()), email=str(uuid.uuid4()) + "@example.invalid",
            nombre="Synthetic peer admin", apellido="", tipo="usuario", role=UserRole.ADMIN,
            team_gym_id=parent.id, password_hash=parent.password_hash, activo=True,
            session_version=service.MAX_SV)
        db.add(actor)
        if state == "empty": parent.invitation_token = ""
        if state == "pending": parent.invitation_token = "synthetic-pending"
        if state == "inactive": parent.activo = False
        if state == "nonowner": parent.role = UserRole.ADMIN
        if state == "nested": parent.team_gym_id = parent.id
        db.flush()
        if state == "null":
            assert service.current_identity(db, actor)["session_version"] == service.MAX_SV
        else:
            with pytest.raises(HTTPException) as denied:
                service.current_identity(db, actor)
            assert denied.value.status_code == 401


def terminal_login(client, actor, clock):
    from web.services.mfa_service import MAX_SV
    password_login(client, actor)
    _, kit = enroll(client, clock)
    version(actor, MAX_SV)
    clock[0] += timedelta(seconds=31)
    client.headers.pop("Authorization", None)
    pair, _ = authenticate(client, actor, clock, recovery=kit["recovery_codes"][0])
    return pair, kit


@pytest.mark.parametrize("path", ["/api/auth/mfa/revoke", "/api/auth/mfa/enroll"])
def test_terminal_revoke_and_replacement_cannot_consume_existing_factor(mfa_client, path):
    client, actor, clock = mfa_client
    _, kit = terminal_login(client, actor, clock)
    primary = client.post("/api/auth/mfa/reauth", json={"password": "test123"})
    assert primary.status_code == 200
    before = snapshot()
    result = client.post(path, json={"reauthentication_token": primary.json()["reauthentication_token"],
        "recovery_code": kit["recovery_codes"][1]})
    assert result.status_code == 409
    assert result.json()["detail"]["code"] == "mfa_session_version_exhausted"
    assert result.headers["Cache-Control"] == "no-store"
    assert snapshot() == before


def test_last_available_increment_confirms_and_still_challenges_next_login(mfa_client):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services.mfa_service import MAX_SV
    client, actor, clock = mfa_client
    version(actor, MAX_SV - 1)
    password_login(client, actor)
    _, kit = enroll(client, clock)
    with Session(get_engine()) as db:
        assert db.get(Usuario, actor["id"]).session_version == MAX_SV
    assert client.get("/api/auth/mfa/status").status_code == 401
    client.headers.pop("Authorization", None)
    pair, _ = authenticate(client, actor, clock, recovery=kit["recovery_codes"][0])
    from web.auth import verificar_token
    assert verificar_token(pair["token"])["sv"] == MAX_SV
    assert client.get("/api/auth/mfa/status").json()["enabled"] is True


def test_last_available_regeneration_revokes_old_sessions_without_wrap(mfa_client):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services.mfa_service import MAX_SV
    from web.auth import verificar_token, verificar_refresh_token
    client, actor, clock = mfa_client
    password_login(client, actor)
    _, kit = enroll(client, clock)
    version(actor, MAX_SV - 1)
    pair, _ = authenticate(client, actor, clock, recovery=kit["recovery_codes"][0])
    primary = client.post("/api/auth/mfa/reauth", json={"password": "test123"})
    assert primary.status_code == 200
    result = client.post("/api/auth/mfa/recovery-codes/regenerate", json={
        "reauthentication_token": primary.json()["reauthentication_token"],
        "recovery_code": kit["recovery_codes"][1]})
    assert result.status_code == 200
    assert len(result.json()["recovery_codes"]) == 8
    with Session(get_engine()) as db:
        assert db.get(Usuario, actor["id"]).session_version == MAX_SV
    assert verificar_token(pair["token"]) is None
    assert verificar_refresh_token(pair["refresh_token"]) is None
    client.headers.pop("Authorization", None)
    authenticate(client, actor, clock, recovery=result.json()["recovery_codes"][0])


def test_pre_terminal_challenge_stays_stale_and_does_not_consume_recovery(mfa_client):
    from web.services.mfa_service import MAX_SV
    client, actor, clock = mfa_client
    password_login(client, actor)
    _, kit = enroll(client, clock)
    version(actor, MAX_SV - 1)
    client.headers.pop("Authorization", None)
    primary = client.post("/api/auth/login", json={"email": actor["email"], "password": "test123"})
    assert primary.status_code == 202
    version(actor, MAX_SV)
    before = snapshot()
    denied = client.post("/api/auth/mfa/login/verify", json={"challenge": primary.json()["challenge"],
        "recovery_code": kit["recovery_codes"][0]})
    assert denied.status_code == 401
    assert snapshot() == before

