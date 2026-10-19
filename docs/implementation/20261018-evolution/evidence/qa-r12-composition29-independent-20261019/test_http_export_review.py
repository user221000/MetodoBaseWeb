"""Seven actual HTTP controls x both factories x SQLite/restricted PG.

Only the mail transport is a local private sink. Every R12/auth/privacy route,
commit, persisted row and object read is the real composed implementation.
"""
import hashlib
from html import unescape
import json
import os
from pathlib import Path
import re
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session,sessionmaker

from tests import integration_client_link_services as shared
from tests import integration_client_link_http as maintained
from web.database.models import Cliente,ClientAccountLink,ClientLinkInvitation,ClientPlanPublication,Usuario

link_db=shared.link_db
case=shared.case
http=maintained.http
DATASETS={'profiles','plans','measurements','purchases','generation_requests','personal_diary','member_links'}
RECORD={'id','status','version','gym_name','client_display_name','accepted_at','publication'}

@pytest.fixture
def actual_http(http,monkeypatch):
    from web.database.tenant_context import current_tenant
    from web.services import email_service
    # A recipient may have two invitations in two gyms. Witness exact pending
    # digest, rather than assuming the first row for an email is still pending.
    def private_sink(recipient,subject,html,**kwargs):
        assert current_tenant.get()==''
        match=re.search(r'/auth/accept-client-link#token=([A-Za-z0-9_-]{43})',unescape(html))
        if match:
            token=match.group(1);digest=shared.hashlib.sha256(('client-account-invite-v1:'+token).encode()).hexdigest() if hasattr(shared,'hashlib') else hashlib.sha256(('client-account-invite-v1:'+token).encode()).hexdigest()
            with Session(http['admin']) as db:
                assert db.scalar(select(ClientLinkInvitation.status).where(ClientLinkInvitation.token_hash==digest,ClientLinkInvitation.recipient_email==recipient))=='pending'
            private=Path(os.environ['QA_PHASE'])/'private-mail-proofs.json'
            values=json.loads(private.read_bytes()) if private.exists() else []
            values.append(token);private.write_text(json.dumps(values)+'\n',encoding='utf8')
            http['mail'].append((recipient,subject,html));http['received'].set()
        return True
    monkeypatch.setattr(email_service,'_send',private_sink)
    return http

def private_headers(response):
    assert response.headers['cache-control']=='no-store'
    assert response.headers['referrer-policy']=='no-referrer'
    assert response.headers['x-content-type-options']=='nosniff'

def link(case,*,gym='gym',client='client',recipient='person',publish=True,marker='own-review'):
    case['received'].clear()
    response=case['client_http'].post('/api/clientes/'+case[client]+'/vinculacion/invitaciones',headers=case['headers'][gym],
       json={'recipient_email':case[recipient]+'@example.invalid' if recipient!='person' else case['email'],'request_key':str(uuid.uuid4())})
    assert response.status_code==202,response.text
    assert case['received'].wait(5)
    token=re.search(r'#token=([A-Za-z0-9_-]{43})',unescape(case['mail'][-1][2])).group(1)
    issued=response.json();assert token not in response.text
    accepted=case['client_http'].post('/api/usuario/vinculaciones/aceptar',headers=case['headers'][recipient],
       json={'token':token,'expected_version':issued['version'],'confirm':True})
    assert accepted.status_code==200,accepted.text
    values={'id':issued['link_id'],'version':accepted.json()['version'],'publication':None,'descriptor':None,'content':None}
    if publish:
        cloned=dict(case,gym=case[gym],client=case[client])
        plan,descriptor,content=shared.source(cloned,marker=marker)
        published=case['client_http'].post('/api/clientes/'+case[client]+'/vinculacion/'+values['id']+'/publicaciones',headers=case['headers'][gym],
           json={'plan_id':plan,'expected_link_version':values['version'],'expected_publication_version':0,'expected_publication_id':None})
        assert published.status_code==200,published.text
        values.update(publication=published.json()['publication_id'],descriptor=descriptor,content=content)
    return values

def export(case,actor='person',**params):
    response=case['client_http'].get('/api/usuario/privacidad/exportar',headers=case['headers'][actor],params=params)
    assert response.status_code==200,response.text
    private_headers(response)
    return response

def identity(case,actor='person'):
    with Session(case['admin']) as db:
        user=db.get(Usuario,case[actor])
        return (user.tipo,user.role,user.team_gym_id,user.session_version,user.email,user.password_hash,
                tuple(db.scalars(select(Cliente.id_cliente).where(Cliente.gym_id==case[actor]).order_by(Cliente.id_cliente))))

def test_export_contains_seven_collections_and_only_exact_member_metadata(actual_http):
    case=actual_http;marker='NEVER_EXPORT_SOURCE_MENU_'+uuid.uuid4().hex
    result=link(case,marker=marker);response=export(case,limit=1);data=response.json()
    assert DATASETS <= set(data)
    assert data['scope']['coverage']=='account_persisted_personal_space_and_active_member_link_metadata'
    assert data['scope']['member_links']=='active_recipient_metadata_only'
    for name in DATASETS:assert set(data[name])=={'records','next_after'}
    row=data['member_links']['records'][0]
    assert set(row)==RECORD and row['id']==result['id'] and row['status']=='active'
    assert set(row['publication'])=={'id','version','published_at'} and row['publication']['id']==result['publication']
    assert marker not in response.text and result['descriptor'].key not in response.text
    assert all(not data[name]['records'] for name in DATASETS-{'member_links'})

def test_owner_own_and_external_contexts_export_without_professional_portfolio_or_profile_adoption(actual_http):
    case=actual_http;before=identity(case,'gym')
    own=link(case,recipient='gym',marker='OWNER_OWN_PRIVATE_MENU')
    external=link(case,gym='othergym',client='otherclient',recipient='gym',marker='OWNER_EXTERNAL_PRIVATE_MENU')
    response=export(case,'gym');data=response.json()
    assert data['scope']['personal_space'] is False
    assert {row['id'] for row in data['member_links']['records']}=={own['id'],external['id']}
    assert all(not data[name]['records'] for name in DATASETS-{'member_links'})
    assert 'PRIVATE_MENU' not in response.text and identity(case,'gym')==before

def test_http_self_revoke_inactive_source_preserves_personal_profile_and_has_no_reactivation(actual_http):
    case=actual_http;personal=str(uuid.uuid4())
    with Session(case['admin']) as db:
        db.add(Cliente(id_cliente=personal,gym_id=case['person'],nombre='Synthetic own personal',notas='OWN_PRIVATE_PROFILE'));db.commit()
    before=identity(case);result=link(case)
    with Session(case['admin']) as db:
        db.get(Usuario,case['gym']).activo=False;db.commit()
    path='/api/usuario/vinculos/'+result['id']
    other=case['client_http'].request('DELETE',path,headers=case['headers']['other'],json={'expected_version':result['version']})
    assert other.status_code==404;private_headers(other)
    revoked=case['client_http'].request('DELETE',path,headers=case['headers']['person'],json={'expected_version':result['version']})
    assert revoked.status_code==200 and revoked.json()['status']=='revoked';private_headers(revoked)
    with Session(case['admin']) as db:
        db.get(Usuario,case['gym']).activo=True;db.commit()
    assert export(case).json()['member_links']['records']==[]
    assert case['client_http'].get(path+'/plan',headers=case['headers']['person']).status_code==404
    assert case['client_http'].get('/api/auth/me',headers=case['headers']['person']).status_code==200
    assert identity(case)==before

def test_physical_PDF_corruption_is_not_served_or_replaced_with_another_object(actual_http):
    from web.storage.runtime import get_object_store
    case=actual_http;result=link(case,marker='PHYSICAL_PRIVATE_PDF')
    path='/api/usuario/vinculos/'+result['id']+'/publicaciones/'+result['publication']+'/pdf'
    assert case['client_http'].get(path,headers=case['headers']['person']).content==result['content']
    store=get_object_store();target=store._path(result['descriptor'],case['gym']);original=target.read_bytes()
    try:
        target.write_bytes(b'%PDF-1.7\nTAMPERED_PRIVATE_BYTES')
        response=case['client_http'].get(path,headers=case['headers']['person'])
        assert response.status_code==404 and b'TAMPERED_PRIVATE_BYTES' not in response.content
        assert result['descriptor'].key not in response.text;private_headers(response)
    finally:target.write_bytes(original)

def test_session_version_change_rejects_stale_readers_PDF_and_export(actual_http):
    case=actual_http;result=link(case)
    with Session(case['admin']) as db:
        db.get(Usuario,case['person']).session_version=1;db.commit()
    root='/api/usuario/vinculos/'+result['id']
    for path in ['/api/usuario/vinculos',root+'/plan',root+'/publicaciones/'+result['publication']+'/pdf']:
        response=case['client_http'].get(path,headers=case['headers']['person'])
        assert response.status_code==401;private_headers(response)
    response=case['client_http'].get('/api/usuario/privacidad/exportar',headers=case['headers']['person'])
    assert response.status_code==401 and 'member_links' not in response.text

def test_lost_revoke_commit_ACK_never_reports_success_and_requires_reconciliation(actual_http,monkeypatch,caplog):
    from web.database import engine as database
    case=actual_http;result=link(case);before=identity(case)
    class LostAcknowledgment(Session):
        def commit(self):
            super().commit()
            if self.info.get('member_commit_attempted'):raise RuntimeError('PRIVATE_QA_ACK_DETAIL')
    factory=database._SessionLocal
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=case['app'],class_=LostAcknowledgment,autoflush=False,expire_on_commit=False))
    path='/api/usuario/vinculos/'+result['id']
    uncertain=case['client_http'].request('DELETE',path,headers=case['headers']['person'],json={'expected_version':result['version']})
    assert uncertain.status_code==503 and uncertain.json()['detail']['code']=='member_link_reconciliation_required'
    assert 'PRIVATE_QA_ACK_DETAIL' not in uncertain.text+caplog.text and uncertain.json().get('success') is not True
    private_headers(uncertain);monkeypatch.setattr(database,'_SessionLocal',factory)
    with Session(case['admin']) as db:assert db.get(ClientAccountLink,result['id']).status=='revoked'
    retry=case['client_http'].request('DELETE',path,headers=case['headers']['person'],json={'expected_version':result['version']})
    assert retry.status_code==404 and export(case).json()['member_links']['records']==[]
    assert identity(case)==before and len(case['mail'])==1

def test_exact_live_export_cursor_survives_revocation_of_its_own_anchor_row(actual_http):
    case=actual_http;first=link(case,publish=False)
    second=link(case,gym='othergym',client='otherclient',publish=False)
    page=export(case,limit=1).json()['member_links'];anchor=page['records'][0]
    assert page['next_after']==anchor['id'] and {first['id'],second['id']}=={anchor['id'],max(first['id'],second['id'])}
    removed=case['client_http'].request('DELETE','/api/usuario/vinculos/'+anchor['id'],headers=case['headers']['person'],json={'expected_version':anchor['version']})
    assert removed.status_code==200
    following=export(case,limit=1,after_member_link=page['next_after']).json()['member_links']
    assert [row['id'] for row in following['records']]==[max(first['id'],second['id'])]
    assert following['next_after'] is None
