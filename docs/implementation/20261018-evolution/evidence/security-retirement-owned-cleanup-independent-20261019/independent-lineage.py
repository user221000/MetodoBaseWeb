"""Independent supported invite lineage; same expected retirement contract before/after."""
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.test_personal_progress_http import progress_db, progress_http  # noqa:F401
from tests.test_personal_progress_http import accepted, grant, shared_path


@pytest.mark.parametrize('progress_http',['web.main_web'],indirect=True)
def test_supported_invited_member_can_retire_without_general_login(progress_http,monkeypatch):
    from web.database.models import Usuario,Cliente,Subscription,ProgressConsent
    from web.services.mfa_crypto import totp
    from web.services import mfa_service
    from web.settings import get_settings
    c=progress_http;client=c['client_http'];password='Synthetic progress password 42!'
    clock=datetime.now(timezone.utc)
    actual=mfa_service.instant
    monkeypatch.setattr(mfa_service,'instant',lambda now=None:actual(clock if now is None else now))
    monkeypatch.setattr(get_settings(),'MFA_ENCRYPTION_KEY',base64.urlsafe_b64encode(bytes(range(32))).decode())
    owner_headers=c['headers']['gym']
    primary=client.post('/api/auth/mfa/reauth',headers=owner_headers,json={'password':password});assert primary.status_code==200
    pending=client.post('/api/auth/mfa/enroll',headers=owner_headers,json={'reauthentication_token':primary.json()['reauthentication_token']});assert pending.status_code==200
    done=client.post('/api/auth/mfa/enroll/confirm',headers=owner_headers,json={'enrollment_id':pending.json()['enrollment_id'],
        'code':totp(base64.b32decode(pending.json()['secret']),int(clock.timestamp())//30)});assert done.status_code==200
    challenge=client.post('/api/auth/login',json={'email':c['emails']['gym'],'password':password});assert challenge.status_code==202
    factor=client.post('/api/auth/mfa/login/verify',json={'challenge':challenge.json()['challenge'],
        'recovery_code':done.json()['recovery_codes'][0]});assert factor.status_code==200
    owner_headers={'Authorization':'Bearer '+factor.json()['token']}
    member_email=uuid.uuid4().hex+'@example.invalid'
    invite_body={'email':member_email,'nombre':'Synthetic independent member','apellido':'','role':'viewer'}
    action=client.post('/api/auth/mfa/step-up',headers=owner_headers,json={'method':'POST','path':'/api/gym/team/invite','body':invite_body});assert action.status_code==200
    invited=client.post('/api/gym/team/invite',headers={**owner_headers,'X-MFA-Grant':action.json()['grant']},json=invite_body);assert invited.status_code==200
    consumed=client.post('/api/auth/accept-invite',json={'token':invited.json()['invitation_token'],'password':password});assert consumed.status_code==200
    member_login=client.post('/api/auth/login',json={'email':member_email,'password':password});assert member_login.status_code==200
    member_headers={'Authorization':'Bearer '+member_login.json()['token']}
    member_me=client.get('/api/auth/me',headers=member_headers);assert member_me.status_code==200
    member_id=member_me.json()['id']
    assert member_me.json()['role']=='viewer' and member_me.json()['team_gym_id']==c['gym']

    # Independent linked professional gym is created through actual registration.
    # Its commercial eligibility and Cliente are explicit synthetic DB fixtures.
    linked_email=uuid.uuid4().hex+'@example.invalid'
    registered=client.post('/api/auth/registro',json={'email':linked_email,'nombre':'Synthetic linked gym','tipo':'gym','password':password});assert registered.status_code==200
    linked_login=client.post('/api/auth/login',json={'email':linked_email,'password':password});assert linked_login.status_code==200
    linked_headers={'Authorization':'Bearer '+linked_login.json()['token']}
    linked_me=client.get('/api/auth/me',headers=linked_headers);assert linked_me.status_code==200
    linked_id=linked_me.json()['id'];client_id=str(uuid.uuid4())
    with Session(c['admin']) as db:
        db.add(Cliente(id_cliente=client_id,gym_id=linked_id,nombre='Synthetic member link',activo=True))
        db.add(Subscription(gym_id=linked_id,plan='clinica',status='active',provider='stripe',max_clientes=0,
            current_period_start=clock-timedelta(days=1),current_period_end=clock+timedelta(days=1)))
        db.commit()
    case={**c,'person':member_id,'gym':linked_id,'client':client_id,
        'headers':{**c['headers'],'person':member_headers,'gym':linked_headers},
        'emails':{**c['emails'],'person':member_email,'gym':linked_email}}
    c['ready'].clear();link=accepted(case)
    result,_=grant(case,link,source_profile_id=None,categories={'weight':False,'body_fat':False,'lean_mass':False,'completion':True})
    assert result.status_code==200
    consent=result.json()['consent'];own_path='/api/usuario/vinculos/'+link+'/progreso/consentimiento'
    prior=client.get(own_path,headers=member_headers);assert prior.status_code==200 and prior.json()['capabilities']['withdraw'] is True
    assert client.get(shared_path(case,link,consent),headers=linked_headers).status_code==200
    # Explicit administrative shutdown stimulus; no public shutdown endpoint is claimed.
    with Session(c['admin']) as db:db.get(Usuario,c['gym']).activo=False;db.commit()
    assert client.get('/api/auth/me',headers=member_headers).status_code==401
    primary={'method':'password','email':member_email,'password':password}
    metadata=client.post('/api/auth/progress-retirement/metadata',json={'primary':primary})
    withdrawal=client.post('/api/auth/progress-retirement/withdraw',json={'primary':primary,'link_id':link,'expected_consent_id':consent['id'],'expected_version':1})
    receipt={'lineage':'real team invite, public accept, real password login, explicit grant','factory':c['factory'],
        'parent_off':'administrative SQL stimulus, actor remains active','general_login_after_parent_off':401,
        'metadata_http':metadata.status_code,'withdraw_http':withdrawal.status_code,
        'no_access_or_refresh_keys':all(k not in metadata.json() and k not in withdrawal.json() for k in ['token','access_token','refresh_token','challenge'])}
    target=Path(os.environ['SEC_RETIREMENT_LINEAGE_RECEIPT'])
    with target.open('x',encoding='utf8') as output:json.dump(receipt,output,indent=2);output.write('\n')
    assert metadata.status_code==200 and withdrawal.status_code==200
    assert metadata.json()['items'][0]['link_id']==link
    assert withdrawal.json()['consent']['event']=='withdraw'
    assert receipt['no_access_or_refresh_keys']
    with Session(c['admin']) as db:
        assert [row.event for row in db.scalars(select(ProgressConsent).where(ProgressConsent.link_id==link).order_by(ProgressConsent.version))]==['grant','withdraw']
