"""Terminal valid sessions retain login; factor changes cannot overflow them."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate  # noqa: F401


def password_login(client, actor, expected=200):
    # The shared fixture seeds an account. Discard its minted bearer before
    # every positive request: authority here comes from actual password HTTP.
    client.headers.pop("Authorization", None)
    result = client.post("/api/auth/login", json={"email": actor["email"], "password": "test123"})
    assert result.status_code == expected
    if expected == 200:
        client.headers["Authorization"] = "Bearer " + result.json()["token"]
    return result


def version(actor, value):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    with Session(get_engine()) as db:
        db.get(Usuario, actor["id"]).session_version = value
        db.commit()


def snapshot():
    from web.database.engine import get_engine
    from web.database.models import Usuario, MfaCredential, MfaRecoveryCode, MfaAuthorization, RefreshToken, AuthAuditLog
    with Session(get_engine()) as db:
        return {model.__tablename__: [tuple(row) for row in db.execute(
            select(model.__table__).order_by(*model.__table__.primary_key.columns)
        )] for model in [Usuario, MfaCredential, MfaRecoveryCode, MfaAuthorization, RefreshToken, AuthAuditLog]}


def at_terminal_factor(client, actor, clock):
    from web.services.mfa_service import MAX_SV
    password_login(client, actor)
    _, kit = enroll(client, clock)
    version(actor, MAX_SV)
    clock[0] += timedelta(seconds=31)
    client.headers.pop("Authorization", None)
    pair, body = authenticate(client, actor, clock, recovery=kit["recovery_codes"][0])
    return pair, body, kit


def capacity_denied(response):
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "mfa_session_version_exhausted"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert all(key not in response.json() for key in ["secret", "token", "refresh_token", "recovery_codes"])


def test_terminal_factor_still_requires_and_consumes_real_evidence(mfa_client):
    from web import auth
    from web.services.mfa_service import MAX_SV
    client, actor, clock = mfa_client
    pair, body, _ = at_terminal_factor(client, actor, clock)
    claims = auth.verificar_token(pair["token"])
    assert claims["sv"] == MAX_SV and claims["amr"] == ["pwd", "recovery"]
    assert client.get("/api/auth/me").status_code == 200
    state = client.get("/api/auth/mfa/status")
    assert state.status_code == 200 and state.json()["enabled"] is True
    assert state.json()["recovery_codes_remaining"] == 7
    assert client.post("/api/auth/mfa/login/verify", json=body).status_code == 400


def test_terminal_rotation_refuses_without_consuming_proof_factor_or_sessions(mfa_client):
    client, actor, clock = mfa_client
    _, _, kit = at_terminal_factor(client, actor, clock)
    primary = client.post("/api/auth/mfa/reauth", json={"password": "test123"})
    assert primary.status_code == 200
    before = snapshot()
    response = client.post("/api/auth/mfa/recovery-codes/regenerate", json={
        "reauthentication_token": primary.json()["reauthentication_token"],
        "recovery_code": kit["recovery_codes"][1],
    })
    capacity_denied(response)
    assert snapshot() == before


def test_terminal_enrollment_never_publishes_a_seed_or_consumes_primary_proof(mfa_client):
    from web.services.mfa_service import MAX_SV
    client, actor, _ = mfa_client
    version(actor, MAX_SV)
    password_login(client, actor)
    primary = client.post("/api/auth/mfa/reauth", json={"password": "test123"})
    assert primary.status_code == 200
    before = snapshot()
    response = client.post("/api/auth/mfa/enroll", json={
        "reauthentication_token": primary.json()["reauthentication_token"],
    })
    capacity_denied(response)
    assert snapshot() == before


def test_terminal_confirmation_retains_pending_factor_and_does_not_overflow(mfa_client):
    import base64
    from web.services.mfa_service import MAX_SV
    from web.services.mfa_crypto import totp
    client, actor, clock = mfa_client
    version(actor, MAX_SV - 1)
    password_login(client, actor)
    primary = client.post("/api/auth/mfa/reauth", json={"password": "test123"})
    assert primary.status_code == 200
    start = client.post("/api/auth/mfa/enroll", json={
        "reauthentication_token": primary.json()["reauthentication_token"],
    })
    assert start.status_code == 200
    version(actor, MAX_SV)
    password_login(client, actor)
    before = snapshot()
    response = client.post("/api/auth/mfa/enroll/confirm", json={
        "enrollment_id": start.json()["enrollment_id"],
        "code": totp(base64.b32decode(start.json()["secret"]), int(clock[0].timestamp()) // 30),
    })
    capacity_denied(response)
    assert snapshot() == before
