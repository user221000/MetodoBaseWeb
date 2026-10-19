"""Factor lifecycle keeps primary freshness, session invalidation and kit use."""
import base64
from datetime import timedelta

from tests.test_mfa31_http import mfa_client, enroll, authenticate


def test_regenerate_requires_primary_plus_factor_and_revokes_old_session_and_kit(mfa_client):
    client, actor, clock = mfa_client
    from web.auth import verificar_token
    from web.services.mfa_crypto import totp
    started, first = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=first["recovery_codes"][0])
    primary = client.post("/api/auth/mfa/reauth", json={"password": "test123"}).json()["reauthentication_token"]
    missing = client.post("/api/auth/mfa/recovery-codes/regenerate", json={"reauthentication_token": primary})
    assert missing.status_code == 422
    regenerated = client.post("/api/auth/mfa/recovery-codes/regenerate", json={"reauthentication_token": primary,
        "recovery_code": first["recovery_codes"][1]})
    assert regenerated.status_code == 200 and regenerated.json()["reauthenticate"] is True
    assert set(regenerated.json()["recovery_codes"]).isdisjoint(first["recovery_codes"])
    assert verificar_token(pair["token"]) is None
    primary_login = client.post("/api/auth/login", json={"email":actor["email"],"password":"test123"})
    assert primary_login.status_code == 202
    bad = client.post("/api/auth/mfa/login/verify", json={"challenge": primary_login.json()["challenge"],
        "recovery_code": first["recovery_codes"][2]})
    assert bad.status_code == 400
    authenticate(client, actor, clock, recovery=regenerated.json()["recovery_codes"][0])


def test_replace_pending_keeps_active_factor_then_confirm_changes_generation(mfa_client):
    client, actor, clock = mfa_client
    from web.auth import _decode_token, verificar_token
    from web.services.mfa_crypto import totp
    _, first = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=first["recovery_codes"][0])
    reauth = client.post("/api/auth/mfa/reauth", json={"password":"test123"}).json()["reauthentication_token"]
    denied = client.post("/api/auth/mfa/enroll", json={"reauthentication_token":reauth})
    assert denied.status_code == 422
    replacement = client.post("/api/auth/mfa/enroll", json={"reauthentication_token":reauth,
        "recovery_code":first["recovery_codes"][1]})
    assert replacement.status_code == 200
    assert client.get("/api/auth/mfa/status").json()["enabled"] is True
    assert client.post("/api/auth/mfa/enroll", json={"reauthentication_token":reauth,
        "recovery_code":first["recovery_codes"][2]}).status_code == 400
    seed = base64.b32decode(replacement.json()["secret"])
    confirmed = client.post("/api/auth/mfa/enroll/confirm", json={"enrollment_id":replacement.json()["enrollment_id"],
        "code":totp(seed,int(clock[0].timestamp())//30)})
    assert confirmed.status_code == 200
    assert verificar_token(pair["token"]) is None
    fresh, _ = authenticate(client, actor, clock, recovery=confirmed.json()["recovery_codes"][0])
    assert _decode_token(fresh["token"])["mfa_generation"] == _decode_token(pair["token"])["mfa_generation"] + 1


def test_revoke_requires_both_factors_and_leaves_privileged_mutation_blocked(mfa_client, monkeypatch):
    client, actor, clock = mfa_client
    from web.services import stripe_service
    calls = []
    monkeypatch.setattr(stripe_service,"create_portal_session",lambda **kwargs:calls.append(kwargs))
    _, first = enroll(client, clock)
    pair, _ = authenticate(client, actor, clock, recovery=first["recovery_codes"][0])
    reauth = client.post("/api/auth/mfa/reauth", json={"password":"test123"}).json()["reauthentication_token"]
    revoked = client.post("/api/auth/mfa/revoke", json={"reauthentication_token":reauth,
        "recovery_code":first["recovery_codes"][1]})
    assert revoked.status_code == 200 and revoked.json()["enabled"] is False
    login = client.post("/api/auth/login",json={"email":actor["email"],"password":"test123"})
    assert login.status_code == 200 and login.json()["mfa_required"] is False
    client.headers["Authorization"] = "Bearer " + login.json()["token"]
    denied = client.post("/api/billing/portal",json={"return_url":"/dashboard"})
    assert denied.status_code == 403 and denied.json()["detail"]["code"] == "mfa_enrollment_required"
    assert calls == []


def test_enrollment_primary_proof_is_access_bound_and_expires_without_revoking_login(mfa_client):
    client, actor, clock = mfa_client
    primary = client.post("/api/auth/mfa/reauth",json={"password":"test123"}).json()["reauthentication_token"]
    # A distinct primary access cannot inherit proof minted for the prior one.
    login = client.post("/api/auth/login",json={"email":actor["email"],"password":"test123"})
    assert login.status_code == 200
    original = client.headers["Authorization"]
    client.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert client.post("/api/auth/mfa/enroll",json={"reauthentication_token":primary}).status_code == 400
    client.headers["Authorization"] = original
    clock[0] += timedelta(seconds=300)
    assert client.post("/api/auth/mfa/enroll",json={"reauthentication_token":primary}).status_code == 400
    assert client.get("/api/auth/me").status_code == 200
