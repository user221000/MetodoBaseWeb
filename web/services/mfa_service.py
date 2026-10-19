"""Account-bound TOTP, one-use recovery and exact-operation authorization.

Callers supply a non-autocommitting Session. A returned secret/token follows a
confirmed commit. Business grant consumption is deliberately uncommitted so
the existing mutation/intention owns that same transaction.
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import logging
import math
import re
import secrets
import uuid
from urllib.parse import quote, urlencode

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from web.database.models import MfaCredential, MfaRecoveryCode, MfaAuthorization, Usuario, UserRole, RefreshToken, AuthAuditLog
from web.database.mfa_policy import bind_mfa_actor
from web.services.mfa_crypto import access_digest, decrypt, encrypt, key_bytes, opaque_digest, totp

logger = logging.getLogger(__name__)
PROOF_TTL = timedelta(minutes=5)
ENROLL_TTL = timedelta(minutes=10)
FAILURE_WINDOW = 300
MAX_FAILURES = 10
MAX_CHALLENGE_FAILURES = 5
MAX_SV = 2147483647


def fail(status, code):
    raise HTTPException(status, {"code": code, "message": {
        "mfa_enrollment_required": "Configura un segundo factor para realizar esta acción.",
        "mfa_step_up_required": "Confirma esta acción con tu segundo factor.",
        "mfa_busy": "La cuenta está cambiando. Consulta su estado y vuelve a intentar.",
        "mfa_throttled": "Espera antes de volver a verificar el segundo factor.",
        "mfa_unconfirmed": "No pudimos confirmar la operación. Consulta el estado o inicia sesión de nuevo.",
        "mfa_session_version_exhausted": "La cuenta necesita revisión antes de cambiar sus opciones de seguridad.",
    }.get(code, "No se pudo verificar esta operación de seguridad.")})


def instant(now=None):
    value = datetime.now(timezone.utc) if now is None else now
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("MFA requires an aware clock")
    return value.astimezone(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def configuration():
    from web.settings import get_settings
    settings = get_settings()
    try:
        key = key_bytes(settings.MFA_ENCRYPTION_KEY)
        if settings.is_production and not settings.REDIS_URL:
            raise ValueError("Distributed limiter required")
        if settings.MFA_ENCRYPTION_KEY == settings.SECRET_KEY or key == settings.SECRET_KEY.encode("utf-8"):
            raise ValueError("Independent key required")
        return key
    except (ValueError, AttributeError):
        fail(503, "mfa_service_unavailable")


def rollback(db):
    try:
        db.rollback()
    except Exception as error:
        logger.error("MFA rollback unconfirmed class=%s", type(error).__name__)


def commit(db):
    try:
        db.commit()
    except Exception as error:
        logger.error("MFA commit unconfirmed class=%s", type(error).__name__)
        rollback(db)
        fail(503, "mfa_unconfirmed")


def current_identity(db, user):
    from web.auth import identity_from_user
    if (user is None or not user.activo or user.deleted_at is not None or user.invitation_token is not None
            or type(user.session_version) is not int or not 0 <= user.session_version <= MAX_SV):
        fail(401, "mfa_identity_unavailable")
    identity = identity_from_user(user, db)
    if not identity:
        fail(401, "mfa_identity_unavailable")
    if user.team_gym_id:
        parent = db.get(Usuario, user.team_gym_id, populate_existing=True)
        if (not parent or not parent.activo or parent.deleted_at is not None
                or parent.tipo != "gym" or parent.role != UserRole.OWNER or parent.team_gym_id
                or parent.invitation_token is not None):
            fail(401, "mfa_identity_unavailable")
    return identity


def lock_actor(db, expected, *, extra_ids=()):
    """Take every required account NOWAIT in global order before any resources."""
    if db.in_nested_transaction():
        fail(409, "mfa_transaction_unavailable")
    user = db.get(Usuario, expected["id"], populate_existing=True)
    if user is None:
        fail(401, "mfa_identity_unavailable")
    parent_id = user.team_gym_id
    ids = sorted({user.id, *extra_ids, *([parent_id] if parent_id else [])})
    try:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(select(Usuario).where(Usuario.id.in_(ids)).order_by(Usuario.id).with_for_update(nowait=True)).scalars().all()
        else:
            for identity in ids:
                db.execute(update(Usuario).where(Usuario.id == identity).values(id=Usuario.id))
    except DBAPIError as error:
        rollback(db)
        if getattr(error.orig, "pgcode", None) == "55P03" or "locked" in type(error.orig).__name__.lower():
            fail(409, "mfa_busy")
        raise
    user = db.get(Usuario, expected["id"], populate_existing=True)
    if user.team_gym_id != parent_id:
        fail(409, "mfa_busy")
    identity = current_identity(db, user)
    version = expected.get("session_version", expected.get("sv", 0))
    if identity["session_version"] != version or identity.get("team_gym_id") != expected.get("team_gym_id"):
        fail(401, "mfa_identity_unavailable")
    bind_mfa_actor(db, user.id)
    return user, identity


def credential(db, user_id, *, create=False):
    row = db.get(MfaCredential, user_id, populate_existing=True)
    if row is None and create:
        row = MfaCredential(user_id=user_id, factor_id=uuid.uuid4().hex, generation=0,
                            last_counter=-1, attempts={})
        db.add(row)
        db.flush()
    return row


def _budget(row, purpose, now, *, failure=False, limit=MAX_FAILURES):
    budgets = dict(row.attempts or {})
    entry = budgets.get(purpose, {})
    epoch = int(now.timestamp())
    start = entry.get("start", epoch)
    count = entry.get("count", 0)
    if type(start) is not int or type(count) is not int or epoch - start >= FAILURE_WINDOW:
        start, count = epoch, 0
    if count >= limit:
        fail(429, "mfa_throttled")
    if failure:
        budgets[purpose] = {"start": start, "count": count + 1}
        row.attempts = budgets


def _aad(row, generation, purpose):
    return ("mfa31:" + row.user_id + ":" + row.factor_id + ":" + str(generation) + ":" + purpose).encode("ascii")


def _proof(db, user, row, purpose, now, *, access=None, binding=None, method="password", remember=False, expires=None, factor_time=None):
    if row is not None:
        _budget(row, "issue:" + purpose, now, failure=True, limit=30)
    token = secrets.token_urlsafe(32)
    item = MfaAuthorization(token_hash=opaque_digest(purpose, token), user_id=user.id,
        session_version=user.session_version, generation=row.generation if row else 0,
        purpose=purpose, access_hash=access_digest(access) if access else None,
        action_binding=binding, primary_method=method, remember_me=remember, attempts=0,
        factor_verified_at=factor_time,
        created_at=now, expires_at=min(now + PROOF_TTL, expires) if expires else now + PROOF_TTL)
    db.add(item)
    return token, item


def _find_proof(db, token, purpose, now, *, user=None, access=None):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        fail(400, "mfa_proof_unavailable")
    item = db.get(MfaAuthorization, opaque_digest(purpose, token), populate_existing=True)
    if (not item or item.purpose != purpose or item.consumed_at is not None
            or aware(item.expires_at) <= now or aware(item.created_at) > now or item.attempts >= MAX_CHALLENGE_FAILURES
            or (user is not None and (item.user_id != user.id or item.session_version != user.session_version))
            or (access is not None and not hmac.compare_digest(item.access_hash or "", access_digest(access)))):
        fail(400, "mfa_proof_unavailable")
    return item


def audit(db, user, event, now, **metadata):
    db.add(AuthAuditLog(user_id=user.id, event_type=event,
        event_metadata=metadata, created_at=now))


def _failed_factor(db, row, purpose, now, proof=None):
    _budget(row, purpose, now, failure=True)
    if proof is not None:
        proof.attempts += 1
    commit(db)  # Failed attempts survive a new challenge and another worker.
    fail(400, "mfa_verification_failed")


def verify_factor(db, row, *, code=None, recovery_code=None, purpose, now, proof=None):
    configuration()
    if not row or not row.enabled_at:
        fail(403, "mfa_enrollment_required")
    _budget(row, purpose, now)
    if bool(code) == bool(recovery_code):
        fail(422, "mfa_invalid_input")
    if code:
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
            _failed_factor(db, row, purpose, now, proof)
        counter = int(now.timestamp()) // 30
        try:
            secret = decrypt(row.secret_ciphertext, configuration(), _aad(row, row.generation, "active"))
        except Exception as error:
            logger.error("MFA ciphertext unavailable class=%s", type(error).__name__)
            fail(503, "mfa_service_unavailable")
        if counter <= row.last_counter or not hmac.compare_digest(totp(secret, counter), code):
            _failed_factor(db, row, purpose, now, proof)
        row.last_counter = counter
        return "otp"
    if not isinstance(recovery_code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{22}", recovery_code):
        _failed_factor(db, row, purpose, now, proof)
    item = db.scalar(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == row.user_id,
        MfaRecoveryCode.generation == row.generation,
        MfaRecoveryCode.code_hash == opaque_digest("recovery", recovery_code),
        MfaRecoveryCode.used_at.is_(None)))
    if item is None:
        _failed_factor(db, row, purpose, now, proof)
    item.used_at = now
    return "recovery"


def _require_session_capacity(user):
    if type(user.session_version) is not int or not 0 <= user.session_version < MAX_SV:
        fail(409, "mfa_session_version_exhausted")


def _revoke_sessions(db, user):
    _require_session_capacity(user)
    user.session_version += 1
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))


def _codes(db, row, now):
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == row.user_id))
    codes = [secrets.token_urlsafe(16) for _ in range(8)]
    for code in codes:
        db.add(MfaRecoveryCode(user_id=row.user_id, generation=row.generation,
            code_hash=opaque_digest("recovery", code), created_at=now))
    return codes


def login(db, expected, *, remember=False, method="password", now=None):
    """Primary proof has already been verified; serialize factor/mint decision."""
    user, identity = lock_actor(db, expected)
    now = instant(now)
    row = credential(db, user.id)
    if row and row.enabled_at:
        configuration()
        _budget(row, "login", now)
        token, proof = _proof(db, user, row, "login", now, method=method, remember=remember)
        audit(db, user, "mfa_login_challenge", now, primary_method=method)
        commit(db)
        return {"mfa_required": True, "challenge": token, "expires_at": now + PROOF_TTL,
                "methods": ["totp", "recovery_code"]}
    from web.auth import crear_token_pair
    tokens = crear_token_pair(identity, remember_me=remember, db=db)
    commit(db)
    return {"mfa_required": False, "token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"], "tipo": identity["tipo"], "role": identity["role"],
        "team_gym_id": identity.get("team_gym_id"), "nombre": (identity["nombre"] + " " + identity.get("apellido", "")).strip(),
        "email": identity["email"]}


def verify_login(db, token, *, code=None, recovery_code=None, now=None):
    clock_argument = now
    now = instant(now)
    proof = _find_proof(db, token, "login", now)
    expected = {"id": proof.user_id, "sv": proof.session_version}
    user = db.get(Usuario, proof.user_id)
    expected["team_gym_id"] = user.team_gym_id if user else None
    user, identity = lock_actor(db, expected)
    now = instant(clock_argument)
    proof = _find_proof(db, token, "login", now, user=user)
    row = credential(db, user.id)
    if not row or row.generation != proof.generation:
        fail(400, "mfa_proof_unavailable")
    method = verify_factor(db, row, code=code, recovery_code=recovery_code, purpose="login", now=now, proof=proof)
    proof.consumed_at = now
    proof.factor_verified_at = now
    from web.auth import crear_token_pair
    claims = {"amr": ["pwd" if proof.primary_method == "password" else "google", method],
              "mfa_generation": row.generation, "mfa_at": now.timestamp()}
    tokens = crear_token_pair(identity, remember_me=proof.remember_me, db=db, mfa_claims=claims)
    audit(db, user, "mfa_login", now, method=method)
    commit(db)
    return {"token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
        "tipo": identity["tipo"], "role": identity["role"], "team_gym_id": identity.get("team_gym_id"),
        "nombre": identity["nombre"], "email": identity["email"]}


def status(db, expected, *, now=None):
    # Read-only: no implicit row creation, counter mutation or commit.
    user = db.get(Usuario, expected["id"])
    identity = current_identity(db, user)
    if identity["session_version"] != expected.get("session_version", expected.get("sv", 0)):
        fail(401, "mfa_identity_unavailable")
    bind_mfa_actor(db, user.id)
    row = credential(db, user.id)
    remaining = 0 if not row else len(db.scalars(select(MfaRecoveryCode.id).where(
        MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.generation == row.generation,
        MfaRecoveryCode.used_at.is_(None))).all())
    return {"enabled": bool(row and row.enabled_at),
        "pending": bool(row and row.pending_expires_at and aware(row.pending_expires_at) > instant(now)),
        "recovery_codes_remaining": remaining, "methods": ["totp", "recovery_code"],
        "required_for_privileged_actions": identity["role"] in {"owner", "admin"},
        "totp_period_seconds": 30, "challenge_lifetime_seconds": 300}


def reauthenticate(db, expected, access, *, password=None, google_identity=None, now=None):
    configuration()
    user, identity = lock_actor(db, expected)
    now = instant(now)
    row = credential(db, user.id, create=True)
    _budget(row, "reauth", now)
    from web.auth import verify_password
    valid = bool(password and verify_password(password, user.password_hash))
    expires = now + PROOF_TTL
    if google_identity is not None:
        from web.services.google_identity import VerifiedGooglePrimary
        valid = (isinstance(google_identity, VerifiedGooglePrimary) and google_identity.email == user.email
            and 0 <= (now - google_identity.authenticated_at).total_seconds() < PROOF_TTL.total_seconds())
        if valid:
            expires = min(expires, google_identity.authenticated_at + PROOF_TTL)
    if not valid:
        _budget(row, "reauth", now, failure=True)
        commit(db)
        fail(400, "mfa_verification_failed")
    token, proof = _proof(db, user, row, "reauth", now, access=access,
        method="google" if google_identity is not None else "password", expires=expires)
    commit(db)
    return {"reauthentication_token": token, "expires_at": expires}


def admit_google_reauthentication(db, expected, *, now=None):
    """Durable pre-provider budget, not an authentication result or a grant."""
    configuration()
    user, _ = lock_actor(db, expected)
    now = instant(now)
    row = credential(db, user.id, create=True)
    _budget(row, "google_primary", now, failure=True)
    commit(db)


def enroll(db, expected, access, proof_token, *, code=None, recovery_code=None, now=None):
    key = configuration()
    user, _ = lock_actor(db, expected)
    _require_session_capacity(user)
    now = instant(now)
    row = credential(db, user.id, create=True)
    proof = _find_proof(db, proof_token, "reauth", now, user=user, access=access)
    if row.enabled_at:
        verify_factor(db, row, code=code, recovery_code=recovery_code, purpose="replace", now=now)
    elif code is not None or recovery_code is not None:
        fail(422, "mfa_invalid_input")
    seed = secrets.token_bytes(20)
    enrollment = uuid.uuid4().hex
    row.pending_id = enrollment
    row.pending_ciphertext = encrypt(seed, key, _aad(row, row.generation + 1, "pending:" + enrollment))
    row.pending_expires_at = now + ENROLL_TTL
    proof.consumed_at = now
    audit(db, user, "mfa_enrollment_started", now)
    encoded = base64.b32encode(seed).decode("ascii").rstrip("=")
    uri = "otpauth://totp/" + quote("MetodoBase:" + user.email, safe="") + "?" + urlencode(
        {"secret": encoded, "issuer": "MetodoBase", "algorithm": "SHA1", "digits": 6, "period": 30})
    # Capture primitive output while the authenticated LOCAL capability is
    # valid. Never perform an expired-ORM lazy load after the confirmed commit.
    commit(db)
    return {"enrollment_id": enrollment, "secret": encoded, "otpauth_uri": uri,
        "expires_at": now + ENROLL_TTL, "shown_once": True}


def confirm_enrollment(db, expected, enrollment, code, *, now=None):
    key = configuration()
    user, _ = lock_actor(db, expected)
    _require_session_capacity(user)
    now = instant(now)
    row = credential(db, user.id)
    if (not row or not row.pending_id or row.pending_id != enrollment
            or aware(row.pending_expires_at) <= now):
        fail(400, "mfa_enrollment_unavailable")
    _budget(row, "enroll", now)
    seed = decrypt(row.pending_ciphertext, key, _aad(row, row.generation + 1, "pending:" + enrollment))
    counter = int(now.timestamp()) // 30
    if not isinstance(code, str) or not hmac.compare_digest(totp(seed, counter), code):
        _failed_factor(db, row, "enroll", now)
    row.generation += 1
    row.secret_ciphertext = encrypt(seed, key, _aad(row, row.generation, "active"))
    row.enabled_at = now
    row.last_counter = counter
    row.pending_id = row.pending_ciphertext = row.pending_expires_at = None
    codes = _codes(db, row, now)
    _revoke_sessions(db, user)
    audit(db, user, "mfa_enabled", now)
    commit(db)
    return {"success": True, "enabled": True, "recovery_codes": codes,
        "shown_once": True, "reauthenticate": True}


def change_factor(db, expected, access, proof_token, *, revoke=False, code=None, recovery_code=None, now=None):
    configuration()
    user, _ = lock_actor(db, expected)
    _require_session_capacity(user)
    now = instant(now)
    row = credential(db, user.id)
    proof = _find_proof(db, proof_token, "reauth", now, user=user, access=access)
    method = verify_factor(db, row, code=code, recovery_code=recovery_code,
        purpose="revoke" if revoke else "codes", now=now)
    proof.consumed_at = now
    if revoke:
        row.secret_ciphertext = row.enabled_at = None
        row.pending_id = row.pending_ciphertext = row.pending_expires_at = None
        db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id))
        result = {"success": True, "enabled": False, "reauthenticate": True}
    else:
        result = {"success": True, "recovery_codes": _codes(db, row, now),
                  "shown_once": True, "reauthenticate": True}
    _revoke_sessions(db, user)
    audit(db, user, "mfa_revoked" if revoke else "mfa_recovery_rotated", now, method=method)
    commit(db)
    return result


def _locked_access(access, user, identity, now):
    """Verify the MAC and access context without a second database Session."""
    from web.auth import _decode_token, _valid_token_payload
    claims = _decode_token(access)
    # Identity was reloaded under the account locks above. Verify the signed
    # access against that SAME identity/transaction instead of opening a second
    # Session (which deadlocks a legitimate pool of size one).
    if (not _valid_token_payload(claims, "access") or claims["id"] != user.id
            or claims.get("iss") != "metodobase" or claims.get("aud") != "metodobase-web"
            or claims.get("v") != 1 or claims["exp"] <= now.timestamp()
            or claims.get("sv", 0) != user.session_version
            or claims.get("team_gym_id") != identity.get("team_gym_id")):
        fail(401, "mfa_identity_unavailable")
    return claims


def issue_step_up(db, expected, access, method, path, body, *, idempotency_key=None,
                  code=None, recovery_code=None, now=None):
    from web.services.mfa_actions import specification, authorize, binding
    configuration()
    action, target, spec = specification(method, path, body, idempotency_key)
    user, identity = lock_actor(db, expected, extra_ids=[target] if target else [])
    now = instant(now)
    claims = _locked_access(access, user, identity, now)
    gym_id = authorize(db, identity, action, target)
    row = credential(db, user.id)
    if not row or not row.enabled_at:
        fail(403, "mfa_enrollment_required")
    if (claims.get("mfa_generation") != row.generation
            or claims.get("amr") not in (["pwd", "otp"], ["google", "otp"], ["pwd", "recovery"], ["google", "recovery"])):
        fail(403, "mfa_fresh_verification_required")
    if claims["mfa_at"] > now.timestamp():
        fail(403, "mfa_fresh_verification_required")
    _budget(row, "stepup", now)
    if code is not None or recovery_code is not None:
        verify_factor(db, row, code=code, recovery_code=recovery_code, purpose="stepup", now=now)
        factor_time = now
    else:
        # A recently verified factor can authorize distinct single-use grants;
        # this never accepts the same OTP as a second authentication event.
        timestamp = claims.get("mfa_at") if claims else None
        factor_time = (datetime.fromtimestamp(timestamp,timezone.utc)
            if type(timestamp) in (int,float) and math.isfinite(timestamp) and 0 <= now.timestamp()-timestamp < PROOF_TTL.total_seconds()
            else None)
        witness = db.scalar(select(MfaAuthorization.factor_verified_at).where(
            MfaAuthorization.user_id == user.id, MfaAuthorization.purpose == "action",
            MfaAuthorization.session_version == user.session_version, MfaAuthorization.generation == row.generation,
            MfaAuthorization.access_hash == access_digest(access),
            MfaAuthorization.factor_verified_at <= now,
            MfaAuthorization.factor_verified_at > now - PROOF_TTL).order_by(MfaAuthorization.factor_verified_at.desc()).limit(1))
        if witness is not None and (factor_time is None or aware(witness) > factor_time):
            factor_time = aware(witness)
        if factor_time is None:
            fail(403, "mfa_fresh_verification_required")
    expires = min(factor_time + PROOF_TTL, datetime.fromtimestamp(claims["exp"],timezone.utc))
    token, proof = _proof(db, user, row, "action", now, access=access, binding=binding(spec, gym_id),
        method="google" if claims["amr"][0] == "google" else "password", expires=expires, factor_time=factor_time)
    audit(db, user, "mfa_step_up_issued", now, action=action)
    commit(db)
    return {"grant": token, "expires_at": expires, "action": action,
            "method": method, "path": path, "single_use": True}


def consume_step_up(db, expected, access, token, method, path, body, *, idempotency_key=None, now=None):
    """No COMMIT: the exact business mutation/intention confirms grant use."""
    from web.services.mfa_actions import specification, authorize, binding
    action, target, spec = specification(method, path, body, idempotency_key)
    user, identity = lock_actor(db, expected, extra_ids=[target] if target else [])
    now = instant(now)
    claims = _locked_access(access, user, identity, now)
    gym_id = authorize(db, identity, action, target)
    row = credential(db, user.id)
    if not row or not row.enabled_at:
        fail(403, "mfa_enrollment_required")
    configuration()
    if not token:
        fail(403, "mfa_step_up_required")
    proof = _find_proof(db, token, "action", now, user=user, access=access)
    if (proof.generation != row.generation or claims.get("mfa_generation") != row.generation
            or not hmac.compare_digest(proof.action_binding or "", binding(spec, gym_id))):
        fail(403, "mfa_action_mismatch")
    result = db.execute(update(MfaAuthorization).where(MfaAuthorization.token_hash == proof.token_hash,
        MfaAuthorization.user_id == user.id, MfaAuthorization.purpose == "action",
        MfaAuthorization.consumed_at.is_(None), MfaAuthorization.session_version == user.session_version,
        MfaAuthorization.expires_at > now).values(consumed_at=now).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        fail(409, "mfa_grant_consumed")
    audit(db, user, "mfa_step_up_consumed", now, action=action)
    return identity
