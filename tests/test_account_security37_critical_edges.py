"""Additional current37 concurrent consume, terminal SV and linked Google use."""
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests import account_security37_fixtures as current
from tests import account_security37_http as current_http
from tests import test_account_security37_service as own
from tests import test_google33_http as google
from web.database.models import (
    AuthAuditLog,
    AuthExternalIdentity,
    MfaAuthorization,
    RefreshToken,
    Usuario,
)
from web.services import account_security as service
from web.services import mfa_service as mfa

account37_engine = current.account37_engine
account37 = current.account37
google_db = current_http.followup_db
google_http = google.google_http


def test_concurrent_contact_proof_has_at_most_one_success_and_one_audit(account37):
    from fastapi import HTTPException
    token = own.issue(account37)
    def confirm():
        try:
            return service.confirm_email(token, factory=account37["factory"])["code"]
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(), range(2)))
    assert results.count("account_email_confirmed") == 1
    assert next(value for value in results if value != "account_email_confirmed") in {400, 503}
    own.denied(400, lambda: service.confirm_email(token, factory=account37["factory"]))
    with account37["factory"]() as db:
        assert db.scalar(select(func.count()).select_from(AuthAuditLog).where(
            AuthAuditLog.user_id == account37["user"], AuthAuditLog.event_type == "email_contact_verified")) == 1


def test_concurrent_password_change_never_increments_sv_twice(account37):
    from fastapi import HTTPException
    proofs = [own.reauth(account37), own.reauth(account37)]
    def change(proof):
        try:
            return own.invoke_password(account37, proof)["code"]
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(change, proofs))
    assert results.count("account_password_changed") == 1
    assert next(value for value in results if value != "account_password_changed") in {401, 503}
    with account37["factory"]() as db:
        assert db.get(Usuario, account37["user"]).session_version == 1
        assert all(db.scalars(select(RefreshToken.revoked).where(RefreshToken.user_id == account37["user"])))


def test_terminal_session_version_never_wraps_or_consumes_proof(account37):
    from web.auth import crear_token_pair, identity_from_user, verify_password
    with account37["factory"]() as db:
        user = db.get(Usuario, account37["user"])
        user.session_version = mfa.MAX_SV
        db.flush()
        account37["expected"] = identity_from_user(user, db)
        pair = crear_token_pair(account37["expected"], db=db)
        account37["access"] = pair["access_token"]
        db.commit()
    proof = own.reauth(account37)
    assert own.denied(409, lambda: own.invoke_password(account37, proof)) == "mfa_session_version_exhausted"
    with account37["factory"]() as db:
        user = db.get(Usuario, account37["user"])
        assert user.session_version == mfa.MAX_SV and verify_password(current.PASSWORD, user.password_hash)
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).consumed_at is None


def test_linked_google_primary_can_change_password_without_contact_adoption(google_http):
    from web.settings import get_settings
    case = google_http
    issued = google.start(case)
    assert issued.status_code == 200
    confirmed = case["client"].post("/api/auth/google/link/confirm", headers=case["headers"],
                                  json={"intent": issued.json()["intent"], "confirm": True})
    assert confirmed.status_code == 200
    login = case["client"].post("/api/auth/google", json={"credential": case["credential"]()})
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["token"], "Origin": get_settings().BASE_URL,
               "X-MetodoBase-Browser": "1"}
    if case["client"].cookies.get("_csrf"):
        headers["X-CSRF-Token"] = case["client"].cookies.get("_csrf")
    proof = case["client"].post("/api/auth/mfa/reauth", headers=headers,
                              json={"google_credential": case["credential"]()})
    assert proof.status_code == 200
    response = case["client"].post("/api/account/security/password", headers=headers, json={
        "reauthentication_token": proof.json()["reauthentication_token"],
        "new_password": current.NEW_PASSWORD, "confirm_password": current.NEW_PASSWORD})
    assert response.status_code == 200 and response.json()["sessions_revoked"]
    assert "token" not in response.json() and "refresh_token" not in response.json()
    with Session(case["admin"]) as db:
        user = db.get(Usuario, case["user"])
        assert user.email == case["email"] and user.email_verified_at is None
        assert user.session_version == 2
        assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.subject == case["google"]["sub"],
            AuthExternalIdentity.revoked_at.is_(None))) == case["user"]
    # Password change revokes sessions, preserving the explicit Google binding.
    resumed = case["client"].post("/api/auth/google", json={"credential": case["credential"]()})
    assert resumed.status_code == 200
