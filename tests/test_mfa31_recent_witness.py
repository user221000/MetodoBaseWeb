"""A recent verification is bounded to its original factor time and access."""
import base64
from datetime import timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate

ACTION = {"method": "POST", "path": "/api/billing/portal", "body": {"return_url": "/dashboard"}}


def access_with_claims(token, **changes):
    from web.auth import _decode_token, _make_token
    return _make_token({**_decode_token(token), **changes})


def test_durable_recent_witness_does_not_slide_with_grants_reads_or_refresh(mfa_client):
    client, actor, clock = mfa_client
    from web.auth import _decode_token
    from web.database.engine import get_engine
    from web.database.models import MfaAuthorization
    _, done = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=done["recovery_codes"][0])
    clock[0] += timedelta(seconds=301)
    # An old MFA session requires a NEW, unused factor. No OTP is replayed.
    stale = client.post("/api/auth/mfa/step-up", json=ACTION)
    assert stale.status_code == 403
    verified_at = clock[0]
    first = client.post("/api/auth/mfa/step-up", json={**ACTION, "recovery_code": done["recovery_codes"][1]})
    assert first.status_code == 200, first.text
    expiry = first.json()["expires_at"]
    clock[0] += timedelta(seconds=240)
    assert client.get("/api/auth/mfa/status").status_code == 200
    second = client.post("/api/auth/mfa/step-up", json=ACTION)
    assert second.status_code == 200 and second.json()["expires_at"] == expiry
    with Session(get_engine()) as db:
        witnesses = db.scalars(select(MfaAuthorization.factor_verified_at).where(MfaAuthorization.purpose == "action")).all()
        assert len(witnesses) == 2 and all(value.replace(tzinfo=verified_at.tzinfo) == verified_at for value in witnesses)
    # Refresh preserves login MFA time, and cannot copy an access-bound later
    # verification to the new access token.
    refresh = client.post("/api/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert refresh.status_code == 200
    assert _decode_token(refresh.json()["token"])["mfa_at"] == _decode_token(pair["token"])["mfa_at"]
    client.headers["Authorization"] = "Bearer " + refresh.json()["token"]
    assert client.post("/api/auth/mfa/step-up", json=ACTION).status_code == 403
    client.headers["Authorization"] = "Bearer " + pair["token"]
    clock[0] = verified_at + timedelta(seconds=300)
    assert client.post("/api/auth/mfa/step-up", json=ACTION).status_code == 403


@pytest.mark.parametrize("change", ["future", "boolean", "string", "generation", "sv", "aud", "purpose"])
def test_recent_witness_rejects_wrong_signed_context_and_timestamp(mfa_client, change):
    client, actor, clock = mfa_client
    from web.auth import _decode_token
    _, done = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=done["recovery_codes"][0])
    claims = _decode_token(pair["token"])
    values = {"future": {"mfa_at": clock[0].timestamp() + 1}, "boolean": {"mfa_at": True},
        "string": {"mfa_at": str(clock[0].timestamp())}, "generation": {"mfa_generation": claims["mfa_generation"] + 1},
        "sv": {"sv": claims["sv"] + 1}, "aud": {"aud": "foreign"}, "purpose": {"type": "refresh"}}
    client.headers["Authorization"] = "Bearer " + access_with_claims(pair["token"], **values[change])
    assert client.post("/api/auth/mfa/step-up", json=ACTION).status_code in (401, 403)


def test_durable_witness_future_is_not_a_current_verification(mfa_client):
    client, actor, clock = mfa_client
    from web.database.engine import get_engine
    from web.database.models import MfaAuthorization
    _, done = enroll(client, clock)
    authenticate(client, actor, clock, recovery=done["recovery_codes"][0])
    clock[0] += timedelta(seconds=301)
    grant = client.post("/api/auth/mfa/step-up", json={**ACTION, "recovery_code": done["recovery_codes"][1]})
    assert grant.status_code == 200
    # Simulate a clock that went backwards; the existing immutable fact is
    # future evidence, not permission to authenticate before it happened.
    clock[0] -= timedelta(seconds=1)
    assert client.post("/api/auth/mfa/step-up", json=ACTION).status_code == 403


def test_grant_expires_at_access_expiry_even_with_more_recent_factor(mfa_client):
    client, actor, clock = mfa_client
    from datetime import datetime, timezone
    _, done = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=done["recovery_codes"][0])
    expires = clock[0].timestamp() + 45
    client.headers["Authorization"] = "Bearer " + access_with_claims(pair["token"], exp=expires)
    issued = client.post("/api/auth/mfa/step-up", json=ACTION)
    assert issued.status_code == 200
    assert datetime.fromisoformat(issued.json()["expires_at"].replace("Z", "+00:00")) == datetime.fromtimestamp(expires, timezone.utc)
