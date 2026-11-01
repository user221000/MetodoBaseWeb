"""Persistent, current-contact proof reused safely by later billing operations.

Real SQLite/JWT/HTTP routes; Redis protocol and all mail transport are synthetic.
No provider, production account or mailbox is contacted.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from tests.test_billing_email_identity import account, request
from tests.test_billing_email_verification import case as mailbox_case


@pytest.fixture(scope='module')
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture
def billing_contact(account, mailbox_case):
    from web.routes.billing_email import router
    app=FastAPI()
    app.include_router(router,prefix='/api')
    with TestClient(app,raise_server_exceptions=False) as client:
        yield SimpleNamespace(account=account,mailbox=mailbox_case,client=client)


def issue(c,kind='gym'):
    return c.client.post('/api/billing/email-verification/request',
        headers={'Authorization':'Bearer '+c.account.tokens[kind]},
        json={'action':'gym_stripe_checkout','plan':'standard'})


def verify(c,challenge,code,kind='gym'):
    return c.client.post('/api/billing/email-verification/verify',
        headers={'Authorization':'Bearer '+c.account.tokens[kind]},
        json={'action':'gym_stripe_checkout','plan':'standard','challenge':challenge,'code':code})


def mark_verified(c,kind='gym',*,version=None,when=None):
    a=c.account
    with a.sessions() as db:
        user=db.get(a.Usuario,a.ids[kind])
        user.email_verified_at=when or datetime.now(timezone.utc)
        user.email_verified_contact_version=user.notification_contact_version if version is None else version
        db.commit()


def current_contact(a,kind='gym'):
    from web.services.account_security import verified
    with a.sessions() as db:
        user=db.get(a.Usuario,a.ids[kind])
        return verified(user,datetime.now(timezone.utc)),user.email_verified_contact_version,user.notification_contact_version


def test_verified_contact_request_skips_all_email_and_redis_work(billing_contact,monkeypatch):
    c=billing_contact
    mark_verified(c)
    monkeypatch.setattr(c.mailbox.settings,'RESEND_API_KEY','')
    monkeypatch.setattr(c.mailbox.settings,'REDIS_URL','')
    response=issue(c)
    assert response.status_code==200
    assert response.json()=={'email_verification_required':False,'email_verified':True}
    assert 'no-store' in response.headers['Cache-Control']
    assert c.mailbox.mail==[] and c.mailbox.cache.rows=={} and c.mailbox.limits==[]


def test_billing_codes_stay_with_each_own_account_and_persist_separately(billing_contact):
    c=billing_contact
    first=issue(c)
    assert first.status_code==200
    first_code=c.mailbox.mail[-1][1]
    second=issue(c,'other')
    assert second.status_code==200
    second_code=c.mailbox.mail[-1][1]
    assert [message[0] for message in c.mailbox.mail]==['gym@example.invalid','other@example.invalid']
    assert first.json()['challenge']!=second.json()['challenge']
    completed=verify(c,second.json()['challenge'],second_code,'other')
    assert completed.status_code==200 and 'verification_token' in completed.json()
    assert current_contact(c.account,'other')==(True,6,6)
    assert current_contact(c.account,'gym')==(False,None,6)
    assert verify(c,first.json()['challenge'],first_code).status_code==200
    assert current_contact(c.account,'gym')==(True,6,6)
    count=len(c.mailbox.mail)
    assert issue(c).json()=={'email_verification_required':False,'email_verified':True}
    assert len(c.mailbox.mail)==count


@pytest.mark.parametrize('condition',['missing','old_version','future'])
def test_unverified_old_version_or_future_proof_still_requires_code(billing_contact,condition):
    c=billing_contact
    if condition=='old_version': mark_verified(c,version=5)
    elif condition=='future': mark_verified(c,when=datetime.now(timezone.utc)+timedelta(days=1))
    response=issue(c)
    assert response.status_code==200 and response.json()['email_verification_required'] is True
    assert c.mailbox.mail[-1][0]=='gym@example.invalid'


@pytest.mark.asyncio
@pytest.mark.parametrize('grant',[False,True])
async def test_unverified_contact_cannot_use_client_claim_or_old_grant(billing_contact,monkeypatch,grant):
    from web.services import billing_email_verification
    c=billing_contact;a=c.account
    async def unexpected(*args,**kwargs):
        raise AssertionError('Unverified current contact must not consume a payment grant')
    monkeypatch.setattr(billing_email_verification,'consume',unexpected)
    expected={**a.identities['gym'],'email_verified':True}
    extra=[(b'x-billing-email-grant',b'a'*43)] if grant else []
    with a.sessions() as db,pytest.raises(HTTPException) as error:
        await a.service.require_email(db,expected,request(a.tokens['gym'],extra=extra),
            'gym_stripe_checkout','standard',{'plan':'standard'})
    assert error.value.status_code==403 and error.value.detail['code']=='billing_email_required'


@pytest.mark.asyncio
async def test_verified_contact_without_grant_keeps_lock_and_no_mail_transport(billing_contact,monkeypatch):
    from web.services import billing_email_verification
    c=billing_contact;a=c.account
    mark_verified(c)
    async def unexpected(*args,**kwargs):
        raise AssertionError('No new mailbox transport or grant consumption for verified contact')
    monkeypatch.setattr(billing_email_verification,'consume',unexpected)
    with a.sessions() as db:
        actor=await a.service.require_email(db,a.identities['gym'],request(a.tokens['gym']),
            'gym_stripe_checkout','standard',{'plan':'standard'})
        assert db.in_transaction()
        assert actor['id']==a.ids['gym']
        db.rollback()
    assert c.mailbox.mail==[]


@pytest.mark.asyncio
async def test_contact_change_after_verified_response_is_rechecked_at_payment(billing_contact):
    c=billing_contact;a=c.account
    mark_verified(c)
    assert issue(c).json()['email_verification_required'] is False
    with a.sessions() as db:
        user=db.get(a.Usuario,a.ids['gym'])
        user.email='changed@example.invalid'
        user.notification_contact_version+=1
        db.commit()
    with a.sessions() as db,pytest.raises(HTTPException) as error:
        await a.service.require_email(db,a.identities['gym'],request(a.tokens['gym']),
            'gym_stripe_checkout','standard',{'plan':'standard'})
    assert error.value.status_code==403
    retry=issue(c)
    assert retry.status_code==200 and retry.json()['email_verification_required'] is True
    assert c.mailbox.mail[-1][0]=='changed@example.invalid'


@pytest.mark.parametrize('change',['contact','session','role','disabled'])
def test_changed_authority_after_code_consumption_cannot_mark_contact(billing_contact,monkeypatch,change):
    c=billing_contact;a=c.account
    stage=issue(c).json();code=c.mailbox.mail[-1][1]
    real_verify=c.mailbox.service.verify
    async def changed_after_otp(*args,**kwargs):
        value=await real_verify(*args,**kwargs)
        with a.sessions() as db:
            user=db.get(a.Usuario,a.ids['gym'])
            if change=='contact': user.email='changed@example.invalid';user.notification_contact_version+=1
            elif change=='session': user.session_version+=1
            elif change=='role': user.role=a.UserRole.VIEWER
            else: user.activo=False
            db.commit()
        return value
    monkeypatch.setattr(c.mailbox.service,'verify',changed_after_otp)
    completed=verify(c,stage['challenge'],code)
    assert completed.status_code in (401,403,409)
    assert 'verification_token' not in completed.text
    with a.sessions() as db:
        assert db.get(a.Usuario,a.ids['gym']).email_verified_at is None


@pytest.mark.parametrize('after_commit',[False,True])
def test_commit_uncertainty_never_returns_an_unconfirmed_billing_token(billing_contact,monkeypatch,after_commit):
    c=billing_contact;a=c.account
    stage=issue(c).json();code=c.mailbox.mail[-1][1]
    commit=a.sessions.class_.commit
    def uncertain(db):
        if after_commit: commit(db)
        raise ConnectionError('synthetic-private-commit-information')
    monkeypatch.setattr(a.sessions.class_,'commit',uncertain)
    completed=verify(c,stage['challenge'],code)
    assert completed.status_code==503
    assert completed.json()['detail']['code']=='billing_email_unconfirmed'
    assert 'verification_token' not in completed.text and 'synthetic-private' not in completed.text
    assert current_contact(a)[0] is after_commit


def test_contact_confirmation_links_go_only_to_each_own_recipient(account,monkeypatch):
    from web.services import account_security
    a=account;mail=[]
    monkeypatch.setattr(account_security,'configuration',lambda:'https://example.invalid')
    for kind in ('gym','other'):
        account_security.issue_email(a.identities[kind],factory=a.sessions,
            sender=lambda email,link: mail.append((email,link)) or True)
    assert [value[0] for value in mail]==['gym@example.invalid','other@example.invalid']
    first=parse_qs(urlsplit(mail[0][1]).fragment)['token'][0]
    second=parse_qs(urlsplit(mail[1][1]).fragment)['token'][0]
    assert first!=second
    assert account_security.confirm_email(first,factory=a.sessions)['email_verified'] is True
    assert current_contact(a,'gym')[0] is True and current_contact(a,'other')[0] is False
    assert account_security.confirm_email(second,factory=a.sessions)['email_verified'] is True
    assert current_contact(a,'other')[0] is True
