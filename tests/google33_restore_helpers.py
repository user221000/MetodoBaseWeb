"""Real HTTP33 bindings in a full populated restore, with no old seed changes."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import importlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session,sessionmaker

from tests.google33_signed_provider import SignedProvider
from tests.test_google33_http import CLIENT_ID,PASSWORD
from web.database.models import AuthExternalIdentity,MfaCredential,GoogleLinkIntent,Usuario,RefreshToken


@contextmanager
def client_for(application,monkeypatch,claims):
    from fastapi.testclient import TestClient
    from web.database import engine as database
    from web.settings import get_settings
    with monkeypatch.context() as scope:
        scope.setattr(database,'_engine',application)
        scope.setattr(database,'_SessionLocal',sessionmaker(bind=application,expire_on_commit=True,autoflush=False))
        scope.setattr(get_settings(),'GOOGLE_CLIENT_ID',CLIENT_ID)
        provider=SignedProvider(scope,claims)
        with TestClient(importlib.import_module('api.app').create_app(),raise_server_exceptions=False,
                client=('192.8.33.1',51001)) as client:
            yield client,provider


def populate_google33(source_url,admin,monkeypatch):
    from tests.integration_provider_subjects import application_engine
    now=datetime.now(timezone.utc)
    claims={'aud':CLIENT_ID,'iss':'https://accounts.google.com','sub':str(uuid.uuid4().int),
        'email':uuid.uuid4().hex+'@thirdparty.example.invalid','email_verified':True,
        'iat':int(now.timestamp()),'exp':int((now+timedelta(hours=1)).timestamp()),'auth_time':int(now.timestamp())}
    expected={'email':uuid.uuid4().hex+'@example.invalid','subjects':{},'private_material':[],'claims':claims}
    app=application_engine(source_url,admin)
    try:
        with client_for(app,monkeypatch,claims) as (client,provider):
            made=client.post('/api/auth/registro',json={'email':expected['email'],'password':PASSWORD,'nombre':'Synthetic33 restore','tipo':'usuario'})
            assert made.status_code==200
            def login():
                response=client.post('/api/auth/login',json={'email':expected['email'],'password':PASSWORD})
                assert response.status_code==200
                expected['private_material'].extend([response.json()['token'],response.json()['refresh_token']])
                return {'Authorization':'Bearer '+response.json()['token']}
            # Registration itself issues a real pair. Use that initial access;
            # later password logins prove the updated local primary after SV++.
            expected['private_material'].extend([made.json()['token'],made.json()['refresh_token']])
            headers={'Authorization':'Bearer '+made.json()['token']}
            me=client.get('/api/auth/me',headers=headers);assert me.status_code==200
            expected['actor']=me.json()['id']
            for label in ('active','revoked'):
                claims['sub']=str(uuid.uuid4().int);expected['subjects'][label]=claims['sub']
                credential=provider.credential();expected['private_material'].append(credential)
                issued=client.post('/api/auth/google/link/start',headers=headers,json={'password':PASSWORD,'google_credential':credential})
                assert issued.status_code==200
                expected['private_material'].append(issued.json()['intent'])
                result=client.post('/api/auth/google/link/confirm',headers=headers,json={'intent':issued.json()['intent'],'confirm':True})
                assert result.status_code==200 and result.json()['reauthenticate'] is True
                headers=login()
            with Session(admin) as db:
                revoked=db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.subject==expected['subjects']['revoked']))
                binding_id,version=revoked.id,revoked.version
            withdrawn=client.post('/api/auth/google/link/unlink',headers=headers,json={'identity_id':binding_id,'expected_version':version,'password':PASSWORD})
            assert withdrawn.status_code==200
            headers=login();expected['access']=headers['Authorization'][7:]
            claims['sub']=str(uuid.uuid4().int);expected['subjects']['pending']=claims['sub']
            pending=client.post('/api/auth/google/link/start',headers=headers,json={'password':PASSWORD,'google_credential':provider.credential()})
            assert pending.status_code==200
            expected['pending']=pending.json()['intent'];expected['private_material'].append(expected['pending'])
            claims['sub']=str(uuid.uuid4().int);expected['subjects']['new_account']=claims['sub']
            claims['email']=uuid.uuid4().hex+'@thirdparty.example.invalid'
            new=client.post('/api/auth/google',json={'credential':provider.credential()})
            assert new.status_code==200
            expected['private_material'].extend([new.json()['token'],new.json()['refresh_token']])
            second=client.get('/api/auth/me',headers={'Authorization':'Bearer '+new.json()['token']})
            assert second.status_code==200 and second.json()['id']!=expected['actor']
            expected['other']=second.json()['id']
        with Session(admin) as db:
            assert db.get(Usuario,expected['actor']).session_version==3
            expected['bindings']={row.subject:row.id for row in db.scalars(select(AuthExternalIdentity))}
            assert set(expected['bindings'])=={expected['subjects'][key] for key in ('active','revoked','new_account')}
            row=db.get(MfaCredential,expected['actor'])
            assert row is not None and row.enabled_at is None and row.generation==0
            expected['refresh_rows']=[dict(row) for row in db.execute(select(RefreshToken.__table__).where(
                RefreshToken.user_id.in_([expected['actor'],expected['other']])).order_by(RefreshToken.jti)).mappings()]
            assert len(expected['refresh_rows'])==5
            assert sum(row['revoked'] for row in expected['refresh_rows'])==3
            assert sum(row['user_id']==expected['actor'] for row in expected['refresh_rows'])==4
    finally:app.dispose()
    return expected


def reject_plain_google33(rows,expected,mfa_expected,original_mfa_rows):
    """Check the complete four-row set before applying the old three-row oracle."""
    from tests.mfa31_restore_helpers import reject_plain_mfa31
    all_rows=rows['mfa_credentials'];ids={row['user_id'] for row in all_rows}
    original_ids=set(mfa_expected['actors'])
    assert len(all_rows)==4 and ids==original_ids|{expected['actor']}
    assert [row for row in all_rows if row['user_id'] in original_ids]==original_mfa_rows
    assert [row for row in all_rows if row['user_id']==expected['actor']]==[expected['inactive_credential']]
    # This is the only narrowed input to the unchanged31 three-actor checker.
    reject_plain_mfa31({**rows,'mfa_credentials':[row for row in all_rows if row['user_id'] in original_ids]},mfa_expected)
    serialized=json.dumps(rows,default=str)
    assert all(value not in serialized for value in expected['private_material'])
    assert len(rows['auth_external_identities'])==3 and len(rows['google_link_intents'])==3
    assert sum(row['revoked_at'] is not None for row in rows['auth_external_identities'])==1
    assert sum(row['consumed_at'] is not None for row in rows['google_link_intents'])==2


def observe_source_refresh(admin,expected,*,after_existing_cleanup):
    with Session(admin) as db:
        actual=[dict(row) for row in db.execute(select(RefreshToken.__table__).where(
            RefreshToken.user_id.in_([expected['actor'],expected['other']])).order_by(RefreshToken.jti)).mappings()]
    before=expected['refresh_rows']
    required=[row for row in before if not row['revoked']] if after_existing_cleanup else before
    assert actual==required and len(actual)==(2 if after_existing_cleanup else 5)
    return {'rows':len(actual),'revoked':sum(row['revoked'] for row in actual),'exact_prior_jti_and_fields':True}


@contextmanager
def witness_existing_cleanup(admin,expected,monkeypatch,measurements):
    """Observe the unchanged cleanup, including every refresh row, not a slice."""
    from web import auth
    original=auth._cleanup_expired_refresh_tokens
    def rows():
        with Session(admin) as db:
            return [dict(row) for row in db.execute(select(RefreshToken.__table__).order_by(RefreshToken.jti)).mappings()]
    def measured():
        before=rows()
        result=original()
        after=rows()
        assert before==expected['refresh_rows'] and len(before)==5
        removed=[row for row in before if row['revoked']]
        assert len(removed)==3 and all(row['user_id']==expected['actor'] for row in removed)
        assert after==[row for row in before if not row['revoked']] and len(after)==2
        measurements.append({'all_rows_before':5,'all_rows_after':2,'exact_removed_google_revoked':3,
            'no_other_row_removed_or_changed':True,'original_cleanup_returned':result})
        return result
    with monkeypatch.context() as scope:
        scope.setattr(auth,'_cleanup_expired_refresh_tokens',measured)
        yield
    assert len(measurements)==1


def verify_restored_google33(admin,restricted,expected,monkeypatch):
    claims=dict(expected['claims']);claims['sub']=expected['subjects']['active']
    # The fixed signed provider represents changed contact data for the same sub.
    claims['email']='changed-restore-contact@thirdparty.example.invalid'
    with client_for(restricted,monkeypatch,claims) as (client,provider):
        active=client.post('/api/auth/google',json={'credential':provider.credential()})
        assert active.status_code==200 and active.json()['email']==expected['email']
        headers={'Authorization':'Bearer '+active.json()['token']}
        me=client.get('/api/auth/me',headers=headers);assert me.status_code==200 and me.json()['id']==expected['actor']
        status=client.get('/api/auth/google/link/status',headers=headers)
        assert status.status_code==200
        assert {row['id'] for row in status.json()['items']}=={expected['bindings'][expected['subjects'][name]] for name in ('active','revoked')}
        claims['sub']=expected['subjects']['new_account']
        other=client.post('/api/auth/google',json={'credential':provider.credential()})
        assert other.status_code==200
        other_me=client.get('/api/auth/me',headers={'Authorization':'Bearer '+other.json()['token']})
        assert other_me.status_code==200 and other_me.json()['id']==expected['other']
        claims['sub']=expected['subjects']['revoked']
        assert client.post('/api/auth/google',json={'credential':provider.credential()}).status_code==409
        claims['sub']=str(uuid.uuid4().int);claims['email']=expected['email']
        assert client.post('/api/auth/google',json={'credential':provider.credential()}).status_code==409
        old={'Authorization':'Bearer '+expected['access']}
        confirmed=client.post('/api/auth/google/link/confirm',headers=old,json={'intent':expected['pending'],'confirm':True})
        assert confirmed.status_code==200 and confirmed.json()['reauthenticate'] is True
        assert 'token' not in confirmed.json() and client.get('/api/auth/me',headers=old).status_code==401
        fresh=client.post('/api/auth/login',json={'email':expected['email'],'password':PASSWORD});assert fresh.status_code==200
        fresh_headers={'Authorization':'Bearer '+fresh.json()['token']}
        replay=client.post('/api/auth/google/link/confirm',headers=fresh_headers,json={'intent':expected['pending'],'confirm':True})
        assert replay.status_code==409
        forbidden=client.post('/api/auth/google/link/unlink',headers=fresh_headers,json={'identity_id':expected['bindings'][expected['subjects']['new_account']],'expected_version':1,'password':PASSWORD})
        assert forbidden.status_code==409
    with Session(admin) as db:
        assert db.get(Usuario,expected['actor']).session_version==4
        assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==expected['actor'],GoogleLinkIntent.subject==expected['subjects']['pending'])) is not None
        assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.subject==expected['subjects']['pending']))==expected['actor']
        assert db.scalar(select(AuthExternalIdentity.revoked_at).where(AuthExternalIdentity.subject==expected['subjects']['revoked'])) is not None
    assert restricted.pool.checkedout()==0
    return {'actors':2,'active_bindings_before':2,'revoked_bindings_before':1,'pending_intent_restored_and_consumed_once':True,
        'stable_subject_ignores_changed_email':True,'recipient_status_filters_actor':True,'revoked_subject_denied':True,
        'exact_source_access_required_and_revoked_after_confirmation':True,'no_plaintext_in_rows':True}
