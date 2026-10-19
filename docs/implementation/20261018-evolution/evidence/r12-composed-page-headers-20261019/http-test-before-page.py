"""Both real factories + real29 migration/auth; only mail transport is synthetic."""
from html import unescape
import importlib
from itertools import count
import re
from threading import Event
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event,select,text
from sqlalchemy.orm import Session,sessionmaker

from tests import integration_client_link_services as shared
from web.database.models import ClientAccountLink,ClientLinkInvitation,Usuario,UserRole,Cliente

link_db=shared.link_db
case=shared.case
source=shared.source
_peers=count(1)


@pytest.fixture(params=['web.main_web','api.app'])
def http(case,request,monkeypatch):
    from web import auth
    from web.database import engine as database
    from web.database.tenant_context import current_tenant
    from web.services import email_service
    from web.settings import get_settings
    settings=get_settings()
    monkeypatch.setattr(settings,'BASE_URL','https://member.example.invalid')
    monkeypatch.setattr(settings,'RESEND_API_KEY','re_synthetic_offline_only')
    monkeypatch.setattr(database,'_engine',case['app'])
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=case['app'],autoflush=False,expire_on_commit=False))
    mail=[];received=Event()
    def send(recipient,subject,html,**kwargs):
        assert current_tenant.get()==''
        if '#token=' in html:
            with Session(case['admin']) as db:
                assert db.scalar(select(ClientLinkInvitation.status).where(ClientLinkInvitation.recipient_email==recipient))=='pending'
            mail.append((recipient,subject,html));received.set()
        return True
    monkeypatch.setattr(email_service,'_send',send)
    app=importlib.import_module(request.param).create_app()
    with Session(case['app']) as db:
        headers={key:{'Authorization':'Bearer '+auth.crear_access_token(auth.identity_from_user(db.get(Usuario,case[key]),db))}
            for key in ('gym','othergym','person','other')}
    # Independent scenarios use independent synthetic socket peers. Keep real
    # rate limiting enabled; sharing TestClient's default peer across all
    # scenarios would consume the same issue bucket between unrelated cases.
    with TestClient(app,raise_server_exceptions=False,client=('192.0.2.'+str(next(_peers)),50000)) as client:
        assert client.get('/api/auth/me',headers=headers['person']).status_code==200
        yield {**case,'client_http':client,'headers':headers,'mail':mail,'received':received,'factory':request.param}


def issued(http,recipient=None):
    result=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':recipient or http['email'],'request_key':str(uuid.uuid4())})
    assert result.status_code==202,result.text
    assert http['received'].wait(5),'Synthetic local dispatcher did not complete'
    token=re.search(r'https://member\.example\.invalid/auth/accept-client-link#token=([A-Za-z0-9_-]{43})',unescape(http['mail'][-1][2])).group(1)
    assert token not in result.text and all(word not in result.json() for word in ('token','token_hash','url','recipient_email','recipient_user_id'))
    return result.json(),token


def test_real_registration_uses_same_issued_proof_and_keeps_own_personal_profile(http):
    client=http['client_http'];email='new-r12-'+uuid.uuid4().hex+'@example.invalid'
    issue,token=issued(http,email)
    registered=client.post('/api/auth/registro',json={'email':email,'password':'Synthetic password 42!','nombre':'New member','tipo':'usuario'})
    assert registered.status_code==200,registered.text
    bearer={'Authorization':'Bearer '+registered.json()['token']}
    me=client.get('/api/auth/me',headers=bearer)
    assert me.status_code==200 and me.json()['role']=='viewer'
    before=client.get('/api/usuario/vinculos',headers=bearer)
    assert before.json()['items']==[]
    info=client.post('/api/usuario/vinculaciones/invitacion',headers=bearer,json={'token':token})
    assert info.status_code==200 and info.json()['can_accept'] is True,info.text
    rejected=client.post('/api/usuario/vinculaciones/aceptar',headers=bearer,json={'token':token,'expected_version':1,'confirm':False})
    assert rejected.status_code==422
    accepted=client.post('/api/usuario/vinculaciones/aceptar',headers=bearer,json={'token':token,'expected_version':1,'confirm':True})
    assert accepted.status_code==200 and accepted.json()['version']==2,accepted.text
    identity=me.json()['id']
    with Session(http['admin']) as db:
        user=db.get(Usuario,identity)
        assert user.role==UserRole.VIEWER and user.team_gym_id is None and user.session_version==0
        assert db.scalar(select(Cliente.gym_id).where(Cliente.id_cliente==http['client']))==http['gym']
        assert db.scalar(select(ClientAccountLink.user_id).where(ClientAccountLink.id==issue['link_id']))==identity


def test_http_explicit_publication_and_exact_old_pdf_replacement(http):
    client=http['client_http'];issue,token=issued(http)
    accepted=client.post('/api/usuario/vinculaciones/aceptar',headers=http['headers']['person'],
        json={'token':token,'expected_version':1,'confirm':True})
    assert accepted.status_code==200,accepted.text
    link=issue['link_id'];professional='/api/clientes/'+http['client']+'/vinculacion/'+link
    plan,_,content=source(http)
    published=client.post(professional+'/publicaciones',headers=http['headers']['gym'],
        json={'plan_id':plan,'expected_link_version':2,'expected_publication_version':0,'expected_publication_id':None})
    assert published.status_code==200,published.text
    member='/api/usuario/vinculos/'+link
    result=client.get(member+'/plan',headers=http['headers']['person'])
    assert result.status_code==200,result.text
    dto=result.json();pdf_url=dto['publication']['pdf_url']
    assert dto['publication']['source_plan_id']==plan and dto['capabilities']['manage_clients'] is False
    download=client.get(pdf_url,headers=http['headers']['person'])
    assert download.status_code==200 and download.content==content
    assert download.headers['referrer-policy']=='no-referrer' and download.headers['cache-control']=='no-store'
    assert client.get(pdf_url,headers=http['headers']['other']).status_code==404
    state=client.get('/api/clientes/'+http['client']+'/vinculacion',headers=http['headers']['gym'])
    assert state.status_code==200 and state.json()['items'][0]['publication']['id']==published.json()['publication_id']
    second,_,new_content=source(http,marker='new')
    replace=client.post(professional+'/publicaciones',headers=http['headers']['gym'],
        json={'plan_id':second,'expected_link_version':2,'expected_publication_version':1,
            'expected_publication_id':published.json()['publication_id']})
    assert replace.status_code==200,replace.text
    assert client.get(pdf_url,headers=http['headers']['person']).status_code==404
    stale,_,_=source(http,marker='stale')
    outdated=client.post(professional+'/publicaciones',headers=http['headers']['gym'],
        json={'plan_id':stale,'expected_link_version':2,'expected_publication_version':1,
            'expected_publication_id':published.json()['publication_id']})
    assert outdated.status_code==409 and outdated.json()['detail']['code']=='member_version_conflict',outdated.text
    latest=client.get(member+'/plan',headers=http['headers']['person']).json()
    assert latest['publication']['id']==replace.json()['publication_id']
    assert client.get(latest['publication']['pdf_url'],headers=http['headers']['person']).content==new_content
    revoked=client.request('DELETE',member,headers=http['headers']['person'],json={'expected_version':2})
    assert revoked.status_code==200 and revoked.json()['status']=='revoked',revoked.text
    assert client.get(member+'/plan',headers=http['headers']['person']).status_code==404
    assert client.get('/api/auth/me',headers=http['headers']['person']).status_code==200
    with http['app'].connect() as db:
        if db.dialect.name=='postgresql':
            assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
            assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''


@pytest.mark.parametrize('path,method',[
    ('/api/usuario/vinculaciones/aceptar','get'),('/api/usuario/vinculaciones/invitacion','get'),
    ('/api/usuario/vinculos','post'),('/auth/accept-client-link','get'),
    ('/api/clientes/c/vinculacion/invitaciones/not-a-uuid/reenviar','get'),
    ('/api/usuario/vinculos/not-a-uuid/publicaciones/not-a-uuid/pdf','post'),
])
def test_privacy_headers_survive_wrong_method_and_missing_page(http,path,method):
    response=getattr(http['client_http'],method)(path,headers=http['headers']['person'])
    assert response.status_code in {404,405}
    assert response.headers['referrer-policy']=='no-referrer' and response.headers['cache-control']=='no-store'
    if path=='/auth/accept-client-link':
        csp=response.headers['content-security-policy']
        assert "default-src 'none'" in csp and "script-src 'self' 'nonce-" in csp
        assert 'https:' not in csp and 'unsafe' not in csp


@pytest.mark.parametrize('confirmed',[False,True])
def test_http_commit_failure_is_visible_without_sending_or_reverting_uncertain_issue(http,monkeypatch,confirmed,caplog):
    from web.database import engine as database
    class FailingSession(Session):
        def commit(self):
            if self.info.get('member_commit_attempted'):
                if confirmed:super().commit()
                raise RuntimeError('PRIVATE_DATABASE_DETAIL_MUST_NOT_APPEAR')
            return super().commit()
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=http['app'],class_=FailingSession,autoflush=False,expire_on_commit=False))
    result=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':http['email'],'request_key':'uncertain-http'})
    assert result.status_code==503 and result.json()['detail']['code']=='member_link_reconciliation_required',result.text
    assert http['mail']==[] and 'PRIVATE_DATABASE_DETAIL_MUST_NOT_APPEAR' not in result.text+caplog.text
    with Session(http['admin']) as db:
        links=db.scalars(select(ClientAccountLink).where(ClientAccountLink.client_id==http['client'])).all()
        assert len(links)==int(confirmed)
        if links:assert links[0].status=='pending'
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=http['app'],autoflush=False,expire_on_commit=False))
    if confirmed:
        replay=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
            json={'recipient_email':http['email'],'request_key':'uncertain-http'})
        assert replay.status_code==202 and replay.json()['delivery_status']=='not_confirmed'
        assert http['mail']==[]


def test_queue_failure_after_confirmed_commit_keeps_pending_without_faking_delivery(http,monkeypatch,caplog):
    class UnavailableDispatcher:
        def submit(self,*args):raise RuntimeError('PRIVATE_MAIL_DESTINATION_MUST_NOT_APPEAR')
    monkeypatch.setattr(http['client_http'].app.state,'member_link_dispatcher',UnavailableDispatcher())
    response=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':http['email'],'request_key':'queue-unavailable'})
    assert response.status_code==202 and response.json()['delivery_status']=='not_confirmed',response.text
    assert http['mail']==[] and 'PRIVATE_MAIL_DESTINATION_MUST_NOT_APPEAR' not in response.text+caplog.text
    with Session(http['admin']) as db:
        assert db.get(ClientAccountLink,response.json()['link_id']).status=='pending'
        assert db.get(ClientLinkInvitation,response.json()['invitation_id']).status=='pending'


def test_member_get_plan_list_and_export_have_no_business_dml_or_commit(http):
    issue,token=issued(http)
    accepted=http['client_http'].post('/api/usuario/vinculaciones/aceptar',headers=http['headers']['person'],
        json={'token':token,'expected_version':1,'confirm':True})
    assert accepted.status_code==200,accepted.text
    commits=[];dml=[]
    def committed(db):commits.append(True)
    def statement(connection,cursor,sql,parameters,context,executemany):
        if sql.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE'}:dml.append(True)
    event.listen(Session,'after_commit',committed);event.listen(http['app'],'before_cursor_execute',statement)
    try:
        for path in ['/api/usuario/vinculos','/api/usuario/vinculos/'+issue['link_id']+'/plan','/api/usuario/privacidad/exportar']:
            response=http['client_http'].get(path,headers=http['headers']['person'])
            assert response.status_code==200,response.text
        assert commits==[] and dml==[]
    finally:
        event.remove(Session,'after_commit',committed);event.remove(http['app'],'before_cursor_execute',statement)


def test_unexpected_adapter_failure_has_private_headers_and_sanitized_visible_error(http,monkeypatch,caplog):
    from web.routes import client_links
    def unavailable(*args,**kwargs):raise RuntimeError('PRIVATE_SQL_PARAMETERS_MUST_NOT_APPEAR')
    monkeypatch.setattr(client_links,'_invoke',unavailable)
    result=http['client_http'].get('/api/usuario/vinculos',headers=http['headers']['person'])
    assert result.status_code==503 and result.json()['detail']['code']=='member_service_unavailable',result.text
    assert result.headers['referrer-policy']=='no-referrer' and result.headers['cache-control']=='no-store'
    assert 'PRIVATE_SQL_PARAMETERS_MUST_NOT_APPEAR' not in result.text+caplog.text


@pytest.mark.parametrize('plan_type',['menu_fijo','opciones'])
def test_current_real_worker_four_meals_and_pdf_can_be_explicitly_published(http,plan_type):
    with Session(http['admin']) as db:
        row=db.scalar(select(Cliente).where(Cliente.id_cliente==http['client']))
        row.edad=30;row.sexo='M';row.peso_kg=75;row.estatura_cm=175;row.grasa_corporal_pct=20
        row.nivel_actividad='moderada';row.objetivo='mantenimiento';db.commit()
    issue,token=issued(http)
    accepted=http['client_http'].post('/api/usuario/vinculaciones/aceptar',headers=http['headers']['person'],
        json={'token':token,'expected_version':1,'confirm':True})
    assert accepted.status_code==200,accepted.text
    generated=http['client_http'].post('/api/generar-plan',headers={**http['headers']['gym'],'Idempotency-Key':'r12-real-worker-'+plan_type},
        json={'id_cliente':http['client'],'tipo_plan':plan_type,'plan_numero':1})
    assert generated.status_code==200,generated.text
    source=generated.json()
    assert set(source['plan'])=={'desayuno','almuerzo','comida','cena'}
    published=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/'+issue['link_id']+'/publicaciones',headers=http['headers']['gym'],
        json={'plan_id':source['plan_id'],'expected_link_version':2,'expected_publication_version':0,'expected_publication_id':None})
    assert published.status_code==200,published.text
    delivered=http['client_http'].get('/api/usuario/vinculos/'+issue['link_id']+'/plan',headers=http['headers']['person'])
    assert delivered.status_code==200 and delivered.json()['publication']['plan']==source['plan'],delivered.text
    private_pdf=http['client_http'].get(delivered.json()['publication']['pdf_url'],headers=http['headers']['person'])
    professional_pdf=http['client_http'].get('/api/descargar-pdf/'+http['client'],headers=http['headers']['gym'])
    assert private_pdf.status_code==professional_pdf.status_code==200
    assert private_pdf.content==professional_pdf.content and private_pdf.content.startswith(b'%PDF-')


def test_publication_lost_commit_ack_requires_fresh_exact_observation_before_replacement(http,monkeypatch):
    from web.database import engine as database
    client=http['client_http'];issue,token=issued(http)
    accepted=client.post('/api/usuario/vinculaciones/aceptar',headers=http['headers']['person'],
        json={'token':token,'expected_version':1,'confirm':True})
    assert accepted.status_code==200,accepted.text
    plan,_,_=source(http,marker='acknowledgement-lost')
    endpoint='/api/clientes/'+http['client']+'/vinculacion/'+issue['link_id']+'/publicaciones'
    body={'plan_id':plan,'expected_link_version':2,'expected_publication_version':0,'expected_publication_id':None}
    class LostAckSession(Session):
        def commit(self):
            super().commit()
            if self.info.get('member_commit_attempted'):raise RuntimeError('PRIVATE_COMMIT_ACK_MUST_NOT_APPEAR')
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=http['app'],class_=LostAckSession,autoflush=False,expire_on_commit=False))
    uncertain=client.post(endpoint,headers=http['headers']['gym'],json=body)
    assert uncertain.status_code==503 and uncertain.json()['detail']['code']=='member_link_reconciliation_required',uncertain.text
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=http['app'],autoflush=False,expire_on_commit=False))
    retry=client.post(endpoint,headers=http['headers']['gym'],json=body)
    assert retry.status_code==409 and retry.json()['detail']['code']=='member_version_conflict',retry.text
    state=client.get('/api/clientes/'+http['client']+'/vinculacion',headers=http['headers']['gym'])
    assert state.status_code==200,state.text
    observed=state.json()['items'][0]['publication']
    assert observed['source_plan_id']==plan
    replacement,_,_=source(http,marker='after-authorized-readback')
    next_body={'plan_id':replacement,'expected_link_version':2,'expected_publication_version':observed['version'],
        'expected_publication_id':observed['id']}
    result=client.post(endpoint,headers=http['headers']['gym'],json=next_body)
    assert result.status_code==200,result.text
    assert result.json()['publication_id']!=observed['id']
    stale=client.post(endpoint,headers=http['headers']['gym'],json=next_body)
    assert stale.status_code==409 and stale.json()['detail']['code']=='member_version_conflict',stale.text
    readback=client.get('/api/usuario/vinculos/'+issue['link_id']+'/plan',headers=http['headers']['person'])
    assert readback.status_code==200,readback.text
    assert readback.json()['publication']['id']==result.json()['publication_id']
    assert readback.json()['publication']['source_plan_id']==replacement
