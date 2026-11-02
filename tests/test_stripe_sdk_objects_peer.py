"""Exercise SDK-native response objects instead of only plain provider dicts."""
from copy import deepcopy

import pytest
import stripe

from tests.test_stripe_invoice_authority_peer import (
    billing_case, invoice_case, event_from, deliver, client_for, SURFACES,
)


@pytest.mark.parametrize('surface', SURFACES)
def test_sdk_native_invoice_subscription_and_charge_are_accepted_only_after_verification(
        invoice_case, monkeypatch, surface):
    factory, _, state = invoice_case
    invoice = stripe.Invoice.construct_from(deepcopy(state['invoice']), 'sk_test_owned_no_network')
    subscription = stripe.Subscription.construct_from(deepcopy(state['subscription']), 'sk_test_owned_no_network')
    assert isinstance(invoice, stripe.Invoice)
    assert isinstance(invoice.get('charge'), stripe.Charge)
    assert isinstance(subscription.get('latest_invoice'), stripe.Invoice)
    reads = []
    def read(reference, **kwargs):
        reads.append(reference)
        return invoice
    monkeypatch.setattr(stripe.Invoice, 'retrieve', read)
    monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda *a, **kw: subscription)
    event = event_from(state)
    response = deliver(client_for(surface), surface[1], event)
    assert response.status_code == 200, response.text
    assert response.json()['result'] == 'paid:7900'
    assert reads
    from web.database.models import Payment
    with factory() as db:
        assert db.query(Payment).one().status == 'succeeded'
