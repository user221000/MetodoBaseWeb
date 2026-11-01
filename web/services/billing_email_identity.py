"""Fresh account authority for subscription email confirmation; no new schema."""
import hashlib
import json
import logging
from fastapi import HTTPException
from web.account_values import normalize_account_email
from web.database.models import Usuario
from web.services import mfa_service

logger = logging.getLogger(__name__)

GYM_PLANS = frozenset({'standard', 'gym_comercial', 'clinica'})
ACTION_RULES = {
    'gym_stripe_checkout': ('gym', GYM_PLANS),
    'gym_stripe_subscribe': ('gym', GYM_PLANS),
    'gym_mp_preference': ('gym', GYM_PLANS),
    'personal_stripe_checkout': ('personal', frozenset({'pro'})),
    'personal_stripe_subscribe': ('personal', frozenset({'pro'})),
    'personal_mp_preference': ('personal', frozenset({'pro'})),
    'gym_stripe_portal': ('gym', frozenset({'manage'})),
    'personal_stripe_portal': ('personal', frozenset({'manage'})),
    'legacy_stripe_checkout': ('gym', GYM_PLANS),
    'legacy_mp_preference': ('gym', GYM_PLANS),
}


def fail(status, code, message):
    raise HTTPException(status, {'code': code, 'message': message}, headers={
        'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})


def validate_action_plan(action, plan):
    if action not in ACTION_RULES or plan not in ACTION_RULES[action][1]:
        fail(422, 'billing_email_invalid_input', 'Elige un plan y un medio de pago válidos.')


def _access(request, identity):
    values = request.headers.getlist('authorization')
    if len(values) != 1 or not values[0].startswith('Bearer '):
        fail(401, 'billing_email_identity_changed', 'Inicia sesión de nuevo para confirmar tu compra.')
    access = values[0][7:]
    if not 1 <= len(access) <= 8192:
        fail(401, 'billing_email_identity_changed', 'Inicia sesión de nuevo para confirmar tu compra.')
    from web.auth import _decode_token, _valid_token_payload
    payload = _decode_token(access)
    if (not _valid_token_payload(payload, 'access') or payload['id'] != identity['id']
            or payload.get('sv', 0) != identity['session_version']
            or payload.get('team_gym_id') != identity.get('team_gym_id')):
        fail(401, 'billing_email_identity_changed', 'La sesión cambió. Inicia una nueva verificación.')
    return access


def _catalog(plan):
    from web.constants import PLANES_LICENCIA
    from web.services.billing_integrity import price_in_cents
    internal = 'pro_usuario' if plan == 'pro' else plan
    identifiers = sorted(GYM_PLANS | {'pro_usuario'}) if plan == 'manage' else [internal]
    values = [{'plan': key, 'amount_cents': price_in_cents(key), 'currency': 'MXN',
               'period': PLANES_LICENCIA[key].get('periodo', 'month'),
               'stripe_price_id': PLANES_LICENCIA[key].get('stripe_price_id') or ''}
              for key in identifiers]
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def snapshot(db, expected, request, action, plan, *, lock=False):
    """Copy current account facts; locking is reserved for payment admission."""
    validate_action_plan(action, plan)
    if lock:
        user, identity = mfa_service.lock_actor(db, expected)
    else:
        user = db.get(Usuario, expected['id'], populate_existing=True)
        identity = mfa_service.current_identity(db, user)
    if (identity['session_version'] != expected.get('session_version', expected.get('sv', 0))
            or identity.get('team_gym_id') != expected.get('team_gym_id')):
        fail(401, 'billing_email_identity_changed', 'La cuenta cambió. Inicia una nueva verificación.')
    if ACTION_RULES[action][0] == 'gym':
        if identity.get('tipo') != 'gym' or identity.get('role') != 'owner' or identity.get('team_gym_id'):
            fail(403, 'billing_email_forbidden', 'La compra del plan del negocio corresponde a su propietario.')
    elif identity.get('tipo') != 'usuario' and not identity.get('team_gym_id'):
        fail(403, 'billing_email_forbidden', 'Este plan corresponde al espacio personal.')
    email = normalize_account_email(user.email)
    if (not email or len(email) > 255 or email.count('@') != 1 or not all(email.split('@'))
            or any(ord(char) < 33 or ord(char) == 127 for char in email)):
        fail(409, 'billing_email_recipient_unavailable', 'Revisa el correo registrado en tu cuenta.')
    contact_version = user.notification_contact_version
    if type(contact_version) is not int or not 0 <= contact_version <= 2147483647:
        fail(503, 'billing_email_unavailable', 'No pudimos verificar los datos de la cuenta.')
    access = _access(request, identity)
    binding = {'actor_id': identity['id'], 'session_version': identity['session_version'],
        'notification_contact_version': contact_version,
        'email_hash': hashlib.sha256(email.encode('utf8')).hexdigest(),
        'access_hash': hashlib.sha256(access.encode('utf8')).hexdigest(),
        'tipo': identity['tipo'], 'role': identity['role'], 'team_gym_id': identity.get('team_gym_id'),
        'action': action, 'plan': plan, 'catalog_digest': _catalog(plan)}
    return binding, email, identity


def owned_snapshot(expected, request, action, plan):
    """Release SQL before Redis/email I/O; never reads tenant billing records."""
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        return snapshot(db, expected, request, action, plan)


def owned_contact_snapshot(expected, request, action, plan):
    """Return fresh contact authority; this read never authorizes a payment."""
    from web.database.engine import SessionLocal
    from web.services.account_security import verified
    with SessionLocal() as db:
        binding, email, identity = snapshot(db, expected, request, action, plan)
        user = db.get(Usuario, identity['id'])
        return binding, email, identity, verified(user, mfa_service.instant())


def confirm_contact(expected, request, action, plan, expected_binding):
    """Persist mailbox possession only after its exact billing OTP was consumed."""
    from web.database.engine import SessionLocal
    from web.services.account_security import PENDING, epoch
    from web.services import billing_email_verification as service
    with SessionLocal() as db:
        try:
            current, _, identity = snapshot(db, expected, request, action, plan, lock=True)
            if current != expected_binding:
                fail(409, 'billing_email_identity_changed', 'La cuenta cambió. Solicita un nuevo código.')
            user = db.get(Usuario, identity['id'])
            now = mfa_service.instant()
            user.email_verified_at = now
            user.email_verified_contact_version = epoch(user)
            for name in PENDING:
                setattr(user, name, None)
            mfa_service.audit(db, user, 'email_contact_verified', now, channel='billing_code')
            db.commit()
        except HTTPException:
            mfa_service.rollback(db)
            raise
        except Exception as error:
            logger.error('Billing contact confirmation unconfirmed class=%s', type(error).__name__)
            mfa_service.rollback(db)
            service.fail(503, 'billing_email_unconfirmed')


async def require_email(db, expected, request, action, plan, body, *, idempotency_key=None):
    from starlette.concurrency import run_in_threadpool
    from web.services import billing_email_verification as service
    from web.services.account_security import verified
    values = request.headers.getlist('x-billing-email-grant')
    if len(values) > 1:
        service.fail(403, 'billing_email_required')
    binding, _, identity = await run_in_threadpool(snapshot, db, expected, request, action, plan, lock=True)
    user = db.get(Usuario, identity['id'])
    if not verified(user, mfa_service.instant()):
        service.fail(403, 'billing_email_required')
    # Existing grants retain their exact-request binding; already confirmed
    # contact needs no new mailbox proof. The caller still owns MFA step-up.
    if values:
        await service.consume(binding, values[0], request, body=body, idempotency_key=idempotency_key)
    return identity
