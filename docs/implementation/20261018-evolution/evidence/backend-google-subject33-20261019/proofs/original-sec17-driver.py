"""Account-association canaries using a modeled tokeninfo transport only.

Assertions are structurally consistent with a valid Google result, but no
Google credential, signature verification or live takeover is exercised.
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import httpx
import pytest
from sqlalchemy.orm import Session

from tests.test_personal_progress_http import progress_db, progress_http  # noqa:F401

CLIENT_ID='000000000000-independent-review.apps.googleusercontent.com'
CREDENTIAL='synthetic-tokeninfo-transport-credential'
SUBJECT_A='104000000000000000001'
SUBJECT_B='104000000000000000002'


def receipt(case,name,value):
    directory=Path(os.environ['SEC_GOOGLE_PRIVATE_RECEIPTS'])
    directory.mkdir(exist_ok=True)
    with (directory/(name+'-'+case['factory'].replace('.','_')+'.json')).open('x',encoding='utf8') as target:
        json.dump(value,target,indent=2);target.write('\n')


def provider(monkeypatch,email,*,bad_audience=False,status=200):
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(),'GOOGLE_CLIENT_ID',CLIENT_ID)
    now=int(time.time())
    assertion={'aud':'other-client' if bad_audience else CLIENT_ID,'iss':'https://accounts.google.com',
        'exp':str(now+3600),'iat':str(now),'auth_time':str(now),'email':email,'email_verified':'true',
        'sub':SUBJECT_A,'given_name':'Synthetic Google identity'}
    assert not email.endswith('@gmail.com') and 'hd' not in assertion
    assert assertion['iss']=='https://accounts.google.com' and int(assertion['exp'])>time.time()
    assert assertion['sub'] and assertion['email_verified']=='true'
    calls=[]
    def transport(request):
        assert request.method=='GET'
        assert request.url.scheme=='https' and request.url.host=='oauth2.googleapis.com' and request.url.path=='/tokeninfo'
        assert dict(request.url.params)=={'id_token':CREDENTIAL}
        calls.append({'fixed_https_tokeninfo':True,'aud_matches':assertion['aud']==CLIENT_ID,
            'sub_nonempty':bool(assertion['sub']),'sub_changed':assertion['sub']==SUBJECT_B,
            'issuer_google':assertion['iss']=='https://accounts.google.com','future_exp':int(assertion['exp'])>time.time(),
            'email_verified_true':assertion['email_verified']=='true','hd_absent':'hd' not in assertion,
            'email_class':'third_party_synthetic','provider_http':status})
        return httpx.Response(status,json=dict(assertion))
    actual=httpx.AsyncClient
    def client(*args,**kwargs):
        assert 'transport' not in kwargs
        return actual(*args,transport=httpx.MockTransport(transport),**kwargs)
    monkeypatch.setattr(httpx,'AsyncClient',client)
    return assertion,calls


def test_unbound_third_party_google_subject_requires_independent_link_before_login(progress_http,monkeypatch):
    from web.database.models import Usuario
    c=progress_http;client=c['client_http']
    assert client.app.dependency_overrides=={}
    assert 'Authorization' not in client.headers
    with Session(c['admin']) as db:original_password=db.get(Usuario,c['person']).password_hash
    assertion,calls=provider(monkeypatch,c['emails']['person'])
    outcomes=[]
    for subject in [SUBJECT_A,SUBJECT_B]:
        assertion['sub']=subject
        result=client.post('/api/auth/google',json={'credential':CREDENTIAL})
        body=result.json();issued='token' in body or 'refresh_token' in body
        same=False
        if 'token' in body:
            me=client.get('/api/auth/me',headers={'Authorization':'Bearer '+body['token']})
            same=me.status_code==200 and me.json().get('id')==c['person']
        outcomes.append({'google_http':result.status_code,'issued_general_tokens':issued,'resolved_existing_password_account':same})
    with Session(c['admin']) as db:password_preserved=db.get(Usuario,c['person']).password_hash==original_password
    data={'scope':'Modeled structurally valid tokeninfo result only; not Google live or signature bypass',
        'no_independent_password_or_factor_in_google_request':True,'no_authorization_header_in_google_request':True,
        'distinct_nonempty_subjects_same_third_party_email':True,'outcomes':outcomes,'provider_calls':calls,
        'persisted_password_unchanged':password_preserved}
    receipt(c,'unbound-login',data)
    assert len(calls)==2 and all(x['fixed_https_tokeninfo'] and x['future_exp'] and x['aud_matches'] for x in calls)
    assert password_preserved
    # Rejection or an explicit linking flow must not issue a normal session yet.
    assert not any(x['issued_general_tokens'] for x in outcomes)


def test_unbound_google_subject_cannot_supply_fresh_primary_for_factor_account(progress_http,monkeypatch):
    from web.settings import get_settings
    from web.services.mfa_crypto import totp
    c=progress_http;client=c['client_http'];password='Synthetic progress password 42!'
    monkeypatch.setattr(get_settings(),'MFA_ENCRYPTION_KEY',base64.urlsafe_b64encode(bytes(range(32))).decode())
    headers=c['headers']['person']
    primary=client.post('/api/auth/mfa/reauth',headers=headers,json={'password':password});assert primary.status_code==200
    pending=client.post('/api/auth/mfa/enroll',headers=headers,json={'reauthentication_token':primary.json()['reauthentication_token']});assert pending.status_code==200
    counter=int(datetime.now(timezone.utc).timestamp())//30
    done=client.post('/api/auth/mfa/enroll/confirm',headers=headers,json={'enrollment_id':pending.json()['enrollment_id'],
        'code':totp(base64.b32decode(pending.json()['secret']),counter)});assert done.status_code==200
    challenge=client.post('/api/auth/login',json={'email':c['emails']['person'],'password':password});assert challenge.status_code==202
    complete=client.post('/api/auth/mfa/login/verify',json={'challenge':challenge.json()['challenge'],
        'recovery_code':done.json()['recovery_codes'][0]});assert complete.status_code==200
    headers={'Authorization':'Bearer '+complete.json()['token']}
    _,calls=provider(monkeypatch,c['emails']['person'])
    result=client.post('/api/auth/mfa/reauth',headers=headers,json={'google_credential':CREDENTIAL})
    body=result.json();issued='reauthentication_token' in body
    factor_still_required=None
    if issued:
        missing=client.post('/api/auth/mfa/recovery-codes/regenerate',headers=headers,
            json={'reauthentication_token':body['reauthentication_token']})
        factor_still_required=missing.status_code==422
    data={'scope':'Real password/factor setup; Google transport modeled only, no factor bypass asserted',
        'google_reauth_http':result.status_code,'issued_primary_reauthentication_proof':issued,
        'existing_second_factor_still_required':factor_still_required,'provider_calls':calls,
        'new_google_subject_was_not_explicitly_linked':True}
    receipt(c,'unbound-reauth',data)
    assert len(calls)==1 and calls[0]['aud_matches'] and calls[0]['future_exp']
    if issued:assert factor_still_required is True
    assert issued is False


@pytest.mark.parametrize('invalid',['audience','provider_rejection'])
def test_provider_validation_controls_do_not_issue_a_local_session(progress_http,monkeypatch,invalid):
    c=progress_http
    _,calls=provider(monkeypatch,c['emails']['person'],bad_audience=invalid=='audience',
        status=400 if invalid=='provider_rejection' else 200)
    result=c['client_http'].post('/api/auth/google',json={'credential':CREDENTIAL})
    assert result.status_code==401
    assert all(key not in result.json() for key in ['token','refresh_token','challenge'])
    assert result.headers['Cache-Control']=='no-store' and result.headers['Referrer-Policy']=='no-referrer'
    assert len(calls)==1
    receipt(c,'control-'+invalid,{'google_http':result.status_code,'issued_general_tokens':False,'provider_calls':calls})

