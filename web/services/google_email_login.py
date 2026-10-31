"""Google primary plus one-use email proof, before account creation or sessions.

Redis retains bounded, authenticated snapshots and keyed code digests only.
An existing legacy account is authenticated by proved mailbox access; this
never backfills a provider subject or merges account data.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
import re
import secrets
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from config.settings import DEFAULT_EMAIL_FROM
from web.database.models import AuthExternalIdentity, Usuario, UserRole
from web.services import google_link, mfa_service as mfa
from web.services.google_identity import ISSUER

logger = logging.getLogger(__name__)
TTL_SECONDS = 600
MAX_ATTEMPTS = 5
CHALLENGE_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
CODE_PATTERN = re.compile(r"[0-9]{6}")

# Validation, attempt accounting, expiry preservation and consumption are one
# Redis operation. A correct proof is deleted before any account/session work.
CONSUME_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw then return {0} end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then redis.call('DEL', KEYS[1]); return {0} end
local item = cjson.decode(raw)
if item.code_digest ~= ARGV[1] then
    item.attempts = tonumber(item.attempts) + 1
    if item.attempts >= tonumber(ARGV[2]) then
        redis.call('DEL', KEYS[1])
    else
        redis.call('SET', KEYS[1], cjson.encode(item), 'PX', ttl)
    end
    return {0}
end
redis.call('DEL', KEYS[1])
return {1, item.payload, item.signature}
"""


def fail(status, code):
    messages = {
        "google_email_unavailable": "La verificación por correo no está disponible temporalmente.",
        "google_email_delivery_unconfirmed": "No pudimos confirmar el envío del código. Vuelve a intentarlo.",
        "google_email_code_invalid": "El código no es válido o venció. Revisa el código o inicia de nuevo con Google.",
        "google_email_throttled": "Espera antes de volver a solicitar o verificar un código.",
        "google_email_identity_changed": "La cuenta cambió. Inicia de nuevo con Google.",
        "google_email_unconfirmed": "No pudimos confirmar la verificación. Inicia de nuevo con Google.",
    }
    raise HTTPException(status, {"code": code, "message": messages[code]},
                        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


def _configuration():
    from web.settings import get_settings
    settings = get_settings()
    if (not settings.REDIS_URL or not settings.RESEND_API_KEY
            or not getattr(settings, "RESEND_FROM_EMAIL", DEFAULT_EMAIL_FROM)
            or not isinstance(settings.SECRET_KEY, str) or len(settings.SECRET_KEY) < 32):
        fail(503, "google_email_unavailable")
    return settings


def _digest(purpose, value):
    from web.settings import get_settings
    return hmac.new(get_settings().SECRET_KEY.encode("utf-8"),
                    ("google-email-v1:" + purpose + ":" + value).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _key(challenge):
    return "gel:v1:challenge:" + _digest("challenge", challenge)


async def _redis():
    from web.rate_limiter_redis import _get_redis
    return await _get_redis()


async def _limit(request, purpose, email=None):
    from web.middleware.rate_limiter import get_client_identifier
    from web.rate_limiter_redis import check_rate_limit
    buckets = [("ip", get_client_identifier(request), 5 if purpose == "send" else 30)]
    if email is not None:
        buckets.append(("email", email, 5))
    for kind, value, maximum in buckets:
        key = "gel:v1:limit:" + purpose + ":" + kind + ":" + _digest("limit:" + kind, value)
        allowed, info, _ = await check_rate_limit(key, maximum, 900, use_redis=True, sensitive=True)
        if not allowed:
            try:
                fail(429, "google_email_throttled")
            except HTTPException as error:
                error.headers["Retry-After"] = str(max(int(info["retry_after"]), 1))
                raise


@contextmanager
def _owned_session():
    from web.database.engine import SessionLocal
    from web.database.tenant_context import current_tenant
    token = current_tenant.set("")
    db = None
    try:
        db = SessionLocal()
        try:
            yield db
        except Exception:
            google_link.rollback(db)
            raise
        finally:
            google_link.close_owned_session(db)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Google email database unconfirmed class=%s", type(error).__name__)
        fail(503, "google_email_unconfirmed")
    finally:
        current_tenant.reset(token)


def _binding(db, subject):
    return db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.issuer == ISSUER,
        AuthExternalIdentity.subject == subject).execution_options(populate_existing=True))


def _any_binding(db, user_id):
    return db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.issuer == ISSUER,
        AuthExternalIdentity.user_id == user_id).limit(1)) is not None


def _user_snapshot(db, user):
    identity = mfa.current_identity(db, user)
    return {**identity, "notification_contact_version": user.notification_contact_version}


def snapshot(info, tipo):
    """Read and release the target before Redis/provider transport; no writes."""
    with _owned_session() as db:
        binding = _binding(db, info["sub"])
        if binding is not None:
            if binding.revoked_at is not None:
                google_link.fail(409, "google_link_required")
            user = db.get(Usuario, binding.user_id, populate_existing=True)
            target = _user_snapshot(db, user)
            mode = "bound"
            association = {"id": binding.id, "version": binding.version}
        else:
            user = db.scalar(select(Usuario).where(Usuario.email == info["email"]))
            if user is None:
                target, association, mode = None, None, "new"
            else:
                # Email proof cannot undo an existing or revoked Google binding.
                if _any_binding(db, user.id):
                    google_link.fail(409, "google_link_required")
                target, association, mode = _user_snapshot(db, user), None, "legacy"
    given = info.get("given_name", info.get("name", "Usuario"))
    family = info.get("family_name", "")
    return {"mode": mode, "target": target, "binding": association,
        "provider": {"iss": ISSUER, "sub": info["sub"], "email": info["email"],
            "given_name": (given.strip() or "Usuario")[:150] if isinstance(given, str) else "Usuario",
            "family_name": family.strip()[:150] if isinstance(family, str) else ""},
        "tipo": tipo if tipo in {"usuario", "gym"} else "usuario"}


def _masked_email(email):
    local, domain = email.rsplit("@", 1)
    return local[0] + "***@" + domain


async def begin(info, tipo, request):
    """A signed Google primary only sends a code; it never creates a session."""
    _configuration()
    await _limit(request, "send", info["email"])
    state = await run_in_threadpool(snapshot, info, tipo)
    expires = datetime.now(timezone.utc) + timedelta(seconds=TTL_SECONDS)
    state["expires_at"] = expires.timestamp()
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    challenge = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1000000):06d}"
    item = json.dumps({"payload": payload, "signature": _digest("snapshot", challenge + ":" + payload),
        "code_digest": _digest("code", challenge + ":" + code), "attempts": 0}, separators=(",", ":"))
    key = _key(challenge)
    try:
        cache = await _redis()
        if not await cache.set(key, item, ex=TTL_SECONDS, nx=True):
            fail(503, "google_email_unconfirmed")
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Google email challenge unavailable class=%s", type(error).__name__)
        fail(503, "google_email_unavailable")
    from web.services.email_service import send_google_login_code
    try:
        sent = await run_in_threadpool(send_google_login_code, info["email"], code)
    except Exception as error:
        logger.error("Google email transport unconfirmed class=%s", type(error).__name__)
        sent = False
    if sent is not True:
        try:
            await cache.delete(key)
        except Exception as error:
            logger.error("Google email discard unavailable class=%s", type(error).__name__)
        fail(503, "google_email_delivery_unconfirmed")
    return {"email_verification_required": True, "challenge": challenge,
            "expires_at": expires.isoformat(), "masked_email": _masked_email(info["email"])}


def _create_new(db, state):
    """Never adopt a registration that appeared after this challenge's issue."""
    from web.auth import hash_password
    from web.database.tenant_context import bind_verified_subject
    info = state["provider"]
    if (_binding(db, info["sub"]) is not None
            or db.scalar(select(Usuario.id).where(Usuario.email == info["email"])) is not None):
        fail(409, "google_email_identity_changed")
    now = mfa.instant()
    kind = state["tipo"]
    user = Usuario(id=str(uuid.uuid4()), email=info["email"],
        password_hash=hash_password(secrets.token_urlsafe(48)), nombre=info["given_name"],
        apellido=info["family_name"], tipo=kind,
        role=UserRole.OWNER if kind == "gym" else UserRole.VIEWER,
        activo=True, session_version=0, fecha_registro=now)
    try:
        db.add(user)
        db.flush()
        db.add(AuthExternalIdentity(id=str(uuid.uuid4()), user_id=user.id,
            issuer=ISSUER, subject=info["sub"], created_at=now, version=1))
        if kind == "gym":
            from web.database.repository import crear_gym_profile
            bind_verified_subject(db, user.id)
            crear_gym_profile(db, user.id, {"nombre_negocio": user.nombre}, initialize_memberships=True)
        identity = mfa.current_identity(db, user)
        mfa.audit(db, user, "google_identity_registered", now)
        google_link.commit(db)
    except IntegrityError:
        google_link.rollback(db)
        fail(409, "google_email_identity_changed")
    return identity


def resolve(state):
    """Revalidate a consumed proof's exact account and authority snapshot."""
    with _owned_session() as db:
        if state["mode"] == "new":
            return _create_new(db, state)
        expected = state["target"]
        try:
            user, _ = mfa.lock_actor(db, expected)
        except HTTPException as error:
            if (error.status_code == 401 and isinstance(error.detail, dict)
                    and error.detail.get("code") == "mfa_identity_unavailable"):
                fail(409, "google_email_identity_changed")
            raise
        if _user_snapshot(db, user) != expected:
            fail(409, "google_email_identity_changed")
        binding = _binding(db, state["provider"]["sub"])
        if state["mode"] == "bound":
            if (binding is None or binding.revoked_at is not None or binding.user_id != user.id
                    or {"id": binding.id, "version": binding.version} != state["binding"]):
                fail(409, "google_email_identity_changed")
        elif (state["mode"] != "legacy" or binding is not None or _any_binding(db, user.id)
                or user.email != state["provider"]["email"]):
            fail(409, "google_email_identity_changed")
        identity = mfa.current_identity(db, user)
        mfa.audit(db, user, "google_email_verified", mfa.instant(), association=state["mode"])
        google_link.commit(db)
        return identity


async def verify(challenge, code, request):
    _configuration()
    await _limit(request, "verify")
    if (not isinstance(challenge, str) or CHALLENGE_PATTERN.fullmatch(challenge) is None
            or not isinstance(code, str) or CODE_PATTERN.fullmatch(code) is None):
        fail(400, "google_email_code_invalid")
    try:
        cache = await _redis()
        result = await cache.eval(CONSUME_LUA, 1, _key(challenge),
                                  _digest("code", challenge + ":" + code), MAX_ATTEMPTS)
        if not result or int(result[0]) != 1:
            fail(400, "google_email_code_invalid")
        payload, signature = result[1:3]
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if isinstance(signature, bytes):
            signature = signature.decode("ascii")
        if not hmac.compare_digest(_digest("snapshot", challenge + ":" + payload), signature):
            fail(503, "google_email_unconfirmed")
        state = json.loads(payload)
        if state["expires_at"] <= datetime.now(timezone.utc).timestamp():
            fail(400, "google_email_code_invalid")
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Google email consumption unconfirmed class=%s", type(error).__name__)
        fail(503, "google_email_unconfirmed")
    return await run_in_threadpool(resolve, state)
