"""Independent HTTP security assertions against exact canonical29 API; no provider I/O."""
from pathlib import Path
import hashlib,json,os,re,uuid
from urllib.parse import urlsplit,urlunsplit
from html import unescape
import pytest
from sqlalchemy import create_engine,event,select,text
from sqlalchemy.orm import Session

from tests import integration_client_link_services as shared
from tests import integration_client_link_http as author_fixture
from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
from web.database.tenant_context import configure_tenant_engine
from web.database.models import Usuario,UserRole,ClientAccountLink,ClientLinkInvitation,ClientPlanPublication,Cliente

HERE=Path(__file__).parent
case=shared.case
http=author_fixture.http

@pytest.fixture(scope='module',params=['sqlite','postgresql'])
def link_db(request,tmp_path_factory):
    """Only this UUID is eligible for cleanup; no shared test fixture DB ownership."""
    control=None;name=None;admin=None;app=None
    if request.param=='sqlite':
        url='sqlite:///'+(tmp_path_factory.mktemp('r12-security-http')/'api.db').as_posix()
    else:
        import psycopg2
        from psycopg2 import sql
        private=os.environ['METODOBASE_TEST_MIGRATOR_URL'];parsed=urlsplit(private)
        assert parsed.hostname in ('127.0.0.1','localhost') and parsed.port==55483
        name='metodobase_test_sec_r12_api_'+uuid.uuid4().hex
        control=psycopg2.connect(private.replace('postgresql+psycopg2://','postgresql://',1));control.autocommit=True
        with control.cursor() as cursor:cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        (HERE/'owned-database-created.json').write_text(json.dumps({'name':name,'state':'created'})+'\n')
        url=urlunsplit(parsed._replace(path='/'+name))
    try:
        run_migration(url,'db_bootstrap.py','--revision','20261019_client_account_links')
        admin=create_engine(url,hide_parameters=True)
        if request.param=='sqlite':
            @event.listens_for(admin,'connect')
            def fk(c,r):c.execute('PRAGMA foreign_keys=ON')
        app=configure_tenant_engine(application_engine(url,admin))
        if request.param=='postgresql':
            with app.connect() as c:
                assert c.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()==(False,False,False,False)
        yield admin,app
    finally:
        if app is not None and app is not admin:app.dispose()
        if admin is not None:admin.dispose()
        if control is not None:
            assert re.fullmatch(r'metodobase_test_sec_r12_api_[0-9a-f]{32}',name)
            with control.cursor() as c:
                c.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
                c.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(name,));assert c.fetchone()[0]==0
            control.close()
            (HERE/'owned-database-closed.json').write_text(json.dumps({'name':name,'state':'dropped','remaining':0})+'\n')

def fresh_header(http,who):
    from web import auth
    with Session(http['app']) as db:
        return {'Authorization':'Bearer '+auth.crear_access_token(auth.identity_from_user(db.get(Usuario,http[who]),db))}

def issued(http,*,issuer='gym',client='client',recipient=None,key=None):
    http['received'].clear()
    response=http['client_http'].post('/api/clientes/'+http[client]+'/vinculacion/invitaciones',headers=http['headers'][issuer],
        json={'recipient_email':recipient or http['email'],'request_key':key or str(uuid.uuid4())})
    assert response.status_code==202
    assert http['received'].wait(5)
    token=re.search(r'#token=([A-Za-z0-9_-]{43})',unescape(http['mail'][-1][2])).group(1)
    assert token not in response.text and '#token=' not in response.text
    assert not any(k in response.json() for k in ('recipient_email','recipient_user_id','token_hash','url'))
    return response.json(),token

def accept(http,issue,token,who='person'):
    response=http['client_http'].post('/api/usuario/vinculaciones/aceptar',headers=http['headers'][who],
        json={'token':token,'expected_version':issue['version'],'confirm':True})
    assert response.status_code==200
    return response.json()

@pytest.mark.parametrize('mutation',['session_version','role'])
def test_persisted_authority_is_rechecked_after_auth_before_invitation_commit(http,monkeypatch,mutation):
    from web.routes import client_links
    original=client_links._invoke;seen=[]
    def interleave(function,*args,**kwargs):
        if function is client_links.invitations.issue_invitation:
            with Session(http['admin']) as db:
                row=db.get(Usuario,http['gym'])
                if mutation=='session_version':row.session_version+=1
                else:row.role=UserRole.VIEWER
                db.commit()
            seen.append(True)
        return original(function,*args,**kwargs)
    monkeypatch.setattr(client_links,'_invoke',interleave)
    response=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':http['email'],'request_key':'security-race'})
    assert seen==[True] and response.status_code in (401,403)
    assert http['mail']==[]
    with Session(http['admin']) as db:
        assert db.scalar(select(ClientAccountLink.id).where(ClientAccountLink.client_id==http['client'])) is None

def test_nutri_member_can_read_status_but_cannot_issue_or_elevate_with_body(http):
    with Session(http['admin']) as db:
        member=db.get(Usuario,http['person']);member.role=UserRole.NUTRIOLOGO;member.team_gym_id=http['gym'];db.commit()
    headers=fresh_header(http,'person')
    state=http['client_http'].get('/api/clientes/'+http['client']+'/vinculacion',headers=headers)
    assert state.status_code==200 and state.json()['capabilities']['issue_invitation'] is False
    endpoint='/api/clientes/'+http['client']+'/vinculacion/invitaciones'
    denied=http['client_http'].post(endpoint,headers=headers,json={'recipient_email':http['email'],'request_key':'role-denied'})
    assert denied.status_code==403 and http['mail']==[]
    invalid=http['client_http'].post(endpoint,headers=headers,json={'recipient_email':http['email'],'request_key':'spoof','role':'owner','gym_id':http['gym']})
    assert invalid.status_code==422

def test_professional_cannot_issue_against_another_gym_even_with_known_client_id(http):
    result=http['client_http'].post('/api/clientes/'+http['otherclient']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':http['email'],'request_key':'cross-gym'})
    assert result.status_code==404 and http['mail']==[]
    assert http['othergym'] not in result.text and http['otherclient'] not in result.text
    with Session(http['admin']) as db:
        assert db.scalar(select(ClientLinkInvitation.id).where(ClientLinkInvitation.client_id==http['otherclient'])) is None

@pytest.mark.parametrize('origin',['own','external'])
def test_owner_explicit_recipient_export_keeps_six_collections_empty_and_seventh_scoped(http,origin):
    source_gym='gym' if origin=='own' else 'othergym';client='client' if origin=='own' else 'otherclient'
    with Session(http['admin']) as db:email=db.get(Usuario,http['gym']).email
    invitation,token=issued(http,issuer=source_gym,client=client,recipient=email)
    accept(http,invitation,token,who='gym')
    # A second active member belongs to the same professional portfolio. It
    # must never be included in the professional OWNER's recipient export.
    http['extra_client']=str(uuid.uuid4())
    with Session(http['admin']) as db:
        db.add(Cliente(id_cliente=http['extra_client'],gym_id=http[source_gym],nombre='Other portfolio member',activo=True));db.commit()
    other,other_token=issued(http,issuer=source_gym,client='extra_client')
    accept(http,other,other_token)
    listing=http['client_http'].get('/api/usuario/vinculos',headers=http['headers']['gym'])
    assert listing.status_code==200
    assert [r['link_id'] for r in listing.json()['items']]==[invitation['link_id']]
    response=http['client_http'].get('/api/usuario/privacidad/exportar?limit=1',headers=http['headers']['gym'])
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    dto=response.json();records=dto['member_links']['records']
    assert dto['scope']['personal_space'] is False
    assert len(records)==1 and records[0]['id']==invitation['link_id']
    assert set(records[0])=={'id','status','version','gym_name','client_display_name','accepted_at','publication'}
    for key in ('profiles','plans','measurements','purchases','generation_requests','personal_diary'):
        assert dto[key]=={'records':[],'next_after':None}
    assert dto['personal_subscription'] is None and dto['canonical_subscription'] is None
    assert token not in response.text and 'recipient_email' not in response.text and 'object_key' not in response.text
    with Session(http['admin']) as db:
        user=db.get(Usuario,http['gym']);link=db.get(ClientAccountLink,invitation['link_id'])
        assert user.role==UserRole.OWNER and user.team_gym_id is None and user.session_version==0
        assert link.user_id==http['gym'] and link.gym_id==http[source_gym]
        assert db.scalar(select(Cliente.gym_id).where(Cliente.id_cliente==http[client]))==http[source_gym]

def test_pdf_object_bytes_cannot_substitute_for_pinned_publication_descriptor(http,monkeypatch,caplog):
    invitation,token=issued(http);link=accept(http,invitation,token)
    plan,descriptor,content=shared.source(http,marker='exact-independent-pdf')
    publication=shared.publish(http,link,plan)
    path='/api/usuario/vinculos/'+link['link_id']+'/publicaciones/'+publication['publication_id']+'/pdf'
    good=http['client_http'].get(path,headers=http['headers']['person'])
    assert good.status_code==200 and good.content==content
    from web.storage.runtime import get_object_store
    store=get_object_store()
    monkeypatch.setattr(store,'read',lambda *a,**k:b'%PDF-1.7\nSYNTHETIC_WRONG_CONTENT')
    rejected=http['client_http'].get(path,headers=http['headers']['person'])
    assert rejected.status_code==404 and rejected.headers['cache-control']=='no-store'
    assert 'SYNTHETIC_WRONG_CONTENT' not in rejected.text+caplog.text
    assert descriptor.key not in rejected.text and descriptor.sha256 not in rejected.text

def test_http_proof_never_survives_success_or_denial_on_reused_restricted_pool(http):
    invitation,token=issued(http)
    denied=http['client_http'].post('/api/usuario/vinculaciones/invitacion',headers=http['headers']['other'],json={'token':token})
    assert denied.status_code==404
    accept(http,invitation,token)
    with http['app'].connect() as connection:
        if connection.dialect.name=='postgresql':
            assert connection.scalar(text("SELECT NULLIF(current_setting('app.client_invitation_digest',true),'')")) is None
            assert connection.scalar(text("SELECT NULLIF(current_setting('app.current_tenant',true),'')")) is None
            assert connection.scalar(text('SELECT count(*) FROM client_link_invitations'))==0
    replay=http['client_http'].post('/api/usuario/vinculaciones/aceptar',headers=http['headers']['other'],
        json={'token':token,'expected_version':1,'confirm':True})
    assert replay.status_code==404 and token not in replay.text

def test_sensitive_limiter_outage_returns503_before_accept_and_never_logs_token(http,monkeypatch,caplog):
    invitation,token=issued(http)
    from web import rate_limiter_redis
    from fastapi import HTTPException
    async def fail_closed(*args,**kwargs):
        assert kwargs['sensitive'] is True
        raise HTTPException(503,{'code':'rate_limiter_unavailable','message':'Temporalmente no disponible.'})
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',fail_closed)
    response=http['client_http'].post('/api/usuario/vinculaciones/aceptar',headers=http['headers']['person'],
        json={'token':token,'expected_version':1,'confirm':True})
    assert response.status_code==503 and token not in response.text+caplog.text
    with Session(http['admin']) as db:
        row=db.get(ClientAccountLink,invitation['link_id'])
        assert row.status=='pending' and row.user_id is None and row.version==1

def test_request_replay_canonical_address_never_resends_or_discloses_account_existence(http):
    key='independent-key-'+uuid.uuid4().hex
    invitation,token=issued(http,key=key)
    response=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':'  '+http['email'].upper()+'  ','request_key':key})
    assert response.status_code==202 and response.json()==invitation and len(http['mail'])==1
    assert token not in response.text and http['person'] not in response.text
    mismatch=http['client_http'].post('/api/clientes/'+http['client']+'/vinculacion/invitaciones',headers=http['headers']['gym'],
        json={'recipient_email':'not-registered-'+uuid.uuid4().hex+'@example.invalid','request_key':key})
    assert mismatch.status_code==409 and len(http['mail'])==1
    with Session(http['admin']) as db:
        assert db.get(ClientLinkInvitation,invitation['invitation_id']).recipient_email==http['email']

def test_loaded_product_and_fixture_modules_have_exact_checkout_origin():
    import sys
    root=Path(os.environ.get('R12_REVIEW_SOURCE_ROOT','F:/mb-r12-api-s')).resolve()
    names=('web.routes.client_links','web.services.client_link_context','web.services.client_link_export',
        'web.services.client_link_plans','web.services.client_link_invitations','web.services.client_link_projection',
        'web.middleware.security_headers','web.database.member_link_policy_v1','web.database.alembic.member_link_security_v1',
        'tests.integration_client_link_services','tests.integration_client_link_http')
    checked=[]
    for name in names:
        module=__import__(name,fromlist=['__file__']);path=Path(module.__file__).resolve()
        assert path.is_relative_to(root)
        checked.append({'module':name,'relative_path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (HERE/'module-origins.json').write_text(json.dumps(checked,indent=2)+'\n',encoding='utf8')
