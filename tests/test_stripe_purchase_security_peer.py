"""Independent Stripe admission checks; current SQL/JWT/HTTP, controlled SDK ports.

No Stripe call, financial write, mailbox or production identity is used here.
These tests validate the account boundary, not a provider payment lifecycle.
"""
from datetime import datetime, timedelta, timezone
import importlib
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


REQUESTS = {
    'checkout': ('/api/billing/checkout', {'plan': 'standard', 'success_url': '/suscripciones', 'cancel_url': '/suscripciones'}),
    'subscribe': ('/api/billing/stripe/subscribe', {'plan': 'clinica', 'payment_method_id': 'pm_security_peer'}),
    'confirm': ('/api/billing/confirm-subscription', {'subscription_id': 'sub_security_peer'}),
    'portal': ('/api/billing/portal', {'return_url': '/suscripciones'}),
    'legacy': ('/api/pagos/stripe/session', {'plan': 'gym_comercial', 'email': 'untrusted@example.invalid',
                'success_url': '/suscripciones', 'cancel_url': '/suscripciones'}),
}
TARGETS = [(factory, name) for factory in ('api.app', 'web.main_web') for name in REQUESTS
           if factory == 'api.app' or name != 'legacy']


@pytest.fixture
def principal(test_gym_user):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.auth import identity_from_user
    with Session(get_engine()) as db:
        user = db.get(Usuario, test_gym_user['id'])
        user.email_verified_at = datetime.now(timezone.utc)
        user.email_verified_contact_version = user.notification_contact_version
        db.commit()
        identity = identity_from_user(user, db)
    return SimpleNamespace(raw=test_gym_user, identity=identity)


@pytest.fixture
def ports(monkeypatch):
    from web.services import stripe_service
    calls = []

    def record(kind, args, kwargs):
        db = kwargs.get('db', args[0] if args else None)
        actor = kwargs.get('gym_id', args[1] if len(args) > 1 else None)
        email = kwargs.get('email', args[3] if len(args) > 3 else None)
        calls.append({'kind': kind, 'actor': actor, 'email': email,
                      'transaction_open': db.in_transaction()})
        if kind == 'confirm': return {'status': 'pending', 'plan': 'free'}
        return {'session_id': 'cs_security_peer', 'url': 'https://' + (
            'billing.stripe.com/p/session_peer' if kind == 'portal' else 'checkout.stripe.com/c/pay_peer')}

    for name, kind in (('create_checkout_session', 'checkout'),
                       ('create_subscription_with_payment_method', 'subscribe'),
                       ('confirm_subscription', 'confirm'), ('create_portal_session', 'portal')):
        monkeypatch.setattr(stripe_service, name,
                            lambda *args, _kind=kind, **kwargs: record(_kind, args, kwargs))
    return calls


@pytest.fixture
def api_case(principal, ports, monkeypatch):
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), 'MFA_ENCRYPTION_KEY', '')
    app = importlib.import_module('api.app').create_app()
    with TestClient(app, raise_server_exceptions=False, headers=principal.raw['auth_headers']) as client:
        yield SimpleNamespace(app=app, client=client, principal=principal, calls=ports)


@pytest.mark.parametrize('factory,name', TARGETS)
def test_each_stripe_entry_needs_no_factor_or_grant(principal, ports, monkeypatch, factory, name):
    from web.database.engine import get_engine
    from web.database.models import MfaCredential, MfaAuthorization
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), 'MFA_ENCRYPTION_KEY', '')
    app = importlib.import_module(factory).create_app()
    path, body = REQUESTS[name]
    with TestClient(app, raise_server_exceptions=False, headers=principal.raw['auth_headers']) as client:
        response = client.post(path, json=body, headers={'Idempotency-Key': 'security-peer-purchase'})
    assert response.status_code == 200, (name, response.status_code, response.text)
    assert len(ports) == 1 and ports[0]['actor'] == principal.raw['id']
    if name in {'checkout', 'subscribe', 'legacy'}:
        assert ports[0]['email'] == principal.raw['email']
    if name == 'portal': assert ports[0]['transaction_open'] is False
    with Session(get_engine()) as db:
        assert db.get(MfaCredential, principal.raw['id']) is None
        assert db.query(MfaAuthorization).count() == 0


@pytest.mark.parametrize('factory,name', TARGETS)
def test_unrelated_mfa_header_is_not_required_or_payment_authority(principal, ports, monkeypatch, factory, name):
    app = importlib.import_module(factory).create_app()
    path, body = REQUESTS[name]
    with TestClient(app, raise_server_exceptions=False, headers=principal.raw['auth_headers']) as client:
        response = client.post(path, json=body, headers={'X-MFA-Grant': 'not-a-payment-authority'})
    assert response.status_code == 200
    assert len(ports) == 1 and ports[0]['actor'] == principal.raw['id']


@pytest.mark.parametrize('factory,name', [value for value in TARGETS if value[1] != 'confirm'])
def test_verified_contact_boundary_is_preserved(principal, ports, factory, name):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    with Session(get_engine()) as db:
        user = db.get(Usuario, principal.raw['id'])
        user.email_verified_at = None
        user.email_verified_contact_version = None
        db.commit()
    app = importlib.import_module(factory).create_app()
    path, body = REQUESTS[name]
    with TestClient(app, raise_server_exceptions=False, headers=principal.raw['auth_headers']) as client:
        response = client.post(path, json=body)
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'billing_email_required'
    assert ports == []


@pytest.mark.parametrize('factory,name', TARGETS)
def test_raw_bearer_cannot_disagree_with_the_resolved_dependency(principal, ports, factory, name):
    from web.auth import _decode_token, _make_token
    from web.auth_deps import get_usuario_actual
    app = importlib.import_module(factory).create_app()
    app.dependency_overrides[get_usuario_actual] = lambda: dict(principal.identity)
    payload = _decode_token(principal.raw['access_token'])
    payload['id'] = str(uuid.uuid4())
    token = _make_token(payload)
    path, body = REQUESTS[name]
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(path, json=body, headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401
    assert ports == []


@pytest.mark.parametrize('name', ['checkout', 'subscribe', 'confirm', 'portal'])
@pytest.mark.parametrize('mutation', ['disabled', 'deleted', 'invited', 'version', 'role', 'type', 'team'])
def test_actor_changes_after_auth_resolution_do_not_reach_stripe(api_case, name, mutation):
    from web.auth_deps import get_usuario_actual
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    c = api_case
    c.app.dependency_overrides[get_usuario_actual] = lambda: dict(c.principal.identity)
    with Session(get_engine()) as db:
        user = db.get(Usuario, c.principal.raw['id'])
        if mutation == 'disabled': user.activo = False
        elif mutation == 'deleted': user.deleted_at = datetime.now(timezone.utc)
        elif mutation == 'invited': user.invitation_token = 'security-peer-invitation'
        elif mutation == 'version': user.session_version += 1
        elif mutation == 'role': user.role = UserRole.VIEWER
        elif mutation == 'type': user.tipo = 'usuario'
        elif mutation == 'team':
            parent = Usuario(id=str(uuid.uuid4()), email='parent-' + uuid.uuid4().hex + '@example.invalid',
                nombre='Parent', apellido='', password_hash='not-used', tipo='gym', role=UserRole.OWNER,
                activo=True, session_version=0, fecha_registro=datetime.now(timezone.utc))
            db.add(parent); db.flush(); user.team_gym_id = parent.id
        db.commit()
    path, body = REQUESTS[name]
    response = c.client.post(path, json=body)
    assert response.status_code in {401, 403}
    assert c.calls == []


@pytest.mark.parametrize('name', ['checkout', 'subscribe', 'confirm', 'portal'])
def test_legacy_claims_do_not_broaden_the_previous_access_contract(api_case, name):
    from web.auth import _decode_token, _make_token
    payload = _decode_token(api_case.principal.raw['access_token'])
    for field in ('v', 'iss', 'aud'): payload.pop(field, None)
    token = _make_token(payload)
    path, body = REQUESTS[name]
    response = api_case.client.post(path, json=body, headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401 and api_case.calls == []


@pytest.mark.parametrize('name', ['checkout', 'subscribe', 'confirm', 'portal'])
def test_duplicate_authorization_is_rejected(api_case, name):
    path, body = REQUESTS[name]
    value = 'Bearer ' + api_case.principal.raw['access_token']
    response = api_case.client.post(path, json=body,
        headers=[('Authorization', value), ('Authorization', value)])
    assert response.status_code == 401 and api_case.calls == []


@pytest.mark.parametrize('name', ['checkout', 'subscribe', 'confirm', 'portal'])
def test_cookie_without_access_is_not_stripe_authority(api_case, name):
    path, body = REQUESTS[name]
    api_case.client.headers.pop('Authorization', None)
    api_case.client.cookies.set('__Host-mb_refresh', 'synthetic-refresh-only')
    response = api_case.client.post(path, json=body)
    assert response.status_code == 401 and api_case.calls == []


@pytest.mark.parametrize('factory,path,body', [
    ('api.app', '/api/billing/mp/preference', {'plan': 'standard', 'success_url': '/suscripciones', 'cancel_url': '/suscripciones'}),
    ('api.app', '/api/pagos/mp/preference', {'plan': 'standard', 'email': 'owner@example.invalid', 'success_url': '/suscripciones', 'cancel_url': '/suscripciones'}),
    ('web.main_web', '/api/gym/team/invite', {'email': 'invite@example.invalid', 'nombre': 'Synthetic', 'role': 'nutriologo'}),
])
def test_other_sensitive_operations_still_require_a_factor(principal, ports, factory, path, body):
    app = importlib.import_module(factory).create_app()
    with TestClient(app, raise_server_exceptions=False, headers=principal.raw['auth_headers']) as client:
        response = client.post(path, json=body)
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'mfa_enrollment_required'
    assert ports == []


def test_enabled_account_factor_still_protects_login_not_each_stripe_operation(api_case, monkeypatch):
    import base64
    from web.services import mfa_service
    from web.settings import get_settings
    from tests.test_mfa31_http import enroll, authenticate
    c = api_case
    clock = [datetime.now(timezone.utc)]
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, 'instant', lambda now=None: actual(clock[0] if now is None else now))
    monkeypatch.setattr(get_settings(), 'MFA_ENCRYPTION_KEY', base64.urlsafe_b64encode(b'only-security-peer-synthetic-key!'[:32]).decode())
    _, enabled = enroll(c.client, clock)
    clock[0] += timedelta(seconds=31)
    authenticate(c.client, c.principal.raw, clock, recovery=enabled['recovery_codes'][0])
    for name in ('checkout', 'subscribe', 'confirm', 'portal'):
        path, body = REQUESTS[name]
        response = c.client.post(path, json=body)
        assert response.status_code == 200, (name, response.status_code, response.text)
    assert len(c.calls) == 4
