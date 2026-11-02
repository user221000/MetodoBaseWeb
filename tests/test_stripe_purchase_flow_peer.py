"""Independent real-route purchase checks; only Stripe SDK calls are controlled.

Browser coverage uses an owned loopback server, actual page/JS/auth/billing
routes, and signed sessions. It is not provider sandbox or migration evidence.
"""
from datetime import datetime, timedelta, timezone
import importlib
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def purchase_peer(test_gym_user, monkeypatch):
    import stripe
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.settings import get_settings
    from web.services import stripe_service
    with Session(get_engine()) as db:
        actor = db.get(Usuario, test_gym_user['id'])
        actor.email_verified_at = datetime.now(timezone.utc)
        actor.email_verified_contact_version = actor.notification_contact_version
        db.commit()
    monkeypatch.setattr(get_settings(), 'STRIPE_SECRET_KEY', 'offline-qa-sdk-only')
    monkeypatch.setattr(stripe_service, '_init_stripe', lambda: True)
    calls = []
    def checkout(**values):
        calls.append(('checkout', values))
        reference = values['metadata']['purchase_intent_id']
        return SimpleNamespace(id='cs_peer_' + reference,
            url='https://checkout.stripe.com/c/pay/qa-' + reference)
    def portal(**values):
        calls.append(('portal', values))
        return SimpleNamespace(url='https://billing.stripe.com/p/qa-owned')
    monkeypatch.setattr(stripe.checkout.Session, 'create', checkout)
    monkeypatch.setattr(stripe.billing_portal.Session, 'create', portal)
    return SimpleNamespace(actor=test_gym_user, calls=calls)


@pytest.mark.parametrize('factory', ['api.app', 'web.main_web'])
@pytest.mark.parametrize('plan,amount', [('standard',15900), ('gym_comercial',47900), ('clinica',97900)])
def test_checkout_actual_service_persists_owned_intent_without_factor(purchase_peer, factory, plan, amount):
    from web.database.engine import get_engine
    from web.database.models import PurchaseIntent, Payment, Subscription, MfaCredential, MfaAuthorization
    c=purchase_peer
    app=importlib.import_module(factory).create_app()
    payload={'plan':plan, 'success_url':'/suscripciones?result=success', 'cancel_url':'/suscripciones?result=canceled'}
    with TestClient(app,headers=c.actor['auth_headers'],raise_server_exceptions=False) as client:
        first=client.post('/api/billing/checkout',json=payload,headers={'Idempotency-Key':'qa-exact-intent'})
        second=client.post('/api/billing/checkout',json=payload,headers={'Idempotency-Key':'qa-exact-intent'})
        assert first.status_code == second.status_code == 200, (first.text,second.text)
        assert first.json() == second.json()
        wrong=client.post('/api/billing/checkout',json={**payload,'plan':'standard' if plan!='standard' else 'clinica'},
                          headers={'Idempotency-Key':'qa-exact-intent'})
        assert wrong.status_code == 400
    assert len(c.calls)==2 and all(kind=='checkout' for kind,_ in c.calls)
    assert c.calls[0][1]['idempotency_key']==c.calls[1][1]['idempotency_key']
    with Session(get_engine()) as db:
        intent=db.query(PurchaseIntent).one()
        assert (intent.subject_id,intent.plan,intent.amount_cents,intent.currency,intent.status)==(
            c.actor['id'],plan,amount,'mxn','provider_created')
        assert db.query(Payment).count()==db.query(Subscription).count()==0
        assert db.query(MfaCredential).count()==db.query(MfaAuthorization).count()==0


@pytest.mark.parametrize('factory', ['api.app','web.main_web'])
def test_portal_uses_the_current_owners_customer_and_no_action_grant(purchase_peer,factory):
    from web.database.engine import get_engine
    from web.database.models import Subscription, MfaAuthorization
    c=purchase_peer
    with Session(get_engine()) as db:
        db.add(Subscription(gym_id=c.actor['id'],plan='standard',status='active',provider='stripe',
                            stripe_customer_id='cus_qa_owned',current_period_end=datetime.now(timezone.utc)+timedelta(days=20)))
        db.commit()
    app=importlib.import_module(factory).create_app()
    with TestClient(app,headers=c.actor['auth_headers'],raise_server_exceptions=False) as client:
        answer=client.post('/api/billing/portal',json={'return_url':'/suscripciones'})
        assert answer.status_code==200,answer.text
        bad=client.post('/api/billing/portal',json={'return_url':'https://foreign.example.invalid'})
        assert bad.status_code==400
    assert len(c.calls)==1 and c.calls[0][0]=='portal'
    assert c.calls[0][1]['customer']=='cus_qa_owned'
    assert c.calls[0][1]['return_url'].endswith('/suscripciones')
    with Session(get_engine()) as db: assert db.query(MfaAuthorization).count()==0


@pytest.mark.parametrize('factory', ['api.app','web.main_web'])
def test_another_owners_subscription_cannot_be_confirmed(purchase_peer,factory,monkeypatch):
    import stripe
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole,PurchaseIntent,Subscription,Payment
    other=str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Usuario(id=other,email=other+'@example.invalid',nombre='Other synthetic owner',
                        password_hash=hash_password('test123'),tipo='gym',role=UserRole.OWNER,activo=True))
        db.commit()
        intent=PurchaseIntent(subject_id=other,provider='stripe',operation='elements',request_key='qa-other',plan='standard',
            amount_cents=15900,currency='mxn',status='provider_created',provider_reference_id='sub_qa_other',provider_customer_id='cus_qa_other')
        db.add(intent);db.commit();intent_id=intent.id
    reads=[]
    def current(reference,**kwargs):
        reads.append(reference)
        return {'id':'sub_qa_other','customer':'cus_qa_other','status':'incomplete',
            'metadata':{'gym_id':other,'purchase_intent_id':intent_id,'plan':'standard'}}
    monkeypatch.setattr(stripe.Subscription,'retrieve',current)
    with TestClient(importlib.import_module(factory).create_app(),headers=purchase_peer.actor['auth_headers'],raise_server_exceptions=False) as client:
        result=client.post('/api/billing/confirm-subscription',json={'subscription_id':'sub_qa_other'})
        assert result.status_code==400,result.text
        assert other not in result.text and intent_id not in result.text
    assert reads==['sub_qa_other']
    with Session(get_engine()) as db:
        assert db.query(Subscription).count()==db.query(Payment).count()==0
        assert db.query(PurchaseIntent).one().subject_id==other
