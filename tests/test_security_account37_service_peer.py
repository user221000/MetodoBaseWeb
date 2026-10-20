"""Independent purpose, exact-access, factor and commit/cleanup boundaries."""
import base64
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests import account_security37_fixtures as current
from web.database.models import (
    MfaAuthorization,
    MfaCredential,
    MfaRecoveryCode,
    RefreshToken,
    Usuario,
)
from web.services import account_security as account
from web.services import mfa_service as mfa

account37_engine = current.account37_engine
account37 = current.account37


def issue(case):
    messages = []
    reply = account.issue_email(case["expected"], factory=case["factory"],
                                sender=lambda recipient, url: messages.append((recipient, url)) or True)
    assert reply["delivery"] == "provider_accepted" and len(messages) == 1
    return parse_qs(urlsplit(messages[0][1]).fragment)["token"][0]


def primary(case):
    with case["factory"]() as db:
        return mfa.reauthenticate(db, case["expected"], case["access"], password=current.PASSWORD)["reauthentication_token"]


def change(case, proof, **options):
    return account.change_password(case["expected"], case["access"], proof,
                                   current.NEW_PASSWORD, factory=case["factory"], **options)


def refused(action, status):
    with pytest.raises(HTTPException) as caught:
        action()
    assert caught.value.status_code == status
    return caught.value


def active_factor(case):
    from web.auth import identity_from_user
    from web.services.mfa_crypto import totp
    with case["factory"]() as db:
        enrollment = mfa.enroll(db, case["expected"], case["access"], primary(case))
    now = datetime.now(UTC)
    seed = base64.b32decode(enrollment["secret"])
    with case["factory"]() as db:
        kit = mfa.confirm_enrollment(db, case["expected"], enrollment["enrollment_id"],
                                     totp(seed, int(now.timestamp()) // 30), now=now)
    with case["factory"]() as db:
        case["expected"] = identity_from_user(db.get(Usuario, case["user"]), db)
        challenge = mfa.login(db, case["expected"])
    with case["factory"]() as db:
        pair = mfa.verify_login(db, challenge["challenge"], recovery_code=kit["recovery_codes"][0])
    case["access"] = pair["token"]
    return kit["recovery_codes"][1:]


def test_contact_proof_and_primary_proof_are_not_interchangeable(account37):
    case = account37
    contact = issue(case)
    proof = primary(case)
    refused(lambda: account.confirm_email(proof, factory=case["factory"]), 400)
    refused(lambda: change(case, contact), 400)
    with case["factory"]() as db:
        actor = db.get(Usuario, case["user"])
        assert actor.session_version == case["expected"]["session_version"]
        assert actor.email_verification_hash == account.digest(contact) and actor.email_verified_at is None
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).consumed_at is None
    assert account.confirm_email(contact, factory=case["factory"])["email_verified"] is True
    assert change(case, proof)["sessions_revoked"] is True


def test_primary_proof_does_not_transfer_to_another_valid_access_for_same_subject(account37):
    from web.auth import crear_token_pair
    case = account37
    proof = primary(case)
    original = case["access"]
    with case["factory"]() as db:
        pair = crear_token_pair(case["expected"], db=db)
        db.commit()
    case["access"] = pair["access_token"]
    assert case["access"] != original
    refused(lambda: change(case, proof), 400)
    with case["factory"]() as db:
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).consumed_at is None
    case["access"] = original
    assert change(case, proof)["sessions_revoked"] is True
    refused(lambda: change(case, proof), 401)
    case["access"] = pair["access_token"]
    refused(lambda: change(case, proof), 401)
    with case["factory"]() as db:
        assert all(db.scalars(select(RefreshToken.revoked).where(RefreshToken.user_id == case["user"])))


def test_confirmed_contact_evidence_survives_password_change_but_pending_proof_does_not(account37):
    from web.auth import identity_from_user
    case = account37
    contact = issue(case)
    account.confirm_email(contact, factory=case["factory"])
    assert change(case, primary(case))["sessions_revoked"] is True
    refused(lambda: account.confirm_email(contact, factory=case["factory"]), 400)
    with case["factory"]() as db:
        actor = db.get(Usuario, case["user"])
        assert account.email_status(db, identity_from_user(actor, db))["email_verified"] is True
        assert all(getattr(actor, field) is None for field in account.PENDING)


@pytest.mark.parametrize("when", ["before", "after"])
def test_recovery_factor_password_proof_and_sessions_commit_atomically(account37, when):
    from web.auth import verify_password
    case = account37
    codes = active_factor(case)
    contact = issue(case)
    proof = primary(case)
    old_version = case["expected"]["session_version"]
    class Fault(Session):
        def commit(self):
            if when == "after":
                super().commit()
            raise RuntimeError("Synthetic independent lost commit acknowledgement")
    broken = sessionmaker(bind=case["engine"], class_=Fault, expire_on_commit=True, autoflush=False)
    refused(lambda: account.change_password(case["expected"], case["access"], proof, current.NEW_PASSWORD,
                                           recovery_code=codes[0], factory=broken), 503)
    with case["factory"]() as db:
        actor = db.get(Usuario, case["user"])
        recovery = db.scalar(select(MfaRecoveryCode).where(
            MfaRecoveryCode.user_id == case["user"], MfaRecoveryCode.code_hash == mfa.opaque_digest("recovery", codes[0])))
        assert (recovery.used_at is not None) is (when == "after")
        assert (db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).consumed_at is not None) is (when == "after")
        assert actor.session_version == old_version + (when == "after")
        assert verify_password(current.NEW_PASSWORD if when == "after" else current.PASSWORD, actor.password_hash)
        assert db.get(MfaCredential, case["user"]).enabled_at is not None
        unused = db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == case["user"],
                                                         MfaRecoveryCode.used_at.is_(None))).all()
        assert len(unused) == (6 if when == "after" else 7)
        assert (actor.email_verification_hash is None) is (when == "after")
    if when == "before":
        assert change(case, proof, recovery_code=codes[0])["sessions_revoked"] is True
    else:
        refused(lambda: change(case, proof, recovery_code=codes[0]), 401)
        refused(lambda: account.confirm_email(contact, factory=case["factory"]), 400)


@pytest.mark.parametrize("operation", ["issue", "confirm", "password"])
def test_close_failure_never_returns_an_ack_or_sends_after_issue(account37, operation):
    case = account37
    proof = issue(case) if operation == "confirm" else primary(case) if operation == "password" else None
    messages = []
    class Fault(Session):
        def close(self):
            super().close()
            raise RuntimeError("Synthetic independent private close failure")
    broken = sessionmaker(bind=case["engine"], class_=Fault, expire_on_commit=True, autoflush=False)
    with pytest.raises(RuntimeError):
        if operation == "issue":
            account.issue_email(case["expected"], factory=broken, sender=lambda *_args: messages.append(True) or True)
        elif operation == "confirm":
            account.confirm_email(proof, factory=broken)
        else:
            account.change_password(case["expected"], case["access"], proof, current.NEW_PASSWORD, factory=broken)
    assert messages == []
    assert case["engine"].pool.checkedout() == 0


def test_proof_at_expiry_is_unusable_without_consumption_or_contact_ack(account37):
    case = account37
    contact = issue(case)
    with case["factory"]() as db:
        expires = db.get(Usuario, case["user"]).email_verification_expires_at
    refused(lambda: account.confirm_email(contact, factory=case["factory"], now=mfa.aware(expires)), 400)
    with case["factory"]() as db:
        actor = db.get(Usuario, case["user"])
        assert actor.email_verified_at is None and actor.email_verification_hash == account.digest(contact)


def test_wrong_current_factor_persists_budget_without_consuming_contact_or_primary(account37):
    case = account37
    active_factor(case)
    contact = issue(case)
    proof = primary(case)
    refused(lambda: change(case, proof, recovery_code="Z" * 22), 400)
    with case["factory"]() as db:
        actor = db.get(Usuario, case["user"])
        assert actor.session_version == case["expected"]["session_version"]
        assert actor.email_verification_hash == account.digest(contact)
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).attempts == 1
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).consumed_at is None
        assert db.get(MfaCredential, case["user"]).attempts["password"]["count"] == 1
