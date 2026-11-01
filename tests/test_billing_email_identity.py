"""Owned SQLite account projections and real JWT checks; no payment/provider I/O."""
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


@pytest.fixture(scope='module')
def database_schema(): yield


@pytest.fixture(autouse=True)
def isolated_database(): yield


def request(token, *, extra=(), path='/api/billing/email-verification/request', body=None, content_type='application/json'):
    headers = [(b'authorization', ('Bearer ' + token).encode())] + list(extra)
    if content_type is not None: headers.append((b'content-type', content_type.encode()))
    payload = json.dumps(body or {}).encode()
    messages = [{'type':'http.request','body':payload,'more_body':False}]
    async def receive(): return messages.pop(0)
    return Request({'type':'http','method':'POST','path':path,'headers':headers,
        'client':('192.0.2.71',45000)},receive)


@pytest.fixture
def account(monkeypatch):
    from web.database import engine as database
    from web.database.models import Base, Usuario, UserRole
    from web.database.tenant_context import current_tenant
    from web import auth
    from web.services import billing_email_identity as identity
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    sessions=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    monkeypatch.setattr(database,'_engine',engine)
    monkeypatch.setattr(database,'_SessionLocal',sessions)
    marker=current_tenant.set('')
    auth.init_auth(run_startup_writes=False)
    ids={kind:str(uuid.uuid4()) for kind in ('gym','personal','team','other')}
    with sessions() as db:
        for kind in ids:
            db.add(Usuario(id=ids[kind],email=kind+'@example.invalid',password_hash='unused-synthetic',
                nombre=kind,apellido='',tipo='gym' if kind in {'gym','team','other'} else 'usuario',
                role=UserRole.ADMIN if kind=='team' else UserRole.OWNER if kind!='personal' else UserRole.VIEWER,
                team_gym_id=ids['gym'] if kind=='team' else None,activo=True,session_version=4,
                notification_contact_version=6,fecha_registro=datetime.now(timezone.utc)))
        db.commit()
        identities={kind:auth.identity_from_user(db.get(Usuario,uid),db) for kind,uid in ids.items()}
    tokens={kind:auth.crear_access_token(value) for kind,value in identities.items()}
    try:
        yield SimpleNamespace(service=identity,sessions=sessions,engine=engine,ids=ids,identities=identities,
            tokens=tokens,auth=auth,Usuario=Usuario,UserRole=UserRole)
    finally:
        current_tenant.reset(marker);engine.dispose()


def snapshot(c,kind='gym',action='gym_stripe_checkout',plan='standard',**kwargs):
    with c.sessions() as db:
        return c.service.snapshot(db,c.identities[kind],request(c.tokens[kind]),action,plan,**kwargs)


def test_owner_binding_uses_only_current_account_and_exact_access(account):
    c=account
    binding,email,actor=snapshot(c)
    assert set(binding)=={'actor_id','session_version','notification_contact_version','email_hash','access_hash',
        'tipo','role','team_gym_id','action','plan','catalog_digest'}
    assert email=='gym@example.invalid' and actor['id']==c.ids['gym']
    assert binding['email_hash']==hashlib.sha256(email.encode()).hexdigest()
    assert binding['access_hash']==hashlib.sha256(c.tokens['gym'].encode()).hexdigest()
    assert binding['session_version']==4 and binding['notification_contact_version']==6
    assert email not in json.dumps(binding) and c.tokens['gym'] not in json.dumps(binding)


def test_token_email_claim_cannot_choose_recipient(account):
    c=account
    expected=dict(c.identities['gym']);expected['email']='forged@example.invalid'
    payload=c.auth._decode_token(c.tokens['gym']);payload['email']='forged@example.invalid'
    token=c.auth._make_token(payload)
    with c.sessions() as db:
        binding,email,_=c.service.snapshot(db,expected,request(token),'gym_stripe_checkout','standard')
    assert email=='gym@example.invalid' and binding['email_hash']==hashlib.sha256(email.encode()).hexdigest()


def test_contact_email_and_version_changes_invalidate_old_binding(account):
    c=account
    before,_,_=snapshot(c)
    with c.sessions() as db:
        user=db.get(c.Usuario,c.ids['gym']);user.email='new@example.invalid';user.notification_contact_version+=1;db.commit()
    after,email,_=snapshot(c)
    assert email=='new@example.invalid'
    assert before['email_hash']!=after['email_hash']
    assert before['notification_contact_version']+1==after['notification_contact_version']


@pytest.mark.parametrize('kind,action,plan',[
    ('personal','gym_stripe_checkout','standard'),('team','gym_mp_preference','clinica'),
    ('gym','personal_stripe_checkout','pro'),('gym','personal_stripe_portal','manage')])
def test_business_and_personal_authority_cannot_be_substituted(account,kind,action,plan):
    with pytest.raises(HTTPException) as error:snapshot(account,kind,action,plan)
    assert error.value.status_code==403


@pytest.mark.parametrize('kind',['personal','team'])
def test_personal_purchase_is_bound_to_own_account_not_parent(account,kind):
    c=account
    binding,email,actor=snapshot(c,kind,'personal_stripe_checkout','pro')
    assert binding['actor_id']==actor['id']==c.ids[kind]
    assert binding['actor_id']!=c.ids['gym'] and email==kind+'@example.invalid'


@pytest.mark.parametrize('field,value',[
    ('activo',False),('deleted_at',datetime(2026,11,1,tzinfo=timezone.utc)),
    ('invitation_token','synthetic-invitation'),('session_version',5)])
def test_revocation_or_account_closure_rejects_existing_token(account,field,value):
    c=account
    with c.sessions() as db:
        setattr(db.get(c.Usuario,c.ids['gym']),field,value);db.commit()
    with pytest.raises(HTTPException) as error:snapshot(c)
    assert error.value.status_code==401


def test_current_role_revocation_cannot_reuse_owner_token(account):
    c=account
    with c.sessions() as db:
        db.get(c.Usuario,c.ids['gym']).role=c.UserRole.VIEWER;db.commit()
    with pytest.raises(HTTPException) as error:snapshot(c)
    assert error.value.status_code in {401,403}


def test_disabled_parent_blocks_legacy_team_personal_authority(account):
    c=account
    with c.sessions() as db:
        db.get(c.Usuario,c.ids['gym']).activo=False;db.commit()
    with pytest.raises(HTTPException) as error:snapshot(c,'team','personal_stripe_checkout','pro')
    assert error.value.status_code==401


@pytest.mark.parametrize('mutation',['signature','refresh','subject','version','tenant','duplicate'])
def test_raw_bearer_is_verified_not_merely_hashed(account,mutation):
    c=account
    token=c.tokens['gym'];extra=[]
    if mutation=='signature':
        payload,signature=token.rsplit('.',1)
        token=payload+'.'+('A' if signature[0]!='A' else 'B')+signature[1:]
    elif mutation=='duplicate':extra=[(b'authorization',('Bearer '+token).encode())]
    else:
        payload=c.auth._decode_token(token)
        if mutation=='refresh':payload['type']='refresh'
        elif mutation=='subject':payload['id']=c.ids['other']
        elif mutation=='version':payload['sv']=5
        else:payload['team_gym_id']=c.ids['other']
        token=c.auth._make_token(payload)
    with c.sessions() as db,pytest.raises(HTTPException) as error:
        c.service.snapshot(db,c.identities['gym'],request(token,extra=extra),'gym_stripe_checkout','standard')
    assert error.value.status_code==401


def test_pricing_catalog_change_is_part_of_purchase_authority(account,monkeypatch):
    from web.constants import PLANES_LICENCIA
    c=account
    purchase,_,_=snapshot(c)
    portal,_,_=snapshot(c,action='gym_stripe_portal',plan='manage')
    changed={**PLANES_LICENCIA['standard'],'precio_mxn':PLANES_LICENCIA['standard']['precio_mxn']+1}
    monkeypatch.setitem(PLANES_LICENCIA,'standard',changed)
    next_purchase,_,_=snapshot(c)
    next_portal,_,_=snapshot(c,action='gym_stripe_portal',plan='manage')
    assert next_purchase['catalog_digest']!=purchase['catalog_digest']
    assert next_portal['catalog_digest']!=portal['catalog_digest']


@pytest.mark.parametrize('action,plan',[
    ('gym_stripe_checkout','pro'),('personal_stripe_checkout','standard'),('gym_stripe_portal','clinica'),
    ('unknown','standard'),('gym_stripe_checkout','free')])
def test_action_plan_pair_is_closed_set(account,action,plan):
    with pytest.raises(HTTPException) as error:snapshot(account,action=action,plan=plan)
    assert error.value.status_code==422


@pytest.mark.parametrize('data',[
    {'action':'gym_stripe_checkout','plan':'standard','email':'other@example.invalid'},
    {'action':'gym_stripe_checkout','plan':'standard','actor_id':'other'},
    {'action':True,'plan':'standard'}, {'action':'gym_stripe_checkout','plan':None}])
def test_request_dto_rejects_identity_and_coercion(data):
    from web.routes.billing_email import Begin
    with pytest.raises(ValidationError):Begin.model_validate(data)


@pytest.mark.parametrize('code',[123456,True,'12345','１２３４５６','123456\n'])
def test_verification_dto_requires_six_ascii_digits(code):
    from web.routes.billing_email import Verify
    with pytest.raises(ValidationError):Verify.model_validate({'action':'gym_stripe_checkout','plan':'standard',
        'challenge':'a'*43,'code':code})


def test_verification_dto_preserves_zero_prefix():
    from web.routes.billing_email import Verify
    assert Verify.model_validate({'action':'gym_stripe_checkout','plan':'standard',
        'challenge':'a'*43,'code':'000001'}).code=='000001'


@pytest.mark.asyncio
@pytest.mark.parametrize('extra',[[],[(b'x-billing-email-grant',b'a'*43),(b'x-billing-email-grant',b'b'*43)]])
async def test_missing_or_ambiguous_grant_fails_before_lock_or_sdk(account,monkeypatch,extra):
    c=account
    def unexpected(*args,**kwargs):raise AssertionError('No account lock for absent/ambiguous proof')
    monkeypatch.setattr(c.service,'snapshot',unexpected)
    with c.sessions() as db,pytest.raises(HTTPException) as error:
        await c.service.require_email(db,c.identities['gym'],request(c.tokens['gym'],extra=extra),
            'gym_stripe_checkout','standard',{'plan':'standard'})
    assert error.value.status_code==403


@pytest.mark.asyncio
async def test_admission_uses_fresh_locked_binding_and_exact_body(account,monkeypatch):
    from web.services import billing_email_verification
    c=account;calls=[]
    async def consume(binding,token,req,*,body,idempotency_key):
        calls.append((binding,token,req.url.path,body,idempotency_key))
    monkeypatch.setattr(billing_email_verification,'consume',consume)
    body={'plan':'standard','success_url':'/suscripciones?result=success'}
    with c.sessions() as db:
        actor=await c.service.require_email(db,c.identities['gym'],
            request(c.tokens['gym'],extra=[(b'x-billing-email-grant',b'a'*43)],path='/api/billing/checkout'),
            'gym_stripe_checkout','standard',body,idempotency_key='purchase-1')
        assert db.in_transaction()
        db.rollback()
    assert actor['id']==c.ids['gym'] and len(calls)==1
    assert calls[0][0]['actor_id']==c.ids['gym']
    assert calls[0][1:]==('a'*43,'/api/billing/checkout',body,'purchase-1')
