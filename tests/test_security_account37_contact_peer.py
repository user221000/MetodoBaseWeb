"""Independent current-contact epoch and foreign-actor non-adoption checks."""
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests import account_security37_fixtures as current
from tests import account_security37_http as current_http
from tests.followup34_http import PASSWORD
from tests.test_account_security37_http import headers, provider, token_from_packet
from web.database.models import MfaCredential, RefreshToken, Usuario
from web.services import account_security as account

account37_engine = current.account37_engine
account37 = current.account37
followup_db = current_http.followup_db
account_http = current_http.account_http


@pytest.mark.parametrize("already_confirmed", [False, True])
def test_contact_aba_never_revives_proof_or_verified_evidence(account37, already_confirmed):
    case = account37
    now = datetime.now(UTC)
    packets = []
    account.issue_email(case["expected"], factory=case["factory"], now=now,
                        sender=lambda _recipient, url: packets.append(url) or True)
    token = parse_qs(urlsplit(packets[0]).fragment)["token"][0]
    if already_confirmed:
        assert account.confirm_email(token, factory=case["factory"], now=now)["email_verified"] is True
    with case["factory"]() as db:
        user = db.get(Usuario, case["user"])
        original = user.email
        user.email = uuid.uuid4().hex + "@example.invalid"
        db.commit()
        user.email = original
        db.commit()
        assert user.notification_contact_version == 2
        assert account.email_status(db, case["expected"], now=now)["email_verified"] is False
    with pytest.raises(HTTPException) as failure:
        account.confirm_email(token, factory=case["factory"], now=now)
    assert failure.value.status_code == 400
    # A fresh deliberate request and proof can confirm the current epoch.
    account.issue_email(case["expected"], factory=case["factory"], now=now + timedelta(seconds=61),
                        sender=lambda _recipient, url: packets.append(url) or True)
    fresh = parse_qs(urlsplit(packets[-1]).fragment)["token"][0]
    assert fresh != token
    assert account.confirm_email(fresh, factory=case["factory"], now=now + timedelta(seconds=62))["email_verified"] is True
    with case["factory"]() as db:
        actor = db.get(Usuario, case["user"])
        assert actor.email_verified_contact_version == actor.notification_contact_version == 2


def snapshot(case, identifier):
    with Session(case["admin"]) as db:
        actor = db.get(Usuario, identifier)
        own = (actor.email, actor.password_hash, actor.session_version, actor.role, actor.tipo, actor.team_gym_id,
               actor.activo, actor.deleted_at, actor.email_verified_at, actor.email_verified_contact_version,
               actor.email_verification_hash, actor.notification_contact_version)
        refresh = list(db.execute(select(RefreshToken.jti, RefreshToken.revoked).where(
            RefreshToken.user_id == identifier).order_by(RefreshToken.jti)))
        factor = db.get(MfaCredential, identifier)
        factor_state = None if factor is None else (factor.factor_id, factor.generation, factor.enabled_at)
        return own, refresh, factor_state


def test_bearer_b_and_contact_proof_a_change_only_a_contact_evidence(account_http, monkeypatch):
    case = account_http
    packets = provider(monkeypatch)
    response = case["raw"].post("/api/account/security/email/request", json={}, headers=headers(case))
    assert response.status_code == 200
    proof = token_from_packet(packets[0])
    with Session(case["admin"]) as db:
        foreign_email = db.get(Usuario, case["member"]).email
    login = case["raw"].post("/api/auth/login", json={"email": foreign_email, "password": PASSWORD})
    assert login.status_code == 200
    case["raw"].headers["Authorization"] = "Bearer " + login.json()["token"]
    before_b = snapshot(case, case["member"])
    before_a = snapshot(case, case["user"])
    page = case["raw"].get("/auth/verify-email?token=" + proof)
    assert page.status_code == 200 and proof not in page.text
    assert snapshot(case, case["user"]) == before_a
    confirmation = case["raw"].post("/api/account/security/email/confirm", json={"token": proof}, headers=headers(case))
    assert confirmation.status_code == 200 and confirmation.json() == {"code": "account_email_confirmed", "email_verified": True}
    assert all("mb_refresh" not in value for value in confirmation.headers.get_list("set-cookie"))
    assert snapshot(case, case["member"]) == before_b
    after_a = snapshot(case, case["user"])
    assert after_a[0][:8] == before_a[0][:8]
    assert after_a[0][8] is not None and after_a[0][9] == before_a[0][11]
    assert after_a[0][10] is None and after_a[1:] == before_a[1:]
    assert case["raw"].get("/api/auth/me").json()["id"] == case["member"]
