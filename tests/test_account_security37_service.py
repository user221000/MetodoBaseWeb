"""Purpose, revocation, replay, contact ABA and uncertain-commit canaries."""
import base64
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from tests import account_security37_fixtures
from tests.account_security37_fixtures import NEW_PASSWORD, PASSWORD
from web.database.models import MfaAuthorization, MfaCredential, RefreshToken, Usuario
from web.database.tenant_context import current_tenant
from web.services import account_security as service
from web.services import mfa_service as mfa

account37 = account_security37_fixtures.account37
account37_engine = account_security37_fixtures.account37_engine


def issue(case, **kwargs):
    sent = []
    response = service.issue_email(case["expected"], factory=case["factory"],
                                   sender=lambda recipient, link: sent.append((recipient, link)) or True, **kwargs)
    assert response["delivery"] == "provider_accepted"
    assert len(sent) == 1
    parsed = urlsplit(sent[0][1])
    assert parsed.path == "/auth/verify-email" and parsed.query == ""
    return parse_qs(parsed.fragment)["token"][0]


def reauth(case, **kwargs):
    with case["factory"]() as db:
        return mfa.reauthenticate(db, case["expected"], case["access"], password=PASSWORD, **kwargs)["reauthentication_token"]


def invoke_password(case, token, **kwargs):
    return service.change_password(case["expected"], case["access"], token,
                                   NEW_PASSWORD, factory=case["factory"], **kwargs)


def denied(code, action):
    with pytest.raises(HTTPException) as caught:
        action()
    assert caught.value.status_code == code
    return caught.value.detail["code"]


def test_contact_confirmation_single_use_no_auth_or_commercial_mutation(account37):
    case = account37
    token = issue(case)
    with case["factory"]() as db:
        user = db.get(Usuario, case["user"])
        assert user.email_verification_hash == service.digest(token)
        assert token not in user.email_verification_hash
        before = (user.password_hash, user.session_version, user.tipo, user.role, user.team_gym_id)
    assert service.confirm_email(token, factory=case["factory"]) == {"code": "account_email_confirmed", "email_verified": True}
    denied(400, lambda: service.confirm_email(token, factory=case["factory"]))
    with case["factory"]() as db:
        user = db.get(Usuario, case["user"])
        assert before == (user.password_hash, user.session_version, user.tipo, user.role, user.team_gym_id)
        assert user.email_verification_hash is None
        assert service.email_status(db, case["expected"])["email_verified"] is True
        assert db.scalar(select(MfaCredential).where(MfaCredential.user_id == case["user"])) is None
        assert db.scalar(select(RefreshToken.revoked).where(RefreshToken.user_id == case["user"])) is False


@pytest.mark.parametrize("confirmed", [False, True])
def test_contact_aba_invalidates_pending_and_verified_status(account37, confirmed):
    case = account37
    token = issue(case)
    if confirmed:
        service.confirm_email(token, factory=case["factory"])
    with case["factory"]() as db:
        user = db.get(Usuario, case["user"])
        original = user.email
        user.email = uuid.uuid4().hex + "@example.invalid"
        db.commit()
        user.email = original
        db.commit()
        assert user.notification_contact_version == 2
        assert service.email_status(db, case["expected"])["email_verified"] is False
    denied(400, lambda: service.confirm_email(token, factory=case["factory"]))


def test_foreign_context_is_empty_for_new_session_and_restored(account37):
    case = account37
    token = issue(case)
    contexts = []
    original_factory = case["factory"]
    def own_factory():
        contexts.append(current_tenant.get())
        return original_factory()
    context = current_tenant.set("foreign-account-B")
    try:
        assert service.confirm_email(token, factory=own_factory)["email_verified"]
        assert current_tenant.get() == "foreign-account-B"
    finally:
        current_tenant.reset(context)
    assert contexts == [""]


@pytest.mark.parametrize("offset", [-1, 1800, 1801])
def test_expired_or_future_email_proof_is_generic(account37, offset):
    now = datetime.now(UTC)
    token = issue(account37, now=now)
    assert denied(400, lambda: service.confirm_email(token, factory=account37["factory"],
                  now=now + timedelta(seconds=offset))) == "account_email_unavailable"


def test_new_issue_replaces_old_proof_and_resend_has_durable_budget(account37):
    now = datetime.now(UTC)
    token = issue(account37, now=now)
    denied(429, lambda: issue(account37, now=now + timedelta(seconds=59)))
    replacement = issue(account37, now=now + timedelta(seconds=61))
    denied(400, lambda: service.confirm_email(token, factory=account37["factory"], now=now + timedelta(seconds=62)))
    assert service.confirm_email(replacement, factory=account37["factory"], now=now + timedelta(seconds=62))["email_verified"]


@pytest.mark.parametrize("change", ["session", "inactive", "deleted", "invited"])
def test_email_proof_cannot_outlive_current_identity(account37, change):
    token = issue(account37)
    with account37["factory"]() as db:
        user = db.get(Usuario, account37["user"])
        if change == "session":
            user.session_version += 1
        elif change == "inactive":
            user.activo = False
        elif change == "deleted":
            user.deleted_at = datetime.now(UTC)
        else:
            user.invitation_token = "synthetic-invitation-" + uuid.uuid4().hex
        db.commit()
    denied(400, lambda: service.confirm_email(token, factory=account37["factory"]))


def test_missing_configuration_and_contact_epoch_terminal_fail_closed(account37, monkeypatch):
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "")
    denied(503, lambda: issue(account37))
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-not-sent")
    with account37["factory"]() as db:
        # Every intermediate increment is guarded; seed a new terminal account
        # rather than resetting or bypassing the existing monotonic trigger.
        user = Usuario(id=str(uuid.uuid4()), email=uuid.uuid4().hex + "@example.invalid", nombre="Terminal",
                       password_hash="synthetic", tipo="usuario", notification_contact_version=mfa.MAX_SV)
        db.add(user)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    # Application refuses a corrupt/terminal primitive without resetting it.
    class Terminal:
        notification_contact_version = mfa.MAX_SV
    assert service.epoch(Terminal()) == mfa.MAX_SV


@pytest.mark.parametrize("accepted", [False, None, {}, {"id": "synthetic"}])
def test_provider_ack_must_be_literal_true_and_never_marks_verified(account37, accepted):
    denied(503, lambda: service.issue_email(account37["expected"], factory=account37["factory"],
                                         sender=lambda *args: accepted))
    with account37["factory"]() as db:
        assert not service.email_status(db, account37["expected"])["email_verified"]


def lost_ack_factory(case, *, before=False):
    class Uncertain(Session):
        def commit(self):
            if before:
                raise RuntimeError("Synthetic37 before commit")
            super().commit()
            raise RuntimeError("Synthetic37 acknowledgement lost")
    return sessionmaker(bind=case["engine"], class_=Uncertain, expire_on_commit=True, autoflush=False)


def test_issue_commit_ack_loss_never_sends(account37):
    sent = []
    denied(503, lambda: service.issue_email(account37["expected"], factory=lost_ack_factory(account37),
                                         sender=lambda *args: sent.append(True) or True))
    assert sent == []
    with account37["factory"]() as db:
        assert db.get(Usuario, account37["user"]).email_verification_hash is not None


@pytest.mark.parametrize("before", [False, True])
def test_confirmation_uncertain_commit_is_never_success(account37, before):
    token = issue(account37)
    assert denied(503, lambda: service.confirm_email(token, factory=lost_ack_factory(account37, before=before))) == "account_security_unconfirmed"
    with account37["factory"]() as db:
        assert service.email_status(db, account37["expected"])["email_verified"] is (not before)
    if before:
        assert service.confirm_email(token, factory=account37["factory"])["email_verified"]
    else:
        denied(400, lambda: service.confirm_email(token, factory=account37["factory"]))


def test_password_change_consumes_primary_proof_and_revokes_every_session(account37):
    from web.auth import verify_password
    pending_email = issue(account37)
    token = reauth(account37)
    other = reauth(account37)
    assert invoke_password(account37, token) == {"code": "account_password_changed", "reauthenticate": True, "sessions_revoked": True}
    denied(401, lambda: invoke_password(account37, other))
    denied(400, lambda: service.confirm_email(pending_email, factory=account37["factory"]))
    with account37["factory"]() as db:
        user = db.get(Usuario, account37["user"])
        assert verify_password(NEW_PASSWORD, user.password_hash)
        assert not verify_password(PASSWORD, user.password_hash)
        assert user.session_version == account37["expected"]["session_version"] + 1
        assert all(db.scalars(select(RefreshToken.revoked).where(RefreshToken.user_id == user.id)))
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", token)).consumed_at is not None


def test_password_change_invalidates_pending_enrollment_without_disabling_current_factor(account37):
    proof = reauth(account37)
    with account37["factory"]() as db:
        enrollment = mfa.enroll(db, account37["expected"], account37["access"], proof)
    assert enrollment["enrollment_id"]
    current_proof = reauth(account37)
    assert invoke_password(account37, current_proof)["sessions_revoked"]
    with account37["factory"]() as db:
        row = db.get(MfaCredential, account37["user"])
        assert row.pending_id is row.pending_ciphertext is row.pending_expires_at is None


@pytest.mark.parametrize("kind", ["wrong_access", "bad_proof", "expired", "wrong_generation"])
def test_password_requires_current_primary_access_and_factor_generation(account37, kind):
    token = reauth(account37)
    if kind == "wrong_access":
        account37["access"] += "invalid"
    elif kind == "bad_proof":
        token = "Z" * 43
    elif kind == "wrong_generation":
        with account37["factory"]() as db:
            db.get(MfaCredential, account37["user"]).generation += 1
            db.commit()
    kwargs = {"now": datetime.now(UTC) + timedelta(minutes=6)} if kind == "expired" else {}
    denied(401 if kind == "wrong_access" else 400, lambda: invoke_password(account37, token, **kwargs))
    with account37["factory"]() as db:
        assert db.get(Usuario, account37["user"]).session_version == account37["expected"]["session_version"]


def test_enabled_factor_is_required_and_current_counter_is_consumed(account37):
    from web.services.mfa_crypto import encrypt, totp
    from web.settings import get_settings
    now = datetime.now(UTC)
    token = reauth(account37, now=now)
    seed = b"S" * 20
    with account37["factory"]() as db:
        row = db.get(MfaCredential, account37["user"])
        row.generation = 1
        row.enabled_at = now
        row.secret_ciphertext = encrypt(seed, base64.urlsafe_b64decode(get_settings().MFA_ENCRYPTION_KEY), mfa._aad(row, 1, "active"))
        # The reauth predates this new factor and must be invalidated.
        db.commit()
    denied(400, lambda: invoke_password(account37, token, now=now))
    token = reauth(account37, now=now)
    denied(422, lambda: invoke_password(account37, token, now=now))
    result = invoke_password(account37, token, code=totp(seed, int(now.timestamp()) // 30), now=now)
    assert result["sessions_revoked"]
    with account37["factory"]() as db:
        row = db.get(MfaCredential, account37["user"])
        assert row.enabled_at is not None and row.last_counter == int(now.timestamp()) // 30


@pytest.mark.parametrize("before", [False, True])
def test_password_commit_ack_loss_never_claims_success(account37, before):
    from web.auth import verify_password
    token = reauth(account37)
    assert denied(503, lambda: service.change_password(account37["expected"], account37["access"], token,
                  NEW_PASSWORD, factory=lost_ack_factory(account37, before=before))) == "account_security_unconfirmed"
    with account37["factory"]() as db:
        user = db.get(Usuario, account37["user"])
        assert user.session_version == account37["expected"]["session_version"] + (0 if before else 1)
        assert verify_password(PASSWORD if before else NEW_PASSWORD, user.password_hash)
        proof = db.get(MfaAuthorization, mfa.opaque_digest("reauth", token))
        assert (proof.consumed_at is None) is before
