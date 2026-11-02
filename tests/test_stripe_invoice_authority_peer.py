"""Independent persisted Stripe event contract through actual composed HTTP.

Signed event snapshots are never financial truth. Provider HTTP is replaced
by explicit read replies; SQLAlchemy transactions and SDK HMAC verification
are real. This is not a Stripe sandbox acceptance test.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_billing_integrity import billing_case

SECRET = 'peer-synthetic-signature-secret'
SURFACES = [('web', '/api/billing/webhook'), ('api', '/api/billing/webhook'),
            ('api', '/api/pagos/stripe/webhook')]


@pytest.fixture
def invoice_case(billing_case, monkeypatch):
    _, factory, actor = billing_case
    from web.services.billing_integrity import prepare_purchase
    with factory() as db:
        intent = prepare_purchase(db, actor['id'], 'stripe', 'elements', 'pro_usuario', 'peer-invoice-key')
        intent_id = intent.id
    now = int(datetime.now(timezone.utc).timestamp())
    invoice = {'id': 'in_peer', 'object': 'invoice', 'subscription': 'sub_peer',
               'customer': 'cus_peer', 'livemode': False, 'paid': True, 'status': 'paid',
               'amount_paid': 7900, 'amount_due': 7900, 'currency': 'mxn', 'paid_out_of_band': False,
               'payment_intent': 'pi_peer',
               'charge': {'id': 'ch_peer', 'object': 'charge', 'invoice': 'in_peer',
                          'customer': 'cus_peer', 'livemode': False, 'paid': True,
                          'captured': True, 'refunded': False, 'amount_refunded': 0,
                          'amount': 7900, 'currency': 'mxn'}}
    subscription = {'id': 'sub_peer', 'object': 'subscription', 'customer': 'cus_peer',
                    'livemode': False, 'status': 'active',
                    'metadata': {'gym_id': actor['id'], 'plan': 'pro_usuario', 'purchase_intent_id': intent_id},
                    'current_period_start': now-60, 'current_period_end': now+86400*30,
                    'items': {'data': [{'quantity': 1, 'price': {'unit_amount': 7900,
                        'currency': 'mxn', 'recurring': {'interval': 'month', 'interval_count': 1}}}]},
                    'latest_invoice': deepcopy(invoice)}
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), 'STRIPE_WEBHOOK_SECRET', SECRET)
    monkeypatch.setattr(get_settings(), 'BASE_URL', 'https://testserver')
    from web.services import stripe_service
    monkeypatch.setattr(stripe_service, '_init_stripe', lambda: True)
    state = {'invoice': invoice, 'subscription': subscription, 'fail': False, 'reads': []}
    def fetch_invoice(reference, **kwargs):
        state['reads'].append(reference)
        if state['fail']:
            raise TimeoutError('owned synthetic provider unavailable')
        return deepcopy(state['invoice'])
    import stripe
    monkeypatch.setattr(stripe.Invoice, 'retrieve', fetch_invoice)
    monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda *a, **kw: deepcopy(state['subscription']))
    def blocked(*a, **kw):
        raise AssertionError('unapproved external payment capability')
    monkeypatch.setattr(stripe.Customer, 'create', blocked)
    monkeypatch.setattr(stripe.Subscription, 'create', blocked)
    monkeypatch.setattr(stripe.Charge, 'retrieve', blocked)
    return factory, actor, state


def event_from(state, event_type='invoice.paid', modern=True):
    body = deepcopy(state['invoice'])
    if modern:
        body['parent'] = {'type': 'subscription_details',
                          'subscription_details': {'subscription': body.pop('subscription')}}
        for key in ('paid', 'paid_out_of_band', 'charge', 'payment_intent'):
            body.pop(key)
    return {'id': 'evt_peer_invoice', 'object': 'event', 'type': event_type,
            'api_version': '2026-03-25.dahlia', 'livemode': False, 'data': {'object': body}}


def client_for(surface):
    if surface[0] == 'web':
        from web.main_web import create_app
    else:
        from api.app import create_app
    return TestClient(create_app(), base_url='https://testserver', raise_server_exceptions=False)


def deliver(client, path, event):
    raw = json.dumps(event, ensure_ascii=False, indent=1).encode()
    stamp = str(int(time.time()))
    digest = hmac.new(SECRET.encode(), stamp.encode()+b'.'+raw, hashlib.sha256).hexdigest()
    return client.post(path, content=raw,
                       headers={'Stripe-Signature': f't={stamp},v1={digest}', 'Content-Type': 'application/json'})


@pytest.mark.parametrize('surface', SURFACES)
@pytest.mark.parametrize('modern', [True, False])
def test_signed_invoice_paid_reads_canonical_provider_state_and_replay_is_single_ledger(invoice_case, surface, modern):
    factory, actor, state = invoice_case
    from web.database.models import Payment, StripeWebhookEvent, UserSubscription
    event = event_from(state, modern=modern)
    client = client_for(surface)
    first = deliver(client, surface[1], event)
    assert first.status_code == 200, first.text
    assert first.json()['result'] == 'paid:7900'
    assert state['reads'], 'provider invoice must be read independently of signed snapshot'
    reads = len(state['reads'])
    second = deliver(client, surface[1], event)
    assert second.status_code == 200
    assert second.json()['result'] == 'duplicate:invoice.paid'
    assert len(state['reads']) == reads
    with factory() as db:
        payment = db.query(Payment).one()
        assert (payment.gym_id, payment.amount_cents, payment.currency, payment.status) == (actor['id'], 7900, 'mxn', 'succeeded')
        assert db.query(StripeWebhookEvent).count() == 1
        assert db.query(UserSubscription).filter_by(user_id=actor['id']).one().plan == 'pro'


@pytest.mark.parametrize('surface', SURFACES)
def test_provider_timeout_is_http_retry_with_transactional_inbox_rollback_then_success(invoice_case, surface):
    factory, _, state = invoice_case
    from web.database.models import Payment, StripeWebhookEvent, Subscription
    event = event_from(state, event_type='invoice.payment_succeeded', modern=False)
    state['fail'] = True
    client = client_for(surface)
    failure = deliver(client, surface[1], event)
    assert failure.status_code == 503, failure.text
    with factory() as db:
        assert db.query(Payment).count() == db.query(Subscription).count() == db.query(StripeWebhookEvent).count() == 0
    state['fail'] = False
    retry = deliver(client, surface[1], event)
    assert retry.status_code == 200, retry.text
    assert retry.json()['result'] == 'paid:7900'
    with factory() as db:
        assert db.query(Payment).count() == db.query(StripeWebhookEvent).count() == 1


@pytest.mark.parametrize('surface', SURFACES)
@pytest.mark.parametrize('actual', ['open', 'offline', 'refunded'])
def test_stale_signed_success_cannot_sell_paid_access_when_current_invoice_has_no_funds(invoice_case, surface, actual):
    factory, actor, state = invoice_case
    from web.database.models import Payment, Subscription, UserSubscription
    event = event_from(state, event_type='invoice.payment_succeeded', modern=False)
    # Leave subscription.latest_invoice stale and paid, as an independent trap.
    if actual == 'open':
        state['invoice'].update(status='open', paid=False, amount_paid=0, charge=None)
    elif actual == 'offline':
        state['invoice'].update(paid_out_of_band=True, charge=None)
    else:
        state['invoice']['charge'].update(refunded=True, amount_refunded=7900)
    response = deliver(client_for(surface), surface[1], event)
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.query(Payment).filter_by(status='succeeded').count() == 0
        assert db.query(Subscription).filter_by(status='active').count() == 0
        projection = db.query(UserSubscription).filter_by(user_id=actor['id']).first()
        assert projection is None or projection.plan == 'starter'


@pytest.mark.parametrize('surface', SURFACES)
def test_repaired_failed_snapshot_records_current_success_not_failed_money(invoice_case, surface):
    factory, _, state = invoice_case
    from web.database.models import Payment
    event = event_from(state, event_type='invoice.payment_failed', modern=False)
    event['data']['object'].update(status='open', paid=False, amount_paid=0, charge=None)
    response = deliver(client_for(surface), surface[1], event)
    assert response.status_code == 200, response.text
    assert response.json()['result'] == 'paid:7900'
    with factory() as db:
        assert db.query(Payment).one().status == 'succeeded'
