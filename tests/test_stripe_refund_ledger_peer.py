"""Independent refund ledger regressions, actual HMAC/HTTP/SQLAlchemy.

Current Charge reads are explicit doubles. No live provider or charge is used.
"""
from copy import deepcopy
import pytest
import stripe
from tests.test_stripe_invoice_authority_peer import (
    billing_case, invoice_case, event_from, deliver, client_for, SURFACES,
)


def refund_event(charge, event_id='evt_peer_full_refund'):
    return {'id': event_id, 'object': 'event', 'type': 'charge.refunded',
            'api_version': '2026-03-25.dahlia', 'livemode': False,
            'data': {'object': deepcopy(charge)}}


def make_paid(case, surface):
    factory, actor, state = case
    state['invoice']['charge']['status'] = 'succeeded'
    state['subscription']['latest_invoice'] = deepcopy(state['invoice'])
    client = client_for(surface)
    paid = deliver(client, surface[1], event_from(state))
    assert paid.status_code == 200 and paid.json()['result'] == 'paid:7900'
    return client


def set_refunded(state, amount=7900):
    state['invoice']['charge'].update(refunded=amount==7900, amount_refunded=amount)
    state['subscription']['latest_invoice'] = deepcopy(state['invoice'])
    return deepcopy(state['invoice']['charge'])


@pytest.mark.parametrize('surface', SURFACES)
def test_full_verified_refund_is_visible_in_existing_payment_history(invoice_case, monkeypatch, surface):
    factory, actor, state = invoice_case
    from web.database.models import Payment, UserSubscription
    from web.services.stripe_service import get_payment_history
    client = make_paid(invoice_case, surface)
    actual = set_refunded(state)
    reads = []
    def read(reference, **kwargs):
        reads.append(reference)
        # SDK-native response, including its dict subclass behavior.
        return stripe.Charge.construct_from(deepcopy(actual), 'sk_test_owned_no_network')
    monkeypatch.setattr(stripe.Charge, 'retrieve', read)
    event = refund_event(actual)
    refund = deliver(client, surface[1], event)
    assert refund.status_code == 200 and refund.json()['result'] == 'refund:reconciled'
    with factory() as db:
        assert db.query(UserSubscription).filter_by(user_id=actor['id']).one().plan == 'starter'
        assert db.query(Payment).count() == 1
        history = get_payment_history(db, actor['id'])
        assert history[0]['status'] == 'refunded'
        assert history[0]['amount_cents'] == 7900
    assert reads and set(reads) == {'ch_peer'}
    verified_reads = len(reads)
    replay = deliver(client, surface[1], event)
    assert replay.status_code == 200 and replay.json()['result'] == 'duplicate:charge.refunded'
    assert len(reads) == verified_reads


@pytest.mark.parametrize('surface', SURFACES)
def test_charge_read_failure_remains_retryable_and_never_acknowledges_refund(invoice_case, monkeypatch, surface):
    factory, _, state = invoice_case
    from web.database.models import Payment, StripeWebhookEvent
    client = make_paid(invoice_case, surface)
    actual = set_refunded(state)
    event = refund_event(actual)
    def unavailable(*a, **kw):
        raise TimeoutError('synthetic-owned-provider-failure')
    monkeypatch.setattr(stripe.Charge, 'retrieve', unavailable)
    failure = deliver(client, surface[1], event)
    assert failure.status_code == 503
    with factory() as db:
        assert db.query(Payment).one().status == 'succeeded'
        assert db.query(StripeWebhookEvent).filter_by(event_id=event['id']).count() == 0
    monkeypatch.setattr(stripe.Charge, 'retrieve', lambda *a, **kw: deepcopy(actual))
    retried = deliver(client, surface[1], event)
    assert retried.status_code == 200
    with factory() as db:
        assert db.query(Payment).one().status == 'refunded'


@pytest.mark.parametrize('mutation', ['id','customer','invoice','mode','currency','amount','refunded_amount','paid','captured','event_mode'])
def test_wrong_charge_authority_cannot_rewrite_ledger_or_acknowledge(invoice_case, monkeypatch, mutation):
    factory, _, state = invoice_case
    from web.database.models import Payment, StripeWebhookEvent, UserSubscription
    surface = SURFACES[0]
    client = make_paid(invoice_case, surface)
    actual = set_refunded(state)
    event = refund_event(actual)
    if mutation in {'id','customer','invoice'}:
        actual[mutation] = {'id':'ch_other','customer':'cus_other','invoice':'in_other'}[mutation]
    elif mutation=='mode':
        actual['livemode']=True
    elif mutation=='currency':
        actual['currency']='usd'
    elif mutation=='amount':
        actual['amount']=1
    elif mutation=='refunded_amount':
        actual['amount_refunded']=8000
    elif mutation in {'paid','captured'}:
        actual[mutation]=False
    else:
        event['livemode']=True
    monkeypatch.setattr(stripe.Charge, 'retrieve', lambda *a, **kw: deepcopy(actual))
    denied = deliver(client, surface[1], event)
    assert denied.status_code == 503, denied.text
    with factory() as db:
        assert db.query(Payment).one().status == 'succeeded'
        assert db.query(StripeWebhookEvent).filter_by(event_id=event['id']).count() == 0
        assert db.query(UserSubscription).one().plan == 'pro'


@pytest.mark.parametrize('surface', SURFACES)
def test_partial_refund_is_never_misreported_as_full_refund(invoice_case, monkeypatch, surface):
    factory, _, state = invoice_case
    from web.database.models import Payment
    client = make_paid(invoice_case, surface)
    actual = set_refunded(state, amount=1)
    monkeypatch.setattr(stripe.Charge, 'retrieve', lambda *a, **kw: deepcopy(actual))
    response = deliver(client, surface[1], refund_event(actual))
    assert response.status_code == 200, response.text
    with factory() as db:
        row = db.query(Payment).one()
        assert (row.status,row.amount_cents)==('succeeded',7900)


@pytest.mark.parametrize('surface', SURFACES)
def test_old_refund_updates_old_ledger_and_preserves_new_paid_renewal(invoice_case, monkeypatch, surface):
    factory, _, state = invoice_case
    from web.database.models import Payment, UserSubscription
    client = make_paid(invoice_case, surface)
    old_charge = deepcopy(state['invoice']['charge'])
    old_charge.update(refunded=True,amount_refunded=7900)
    old_invoice = deepcopy(state['invoice'])
    old_invoice['charge'] = deepcopy(old_charge)
    state['invoice']['id']='in_peer_new'
    state['invoice']['payment_intent']='pi_peer_new'
    state['invoice']['charge'].update(id='ch_peer_new',invoice='in_peer_new')
    state['subscription']['latest_invoice']=deepcopy(state['invoice'])
    renewed = event_from(state)
    renewed['id']='evt_peer_renewal'
    response = deliver(client,surface[1],renewed)
    assert response.status_code==200 and response.json()['result']=='paid:7900'
    monkeypatch.setattr(stripe.Charge,'retrieve',lambda *a,**kw:deepcopy(old_charge))
    invoices = {'in_peer':old_invoice,'in_peer_new':deepcopy(state['invoice'])}
    monkeypatch.setattr(stripe.Invoice,'retrieve',lambda reference,**kw:deepcopy(invoices[reference]))
    refund = deliver(client,surface[1],refund_event(old_charge))
    assert refund.status_code==200,refund.text
    with factory() as db:
        assert db.query(Payment).filter_by(stripe_invoice_id='in_peer').one().status=='refunded'
        assert db.query(Payment).filter_by(stripe_invoice_id='in_peer_new').one().status=='succeeded'
        assert db.query(UserSubscription).one().plan=='pro'


@pytest.mark.parametrize('surface', SURFACES)
def test_refund_without_existing_payment_never_fabricates_paid_ledger(invoice_case, monkeypatch, surface):
    factory, _, state=invoice_case
    from web.database.models import Payment
    from web.services.stripe_service import reconcile_subscription
    # A legacy subscription may already be bound/active without a monetary
    # history row. Prepare that real state without creating a synthetic payment.
    with factory() as db:
        assert reconcile_subscription(db,'sub_peer')['activated']
        db.commit()
    actual=set_refunded(state)
    monkeypatch.setattr(stripe.Charge,'retrieve',lambda *a,**kw:deepcopy(actual))
    response=deliver(client_for(surface),surface[1],refund_event(actual))
    assert response.status_code==200,response.text
    with factory() as db:
        assert db.query(Payment).count()==0
