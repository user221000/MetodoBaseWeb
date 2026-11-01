"""Fresh linked Google + mailbox proof for account-security reauthentication.

This is separate from login, contact confirmation and payment confirmation.
An existing verified contact never replaces the fresh proof. A successful code
only mints the existing session-bound MFA reauth proof; it cannot enable a
factor, spend a recovery code, create a session or authorize a payment itself.
"""
from datetime import timedelta
import hashlib
import hmac
import json
import logging
import math
import re
import secrets

from fastapi import HTTPException
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from web.account_values import validate_registration_email
from web.database.models import AuthExternalIdentity, Usuario
from web.services import mfa_service as mfa
from web.services.google_identity import ISSUER

logger = logging.getLogger(__name__)
TTL_SECONDS = 300
RESEND_SECONDS = 60
MAX_ATTEMPTS = 5
PREFIX = 'google-mfa-email:v1:'
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}\Z', re.ASCII)
CODE = re.compile(r'[0-9]{6}\Z', re.ASCII)
PURPOSE = 'account_security_reauthentication'

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
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[3] then return {0} end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then return {0} end
local item = cjson.decode(raw)
if item.payload ~= ARGV[1] or item.signature ~= ARGV[2] then return {0} end
item.delivery_ready = true
redis.call('SET', KEYS[1], cjson.encode(item), 'PX', ttl)
return {1}
"""

CONSUME_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[4] then return {0} end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then return {0} end
local item = cjson.decode(raw)
if item.delivery_ready ~= true or item.payload ~= ARGV[1] or item.signature ~= ARGV[2] then return {0} end
if item.code_digest ~= ARGV[3] then
    item.attempts = tonumber(item.attempts) + 1
    if item.attempts >= tonumber(ARGV[5]) then redis.call('DEL', KEYS[1])
    else redis.call('SET', KEYS[1], cjson.encode(item), 'PX', ttl) end
    return {0}
end
redis.call('DEL', KEYS[1])
redis.call('DEL', KEYS[2])
return {1}
"""


def fail(status, code, *, retry_after=None):
    messages = {
        'mfa_google_email_unavailable': 'La confirmación de seguridad por correo no está disponible. Vuelve a consultar el estado.',
        'mfa_google_email_delivery_unconfirmed': 'No pudimos confirmar el envío. Espera antes de iniciar otra verificación con Google.',
        'mfa_google_email_code_invalid': 'El código no es válido o venció. Revisa las seis cifras o inicia una nueva verificación con Google.',
        'mfa_google_email_identity_changed': 'La cuenta cambió. Inicia una nueva verificación con Google.',
        'mfa_google_email_link_required': 'Elige la cuenta de Google que está vinculada a tu cuenta de Método Base.',
        'mfa_google_email_throttled': 'Espera antes de solicitar o verificar otro código de seguridad.',
    }
    headers = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}
    if retry_after is not None:
        headers['Retry-After'] = str(max(1, int(retry_after)))
    raise HTTPException(status, {'code': code, 'message': messages[code]}, headers=headers)


def configuration():
    from web.settings import get_settings
    settings = get_settings()
    mfa.configuration()
    if (not settings.REDIS_URL or not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL
            or not isinstance(settings.SECRET_KEY, str) or len(settings.SECRET_KEY) < 32):
        fail(503, 'mfa_google_email_unavailable')
    return settings


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(purpose, value):
    from web.settings import get_settings
    return hmac.new(get_settings().SECRET_KEY.encode('utf-8'),
                    (PREFIX + purpose + ':' + value).encode('utf-8'), hashlib.sha256).hexdigest()


def key(challenge):
    return PREFIX + 'challenge:' + digest('challenge', challenge)


def actor_key(actor, kind):
    return PREFIX + kind + ':' + digest('actor', actor)


async def cache():
    from web.rate_limiter_redis import _get_redis
    return await _get_redis()


async def limit(request, actor, purpose):
    from web.middleware.rate_limiter import get_client_identifier
    from web.rate_limiter_redis import check_rate_limit
    for kind, value, maximum in (('actor', actor, 3 if purpose == 'send' else 10),
                                 ('ip', get_client_identifier(request), 10 if purpose == 'send' else 30)):
        bucket = PREFIX + 'limit:' + purpose + ':' + kind + ':' + digest('limit:' + kind, value)
        allowed, info, _ = await check_rate_limit(bucket, maximum, 900, use_redis=True, sensitive=True)
        if not allowed:
            fail(429, 'mfa_google_email_throttled', retry_after=info['retry_after'])


def snapshot(db, expected, access, *, info=None, previous=None):
    """Recheck all authorities in the same locked account/Google projection."""
    user, identity = mfa.lock_actor(db, expected)
    mfa._locked_access(access, user, identity, mfa.instant())
    subject = info['sub'] if info is not None else previous['subject']
    binding = db.scalar(select(AuthExternalIdentity).where(
        AuthExternalIdentity.issuer == ISSUER, AuthExternalIdentity.subject == subject,
        AuthExternalIdentity.user_id == user.id, AuthExternalIdentity.revoked_at.is_(None)).with_for_update())
    if binding is None:
        fail(403, 'mfa_google_email_link_required')
    try:
        recipient = validate_registration_email(user.email)
    except ValueError:
        fail(409, 'mfa_google_email_identity_changed')
    from web.services.account_security import epoch
    factor = mfa.credential(db, user.id)
    state = {'purpose': PURPOSE, 'actor_id': user.id, 'session_version': identity['session_version'],
             'role': identity['role'], 'tipo': identity['tipo'], 'team_gym_id': identity.get('team_gym_id'),
             'contact_version': epoch(user), 'email_hash': hashlib.sha256(recipient.encode('utf-8')).hexdigest(),
             'access_hash': hashlib.sha256(access.encode('utf-8')).hexdigest(),
             'issuer': ISSUER, 'subject': subject, 'google_binding_id': binding.id,
             'google_binding_version': binding.version,
             'factor_id': factor.factor_id if factor is not None else None,
             'factor_generation': factor.generation if factor is not None else 0,
             'factor_enabled': bool(factor and factor.enabled_at)}
    if previous is not None and state != previous:
        fail(409, 'mfa_google_email_identity_changed')
    return state, recipient


def owned_snapshot(expected, access, *, info=None, previous=None):
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        return snapshot(db, expected, access, info=info, previous=previous)


def admit(expected, access):
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        user, identity = mfa.lock_actor(db, expected)
        mfa._locked_access(access, user, identity, mfa.instant())
        mfa.admit_google_reauthentication(db, expected)


def finish(expected, access, previous, *, verified_at):
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        snapshot(db, expected, access, previous=previous)
        now = mfa.instant()
        if not 0 <= (now - verified_at).total_seconds() < mfa.PROOF_TTL.total_seconds():
            fail(400, 'mfa_google_email_code_invalid')
        # Freshness is established by this purpose-bound code, not Google iat
        # or a persisted contact flag. The old auth_time endpoint is unchanged.
        user = db.get(Usuario, expected['id'])
        row = mfa.credential(db, user.id, create=True)
        mfa._budget(row, 'reauth', now)
        from web.services.account_security import PENDING, epoch
        user.email_verified_at = verified_at
        user.email_verified_contact_version = epoch(user)
        for name in PENDING:
            setattr(user, name, None)
        # Use the existing proof factory and schema. This explicit trusted
        # boundary has verified Google subject + fresh purpose-specific mail;
        # it does not manufacture an ID-token auth_time claim.
        token, proof = mfa._proof(db, user, row, 'reauth', now, access=access, method='google',
                                  expires=verified_at + mfa.PROOF_TTL)
        expires = proof.expires_at
        mfa.audit(db, user, 'google_mail_reauthentication_verified', now)
        mfa.audit(db, user, 'email_contact_verified', now, purpose='security_reauthentication')
        mfa.commit(db)
        return {'reauthentication_token': token, 'expires_at': expires}


async def begin(expected, access, credential, request):
    configuration()
    await limit(request, expected['id'], 'send')
    await run_in_threadpool(admit, expected, access)
    from web.services.google_identity import verified_google_info
    info = await verified_google_info(credential)
    binding, recipient = await run_in_threadpool(owned_snapshot, expected, access, info=info)
    challenge = secrets.token_urlsafe(32)
    code = f'{secrets.randbelow(1000000):06d}'
    expires = mfa.instant() + timedelta(seconds=TTL_SECONDS)
    payload = canonical({'binding': binding, 'expires_at': expires.timestamp()})
    signature = digest('state', challenge + ':' + payload)
    item = {'payload': payload, 'signature': signature,
            'code_digest': digest('code', challenge + ':' + code), 'attempts': 0, 'delivery_ready': False}
    reference = digest('challenge', challenge)
    try:
        redis = await cache()
        result = await redis.eval(BEGIN_LUA, 3, key(challenge), actor_key(expected['id'], 'active'),
            actor_key(expected['id'], 'cooldown'), canonical(item), TTL_SECONDS, RESEND_SECONDS, reference)
        if result and int(result[0]) == 0:
            fail(429, 'mfa_google_email_throttled', retry_after=result[1])
        if not result or int(result[0]) != 1:
            fail(503, 'mfa_google_email_unavailable')
    except HTTPException:
        raise
    except Exception as error:
        logger.error('Google MFA challenge unavailable class=%s', type(error).__name__)
        fail(503, 'mfa_google_email_unavailable')
    from web.services.email_service import send_security_verification_code
    try:
        accepted = await run_in_threadpool(send_security_verification_code, recipient, code)
    except Exception as error:
        logger.error('Google MFA email unconfirmed class=%s', type(error).__name__)
        accepted = False
    if accepted is not True:
        try:
            await redis.delete(key(challenge))
        except Exception as error:
            logger.error('Google MFA challenge discard unavailable class=%s', type(error).__name__)
        fail(503, 'mfa_google_email_delivery_unconfirmed')
    await run_in_threadpool(owned_snapshot, expected, access, previous=binding)
    try:
        result = await redis.eval(ACTIVATE_LUA, 2, key(challenge), actor_key(expected['id'], 'active'),
                                  payload, signature, reference)
        if not result or int(result[0]) != 1:
            fail(503, 'mfa_google_email_unavailable')
    except HTTPException:
        raise
    except Exception as error:
        logger.error('Google MFA challenge activation unavailable class=%s', type(error).__name__)
        fail(503, 'mfa_google_email_unavailable')
    local, domain = recipient.rsplit('@', 1)
    return {'email_verification_required': True, 'challenge': challenge,
            'expires_at': expires.isoformat(), 'masked_email': local[:1] + '***@' + domain,
            'resend_after_seconds': RESEND_SECONDS}


async def verify(expected, access, challenge, code, request):
    configuration()
    await limit(request, expected['id'], 'verify')
    if not isinstance(challenge, str) or TOKEN.fullmatch(challenge) is None or not isinstance(code, str) or CODE.fullmatch(code) is None:
        fail(400, 'mfa_google_email_code_invalid')
    try:
        redis = await cache()
        raw = await redis.get(key(challenge))
        if raw is None or len(raw) > 8192:
            fail(400, 'mfa_google_email_code_invalid')
        item = json.loads(raw)
        payload, signature = item['payload'], item['signature']
        if (not isinstance(payload, str) or not isinstance(signature, str)
                or not hmac.compare_digest(digest('state', challenge + ':' + payload), signature)):
            fail(400, 'mfa_google_email_code_invalid')
        state = json.loads(payload)
        binding = state['binding']
        if (binding.get('purpose') != PURPOSE or binding.get('actor_id') != expected['id']
                or type(state.get('expires_at')) not in (int, float)
                or not math.isfinite(state['expires_at']) or state['expires_at'] <= mfa.instant().timestamp()):
            fail(400, 'mfa_google_email_code_invalid')
        await run_in_threadpool(owned_snapshot, expected, access, previous=binding)
        result = await redis.eval(CONSUME_LUA, 2, key(challenge), actor_key(expected['id'], 'active'),
                                  payload, signature, digest('code', challenge + ':' + code),
                                  digest('challenge', challenge), MAX_ATTEMPTS)
        if not result or int(result[0]) != 1:
            fail(400, 'mfa_google_email_code_invalid')
        verified_at = mfa.instant()
        if state['expires_at'] <= verified_at.timestamp():
            fail(400, 'mfa_google_email_code_invalid')
    except HTTPException:
        raise
    except Exception as error:
        logger.error('Google MFA verification unavailable class=%s', type(error).__name__)
        fail(503, 'mfa_google_email_unavailable')
    return await run_in_threadpool(finish, expected, access, binding, verified_at=verified_at)
