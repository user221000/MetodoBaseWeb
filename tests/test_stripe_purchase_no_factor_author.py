"""Stripe billing does not require an account factor; payment truth stays external.

Real routers, signed synthetic sessions, SQLAlchemy and purchase intents. Only
Stripe SDK ports are offline doubles; no charge, email or provider replay.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate


def confirmed_contact(actor):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.services import mfa_service
    with Session(get_engine()) as db:
        user = db.get(Usuario, actor['id'])
        user.email_verified_at = mfa_service.instant()
        user.email_verified_contact_version = user.notification_contact_version
        db.commit()


def offline_stripe(monkeypatch):
    from web.services import stripe_service, mfa_service
    monkeypatch.setattr(stripe_service, '_init_stripe', lambda: True)
    def forbidden_factor_configuration():
        raise AssertionError('A Stripe payment must not consult account MFA configuration')
    monkeypatch.setattr(mfa_service, 'configuration', forbidden_factor_configuration)


@pytest.mark.parametrize('plan', ['standard', 'gym_comercial', 'clinica'])
def test_no_factor_checkout_keeps_one_durable_intent_and_same_provider_key(mfa_client, monkeypatch, plan):
    import stripe
    from web.database.engine import get_engine
    from web.database.models import PurchaseIntent, Subscription, MfaAuthorization, MfaCredential
    from web.services.billing_integrity import price_in_cents
    client, actor, _ = mfa_client
    confirmed_contact(actor)
    offline_stripe(monkeypatch)
    calls = []
    monkeypatch.setattr(stripe.checkout.Session, 'create', lambda **kw: calls.append(kw)
        or SimpleNamespace(id='cs_offline_author', url='https://checkout.stripe.com/c/offline-author'))
    body = {'plan': plan, 'success_url': '/suscripciones?result=success', 'cancel_url': '/suscripciones?result=canceled'}
    headers = {'Idempotency-Key': 'offline-author-purchase'}
    first = client.post('/api/billing/checkout', json=body, headers=headers)
    second = client.post('/api/billing/checkout', json=body, headers=headers)
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    assert first.json()['purchase_intent_id'] == second.json()['purchase_intent_id']
    with Session(get_engine()) as db:
        intent = db.query(PurchaseIntent).one()
        assert (intent.subject_id, intent.plan, intent.amount_cents, intent.currency, intent.status) == (
            actor['id'], plan, price_in_cents(plan), 'mxn', 'provider_created')
        assert db.query(Subscription).count() == 0  # Redirect never grants access.
        assert db.query(MfaAuthorization).count() == db.query(MfaCredential).count() == 0
    assert len(calls) == 2 and calls[0]['idempotency_key'] == calls[1]['idempotency_key']
    assert all(call['metadata']['gym_id'] == actor['id'] and call['metadata']['plan'] == plan for call in calls)
    changed = client.post('/api/billing/checkout', json={**body, 'plan': 'clinica' if plan != 'clinica' else 'standard'}, headers=headers)
    assert changed.status_code == 400 and len(calls) == 2


@pytest.mark.parametrize('plan', ['standard', 'gym_comercial', 'clinica'])
def test_no_factor_elements_preserves_incomplete_provider_state(mfa_client, monkeypatch, plan):
    import stripe
    from web.constants import PLANES_LICENCIA
    from web.database.engine import get_engine
    from web.database.models import PurchaseIntent, StripeCustomer, Subscription
    client, actor, _ = mfa_client
    confirmed_contact(actor)
    offline_stripe(monkeypatch)
    monkeypatch.setitem(PLANES_LICENCIA[plan], 'stripe_price_id', 'price_offline_' + plan)
    calls = []
    monkeypatch.setattr(stripe.Customer, 'create', lambda **kw: SimpleNamespace(id='cus_offline_author'))
    def create(**kw):
        calls.append(kw)
        return stripe.Subscription.construct_from({'id': 'sub_offline_author', 'status': 'incomplete',
            'latest_invoice': {'payment_intent': {'client_secret': 'pi_offline_secret_fixture'}}}, 'offline')
    monkeypatch.setattr(stripe.Subscription, 'create', create)
    response = client.post('/api/billing/stripe/subscribe',
        json={'plan': plan, 'payment_method_id': 'pm_offline_author'}, headers={'Idempotency-Key': 'offline-elements'})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'incomplete'
    with Session(get_engine()) as db:
        intent = db.query(PurchaseIntent).one()
        assert (intent.subject_id, intent.operation, intent.provider_reference_id) == (actor['id'], 'elements', 'sub_offline_author')
        assert db.query(StripeCustomer).one().gym_id == actor['id']
        assert db.query(Subscription).count() == 0
    assert calls[0]['payment_behavior'] == 'default_incomplete'


@pytest.mark.parametrize('paid', [False, True])
def test_no_factor_confirmation_still_requires_current_provider_funding(mfa_client, monkeypatch, paid):
    import stripe
    from web.database.engine import get_engine
    from web.database.models import PurchaseIntent, Subscription
    client, actor, _ = mfa_client
    offline_stripe(monkeypatch)
    with Session(get_engine()) as db:
        intent = PurchaseIntent(subject_id=actor['id'], provider='stripe', operation='elements',
            request_key='offline-confirm', plan='standard', amount_cents=15900, currency='mxn',
            status='provider_created', provider_reference_id='sub_offline_confirm', provider_customer_id='cus_offline_confirm')
        db.add(intent); db.commit(); intent_id = intent.id
    now = int(datetime.now(timezone.utc).timestamp())
    snapshot = {'id': 'sub_offline_confirm', 'customer': 'cus_offline_confirm', 'status': 'active' if paid else 'incomplete',
        'metadata': {'gym_id': actor['id'], 'purchase_intent_id': intent_id, 'plan': 'standard'},
        'current_period_start': now, 'current_period_end': now + 30 * 86400,
        'items': {'data': [{'quantity': 1, 'price': {'currency': 'mxn', 'unit_amount': 15900,
            'recurring': {'interval': 'month', 'interval_count': 1}}}]},
        'latest_invoice': {'paid': paid, 'status': 'paid' if paid else 'open', 'currency': 'mxn', 'amount_paid': 15900 if paid else 0,
            'charge': {'id': 'ch_offline_confirm', 'paid': paid, 'captured': paid, 'refunded': False, 'amount_refunded': 0,
                'currency': 'mxn', 'amount': 15900, 'customer': 'cus_offline_confirm'}}}
    reads = []
    monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda reference, **kw: reads.append(reference) or snapshot)
    response = client.post('/api/billing/confirm-subscription', json={'subscription_id': 'sub_offline_confirm'})
    assert response.status_code == 200, response.text
    assert response.json()['activated'] is paid
    assert reads == ['sub_offline_confirm', 'sub_offline_confirm']
    with Session(get_engine()) as db:
        sub = db.query(Subscription).one_or_none()
        assert (sub is not None and sub.status == 'active') is paid


def test_no_factor_portal_releases_actor_lock_and_uses_own_customer(mfa_client, monkeypatch):
    import stripe
    from web.database.engine import get_engine
    from web.database.models import Subscription, MfaCredential
    from web.services import stripe_service
    client, actor, _ = mfa_client
    confirmed_contact(actor)
    offline_stripe(monkeypatch)
    with Session(get_engine()) as db:
        db.add(Subscription(gym_id=actor['id'], plan='standard', status='active', provider='stripe', stripe_customer_id='cus_offline_owner'))
        db.commit()
    actual = stripe_service.create_portal_session
    entry_transactions = []
    def observed(db, gym_id, return_url):
        entry_transactions.append(db.in_transaction())
        return actual(db, gym_id, return_url)
    monkeypatch.setattr(stripe_service, 'create_portal_session', observed)
    calls = []
    monkeypatch.setattr(stripe.billing_portal.Session, 'create', lambda **kw: calls.append(kw)
        or SimpleNamespace(url='https://billing.stripe.com/p/offline-author'))
    response = client.post('/api/billing/portal', json={'return_url': '/suscripciones'})
    assert response.status_code == 200, response.text
    assert entry_transactions == [False]
    assert calls[0]['customer'] == 'cus_offline_owner'
    with Session(get_engine()) as db:
        assert db.query(MfaCredential).count() == 0


def test_existing_mfa_login_still_required_but_no_additional_payment_factor(mfa_client, monkeypatch):
    import stripe
    client, actor, clock = mfa_client
    confirmed_contact(actor)
    _, kit = enroll(client, clock)
    authenticate(client, actor, clock, recovery=kit['recovery_codes'][0])
    clock[0] += timedelta(seconds=301)
    calls = []
    offline_stripe(monkeypatch)
    monkeypatch.setattr(stripe.checkout.Session, 'create', lambda **kw: calls.append(kw)
        or SimpleNamespace(id='cs_old_factor', url='https://checkout.stripe.com/c/offline-author'))
    response = client.post('/api/billing/checkout', json={'plan': 'standard'})
    assert response.status_code == 200 and len(calls) == 1, response.text


def test_unverified_contact_is_still_a_separate_payment_requirement(mfa_client, monkeypatch):
    import stripe
    client, _, _ = mfa_client
    offline_stripe(monkeypatch)
    calls = []
    monkeypatch.setattr(stripe.checkout.Session, 'create', lambda **kw: calls.append(kw))
    response = client.post('/api/billing/checkout', json={'plan': 'standard'})
    assert response.status_code == 403 and response.json()['detail']['code'] == 'billing_email_required'
    assert calls == []
