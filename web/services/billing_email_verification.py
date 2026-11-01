"""One-use mailbox confirmation before a manual subscription purchase.

Identity and authorization come from the caller's fresh database projection.
Redis stores bounded signed bindings and keyed digests, never a code or email.
No process-local fallback can authorize a payment during backend uncertainty.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
import re
import secrets

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
TTL_SECONDS = 600
GRANT_TTL_SECONDS = 300
RESEND_SECONDS = 60
MAX_ATTEMPTS = 5
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
CODE_PATTERN = re.compile(r"[0-9]{6}\Z", re.ASCII)
KEY_PATTERN = re.compile(r"[\x20-\x7e]{1,128}\Z", re.ASCII)
_HEX = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
_BINDING_KEYS = frozenset(("actor_id", "session_version", "notification_contact_version",
    "email_hash", "access_hash", "tipo", "role", "team_gym_id", "action", "plan", "catalog_digest"))
_PREFIX = "billing-email:v1:"

# The cooldown and active challenge change atomically. Older challenges and
# grants expire normally; their active-reference mismatch prevents reuse.
BEGIN_LUA = """
local wait = redis.call('TTL', KEYS[3])
if wait > 0 then return {0, wait} end
if redis.call('EXISTS', KEYS[1]) ~= 0 then return {-1} end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
redis.call('SET', KEYS[2], ARGV[4], 'EX', ARGV[2])
redis.call('SET', KEYS[3], '1', 'EX', ARGV[3])
return {1}
"""

ACTIVATE_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[4] then return {0} end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then return {0} end
local item = cjson.decode(raw)
if item.payload ~= ARGV[1] or item.signature ~= ARGV[2] or item.code_digest ~= ARGV[3] then return {0} end
item.delivery_ready = true
redis.call('SET', KEYS[1], cjson.encode(item), 'PX', ttl)
return {1}
"""

# A correct code is consumed and its grant created in the SAME operation.
# Incorrect codes retain the original TTL and every failed attempt survives.
VERIFY_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[6] then return {0} end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then redis.call('DEL', KEYS[1]); return {0} end
local item = cjson.decode(raw)
if item.payload ~= ARGV[1] or item.signature ~= ARGV[2] or item.delivery_ready ~= true then return {0} end
if item.code_digest ~= ARGV[3] then
    item.attempts = tonumber(item.attempts) + 1
    if item.attempts >= tonumber(ARGV[4]) then redis.call('DEL', KEYS[1])
    else redis.call('SET', KEYS[1], cjson.encode(item), 'PX', ttl) end
    return {0}
end
if redis.call('EXISTS', KEYS[3]) ~= 0 then return {-1} end
redis.call('SET', KEYS[3], ARGV[5], 'EX', ARGV[7])
redis.call('SET', KEYS[2], ARGV[6], 'EX', ARGV[7])
redis.call('DEL', KEYS[1])
return {1}
"""

# The signed replacement binds a grant to one exact idempotent operation.
# A concurrent different intent cannot replace it; confirmation preserves TTL.
CONSUME_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw or raw ~= ARGV[1] or redis.call('GET', KEYS[2]) ~= ARGV[2] then return {0} end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then redis.call('DEL', KEYS[1]); return {0} end
if ARGV[3] == 'delete' then redis.call('DEL', KEYS[1])
elseif ARGV[3] == 'replace' then redis.call('SET', KEYS[1], ARGV[4], 'PX', ttl)
elseif ARGV[3] ~= 'confirm' then return {0} end
return {1}
"""


def fail(status, code, *, retry_after=None):
    messages = {
        "billing_email_unavailable": "La verificación por correo no está disponible. Consulta el estado de tu suscripción antes de reintentar.",
        "billing_email_delivery_unconfirmed": "No pudimos confirmar el envío del código. Consulta el estado de tu suscripción antes de reintentar.",
        "billing_email_code_invalid": "El código no es válido o venció. Revisa el código o solicita uno nuevo.",
        "billing_email_required": "Confirma el código enviado a tu correo antes de continuar al pago.",
        "billing_email_throttled": "Espera antes de solicitar o verificar otro código.",
        "billing_email_unconfirmed": "No pudimos confirmar esta verificación. Solicita un código nuevo.",
        "billing_email_invalid_input": "Revisa los datos de la verificación.",
    }
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    if retry_after is not None:
        headers["Retry-After"] = str(max(int(retry_after), 1))
    raise HTTPException(status, {"code": code, "message": messages[code]}, headers=headers)


def _now():
    return datetime.now(timezone.utc)


def _configuration():
    from web.settings import get_settings
    settings = get_settings()
    if (not settings.REDIS_URL or not settings.RESEND_API_KEY
            or not getattr(settings, "RESEND_FROM_EMAIL", "")
            or not isinstance(settings.SECRET_KEY, str) or len(settings.SECRET_KEY) < 32):
        fail(503, "billing_email_unavailable")
    return settings


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(purpose, value):
    from web.settings import get_settings
    return hmac.new(get_settings().SECRET_KEY.encode("utf8"),
        ("billing-email-v1:" + purpose + ":" + value).encode("utf8"), hashlib.sha256).hexdigest()


def _binding(value):
    if not isinstance(value, dict) or set(value) != _BINDING_KEYS:
        fail(503, "billing_email_unconfirmed")
    for key in ("actor_id", "tipo", "role", "action", "plan"):
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= 128 or any(ord(c) < 32 for c in value[key]):
            fail(503, "billing_email_unconfirmed")
    for key in ("session_version", "notification_contact_version"):
        if type(value[key]) is not int or not 0 <= value[key] <= 2147483647:
            fail(503, "billing_email_unconfirmed")
    if value["team_gym_id"] is not None and (not isinstance(value["team_gym_id"], str)
            or not 1 <= len(value["team_gym_id"]) <= 128):
        fail(503, "billing_email_unconfirmed")
    for key in ("email_hash", "access_hash", "catalog_digest"):
        if not isinstance(value[key], str) or not _HEX.fullmatch(value[key]):
            fail(503, "billing_email_unconfirmed")
    # Copy through canonical JSON so caller mutations cannot change issued data.
    return json.loads(_canonical(value))


def _account_key(binding, kind):
    return _PREFIX + kind + ":" + _digest("actor", binding["actor_id"])


def _challenge_key(challenge):
    return _PREFIX + "challenge:" + _digest("challenge", challenge)


def _grant_key(token):
    return _PREFIX + "grant:" + _digest("grant", token)


async def _redis():
    from web.rate_limiter_redis import _get_redis
    return await _get_redis()


async def _limit(request, purpose, binding):
    from web.middleware.rate_limiter import get_client_identifier
    from web.rate_limiter_redis import check_rate_limit
    buckets = (("actor", binding["actor_id"], 3 if purpose == "send" else 10),
               ("ip", get_client_identifier(request), 10 if purpose == "send" else 30))
    for kind, value, maximum in buckets:
        key = _PREFIX + "limit:" + purpose + ":" + kind + ":" + _digest("limit:" + kind, value)
        allowed, info, _ = await check_rate_limit(key, maximum, 900, use_redis=True, sensitive=True)
        if not allowed:
            fail(429, "billing_email_throttled", retry_after=info["retry_after"])


def _text(value):
    return value.decode("utf8") if isinstance(value, bytes) else value


def _signed(purpose, token, state):
    payload = _canonical(state)
    return {"payload": payload, "signature": _digest(purpose, token + ":" + payload)}


def _decode(raw, purpose, token):
    try:
        if raw is None or len(raw) > 8192:
            raise ValueError()
        item = json.loads(_text(raw))
        payload, signature = item["payload"], item["signature"]
        if (not isinstance(payload, str) or not isinstance(signature, str)
                or not hmac.compare_digest(_digest(purpose, token + ":" + payload), signature)):
            raise ValueError()
        return item, json.loads(payload)
    except (TypeError, ValueError, KeyError, UnicodeError):
        fail(503, "billing_email_unconfirmed")


def _masked_email(email):
    local, domain = email.rsplit("@", 1)
    return local[0] + "***@" + domain


async def begin(binding, recipient, request):
    _configuration()
    binding = _binding(binding)
    if (not isinstance(recipient, str) or len(recipient) > 255 or recipient.count("@") != 1
            or not all(recipient.split("@")) or any(ord(c) < 33 or ord(c) == 127 for c in recipient)):
        fail(503, "billing_email_unconfirmed")
    if not hmac.compare_digest(binding["email_hash"], hashlib.sha256(recipient.encode("utf8")).hexdigest()):
        fail(503, "billing_email_unconfirmed")
    await _limit(request, "send", binding)
    challenge = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1000000):06d}"
    expiry = _now() + timedelta(seconds=TTL_SECONDS)
    reference = _digest("challenge", challenge)
    state = {"binding": binding, "expires_at": expiry.timestamp(), "challenge_ref": reference}
    item = {**_signed("challenge-state", challenge, state),
        "code_digest": _digest("code", challenge + ":" + code), "attempts": 0, "delivery_ready": False}
    key, active = _challenge_key(challenge), _account_key(binding, "active")
    try:
        cache = await _redis()
        result = await cache.eval(BEGIN_LUA, 3, key, active, _account_key(binding, "cooldown"),
            _canonical(item), TTL_SECONDS, RESEND_SECONDS, reference)
        if not result or int(result[0]) == -1:
            fail(503, "billing_email_unconfirmed")
        if int(result[0]) != 1:
            fail(429, "billing_email_throttled", retry_after=result[1])
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Billing email challenge unavailable class=%s", type(error).__name__)
        fail(503, "billing_email_unavailable")
    from web.services.email_service import send_billing_verification_code
    labels = {"standard": "Standard", "gym_comercial": "Gym Comercial", "clinica": "Clínica",
              "pro": "Pro", "pro_usuario": "Pro", "manage": "gestión de tu suscripción"}
    try:
        accepted = await run_in_threadpool(send_billing_verification_code, recipient, code,
            labels.get(binding["plan"], "suscripción"))
    except Exception as error:
        logger.error("Billing email transport unconfirmed class=%s", type(error).__name__)
        accepted = False
    if accepted is not True:
        try:
            await cache.delete(key)
        except Exception as error:
            logger.error("Billing email discard unavailable class=%s", type(error).__name__)
        fail(503, "billing_email_delivery_unconfirmed")
    try:
        result = await cache.eval(ACTIVATE_LUA, 2, key, active,
            item["payload"], item["signature"], item["code_digest"], reference)
        if not result or int(result[0]) != 1:
            fail(503, "billing_email_unconfirmed")
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Billing email activation unconfirmed class=%s", type(error).__name__)
        fail(503, "billing_email_unconfirmed")
    return {"email_verification_required": True, "challenge": challenge,
        "expires_at": expiry.isoformat(), "masked_email": _masked_email(recipient),
        "resend_after_seconds": RESEND_SECONDS}


async def verify(binding, challenge, code, request):
    _configuration()
    binding = _binding(binding)
    await _limit(request, "verify", binding)
    if (not isinstance(challenge, str) or not TOKEN_PATTERN.fullmatch(challenge)
            or not isinstance(code, str) or not CODE_PATTERN.fullmatch(code)):
        fail(400, "billing_email_code_invalid")
    key = _challenge_key(challenge)
    token = secrets.token_urlsafe(32)
    try:
        cache = await _redis()
        raw = await cache.get(key)
        if raw is None:
            fail(400, "billing_email_code_invalid")
        item, state = _decode(raw, "challenge-state", challenge)
        if (state.get("binding") != binding or state.get("challenge_ref") != _digest("challenge", challenge)
                or type(state.get("expires_at")) not in (int, float) or state["expires_at"] <= _now().timestamp()):
            fail(400, "billing_email_code_invalid")
        proof_state = {"binding": binding, "challenge_ref": state["challenge_ref"],
            "expires_at": (_now() + timedelta(seconds=GRANT_TTL_SECONDS)).timestamp(), "used_binding": None}
        proof = _canonical(_signed("grant-state", token, proof_state))
        result = await cache.eval(VERIFY_LUA, 3, key, _account_key(binding, "active"), _grant_key(token),
            item["payload"], item["signature"], _digest("code", challenge + ":" + code), MAX_ATTEMPTS,
            proof, state["challenge_ref"], GRANT_TTL_SECONDS)
        if not result or int(result[0]) != 1:
            fail(400, "billing_email_code_invalid")
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Billing email verification unconfirmed class=%s", type(error).__name__)
        fail(503, "billing_email_unconfirmed")
    return {"verification_token": token, "expires_in_seconds": GRANT_TTL_SECONDS}


async def consume(binding, verification_token, request, *, body, idempotency_key):
    _configuration()
    binding = _binding(binding)
    if not isinstance(verification_token, str) or not TOKEN_PATTERN.fullmatch(verification_token):
        fail(403, "billing_email_required")
    if idempotency_key is not None and (not isinstance(idempotency_key, str) or not KEY_PATTERN.fullmatch(idempotency_key)):
        fail(422, "billing_email_invalid_input")
    try:
        encoded_body = _canonical(body)
        if not isinstance(body, dict) or len(encoded_body.encode("ascii")) > 16384:
            raise ValueError()
    except (TypeError, ValueError):
        fail(422, "billing_email_invalid_input")
    fingerprint = _digest("request", _canonical({"method": request.method, "path": request.url.path,
        "body": encoded_body, "idempotency_key": idempotency_key}))
    key = _grant_key(verification_token)
    try:
        cache = await _redis()
        # At most one retry handles a concurrent first consume of the SAME
        # idempotent operation. No caller body or opaque proof is logged.
        for _ in range(2):
            raw = await cache.get(key)
            if raw is None:
                fail(403, "billing_email_required")
            _, state = _decode(raw, "grant-state", verification_token)
            if (state.get("binding") != binding or type(state.get("expires_at")) not in (int, float)
                    or state["expires_at"] <= _now().timestamp()
                    or not isinstance(state.get("challenge_ref"), str) or not _HEX.fullmatch(state["challenge_ref"])):
                fail(403, "billing_email_required")
            used = state.get("used_binding")
            if used is not None and (idempotency_key is None or not isinstance(used, str)
                    or not hmac.compare_digest(used, fingerprint)):
                fail(403, "billing_email_required")
            if idempotency_key is None:
                mode, replacement = "delete", ""
            elif used is not None:
                mode, replacement = "confirm", ""
            else:
                mode = "replace"
                state["used_binding"] = fingerprint
                replacement = _canonical(_signed("grant-state", verification_token, state))
            result = await cache.eval(CONSUME_LUA, 2, key, _account_key(binding, "active"),
                _text(raw), state["challenge_ref"], mode, replacement)
            if result and int(result[0]) == 1:
                return None
        fail(403, "billing_email_required")
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Billing email grant unconfirmed class=%s", type(error).__name__)
        fail(503, "billing_email_unconfirmed")
