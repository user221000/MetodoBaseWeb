"""Current-schema Google/mail security reauth acceptance, independent QA.

Only Google JWKS HTTP, mailbox delivery and Redis wire are synthetic in the
HTTP cases. The final test runs the exact Lua in an owned ephemeral Redis.
No account/password/charge/provider from production is accessed.
"""
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from tests.google33_signed_provider import SignedProvider


@pytest.fixture(scope='module')
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


class MailRedis:
    """Atomic protocol model, separate from the real Lua acceptance below."""
    def __init__(self, service):
        self.service=service
        self.rows={}
        self.now=0
        self.fail=None
        self.lock=asyncio.Lock()

    def read(self,key):
        value=self.rows.get(key)
        if value and value[1]<=self.now:
            self.rows.pop(key,None)
            return None
        return value

    async def get(self,key):
        if self.fail=='get':raise ConnectionError('synthetic-private-transport')
        row=self.read(key)
        return row[0] if row else None

    async def delete(self,key):
        if self.fail=='delete':raise ConnectionError('synthetic-private-transport')
        return int(self.rows.pop(key,None) is not None)

    async def eval(self,script,count,*arguments):
        if self.fail in ('eval',script):raise ConnectionError('synthetic-private-transport')
        keys,args=arguments[:count],arguments[count:]
        async with self.lock:
            if script==self.service.BEGIN_LUA:
                challenge,active,cooldown=keys
                item,ttl,wait,reference=args
                pending=self.read(cooldown)
                if pending:return [0,max(1,(pending[1]-self.now)//1000)]
                if self.read(challenge):return [-1]
                self.rows[challenge]=(item,self.now+ttl*1000)
                self.rows[active]=(reference,self.now+ttl*1000)
                self.rows[cooldown]=('1',self.now+wait*1000)
                return [1]
            if script==self.service.ACTIVATE_LUA:
                challenge,active=keys
                payload,signature,reference=args
                row,current=self.read(challenge),self.read(active)
                if not row or not current or current[0]!=reference:return [0]
                item=json.loads(row[0])
                if (item['payload'],item['signature'])!=(payload,signature):return [0]
                item['delivery_ready']=True
                self.rows[challenge]=(json.dumps(item),row[1])
                return [1]
            assert script==self.service.CONSUME_LUA
            challenge,active=keys
            payload,signature,digest,reference,maximum=args
            row,current=self.read(challenge),self.read(active)
            if not row or not current or current[0]!=reference:return [0]
            item=json.loads(row[0])
            if not item['delivery_ready'] or (item['payload'],item['signature'])!=(payload,signature):return [0]
            if item['code_digest']!=digest:
                item['attempts']+=1
                if item['attempts']>=maximum:self.rows.pop(challenge,None)
                else:self.rows[challenge]=(json.dumps(item),row[1])
                return [0]
            self.rows.pop(challenge,None);self.rows.pop(active,None)
            return [1]


@pytest.fixture
def reauth_case(monkeypatch):
    from web import auth
    from web.database import engine as database
    from web.database.models import AuthExternalIdentity,Base,Usuario,UserRole
    from web.database.tenant_context import current_tenant
    from web.services import email_service,google_mfa_reauthentication as service,mfa_service as mfa
    from web.settings import get_settings

    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    sessions=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    monkeypatch.setattr(database,'_engine',engine)
    monkeypatch.setattr(database,'_SessionLocal',sessions)
    settings=get_settings()
    monkeypatch.setattr(settings,'REDIS_URL','redis://127.0.0.1:56379/15')
    monkeypatch.setattr(settings,'RESEND_API_KEY','synthetic-never-used')
    monkeypatch.setattr(settings,'RESEND_FROM_EMAIL','Method Base <no-reply@example.invalid>')
    monkeypatch.setattr(settings,'MFA_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'S'*32).decode())
    monkeypatch.setattr(settings,'GOOGLE_CLIENT_ID','synthetic-mfa-mail.apps.googleusercontent.com')
    marker=current_tenant.set('')
    auth.init_auth(run_startup_writes=False)
    ids={letter:str(uuid.uuid4()) for letter in ('a','b')}
    with sessions() as db:
        for letter,user_id in ids.items():
            db.add(Usuario(id=user_id,email=f'contact-{letter}@example.invalid',nombre=f'Synthetic {letter}',
                apellido='',password_hash='synthetic-unused-hash',tipo='gym',role=UserRole.OWNER,
                activo=True,session_version=0,notification_contact_version=2))
            db.flush()
            db.add(AuthExternalIdentity(id=str(uuid.uuid4()),user_id=user_id,
                issuer='https://accounts.google.com',subject=f'mfa-mail-{letter}',version=1,
                created_at=datetime.now(timezone.utc)))
        db.commit()
        identities={letter:auth.identity_from_user(db.get(Usuario,user_id),db) for letter,user_id in ids.items()}
    tokens={letter:auth.crear_access_token(identity) for letter,identity in identities.items()}
    clock=[datetime.now(timezone.utc)]
    real_clock=mfa.instant
    monkeypatch.setattr(mfa,'instant',lambda now=None:real_clock(clock[0] if now is None else now))
    cache=MailRedis(service);mail=[]
    async def redis():return cache
    async def allowed(*args,**kwargs):return True,{'retry_after':0,'remaining':999},'synthetic'
    monkeypatch.setattr(service,'cache',redis)
    from web import rate_limiter_redis
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',allowed)
    def send(email,code):mail.append((email,code));return True
    monkeypatch.setattr(email_service,'send_security_verification_code',send)
    now=int(datetime.now(timezone.utc).timestamp())
    claims={'iss':'https://accounts.google.com','sub':'mfa-mail-a','aud':settings.GOOGLE_CLIENT_ID,
        'email':'provider-a@example.invalid','email_verified':True,'iat':now,'exp':now+3600}
    provider=SignedProvider(monkeypatch,claims)
    req=Request({'type':'http','method':'POST','path':'/api/auth/mfa/google-email/request',
                 'headers':[],'client':('192.0.2.77',50000)})
    case=SimpleNamespace(service=service,mfa=mfa,auth=auth,engine=engine,sessions=sessions,
        ids=ids,identities=identities,tokens=tokens,cache=cache,mail=mail,clock=clock,
        provider=provider,request=req,settings=settings)
    try:yield case
    finally:current_tenant.reset(marker);engine.dispose()


async def issue(c,letter='a',credential=None):
    return await c.service.begin(c.identities[letter],c.tokens[letter],credential or c.provider.credential(),c.request)


async def confirm(c,issued,*,letter='a',code=None,access=None):
    return await c.service.verify(c.identities[letter],access or c.tokens[letter],issued['challenge'],
                                  c.mail[-1][1] if code is None else code,c.request)


def proofs(c):
    from web.database.models import MfaAuthorization
    with c.sessions() as db:return db.scalars(select(MfaAuthorization)).all()


@pytest.mark.asyncio
async def test_basic_google_and_fresh_mail_issue_only_existing_session_bound_proof(reauth_case):
    from web.database.models import Usuario
    c=reauth_case
    with c.sessions() as db:
        user=db.get(Usuario,c.ids['a']);user.email_verified_at=c.clock[0]-timedelta(days=5)
        user.email_verified_contact_version=user.notification_contact_version;db.commit()
    issued=await issue(c)
    assert 'auth_time' not in c.provider.claims
    assert c.mail[0][0]=='contact-a@example.invalid'
    assert issued['masked_email']=='c***@example.invalid' and issued['resend_after_seconds']==60
    assert 'contact-a@example.invalid' not in json.dumps(issued)
    assert c.mail[0][1] not in json.dumps(issued) and not proofs(c)
    raw=json.dumps(c.cache.rows)
    assert c.mail[0][1] not in raw and 'contact-a@example.invalid' not in raw
    result=await confirm(c,issued)
    assert set(result)=={'reauthentication_token','expires_at'}
    row=proofs(c)[0]
    assert row.purpose=='reauth' and row.primary_method=='google' and row.factor_verified_at is None
    assert row.access_hash==c.mfa.access_digest(c.tokens['a'])
    assert c.mfa.aware(row.expires_at)-c.clock[0]==timedelta(minutes=5)
    with c.sessions() as db:
        assert db.get(Usuario,c.ids['a']).email_verified_contact_version==2
        assert db.get(Usuario,c.ids['b']).email_verified_at is None
    with pytest.raises(HTTPException):await confirm(c,issued)
    assert len(proofs(c))==1


@pytest.mark.asyncio
async def test_recipient_a_and_b_are_current_account_contacts_not_provider_email(reauth_case):
    c=reauth_case
    a=await issue(c)
    b_claims={**c.provider.claims,'sub':'mfa-mail-b','email':'provider-b@example.invalid'}
    b=await issue(c,'b',c.provider.credential(claims=b_claims))
    assert [row[0] for row in c.mail]==['contact-a@example.invalid','contact-b@example.invalid']
    with pytest.raises(HTTPException):await confirm(c,a,letter='b',code=c.mail[0][1])
    assert not proofs(c)
    await confirm(c,a,code=c.mail[0][1])
    await confirm(c,b,letter='b',code=c.mail[1][1])
    assert {row.user_id for row in proofs(c)}==set(c.ids.values())


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['foreign_subject','wrong_audience','wrong_signature','wrong_issuer','expired','future_iat'])
async def test_invalid_or_unlinked_google_never_sends_or_grants(reauth_case,kind):
    c=reauth_case
    claims={**c.provider.claims}
    if kind=='foreign_subject':claims['sub']='mfa-mail-b'
    elif kind=='wrong_audience':claims['aud']='different-client'
    elif kind=='wrong_issuer':claims['iss']='https://untrusted.example.invalid'
    elif kind=='expired':claims['exp']=int(time.time())-1
    elif kind=='future_iat':claims['iat']=int(time.time())+600
    elif kind=='wrong_signature':
        from cryptography.hazmat.primitives.asymmetric import rsa
        credential=c.provider.credential(key=rsa.generate_private_key(public_exponent=65537,key_size=2048))
    credential=credential if kind=='wrong_signature' else c.provider.credential(claims=claims)
    with pytest.raises(HTTPException) as error:await issue(c,credential=credential)
    assert error.value.status_code in {401,403}
    assert c.mail==[] and not proofs(c)


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation',['session','role','contact','contact_version','google_version','google_revoked','factor_generation','access'])
async def test_changed_authority_after_send_cannot_create_reauthentication(reauth_case,mutation):
    from web.database.models import AuthExternalIdentity,MfaCredential,Usuario,UserRole
    c=reauth_case;issued=await issue(c);access=None
    with c.sessions() as db:
        user=db.get(Usuario,c.ids['a'])
        if mutation=='session':user.session_version+=1
        elif mutation=='role':user.role=UserRole.VIEWER
        elif mutation=='contact':user.email='changed@example.invalid'
        elif mutation=='contact_version':user.notification_contact_version+=1
        elif mutation=='factor_generation':db.get(MfaCredential,user.id).generation+=1
        elif mutation.startswith('google_'):
            binding=db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.user_id==user.id))
            if mutation=='google_version':binding.version+=1
            else:binding.revoked_at=c.clock[0]
        else:access=c.auth.crear_access_token(c.identities['a'])
        db.commit()
    with pytest.raises(HTTPException):await confirm(c,issued,access=access)
    assert not proofs(c)


@pytest.mark.asyncio
async def test_wrong_attempts_preserve_expiry_and_fifth_discards_the_challenge(reauth_case):
    c=reauth_case;issued=await issue(c);challenge_key=c.service.key(issued['challenge'])
    expiry=c.cache.rows[challenge_key][1]
    wrong='000001' if c.mail[-1][1]!='000001' else '000002'
    for index in range(5):
        c.cache.now+=1000;c.clock[0]+=timedelta(seconds=1)
        with pytest.raises(HTTPException) as error:await confirm(c,issued,code=wrong)
        assert error.value.status_code==400
        if index<4:
            assert c.cache.rows[challenge_key][1]==expiry
            assert json.loads(c.cache.rows[challenge_key][0])['attempts']==index+1
    assert challenge_key not in c.cache.rows
    with pytest.raises(HTTPException):await confirm(c,issued)
    assert not proofs(c)


@pytest.mark.asyncio
async def test_expiry_and_resend_do_not_resurrect_old_codes(reauth_case):
    c=reauth_case;old=await issue(c);old_code=c.mail[-1][1]
    with pytest.raises(HTTPException) as throttled:await issue(c)
    assert throttled.value.status_code==429 and throttled.value.headers['Retry-After']=='60'
    c.cache.now=61000;c.clock[0]+=timedelta(seconds=61)
    new=await issue(c)
    with pytest.raises(HTTPException):await confirm(c,old,code=old_code)
    c.cache.now+=301000;c.clock[0]+=timedelta(seconds=301)
    with pytest.raises(HTTPException):await confirm(c,new)
    assert not proofs(c)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['rejected','exception','activate','redis'])
async def test_delivery_or_backend_uncertainty_never_grants(reauth_case,monkeypatch,caplog,failure):
    from web.services import email_service
    c=reauth_case
    if failure=='rejected':monkeypatch.setattr(email_service,'send_security_verification_code',lambda *a:False)
    elif failure=='exception':
        def sender(*args):raise RuntimeError('synthetic-private-mailbox')
        monkeypatch.setattr(email_service,'send_security_verification_code',sender)
    elif failure=='activate':c.cache.fail=c.service.ACTIVATE_LUA
    else:c.cache.fail='eval'
    with pytest.raises(HTTPException) as error:await issue(c)
    assert error.value.status_code==503 and not proofs(c)
    assert 'synthetic-private-mailbox' not in caplog.text
    assert 'contact-a@example.invalid' not in caplog.text
    for _,raw in c.cache.rows.items():
        if isinstance(raw[0],str) and 'delivery_ready' in raw[0]:assert json.loads(raw[0])['delivery_ready'] is False


@pytest.mark.asyncio
async def test_unknown_database_commit_does_not_return_a_token_or_allow_code_replay(reauth_case,monkeypatch):
    from sqlalchemy.orm import Session
    c=reauth_case;issued=await issue(c)
    def fail_commit(self):raise RuntimeError('synthetic-commit-unknown')
    monkeypatch.setattr(Session,'commit',fail_commit)
    with pytest.raises(HTTPException) as error:await confirm(c,issued)
    assert error.value.status_code==503
    assert not proofs(c)
    with pytest.raises(HTTPException):await confirm(c,issued)


@pytest.mark.asyncio
@pytest.mark.parametrize('delay',[-1,30,301])
async def test_finish_queue_never_extends_freshness_or_accepts_future_or_expired_proof(reauth_case,monkeypatch,delay):
    from web.database.models import Usuario
    c=reauth_case;issued=await issue(c);verified_at=c.clock[0]
    original=c.service.finish
    def delayed(*args,**kwargs):
        c.clock[0]+=timedelta(seconds=delay)
        return original(*args,**kwargs)
    monkeypatch.setattr(c.service,'finish',delayed)
    if delay<0 or delay>=300:
        with pytest.raises(HTTPException) as error:await confirm(c,issued)
        assert error.value.status_code==400 and not proofs(c)
    else:
        result=await confirm(c,issued)
        row=proofs(c)[0]
        assert c.mfa.aware(row.expires_at)==verified_at+timedelta(seconds=300)
        assert c.mfa.aware(row.expires_at)-c.clock[0]==timedelta(seconds=270)
        with c.sessions() as db:assert c.mfa.aware(db.get(Usuario,c.ids['a']).email_verified_at)==verified_at
        assert c.mfa.aware(result['expires_at'])==c.mfa.aware(row.expires_at)


@pytest.mark.asyncio
async def test_pending_delivery_and_tampered_signature_cannot_create_a_proof(reauth_case,monkeypatch):
    c=reauth_case
    challenge='R'*43
    monkeypatch.setattr(c.service.secrets,'token_urlsafe',lambda count:challenge)
    c.cache.fail=c.service.ACTIVATE_LUA
    with pytest.raises(HTTPException):await issue(c)
    c.cache.fail=None
    with pytest.raises(HTTPException):
        await c.service.verify(c.identities['a'],c.tokens['a'],challenge,c.mail[-1][1],c.request)
    row_key=c.service.key(challenge)
    item=json.loads(c.cache.rows[row_key][0]);item['payload']=item['payload'].replace('"role":"owner"','"role":"viewer"')
    c.cache.rows[row_key]=(json.dumps(item),c.cache.rows[row_key][1])
    with pytest.raises(HTTPException) as error:
        await c.service.verify(c.identities['a'],c.tokens['a'],challenge,c.mail[-1][1],c.request)
    assert error.value.status_code==400 and not proofs(c)


@pytest.mark.asyncio
async def test_real_rate_adapter_hashes_actor_ip_and_requires_distributed_sensitive_budget(reauth_case,monkeypatch):
    from web import rate_limiter_redis
    c=reauth_case;seen=[]
    async def allow(key,maximum,window,**kwargs):
        seen.append((key,maximum,window,kwargs));return True,{'retry_after':0},'synthetic'
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',allow)
    await c.service.limit(c.request,c.ids['a'],'send')
    await c.service.limit(c.request,c.ids['a'],'verify')
    assert [entry[1] for entry in seen]==[3,10,10,30]
    assert all(entry[2:]==(900,{'use_redis':True,'sensitive':True}) for entry in seen)
    assert c.ids['a'] not in repr(seen) and '192.0.2.77' not in repr(seen)
    async def deny(*args,**kwargs):return False,{'retry_after':17},'synthetic'
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',deny)
    with pytest.raises(HTTPException) as error:await c.service.limit(c.request,c.ids['a'],'send')
    assert error.value.status_code==429 and error.value.headers['Retry-After']=='17'


@pytest.fixture(params=['web.main_web','api.app'])
def reauth_http(request,reauth_case):
    c=reauth_case
    app=importlib.import_module(request.param).create_app()
    with TestClient(app,raise_server_exceptions=False,
            headers={'Authorization':'Bearer '+c.tokens['a']},client=('127.5.7.9',50000)) as client:
        yield c,client


def http_proof(c,client):
    issued=client.post('/api/auth/mfa/google-email/request',json={'google_credential':c.provider.credential()})
    assert issued.status_code==202,issued.text
    assert 'no-store' in issued.headers['cache-control']
    verified=client.post('/api/auth/mfa/google-email/verify',json={'challenge':issued.json()['challenge'],'code':c.mail[-1][1]})
    assert verified.status_code==200,verified.text
    return verified.json()['reauthentication_token']


def test_http_basic_google_mail_enrolls_with_real_totp_without_auth_time(reauth_http):
    from web.services.mfa_crypto import totp
    c,client=reauth_http
    proof=http_proof(c,client)
    assert 'auth_time' not in c.provider.claims
    started=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':proof})
    assert started.status_code==200,started.text
    value=started.json()
    seed=base64.b32decode(value['secret'])
    enabled=client.post('/api/auth/mfa/enroll/confirm',json={'enrollment_id':value['enrollment_id'],
        'code':totp(seed,int(c.clock[0].timestamp())//30)})
    assert enabled.status_code==200,enabled.text
    assert enabled.json()['enabled'] is True and len(enabled.json()['recovery_codes'])==8


def test_http_reauth_proof_never_authorizes_a_charge_or_bypasses_existing_factor(reauth_http,monkeypatch):
    from web.database.models import MfaCredential
    from web.services.mfa_crypto import encrypt,totp
    from web.services import stripe_service
    c,client=reauth_http
    secret=b'IndependentQASeed1234'
    with c.sessions() as db:
        user=db.get(importlib.import_module('web.database.models').Usuario,c.ids['a'])
        row=c.mfa.credential(db,user.id,create=True);row.generation=1
        row.secret_ciphertext=encrypt(secret,c.mfa.configuration(),c.mfa._aad(row,1,'active'))
        row.enabled_at=c.clock[0];db.commit()
    token=c.auth.crear_access_token(c.identities['a'],mfa_claims={'amr':['google','otp'],'mfa_generation':1,'mfa_at':c.clock[0].timestamp()})
    client.headers['Authorization']='Bearer '+token
    proof=http_proof(c,client)
    calls=[]
    monkeypatch.setattr(stripe_service,'create_checkout_session',lambda **kwargs:calls.append(kwargs) or {'url':'https://provider.example.invalid'})
    paid=client.post('/api/billing/checkout',json={'plan':'standard'},headers={'X-MFA-Grant':proof})
    assert paid.status_code in {400,403} and calls==[]
    denied=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':proof})
    assert denied.status_code==422,denied.text
    revoked=client.post('/api/auth/mfa/revoke',json={'reauthentication_token':proof})
    assert revoked.status_code==422,revoked.text
    with c.sessions() as db:
        current=db.get(MfaCredential,c.ids['a'])
        assert current.generation==1 and current.enabled_at is not None
    allowed=client.post('/api/auth/mfa/enroll',json={'reauthentication_token':proof,
        'code':totp(secret,int(c.clock[0].timestamp())//30)})
    assert allowed.status_code==200,allowed.text


def test_old_google_reauthentication_contract_stays_strict(reauth_http):
    c,client=reauth_http
    result=client.post('/api/auth/mfa/reauth',json={'google_credential':c.provider.credential()})
    assert result.status_code==403
    assert result.json()['detail']['code']=='mfa_primary_reauthentication_required'
    assert c.mail==[] and not proofs(c)


@pytest.mark.asyncio
async def test_exact_lua_on_owned_redis_has_pending_gate_one_use_atomicity_and_attempt_ttl(tmp_path):
    import redis as redis_sync
    import redis.asyncio as redis_async
    from web.services import google_mfa_reauthentication as service
    executable=Path('E:/MetodoBaseWorkspace/tools/redis-windows-8.10.3-msys2-billing-5e119f7b/Redis-8.10.3-Windows-x64-msys2/redis-server.exe')
    if os.name!='nt' or not executable.is_file():
        pytest.skip('Owned Windows Redis executable is unavailable')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    process=subprocess.Popen([str(executable),'--bind','127.0.0.1','--port',str(port),
        '--protected-mode','yes','--daemonize','no','--save','','--appendonly','no','--dir',str(tmp_path),
        '--logfile',str(tmp_path/'redis.log'),'--pidfile',str(tmp_path/'redis.pid')],
        cwd=tmp_path,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    sync=redis_sync.Redis(host='127.0.0.1',port=port,socket_connect_timeout=.2,socket_timeout=.2)
    client=None;accepted=False;final_keys=None;owned=False;server_pid=None
    try:
        deadline=time.monotonic()+10
        while True:
            try:
                assert sync.ping();break
            except redis_sync.RedisError:
                if process.poll() is not None or time.monotonic()>=deadline:raise
                time.sleep(.03)
        assert process.poll() is None
        # A free-port lookup is not ownership. Before any mutation or shutdown,
        # require the server to report this launch's unique private pidfile.
        configured_pidfile=sync.config_get('pidfile')
        configured_pidfile=configured_pidfile.get(b'pidfile',configured_pidfile.get('pidfile'))
        if isinstance(configured_pidfile,bytes):configured_pidfile=configured_pidfile.decode('utf-8')
        assert str(configured_pidfile).replace('\\','/').lower()==str(tmp_path/'redis.pid').replace('\\','/').lower()
        owned=True
        server_pid=sync.info('server')['process_id']
        assert sync.config_get('appendonly')['appendonly']=='no'
        assert sync.config_get('save')['save']==''
        assert sync.dbsize()==0
        client=redis_async.Redis(host='127.0.0.1',port=port,decode_responses=True)
        prefix='qa-owned:'+uuid.uuid4().hex
        key,active,cooldown=(prefix+':'+suffix for suffix in ('code','active','cooldown'))
        item={'payload':'signed-binding','signature':'signature','code_digest':'correct','attempts':0,'delivery_ready':False}
        assert await client.eval(service.BEGIN_LUA,3,key,active,cooldown,json.dumps(item),300,60,'ref')==[1]
        args=['signed-binding','signature','correct','ref',5]
        assert await client.eval(service.CONSUME_LUA,2,key,active,*args)==[0]
        assert await client.eval(service.ACTIVATE_LUA,2,key,active,'signed-binding','signature','ref')==[1]
        results=await asyncio.gather(*[client.eval(service.CONSUME_LUA,2,key,active,*args) for _ in range(2)])
        assert sorted(results)==[[0],[1]] and not await client.exists(key,active)
        await client.delete(cooldown)
        assert await client.eval(service.BEGIN_LUA,3,key,active,cooldown,json.dumps(item),300,60,'ref2')==[1]
        assert await client.eval(service.ACTIVATE_LUA,2,key,active,'signed-binding','signature','ref2')==[1]
        before=await client.pttl(key)
        for attempt in range(5):
            assert await client.eval(service.CONSUME_LUA,2,key,active,'signed-binding','signature','wrong','ref2',5)==[0]
            if attempt<4:
                assert json.loads(await client.get(key))['attempts']==attempt+1
                current=await client.pttl(key);assert 0<current<=before;before=current
        assert not await client.exists(key)
        await client.delete(active,cooldown)
        final_keys=await client.dbsize()
        assert final_keys==0
        accepted=True
    finally:
        if client is not None:await client.aclose()
        if owned:
            try:sync.shutdown(nosave=True)
            except redis_sync.RedisError:pass
        sync.close()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=5)
        proof_dir=os.environ.get('METODOBASE_MFA_MAIL_EVIDENCE_DIR')
        if proof_dir:
            destination=Path(proof_dir)
            destination.mkdir(parents=True,exist_ok=True)
            receipt=destination/f'owned-redis-{process.pid}.json'
            receipt.write_text(json.dumps({'outcome':'PASS' if accepted else 'FAIL',
                'executable':str(executable),'host':'127.0.0.1','port':port,
                'pid':process.pid,'redis_process_id':server_pid,'returncode':process.returncode,
                'storage':str(tmp_path),'private_pidfile_verified':owned,
                'persistence':False,'final_keys':final_keys,
                'checks':['pending delivery rejects','one concurrent consumer succeeds',
                          'replay rejects','attempt TTL preserved','fifth wrong code deletes'],
                'closed':process.poll() is not None},indent=2)+'\n',encoding='utf-8')
