"""Approved partial refund policy, provider reads synthetic and persistence real."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from tests.test_billing_integrity import _stored_plan
from tests.test_stripe_refund_ledger_author import refund_case, _deliver, _paid, _refund
from tests.test_stripe_webhook_version_contract import _event


@pytest.fixture(scope='session', autouse=True)
def database_schema():
    # Every test owns the complete in-memory domain schema below. Migration
    # acceptance runs separately against genuine SQLite/PostgreSQL databases.
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture
def billing_case(monkeypatch):
    """Own a synchronous domain database; HTTP acceptance belongs to peer QA."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from web.database import engine as engine_module
    from web.database.models import Base, Usuario, UserRole
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(engine_module, '_engine', engine)
    monkeypatch.setattr(engine_module, '_SessionLocal', factory)
    Base.metadata.create_all(engine)
    principal = {'id': 'refund-policy-owner', 'email': 'refund-policy@example.invalid',
                 'tipo': 'usuario', 'role': 'owner', 'team_gym_id': None}
    with factory() as db:
        db.add(Usuario(id=principal['id'], email=principal['email'], password_hash='unused-offline',
            nombre='Synthetic refund owner', tipo='usuario', role=UserRole.OWNER, activo=True))
        db.commit()
    try:
        yield None, factory, principal
    finally:
        engine.dispose()


def test_partial_refund_keeps_exact_paid_period_and_consumed_quota(refund_case):
    from web.database.models import Payment, Subscription, UserSubscription
    from web.services.stripe_service import get_payment_history
    factory, actor, state = refund_case
    _paid(factory, state)
    with factory() as db:
        db.query(UserSubscription).one().planes_usados_mes = 2
        db.commit()
        end = db.query(Subscription).one().current_period_end
    assert _deliver(factory, _refund(state, 1000)) == 'refund:reconciled'
    with factory() as db:
        p = db.query(Payment).one()
        assert (p.status, p.refund_amount_cents, p.stripe_charge_id) == ('partially_refunded', 1000, 'ch_current')
        assert db.query(Subscription).one().current_period_end == end
        projection = db.query(UserSubscription).one()
        assert (projection.plan, projection.planes_usados_mes, projection.max_planes_mes) == ('pro', 2, 5)
        row = get_payment_history(db, actor['id'])[0]
        assert (row['amount_cents'], row['refund_amount_cents'], row['net_amount_cents']) == (7900, 1000, 6900)
        assert datetime.fromisoformat(row['refund_observed_at']).tzinfo is not None
        assert 'stripe_charge_id' not in row


def test_multiple_partials_replay_and_full_refund_are_current_cumulative_facts(refund_case):
    from web.database.models import Payment
    factory, actor, state = refund_case
    _paid(factory, state)
    for index, amount in enumerate((1, 2000, 6500, 7900)):
        event = _refund(state, amount)
        event['id'] += str(index)
        assert _deliver(factory, event) == 'refund:reconciled'
        assert _deliver(factory, event) == 'duplicate:charge.refunded'
        with factory() as db:
            p = db.query(Payment).one()
            assert p.refund_amount_cents == amount
            assert p.status == ('refunded' if amount == 7900 else 'partially_refunded')
    assert _stored_plan(factory, actor['id']) == 'starter'


def test_authoritative_full_charge_revokes_despite_stale_expanded_subscription(refund_case):
    from web.database.models import Payment
    factory, actor, state = refund_case
    _paid(factory, state)
    stale_subscription = deepcopy(state['subscription'])
    event = _refund(state, 7900)
    state['subscription'] = stale_subscription
    assert _deliver(factory, event) == 'refund:reconciled'
    assert _stored_plan(factory, actor['id']) == 'starter'
    with factory() as db:
        assert (db.query(Payment).one().status, db.query(Payment).one().refund_amount_cents) == ('refunded', 7900)
    event['id'] = 'evt_full_refund_fresh_id_stale_embedded_snapshot'
    assert _deliver(factory, event) == 'refund:reconciled'
    assert _stored_plan(factory, actor['id']) == 'starter'


def test_stale_paid_event_cannot_erase_partial_fact_or_move_its_observation_time(refund_case):
    from web.database.models import Payment
    factory, _, state = refund_case
    stale = _event(state['invoices']['in_current'], event_id='evt_stale_success_current_partial')
    _paid(factory, state)
    _deliver(factory, _refund(state, 100))
    with factory() as db:
        observed = db.query(Payment).one().refund_observed_at
    assert _deliver(factory, stale) == 'paid:7900'
    with factory() as db:
        p = db.query(Payment).one()
        assert (p.status, p.refund_amount_cents, p.refund_observed_at) == ('partially_refunded', 100, observed)


def test_current_refund_regression_rolls_back_access_ledger_and_inbox(refund_case):
    from web.database.models import Payment, StripeWebhookEvent
    from web.services.stripe_service import handle_webhook_event
    factory, actor, state = refund_case
    _paid(factory, state)
    _deliver(factory, _refund(state, 500))
    bad = _refund(state, 1)
    bad['id'] = 'evt_current_refund_cannot_regress'
    with factory() as db:
        with pytest.raises(ValueError):
            handle_webhook_event(db, bad)
        db.rollback()
        assert db.query(Payment).one().refund_amount_cents == 500
        assert not db.get(StripeWebhookEvent, bad['id'])
    assert _stored_plan(factory, actor['id']) == 'pro'


def test_legacy_unknown_amount_is_never_presented_as_zero_refund_or_gross_net(refund_case):
    from web.database.models import Payment
    from web.services.stripe_service import get_payment_history
    factory, actor, _ = refund_case
    with factory() as db:
        db.add(Payment(gym_id=actor['id'], amount_cents=7900, currency='mxn', status='refunded'))
        db.commit()
        row = get_payment_history(db, actor['id'])[0]
        assert row['status'] == 'refunded'
        assert (row['refund_amount_cents'], row['net_amount_cents'], row['refund_observed_at']) == (None, None, None)


def test_partial_before_first_invoice_observation_does_not_invent_payment_history(refund_case):
    from web.database.models import Payment
    from web.services.stripe_service import reconcile_subscription
    factory, actor, state = refund_case
    with factory() as db:
        reconcile_subscription(db, 'sub_person', actor['id'])
        db.commit()
    _deliver(factory, _refund(state, 100))
    with factory() as db:
        assert db.query(Payment).count() == 0
    assert _stored_plan(factory, actor['id']) == 'pro'


def test_late_partial_of_old_invoice_keeps_new_paid_renewal_and_exact_new_end(refund_case):
    from web.database.models import Payment, Subscription
    factory, actor, state = refund_case
    _paid(factory, state)
    renewal = deepcopy(state['invoices']['in_current'])
    renewal.update(id='in_renewal', payment_intent='pi_renewal')
    renewal['charge'].update(id='ch_renewal', invoice='in_renewal', payment_intent='pi_renewal')
    state['invoices']['in_renewal'] = renewal
    state['subscription']['latest_invoice'] = renewal
    state['subscription']['current_period_end'] += 30 * 86400
    _paid(factory, state, event_id='evt_refund_policy_renewal')
    _deliver(factory, _refund(state, 500))
    with factory() as db:
        rows = {p.stripe_invoice_id: p for p in db.query(Payment).all()}
        assert rows['in_current'].refund_amount_cents == 500
        assert rows['in_renewal'].refund_amount_cents == 0
        assert rows['in_renewal'].status == 'succeeded'
        assert int(db.query(Subscription).one().current_period_end.replace(tzinfo=timezone.utc).timestamp()) == state['subscription']['current_period_end']
    assert _stored_plan(factory, actor['id']) == 'pro'


def test_expired_partial_payment_does_not_add_a_new_period(refund_case):
    from web.services.billing_integrity import get_individual_subscription
    from web.database.models import Subscription
    factory, actor, state = refund_case
    _paid(factory, state)
    state['subscription']['current_period_end'] = int(datetime.now(timezone.utc).timestamp()) - 1
    _deliver(factory, _refund(state, 500))
    with factory() as db:
        assert get_individual_subscription(db, actor['id']).plan == 'starter'
        assert int(db.query(Subscription).one().current_period_end.replace(tzinfo=timezone.utc).timestamp()) == state['subscription']['current_period_end']


@pytest.mark.parametrize('prior_refund_known', [True, False])
def test_partial_observation_does_not_extend_an_already_observed_invoice(refund_case, prior_refund_known):
    from web.database.models import Subscription, Payment
    factory, _, state = refund_case
    _paid(factory, state)
    with factory() as db:
        original_end = db.query(Subscription).one().current_period_end
        if not prior_refund_known:
            payment = db.query(Payment).one()
            payment.refund_amount_cents = payment.refund_observed_at = payment.stripe_charge_id = None
            db.commit()
    state['subscription']['current_period_start'] += 86400
    state['subscription']['current_period_end'] += 30 * 86400
    _deliver(factory, _refund(state, 1))
    with factory() as db:
        assert db.query(Subscription).one().current_period_end == original_end


@pytest.mark.parametrize('notification', ['invoice', 'refund'])
def test_failed_new_invoice_then_paid_partial_uses_new_period_not_old_expired_end(refund_case, notification):
    from web.database.models import Payment, Subscription
    factory, actor, state = refund_case
    _paid(factory, state)
    boundary = int(datetime.now(timezone.utc).timestamp()) - 60
    with factory() as db:
        sub = db.query(Subscription).one()
        sub.current_period_start = datetime.fromtimestamp(boundary - 30 * 86400, timezone.utc)
        sub.current_period_end = datetime.fromtimestamp(boundary, timezone.utc)
        db.add(Payment(gym_id=actor['id'], stripe_invoice_id='in_new_period',
            stripe_payment_intent_id='pi_new_period', amount_cents=7900, currency='mxn', status='failed'))
        db.commit()
    invoice = deepcopy(state['invoices']['in_current'])
    invoice.update(id='in_new_period', payment_intent='pi_new_period')
    invoice['charge'].update(id='ch_new_period', invoice='in_new_period', payment_intent='pi_new_period',
        amount_refunded=100, refunded=False)
    state['invoices']['in_new_period'] = invoice
    state['subscription']['latest_invoice'] = invoice
    state['subscription']['current_period_start'] = boundary
    state['subscription']['current_period_end'] = boundary + 30 * 86400
    if notification == 'invoice':
        assert _deliver(factory, _event(invoice, event_id='evt_failed_then_paid_partial_renewal')) == 'paid:7900'
    else:
        state['charges']['ch_new_period'] = deepcopy(invoice['charge'])
        event = {'id': 'evt_failed_then_paid_partial_renewal', 'type': 'charge.refunded',
            'livemode': False, 'data': {'object': deepcopy(invoice['charge'])}}
        assert _deliver(factory, event) == 'refund:reconciled'
    with factory() as db:
        sub = db.query(Subscription).one()
        assert sub.status == 'active'
        assert int(sub.current_period_end.replace(tzinfo=timezone.utc).timestamp()) == boundary + 30 * 86400
        assert db.query(Payment).filter_by(stripe_invoice_id='in_new_period').one().status == 'partially_refunded'
    assert _stored_plan(factory, actor['id']) == 'pro'


@pytest.mark.parametrize('field', ['current_period_start', 'current_period_end'])
def test_partial_without_bounded_paid_period_remains_retryable(refund_case, field):
    from web.database.models import Payment, StripeWebhookEvent
    from web.services.stripe_service import handle_webhook_event
    factory, actor, state = refund_case
    _paid(factory, state)
    event = _refund(state, 1)
    state['subscription'].pop(field)
    with factory() as db:
        with pytest.raises(ValueError, match='bounded paid period'):
            handle_webhook_event(db, event)
        db.rollback()
        assert db.query(Payment).one().refund_amount_cents == 0
        assert not db.get(StripeWebhookEvent, event['id'])
    assert _stored_plan(factory, actor['id']) == 'pro'


@pytest.mark.parametrize('amount', [True, -1, 7901, 1.5, '1'])
def test_malformed_partial_amounts_never_become_paid_or_refunded_facts(refund_case, amount):
    from web.database.models import Payment
    from web.services.stripe_service import handle_webhook_event
    factory, actor, state = refund_case
    _paid(factory, state)
    event = _refund(state, amount)
    with factory() as db:
        with pytest.raises(ValueError):
            handle_webhook_event(db, event)
        db.rollback()
        p = db.query(Payment).one()
        assert (p.status, p.refund_amount_cents) == ('succeeded', 0)
    assert _stored_plan(factory, actor['id']) == 'pro'


@pytest.mark.parametrize('mutation', ['partial', 'full', 'paid_type', 'open', 'gross',
                                     'charge_gross', 'capture', 'capture_null', 'out_of_band', 'payment_identity'])
def test_changing_current_funding_between_reads_rolls_back_the_entire_event(refund_case, monkeypatch, mutation):
    from web.database.models import Payment, Subscription, StripeWebhookEvent
    from web.services import stripe_service as service
    factory, _, state = refund_case
    _paid(factory, state)
    normal = deepcopy(state['invoices']['in_current'])
    changed = deepcopy(normal)
    if mutation in {'partial', 'full'}:
        changed['charge'].update(amount_refunded=100 if mutation == 'partial' else 7900,
                                 refunded=mutation == 'full')
    elif mutation == 'paid_type':
        changed['paid'] = 1
    elif mutation == 'open':
        changed.update(paid=False, status='open')
    elif mutation == 'gross':
        changed['amount_paid'] = 7901
    elif mutation == 'charge_gross':
        changed['charge']['amount'] = 7901
    elif mutation == 'capture':
        changed['charge']['captured'] = False
    elif mutation == 'capture_null':
        changed['charge']['amount_captured'] = None
    elif mutation == 'out_of_band':
        changed['paid_out_of_band'] = True
    else:
        changed['charge']['payment_intent'] = 'pi_changed_during_read'
    reads = []
    def retrieve(reference, **kwargs):
        reads.append(reference)
        return deepcopy(changed if len(reads) >= 3 else normal)
    monkeypatch.setattr(service.stripe.Invoice, 'retrieve', retrieve)
    event = _event(normal, event_id='evt_changed_current_funding_' + mutation)
    with factory() as db:
        before = (db.query(Subscription).one().status, db.query(Subscription).one().current_period_end,
                  db.query(Payment).one().status, db.query(Payment).one().refund_amount_cents)
        with pytest.raises(RuntimeError, match='funding changed'):
            service.handle_webhook_event(db, event)
        db.rollback()
        after = (db.query(Subscription).one().status, db.query(Subscription).one().current_period_end,
                 db.query(Payment).one().status, db.query(Payment).one().refund_amount_cents)
        assert before == after and db.get(StripeWebhookEvent, event['id']) is None
    if mutation == 'partial':
        monkeypatch.setattr(service.stripe.Invoice, 'retrieve', lambda *a, **kw: deepcopy(changed))
        assert _deliver(factory, event) == 'paid:7900'
        assert _deliver(factory, event) == 'duplicate:invoice.paid'
        with factory() as db:
            assert (db.query(Payment).one().status, db.query(Payment).one().refund_amount_cents) == ('partially_refunded', 100)


def test_changing_string_charge_resource_cannot_bypass_invoice_coherence(refund_case, monkeypatch):
    from web.database.models import Payment, StripeWebhookEvent
    from web.services import stripe_service as service
    factory, _, state = refund_case
    _paid(factory, state)
    normal = deepcopy(state['invoices']['in_current'])
    original_charge = deepcopy(normal['charge'])
    normal['charge'] = original_charge['id']
    monkeypatch.setattr(service.stripe.Invoice, 'retrieve', lambda *a, **kw: deepcopy(normal))
    reads = []
    def charge_read(reference):
        reads.append(reference)
        actual = deepcopy(original_charge)
        if len(reads) >= 3:
            actual.update(amount_refunded=7900, refunded=True)
        return actual
    monkeypatch.setattr(service.stripe.Charge, 'retrieve', charge_read)
    event = _event(normal, event_id='evt_string_charge_changed_during_read')
    with factory() as db:
        with pytest.raises(RuntimeError, match='funding changed'):
            service.handle_webhook_event(db, event)
        db.rollback()
        assert db.query(Payment).one().refund_amount_cents == 0
        assert db.get(StripeWebhookEvent, event['id']) is None
