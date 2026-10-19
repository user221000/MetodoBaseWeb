"""Local recovery is an independent proof, not a historical Google-sub backfill."""
from threading import Event
from urllib.parse import parse_qs,urlsplit
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.test_google33_http import google_db,google_http,start


def test_unknown_legacy_google_subject_requires_independent_recovery_then_explicit_link(google_http,monkeypatch):
    from web.auth import hash_password
    from web.database.models import Usuario,AuthExternalIdentity
    from web.services import email_service
    from web.settings import get_settings
    c=google_http;client=c['client']
    # Synthetic historical Google-only account: there is no persisted sub, and
    # its randomly generated local password is unknown to this test's caller.
    with Session(c['admin']) as db:
        db.get(Usuario,c['user']).password_hash=hash_password(secrets.token_urlsafe(48));db.commit()
    c['google']['email']=c['email']
    rejected=client.post('/api/auth/google',json={'credential':c['credential']()})
    assert rejected.status_code==409 and 'token' not in rejected.json()
    with Session(c['admin']) as db:
        assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c['user'])) is None
    accepted=Event();messages=[]
    def send(_recipient,_name,link):messages.append(link);accepted.set();return True
    monkeypatch.setattr(email_service,'send_password_reset',send)
    monkeypatch.setattr(email_service,'send_password_changed',lambda *_:False)
    monkeypatch.setattr(get_settings(),'RESEND_API_KEY','synthetic-offline-transport')
    monkeypatch.setattr(get_settings(),'BASE_URL','https://recovery.example.invalid')
    request=client.post('/api/auth/password-reset/request',json={'email':c['email']})
    assert request.status_code==202 and accepted.wait(5) and len(messages)==1
    token=parse_qs(urlsplit(messages[0]).fragment)['token'][0]
    password='Synthetic recovered local primary 33!'
    changed=client.post('/api/auth/password-reset/confirm',json={'token':token,'new_password':password,'confirm_password':password})
    assert changed.status_code==200 and 'token' not in changed.json()
    local=client.post('/api/auth/login',json={'email':c['email'],'password':password})
    assert local.status_code==200
    c['headers']={'Authorization':'Bearer '+local.json()['token']}
    issued=start(c,password=password);assert issued.status_code==200
    confirmed=client.post('/api/auth/google/link/confirm',headers=c['headers'],json={'intent':issued.json()['intent'],'confirm':True})
    assert confirmed.status_code==200 and 'token' not in confirmed.json()
    with Session(c['admin']) as db:
        identities=db.scalars(select(AuthExternalIdentity).where(AuthExternalIdentity.user_id==c['user'])).all()
        assert len(identities)==1 and identities[0].subject==c['google']['sub']
    # This is newly supplied proof; no claim about the unknown old sub follows.
    current=client.post('/api/auth/google',json={'credential':c['credential']()})
    assert current.status_code==200
    me=client.get('/api/auth/me',headers={'Authorization':'Bearer '+current.json()['token']})
    assert me.status_code==200 and me.json()['id']==c['user']
