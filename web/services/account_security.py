"""Current-contact confirmation and atomic authenticated password changes.

Email possession is purpose-only contact evidence. It never authenticates,
adopts a tenant, alters roles/rights, disables MFA or emits session tokens.
"""
import hashlib
import logging
import re
import secrets
from datetime import timedelta
from html import escape
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError

from web.account_values import validate_new_password
from web.database.models import AuthAuditLog, RefreshToken, Usuario
from web.database.tenant_context import current_tenant
from web.services import mfa_service as mfa

logger = logging.getLogger(__name__)
LIFETIME = timedelta(minutes=30)
RESEND_INTERVAL = timedelta(seconds=60)
PENDING = ("email_verification_hash", "email_verification_issued_at", "email_verification_expires_at",
           "email_verification_session_version", "email_verification_contact_version")


def fail(status, code):
    raise HTTPException(status, {"code": code, "message": {
        "account_email_unavailable": "El enlace no está disponible. Solicita uno nuevo desde tu cuenta.",
        "account_security_unconfirmed": "No pudimos confirmar la operación. Consulta el estado o inicia sesión de nuevo.",
        "account_email_delivery_unconfirmed": "No se confirmó la aceptación del correo. Espera antes de solicitar otro enlace.",
        "account_email_throttled": "Espera antes de solicitar otro enlace.",
        "account_security_busy": "La cuenta está cambiando. Vuelve a intentar.",
    }.get(code, "No se pudo realizar esta operación de seguridad.")})


def digest(token):
    return hashlib.sha256(("email-contact-verification37:" + token).encode("ascii")).hexdigest()


def factory_or_default(factory):
    if factory is None:
        from web.database.engine import SessionLocal
        return SessionLocal
    return factory


def configuration():
    from web.browser_session import configuration as browser_configuration
    from web.settings import get_settings
    settings = get_settings()
    if not settings.RESEND_API_KEY or (settings.is_production and not settings.REDIS_URL):
        fail(503, "account_security_service_unavailable")
    try:
        return browser_configuration()[0]
    except HTTPException:
        fail(503, "account_security_service_unavailable")


def epoch(user):
    value = user.notification_contact_version
    if type(value) is not int or not 0 <= value <= mfa.MAX_SV:
        fail(503, "account_security_unconfirmed")
    return value


def verified(user, now):
    return (user.email_verified_at is not None and type(user.email_verified_contact_version) is int
            and user.email_verified_contact_version == epoch(user)
            and mfa.aware(user.email_verified_at) <= now)


def email_status(db, expected, *, now=None):
    user = db.get(Usuario, expected["id"], populate_existing=True)
    identity = mfa.current_identity(db, user)
    if (identity["session_version"] != expected.get("session_version", expected.get("sv", 0))
            or identity.get("team_gym_id") != expected.get("team_gym_id")):
        fail(401, "account_security_identity_unavailable")
    current = mfa.instant(now)
    confirmed = verified(user, current)
    return {"email_verified": confirmed,
            "email_verified_at": user.email_verified_at if confirmed else None,
            "verification_lifetime_seconds": int(LIFETIME.total_seconds()),
            "password_change_reauthentication": "primary_and_current_factor_if_enabled"}


def _commit(db):
    try:
        db.commit()
    except Exception as error:
        logger.exception("Account security commit unconfirmed class=%s", type(error).__name__, exc_info=False)
        mfa.rollback(db)
        fail(503, "account_security_unconfirmed")


def _send_verification(recipient, link):
    from web.services.email_service import _base_layout, _send
    content = '<h2>Confirmar correo de contacto</h2><p>Confirma que puedes recibir mensajes en este correo.</p>'
    content += '<p><a href="' + escape(link, quote=True) + '">Confirmar correo</a></p>'
    content += '<p>El enlace vence en 30 minutos y sólo se usa una vez. No inicia sesión ni cambia tu contraseña. Si no lo solicitaste, ignóralo.</p>'
    return _send(recipient, "Confirmar correo — Método Base", _base_layout(content))


def issue_email(expected, *, factory=None, sender=None, now=None):
    origin = configuration()
    sender = _send_verification if sender is None else sender
    with factory_or_default(factory)() as db:
        try:
            user, _ = mfa.lock_actor(db, expected)
            current = mfa.instant(now)
            contact_epoch = epoch(user)
            if verified(user, current):
                # No proof or transport is needed; leave existing evidence intact.
                return {"email_verified": True, "delivery": "not_required"}
            if contact_epoch == mfa.MAX_SV:
                fail(409, "account_security_contact_version_exhausted")
            if (user.email_verification_issued_at is not None
                    and mfa.aware(user.email_verification_issued_at) + RESEND_INTERVAL > current):
                fail(429, "account_email_throttled")
            token = secrets.token_urlsafe(32)
            user.email_verification_hash = digest(token)
            user.email_verification_issued_at = current
            user.email_verification_expires_at = current + LIFETIME
            user.email_verification_session_version = user.session_version
            user.email_verification_contact_version = contact_epoch
            recipient = user.email
            db.add(AuthAuditLog(user_id=user.id, event_type="email_verification_requested",
                                event_metadata={"purpose": "contact"}, created_at=current))
            _commit(db)
        except HTTPException:
            mfa.rollback(db)
            raise
        except Exception as error:
            logger.exception("Contact proof issue unconfirmed class=%s", type(error).__name__, exc_info=False)
            mfa.rollback(db)
            fail(503, "account_security_unconfirmed")
    # No transaction/connection is retained during provider I/O. A lost commit
    # acknowledgement prevents sending a token that may not be durable.
    link = origin + "/auth/verify-email#" + urlencode({"token": token})
    try:
        accepted = sender(recipient, link)
    except Exception as error:
        logger.exception("Contact proof transport unconfirmed class=%s", type(error).__name__, exc_info=False)
        accepted = False
    if accepted is not True:
        fail(503, "account_email_delivery_unconfirmed")
    return {"email_verified": False, "delivery": "provider_accepted", "expires_in_seconds": 1800}


def _valid_pending(db, user, hashed, now):
    if user is None:
        return False
    try:
        mfa.current_identity(db, user)
    except HTTPException:
        return False
    return (user.email_verification_hash == hashed
            and user.email_verification_issued_at is not None
            and user.email_verification_expires_at is not None
            and mfa.aware(user.email_verification_issued_at) <= now < mfa.aware(user.email_verification_expires_at)
            and user.email_verification_session_version == user.session_version
            and user.email_verification_contact_version == epoch(user))


def confirm_email(token, *, factory=None, now=None):
    # A foreign Bearer is deliberately irrelevant to this purpose-only proof.
    # Open a NEW Session under empty context and restore the caller's context.
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        fail(400, "account_email_unavailable")
    hashed = digest(token)
    context = current_tenant.set("")
    try:
        with factory_or_default(factory)() as db:
            try:
                current = mfa.instant(now)
                user = db.scalar(select(Usuario).where(Usuario.email_verification_hash == hashed))
                if not _valid_pending(db, user, hashed, current):
                    fail(400, "account_email_unavailable")
                identity = user.id
                try:
                    if db.get_bind().dialect.name == "postgresql":
                        db.execute(select(Usuario.id).where(Usuario.id == identity).with_for_update(nowait=True)).all()
                    else:
                        db.execute(update(Usuario).where(Usuario.id == identity).values(id=Usuario.id))
                except DBAPIError as error:
                    if getattr(error.orig, "pgcode", None) == "55P03":
                        fail(409, "account_security_busy")
                    raise
                user = db.get(Usuario, identity, populate_existing=True)
                current = mfa.instant(now)
                if not _valid_pending(db, user, hashed, current):
                    fail(400, "account_email_unavailable")
                contact_epoch = epoch(user)
                result = db.execute(update(Usuario).where(Usuario.id == identity,
                    Usuario.email_verification_hash == hashed,
                    Usuario.notification_contact_version == contact_epoch,
                    Usuario.session_version == user.email_verification_session_version,
                    Usuario.email_verification_expires_at > current).values(
                        **dict.fromkeys(PENDING), email_verified_at=current,
                        email_verified_contact_version=contact_epoch).execution_options(synchronize_session=False))
                if result.rowcount != 1:
                    fail(400, "account_email_unavailable")
                db.add(AuthAuditLog(user_id=identity, event_type="email_contact_verified",
                                    event_metadata={"purpose": "contact"}, created_at=current))
                _commit(db)
                return {"code": "account_email_confirmed", "email_verified": True}
            except HTTPException:
                mfa.rollback(db)
                raise
            except Exception as error:
                logger.exception("Contact proof confirmation unconfirmed class=%s", type(error).__name__, exc_info=False)
                mfa.rollback(db)
                fail(503, "account_security_unconfirmed")
    finally:
        current_tenant.reset(context)


def change_password(expected, access, proof_token, new_password, *, code=None, recovery_code=None, factory=None, now=None):
    try:
        validate_new_password(new_password)
    except ValueError:
        fail(422, "account_security_invalid_input")
    from web.auth import hash_password
    password_hash = hash_password(new_password)
    with factory_or_default(factory)() as db:
        try:
            user = mfa.consume_account_reauthentication(db, expected, access, proof_token,
                                                       code=code, recovery_code=recovery_code, now=now)
            current = mfa.instant(now)
            identity = user.id
            user.password_hash = password_hash
            user.session_version += 1
            user.password_reset_hash = user.password_reset_expires_at = user.password_reset_session_version = None
            for name in PENDING:
                setattr(user, name, None)
            db.execute(update(RefreshToken).where(RefreshToken.user_id == identity).values(revoked=True))
            db.add(AuthAuditLog(user_id=identity, event_type="account_password_changed",
                                event_metadata={"channel": "authenticated_account"}, created_at=current))
            _commit(db)
            return {"code": "account_password_changed", "reauthenticate": True, "sessions_revoked": True}
        except HTTPException:
            mfa.rollback(db)
            raise
        except Exception as error:
            logger.exception("Account password change unconfirmed class=%s", type(error).__name__, exc_info=False)
            mfa.rollback(db)
            fail(503, "account_security_unconfirmed")
