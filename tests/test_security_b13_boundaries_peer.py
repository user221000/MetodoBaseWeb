"""Complementary current37 review: SDK shapes, cursors and private failures."""
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
import stripe

from tests import test_billing_reconciliation13 as author
from web.database.models import Subscription
from web.database.tenant_context import current_tenant
from web.services import billing_reconciliation as service
from web.services.billing_reconciliation_providers import (
    ReadBudget,
    ReadOnlyProviders,
    RetryableRead,
)

account37_engine = author.account37_engine
billing_case = author.billing_case


def test_real_nested_StripeObject_facts_reconcile_selected_elements_without_dict_identity_double(billing_case):
    case = billing_case
    reader = author.ProviderFacts(case)
    reader.subscription_fact = stripe.StripeObject.construct_from(deepcopy(reader.subscription_fact), None)
    reader.charge_fact = stripe.StripeObject.construct_from(deepcopy(reader.charge_fact), None)
    assert isinstance(reader.subscription_fact.latest_invoice, stripe.StripeObject)
    before = author.facts(case)
    result = author.apply(case, reader, author.manifest(case, kind='purchase_intent'))
    assert result['reconciled'] == 1 and result['complete']
    assert author.facts(case)['subscription'][1] == 'active'
    assert author.facts(case)['quota'][3] == before['quota'][3]
    assert [call[0] for call in reader.calls] == ['subscription', 'subscription', 'charge']


def test_transport_close_failure_is_retryable_opaque_and_never_a_confirmed_read(monkeypatch, caplog):
    marker = 'INERT-PRIVATE-TRANSPORT-DIAGNOSTIC-7639'
    closed, retrieved = [], []
    class Transport:
        def __init__(self, timeout):
            assert 0 < timeout <= 5
        def close(self):
            closed.append(True)
            raise OSError(marker)
    class Client:
        def __init__(self, *_args, **kwargs):
            assert kwargs['max_network_retries'] == 0
            self.checkout = SimpleNamespace(sessions=self)
        def retrieve(self, reference, params, options):
            retrieved.append(reference)
            assert options == {'max_network_retries': 0}
            return {'id': reference}
    monkeypatch.setattr(stripe.http_client, 'RequestsClient', Transport)
    monkeypatch.setattr(stripe, 'StripeClient', Client)
    budget = ReadBudget()
    reader = ReadOnlyProviders(budget, SimpleNamespace(STRIPE_SECRET_KEY='inert-synthetic-only'))
    with pytest.raises(RetryableRead) as failure:
        reader.checkout('cs_inert')
    assert str(failure.value) == 'Provider unavailable' and marker not in caplog.text
    assert closed == [True] and retrieved == ['cs_inert'] and budget.reads == 1


def test_cursor_accepts_format_only_changes_and_keeps_foreign_resource_manual_without_SDK(billing_case):
    case = billing_case
    document = json.loads(author.manifest(case))
    document['resources'].append({**document['resources'][0], 'subject_id': case.foreign})
    raw = json.dumps(document).encode()
    before = author.facts(case)
    def forbidden(_budget):
        pytest.fail('Plan or foreign resource constructed provider')
    first = service.run(raw, factory=case.factory, reader_factory=forbidden, max_items=1)
    assert first['planned'] == 1 and first['next_cursor'] and not first['complete']
    formatted = json.dumps(document, indent=4, sort_keys=True).encode()
    second = service.run(formatted, factory=case.factory, reader_factory=forbidden, cursor=first['next_cursor'])
    assert second['manual'] == 1 and second['complete'] and second['provider_reads'] == 0
    assert author.facts(case) == before


def test_cursor_boolean_and_fractional_offsets_fail_before_session_construction(billing_case):
    raw = author.manifest(billing_case)
    _, selection = service.parse_manifest(raw)
    called = []
    def forbidden():
        called.append(True)
        pytest.fail('Malformed cursor opened Session')
    for offset in (True, 0.0):
        with pytest.raises(ValueError, match='Invalid reconciliation cursor'):
            service.run(raw, factory=forbidden, cursor=service._cursor(selection, offset))
    assert called == []


@pytest.mark.parametrize('provider', ['stripe', 'mercadopago'])
def test_persisted_provider_reference_cannot_be_used_as_URL_or_reflected(billing_case, provider, caplog):
    case = billing_case
    marker = 'INERT-PRIVATE-REFERENCE-7639'
    with case.factory() as db:
        row = db.get(Subscription, case.subscription)
        row.provider = provider
        if provider == 'stripe':
            row.stripe_subscription_id = 'https://example.invalid/' + marker
        else:
            row.provider_payment_id = 'https://example.invalid/' + marker
        db.commit()
    reader = author.ProviderFacts(case)
    before = author.facts(case)
    result = author.apply(case, reader, author.manifest(case, provider=provider))
    assert result['manual'] == 1 and result['provider_reads'] == 0 and reader.calls == []
    assert marker not in json.dumps(result) + caplog.text and author.facts(case) == before


def test_malformed_provider_truth_retains_cursor_and_caller_context_without_rights_or_payload_logging(billing_case, caplog):
    case = billing_case
    reader = author.ProviderFacts(case)
    marker = 'INERT-PRIVATE-PROVIDER-BODY-7639'
    reader.subscription_fact['metadata'] = [marker]
    before = author.facts(case)
    token = current_tenant.set(case.foreign)
    try:
        result = author.apply(case, reader)
        assert current_tenant.get() == case.foreign
    finally:
        current_tenant.reset(token)
    assert result['unconfirmed'] == 1 and result['next_cursor'] and not result['complete']
    assert marker not in json.dumps(result) + caplog.text and author.facts(case) == before
