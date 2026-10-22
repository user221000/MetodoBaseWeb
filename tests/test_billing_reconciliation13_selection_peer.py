"""Independent finite selection: a second purchase by the same actor is not selected."""
from copy import deepcopy
import uuid

import pytest

from tests import test_billing_reconciliation13 as author
from web.database.models import PurchaseIntent, Subscription

account37_engine=author.account37_engine
billing_case=author.billing_case


@pytest.mark.parametrize('provider',['stripe','mercadopago'])
@pytest.mark.parametrize('different_intent',[False,True],ids=['selected-intent-control','other-intent-same-actor'])
def test_provider_read_must_keep_exact_selected_purchase(billing_case,provider,different_intent):
    case=billing_case
    reader=author.ProviderFacts(case)
    other=str(uuid.uuid4())
    with case.factory() as db:
        selected=db.get(PurchaseIntent,case.intent)
        selected.provider=provider
        selected.operation='checkout' if provider=='stripe' else 'preference'
        selected.provider_reference_id='cs_b13' if provider=='stripe' else 'pref_selected'
        sub=db.get(Subscription,case.subscription)
        if provider=='mercadopago':
            sub.provider=provider
            sub.provider_payment_id=case.payment
            sub.stripe_subscription_id=sub.stripe_customer_id=None
        db.add(PurchaseIntent(id=other,subject_id=case.subject,provider=provider,
            operation='elements' if provider=='stripe' else 'preference',plan='pro_usuario',
            amount_cents=case.amount,currency='mxn',request_key=uuid.uuid4().hex,
            status='provider_created',provider_reference_id=case.reference if provider=='stripe' else 'pref_other',
            provider_customer_id=case.customer))
        db.commit()
    reported=other if different_intent else case.intent
    if provider=='stripe':
        # Checkout itself is correctly bound to A; the subscription lies on B.
        reader.subscription_fact['metadata']['purchase_intent_id']=reported
    else:
        # Search itself is correctly bound to A; the actual payment lies on B.
        reader.payment_fact['external_reference']=reported
        reader.payment_fact['metadata']['purchase_intent_id']=reported
    selection=author.manifest(case,kind='purchase_intent',provider=provider)
    before=deepcopy(author.facts(case))
    with case.factory() as db:
        other_before=db.get(PurchaseIntent,other).status
    result=author.apply(case,reader,selection)
    if different_intent:
        assert result['manual']==1 and result['reconciled']==0
        assert author.facts(case)==before
        with case.factory() as db:
            assert db.get(PurchaseIntent,other).status==other_before
    else:
        assert result['reconciled']==1 and result['manual']==0
        assert author.facts(case)['subscription'][1]=='active'
