"""Independent alias/key wire binding, real MFA HTTP/SQLite, synthetic business ports."""
import pytest
from conftest import database_schema,isolated_database,test_gym_user
from tests.test_mfa31_http import mfa_client,enroll,authenticate,verify_billing_contact

def consumed_grant(actor, grant):
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import MfaAuthorization
    from web.services.mfa_crypto import opaque_digest
    with Session(get_engine()) as db:
        row = db.get(MfaAuthorization,opaque_digest('action',grant))
        assert row is not None and row.user_id == actor['id']
        return row.consumed_at is not None

def payment_request(client, actor, provider, monkeypatch):
    """Use the real deployed router, never mount an alias for a test."""
    routes=set(client.app.openapi()['paths'])
    alias='/api/pagos/'+provider+('/session' if provider=='stripe' else '/preference')
    if alias in routes:
        return alias,{'plan':'standard','email':actor['email'],'success_url':'/checkout/success','cancel_url':'/checkout/cancel'}
    canonical='/api/billing/'+('checkout' if provider=='stripe' else 'mp/preference')
    assert canonical in routes
    body={'plan':'standard','success_url':'/dashboard','cancel_url':'/suscripciones'}
    if provider=='mp':
        from web.settings import get_settings
        monkeypatch.setattr(get_settings(),'MERCADOPAGO_ACCESS_TOKEN','synthetic-non-live-mp-key')
        body['email']=actor['email']
    return canonical,body

def login(mfa_client):
    client,actor,clock=mfa_client
    _,kit=enroll(client,clock);authenticate(client,actor,clock,recovery=kit['recovery_codes'][0])
    verify_billing_contact(actor)
    return client,actor

@pytest.mark.parametrize('mfa_client',['api.app','web.main_web'],indirect=True)
@pytest.mark.parametrize('provider',['stripe','mp'])
def test_deployed_payment_route_keeps_key_with_only_mp_consuming_action_grant(mfa_client,monkeypatch,provider):
    client,actor=login(mfa_client)
    from web.services import stripe_service,mercadopago_service
    calls=[]
    def port(db,*args,**kw):
        calls.append({'key':kw.get('request_key',args[5] if len(args)>5 else None)})
        db.commit()
        return {'session_id':'cs_synthetic','url':'https://provider.example.invalid/synthetic','redirect_url':'https://provider.example.invalid/synthetic'}
    monkeypatch.setattr(stripe_service,'create_checkout_session',port);monkeypatch.setattr(mercadopago_service,'create_preference',port)
    path,body=payment_request(client,actor,provider,monkeypatch)
    key='synthetic-independent-operation-A'
    issued=client.post('/api/auth/mfa/step-up',json={'method':'POST','path':path,'body':body,'idempotency_key':key})
    assert issued.status_code==200
    response=client.post(path,json=body,headers={'X-MFA-Grant':issued.json()['grant'],'Idempotency-Key':key})
    assert response.status_code==200,'Exact alias key bound at issue must remain consumable'
    assert calls==[{'key':key}],'Confirmed operation key must reach the durable business intent'
    assert consumed_grant(actor,issued.json()['grant']) is (provider == 'mp')
    replay=client.post(path,json=body,headers={'X-MFA-Grant':issued.json()['grant'],'Idempotency-Key':key})
    assert replay.status_code == (400 if provider == 'mp' else 200)
    assert calls == [{'key': key}] * (1 if provider == 'mp' else 2)

@pytest.mark.parametrize('mfa_client',['api.app','web.main_web'],indirect=True)
@pytest.mark.parametrize('provider',['stripe','mp'])
def test_only_mp_requires_payment_key_to_match_optional_action_grant(mfa_client,monkeypatch,provider):
    client,actor=login(mfa_client)
    from web.services import stripe_service,mercadopago_service
    calls=[]
    def port(db,*args,**kw):
        calls.append(True);db.commit()
        return {'session_id':'cs_synthetic','url':'https://provider.example.invalid/synthetic','redirect_url':'https://provider.example.invalid/synthetic'}
    monkeypatch.setattr(stripe_service,'create_checkout_session',port);monkeypatch.setattr(mercadopago_service,'create_preference',port)
    path,body=payment_request(client,actor,provider,monkeypatch)
    issued=client.post('/api/auth/mfa/step-up',json={'method':'POST','path':path,'body':body})
    assert issued.status_code==200
    response=client.post(path,json=body,headers={'X-MFA-Grant':issued.json()['grant'],'Idempotency-Key':'synthetic-added-key'})
    assert response.status_code == (403 if provider == 'mp' else 200)
    assert calls == ([] if provider == 'mp' else [True])
    assert not consumed_grant(actor,issued.json()['grant'])
    exact=client.post(path,json=body,headers={'X-MFA-Grant':issued.json()['grant']})
    assert exact.status_code == 200 and calls == [True] * (1 if provider == 'mp' else 2)
    assert consumed_grant(actor,issued.json()['grant']) is (provider == 'mp')

@pytest.mark.parametrize('mfa_client',['api.app','web.main_web'],indirect=True)
def test_canonical_stripe_checkout_keeps_purchase_key_independent_of_optional_grant(mfa_client,monkeypatch):
    client,actor=login(mfa_client)
    from web.services import stripe_service
    calls=[]
    def port(db,*args,**kw):
        calls.append(kw['request_key']);db.commit();return {'session_id':'cs_synthetic','url':'https://provider.example.invalid/synthetic'}
    monkeypatch.setattr(stripe_service,'create_checkout_session',port)
    body={'plan':'standard','success_url':'/dashboard','cancel_url':'/suscripciones'};key='synthetic-canonical-key'
    issued=client.post('/api/auth/mfa/step-up',json={'method':'POST','path':'/api/billing/checkout','body':body,'idempotency_key':key})
    assert issued.status_code==200
    grant=issued.json()['grant']
    bad=client.post('/api/billing/checkout',json=body,headers={'X-MFA-Grant':grant,'Idempotency-Key':'synthetic-changed-key'})
    assert bad.status_code==200 and calls==['synthetic-changed-key']
    good=client.post('/api/billing/checkout',json=body,headers={'X-MFA-Grant':grant,'Idempotency-Key':key})
    assert good.status_code==200 and calls==['synthetic-changed-key',key]
    assert not consumed_grant(actor,grant)


@pytest.mark.parametrize('mfa_client',['web.main_web'],indirect=True)
@pytest.mark.parametrize('provider',['stripe','mp'])
def test_web_aliases_remain_unmounted_and_never_reach_a_provider(mfa_client,monkeypatch,provider):
    client,actor=login(mfa_client)
    from web.services import stripe_service,mercadopago_service
    calls=[]
    def port(*args,**kwargs):
        calls.append(True)
        raise AssertionError('Unregistered route cannot invoke a business port')
    monkeypatch.setattr(stripe_service,'create_checkout_session',port)
    monkeypatch.setattr(mercadopago_service,'create_preference',port)
    path='/api/pagos/'+provider+('/session' if provider=='stripe' else '/preference')
    assert path not in client.app.openapi()['paths']
    response=client.post(path,json={'plan':'standard','email':actor['email'],'success_url':'/checkout/success','cancel_url':'/checkout/cancel'},headers={'Idempotency-Key':'synthetic-key'})
    assert response.status_code==404 and calls==[]
