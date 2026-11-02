"""Refund ledger regression with owned SQLAlchemy and read-only boundary doubles."""
from copy import deepcopy

import pytest

from tests.test_billing_integrity import billing_case, _stored_plan
from tests.test_stripe_webhook_version_contract import _case, _event


@pytest.fixture
def refund_case(billing_case, monkeypatch):
    factory, actor = billing_case[1:]
    from web.services import stripe_service as service
    snapshot = _case(factory, actor)
    invoice = snapshot['latest_invoice']
    invoice['charge']['payment_intent'] = invoice['payment_intent']
    state = {'subscription': snapshot, 'invoices': {invoice['id']: invoice}, 'charges': {}, 'fail': False}
    monkeypatch.setattr(service, '_init_stripe', lambda: True)
    monkeypatch.setattr(service.stripe.Subscription, 'retrieve', lambda *_a, **_k: deepcopy(state['subscription']))
    monkeypatch.setattr(service.stripe.Invoice, 'retrieve', lambda ref, **_k: deepcopy(state['invoices'][ref]))

    def charge_read(reference):
        if state['fail']:
            raise TimeoutError('synthetic-refund-provider-failure')
        return deepcopy(state['charges'][reference])

    monkeypatch.setattr(service.stripe.Charge, 'retrieve', charge_read)
    return factory, actor, state


def _deliver(factory, event):
    from web.services.stripe_service import handle_webhook_event
    with factory() as db:
        result = handle_webhook_event(db, event)
        db.commit()
        return result


def _paid(factory, state, event_id='evt_author_paid'):
    event = _event(state['subscription']['latest_invoice'], event_id=event_id)
    assert _deliver(factory, event) == 'paid:7900'


def _refund(state, amount=7900):
    invoice = state['invoices']['in_current']
    invoice['charge'].update(refunded=amount == 7900, amount_refunded=amount)
    state['charges']['ch_current'] = deepcopy(invoice['charge'])
    return {'id': 'evt_author_refund', 'type': 'charge.refunded', 'livemode': False,
            'data': {'object': deepcopy(invoice['charge'])}}


def test_actual_full_refund_updates_history_once_and_replays_remain_refunded(refund_case):
    from web.services.stripe_service import get_payment_history
    from web.database.models import Payment
    factory, actor, state = refund_case
    _paid(factory, state)
    event = _refund(state)
    assert _deliver(factory, event) == 'refund:reconciled'
    assert _deliver(factory, event) == 'duplicate:charge.refunded'
    event['id'] = 'evt_author_refund_duplicate_id'
    assert _deliver(factory, event) == 'refund:reconciled'
    stale_paid = _event(state['invoices']['in_current'], event_id='evt_after_refund')
    assert _deliver(factory, stale_paid).startswith('pending:')
    with factory() as db:
        assert db.query(Payment).count() == 1
        assert get_payment_history(db, actor['id'])[0]['status'] == 'refunded'
    assert _stored_plan(factory, actor['id']) == 'starter'


def test_partial_refund_cannot_be_reported_as_full_even_if_snapshot_says_full(refund_case):
    from web.database.models import Payment
    factory, _, state = refund_case
    _paid(factory, state)
    event = _refund(state, amount=1)
    event['data']['object'].update(refunded=True, amount_refunded=7900)
    assert _deliver(factory, event) == 'refund:reconciled'
    with factory() as db:
        assert db.query(Payment).one().status == 'succeeded'


@pytest.mark.parametrize('mutation', ['id', 'customer', 'invoice', 'livemode', 'currency',
                                     'amount', 'amount_refunded', 'payment_intent', 'event_mode'])
def test_mismatched_refund_rolls_back_history_access_and_inbox(refund_case, mutation):
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, StripeWebhookEvent
    factory, actor, state = refund_case
    _paid(factory, state)
    event = _refund(state)
    if mutation == 'event_mode':
        event['livemode'] = True
    else:
        values = {'id': 'ch_wrong', 'customer': 'cus_wrong', 'invoice': 'in_wrong', 'livemode': True,
                  'currency': 'usd', 'amount': 1, 'amount_refunded': 7901, 'payment_intent': 'pi_wrong'}
        state['charges']['ch_current'][mutation] = values[mutation]
    with factory() as db:
        with pytest.raises((ValueError, KeyError)):
            handle_webhook_event(db, event)
        db.rollback()
        assert db.query(Payment).one().status == 'succeeded'
        assert db.query(StripeWebhookEvent).count() == 1
    assert _stored_plan(factory, actor['id']) == 'pro'


def test_provider_read_failure_preserves_retry_and_exactly_one_refund_observation(refund_case):
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, StripeWebhookEvent
    factory, actor, state = refund_case
    _paid(factory, state)
    event = _refund(state)
    state['fail'] = True
    with factory() as db:
        with pytest.raises(TimeoutError):
            handle_webhook_event(db, event)
        db.rollback()
        assert db.query(Payment).one().status == 'succeeded'
        assert db.query(StripeWebhookEvent).count() == 1
    assert _stored_plan(factory, actor['id']) == 'pro'
    state['fail'] = False
    assert _deliver(factory, event) == 'refund:reconciled'
    with factory() as db:
        assert db.query(Payment).one().status == 'refunded'


def test_refund_before_invoice_observation_preserves_missing_history(refund_case):
    from web.services.stripe_service import reconcile_subscription
    from web.database.models import Payment
    factory, actor, state = refund_case
    with factory() as db:
        reconcile_subscription(db, 'sub_person', actor['id'])
        db.commit()
    stale_paid = _event(state['subscription']['latest_invoice'], event_id='evt_paid_after_refund')
    assert _deliver(factory, _refund(state)) == 'refund:reconciled'
    assert _deliver(factory, stale_paid).startswith('pending:')
    with factory() as db:
        assert db.query(Payment).count() == 0


def test_old_refund_updates_old_history_without_touching_paid_renewal(refund_case):
    from web.database.models import Payment
    factory, actor, state = refund_case
    _paid(factory, state)
    renewal = deepcopy(state['invoices']['in_current'])
    renewal.update(id='in_renewal', payment_intent='pi_renewal')
    renewal['charge'].update(id='ch_renewal', invoice='in_renewal', payment_intent='pi_renewal')
    state['invoices']['in_renewal'] = renewal
    state['subscription']['latest_invoice'] = renewal
    state['subscription']['current_period_start'] += 30 * 86400
    state['subscription']['current_period_end'] += 30 * 86400
    _paid(factory, state, event_id='evt_author_renewal_paid')
    assert _deliver(factory, _refund(state)) == 'refund:reconciled'
    with factory() as db:
        assert {p.stripe_invoice_id: p.status for p in db.query(Payment).all()} == {
            'in_current': 'refunded', 'in_renewal': 'succeeded'}
    assert _stored_plan(factory, actor['id']) == 'pro'
