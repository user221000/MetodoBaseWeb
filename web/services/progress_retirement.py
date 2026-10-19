"""Fresh proof for two own-consent operations when general login is unavailable.

No parent authority is asserted and no portable authentication is issued. A
durable admission precedes the one transaction containing factor consumption
and the confirmed projection/withdrawal. A GUC is installed only after the
locked account's password is verified; it is never evidence of identity.
"""
import logging
import uuid
from contextlib import contextmanager
from datetime import timedelta
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import func, select, update

from web.auth import hash_password, verify_password
from web.database.mfa_policy import bind_mfa_actor
from web.database.models import AuthAuditLog, ProgressConsent, UserRole, Usuario
from web.database.tenant_context import bind_verified_subject
from web.services import mfa_service as mfa
from web.services import personal_progress as own
from web.services import progress_share as share

logger = logging.getLogger(__name__)
WINDOW_SECONDS = 300
MAX_ATTEMPTS = 10
ATTEMPT_EVENT = "progress_retirement_attempt"


def fail(status, code):
    raise HTTPException(status, {"code": code, "message": {
        "progress_retirement_verification_failed": "No pudimos verificar esta solicitud.",
        "progress_retirement_throttled": "Espera antes de volver a verificar.",
        "progress_retirement_primary_unavailable": "Este metodo requiere un procedimiento de vinculacion verificado.",
        "progress_retirement_unconfirmed": "No pudimos confirmar el resultado. Consulta con una nueva prueba antes de continuar.",
    }.get(code, "Consulta el estado propio antes de continuar.")})


def _rollback(db):
    try:
        db.rollback()
    except Exception as error:  # noqa: BLE001 -- fail closed; never log exception payload
        logger.error("Consent retirement rollback class=%s", type(error).__name__)
        fail(503, "progress_retirement_unconfirmed")


@contextmanager
def _transaction(db):
    if db.in_transaction() or db.in_nested_transaction():
        fail(503, "progress_retirement_unconfirmed")
    try:
        yield
    except HTTPException:
        _rollback(db)
        raise
    except Exception as error:  # noqa: BLE001 -- fail closed; never log exception payload
        state = getattr(getattr(error, "orig", None), "pgcode", None)
        _rollback(db)
        if state == "55P03":
            fail(409, "progress_retirement_busy")
        logger.error("Consent retirement class=%s", type(error).__name__)
        fail(503, "progress_retirement_unconfirmed")


def _commit(db):
    try:
        db.info["retirement_commit_attempted"] = True
        db.commit()
    except Exception as error:  # noqa: BLE001 -- fail closed; never log exception payload
        logger.error("Consent retirement commit class=%s", type(error).__name__)
        _rollback(db)
        fail(503, "progress_retirement_unconfirmed")


def _locked(db, *, email=None, subject=None, admission=False):
    predicate = Usuario.email == email if subject is None else Usuario.id == subject
    if db.get_bind().dialect.name == "sqlite":
        db.execute(update(Usuario).where(predicate).values(id=Usuario.id).execution_options(synchronize_session=False))
    query = (select(Usuario.id, Usuario.session_version) if admission else select(Usuario)).where(predicate).execution_options(populate_existing=True)
    if db.get_bind().dialect.name == "postgresql":
        query = query.with_for_update(nowait=True)
    return db.execute(query).first() if admission else db.scalar(query)


@lru_cache(maxsize=1)
def _dummy_hash():
    # This constant is never an accepted account credential.
    return hash_password("Purpose limited dummy comparison 2026!")


def _eligible(user):
    return bool(user is not None and user.activo and user.deleted_at is None
        and user.invitation_token is None and user.role in set(UserRole)
        and user.tipo in {"usuario", "gym", "admin"}
        and type(user.session_version) is int and 0 <= user.session_version <= mfa.MAX_SV)


def _admit(db, primary, now):
    """Not proof: known-actor attempt persists even if later work rolls back.

    Unknown accounts are still covered by mandatory IP/account admission at
    the HTTP boundary. No password hash or MFA secret is read by this step.
    """
    with _transaction(db):
        user = _locked(db, email=primary.email, admission=True)
        if user is None:
            db.rollback()
            return None
        total = db.scalar(select(func.count()).select_from(AuthAuditLog).where(
            AuthAuditLog.user_id == user.id, AuthAuditLog.event_type == ATTEMPT_EVENT,
            AuthAuditLog.created_at >= now - timedelta(seconds=WINDOW_SECONDS)))
        if total >= MAX_ATTEMPTS:
            # Retain the same bounded password work for a known limited account.
            verify_password(primary.password, _dummy_hash())
            fail(429, "progress_retirement_throttled")
        candidate = (user.id, user.session_version)
        db.add(AuthAuditLog(user_id=user.id, event_type=ATTEMPT_EVENT,
                           event_metadata={"purpose": "own_consent_retirement"}, created_at=now))
        _commit(db)
        return candidate


def _verify(db, candidate, command, now):
    primary = command.primary
    user = _locked(db, subject=candidate[0]) if candidate is not None else None
    hashed = user.password_hash if user is not None else _dummy_hash()
    valid = verify_password(primary.password, hashed)
    if (not valid or not _eligible(user) or user.email != primary.email
            or user.session_version != candidate[1]):
        fail(401, "progress_retirement_verification_failed")
    # No call to identity_from_user/current_identity: their parent gate stays
    # intact for every other purpose. Only immutable events for this ID follow.
    bind_verified_subject(db, user.id)
    bind_mfa_actor(db, user.id)
    row = mfa.credential(db, user.id)
    factor = command.factor
    if row is not None and row.enabled_at is not None:
        if factor is None:
            fail(401, "progress_retirement_verification_failed")
        try:
            method = mfa.verify_factor(db, row, code=factor.code, recovery_code=factor.recovery_code,
                                      purpose="own_consent_retirement", now=now)
        except HTTPException as error:
            if error.status_code == 400:
                fail(401, "progress_retirement_verification_failed")
            raise
    else:
        if factor is not None:
            fail(401, "progress_retirement_verification_failed")
        method = "none"
    return user, method


def _dto(row):
    consent = share.consent_dto(row)
    # This independent discovery never looks up the source, its name or data.
    consent.pop("source_profile_id")
    return {"link_id": row.link_id, "consent": consent,
            "capabilities": {"withdraw": row.event == "grant", "grant": False}}


def _metadata(db, user, command):
    maximum = select(ProgressConsent.link_id, func.max(ProgressConsent.version).label("version")).where(
        ProgressConsent.user_id == user.id).group_by(ProgressConsent.link_id).subquery()
    query = select(ProgressConsent).join(maximum, (ProgressConsent.link_id == maximum.c.link_id)
        & (ProgressConsent.version == maximum.c.version)).where(ProgressConsent.user_id == user.id)
    if command.after is not None:
        query = query.where(ProgressConsent.link_id > command.after)
    rows = db.scalars(query.order_by(ProgressConsent.link_id).limit(command.limit + 1)).all()
    return {"scope": "own_consent_retirement_only", "items": [_dto(r) for r in rows[:command.limit]],
            "next_after": rows[command.limit - 1].link_id if len(rows) > command.limit else None}


def _withdraw(db, user, command, now):
    prior = share.latest(db, command.link_id, user_id=user.id, lock=True)
    if prior is None:
        own.fail(404, "progress_consent_unavailable")
    share._cas(prior, command.expected_consent_id, command.expected_version)
    if prior.event != "grant":
        own.fail(409, "progress_scope_changed")
    row = ProgressConsent(id=str(uuid.uuid4()), version=prior.version + 1, event="withdraw", created_at=now,
                          **{name: getattr(prior, name) for name in share._SCOPE})
    db.add(row)
    db.flush()
    db.refresh(row)
    return {"scope": "own_consent_retirement_only", **_dto(row), "effective": False}


def perform(db, command, *, operation, now=None):
    if operation not in {"metadata", "withdraw"}:
        raise ValueError("Unknown withdrawal purpose")
    if command.primary.method != "password":
        # Existing Google login/reauth is unchanged. There is no persisted
        # provider subject binding to authorize this exceptional purpose.
        fail(503, "progress_retirement_primary_unavailable")
    current = mfa.instant(now)
    candidate = _admit(db, command.primary, current)
    with _transaction(db):
        user, factor = _verify(db, candidate, command, mfa.instant(now))
        result = _metadata(db, user, command) if operation == "metadata" else _withdraw(db, user, command, mfa.instant(now))
        result = own.bounded(result)
        db.add(AuthAuditLog(user_id=user.id, event_type="progress_retirement_" + operation,
                           event_metadata={"primary": "password", "factor": factor}, created_at=mfa.instant(now)))
        _commit(db)
        return result
