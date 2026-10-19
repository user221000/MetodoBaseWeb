"""Independent R12 error-boundary probes. Synthetic inputs; real factories/auth/migration."""
from pathlib import Path
import importlib,json
from itertools import count
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,event
from sqlalchemy.orm import Session,sessionmaker
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from tests import integration_client_link_services as shared
from tests.integration_schema_migrations import run_migration
from web.database.tenant_context import configure_tenant_engine
from web.middleware.security_headers import SecurityHeadersMiddleware

HERE=Path(__file__).parent
_peers=count(120)
case=shared.case

@pytest.fixture(scope='module')
def link_db(tmp_path_factory):
    path=tmp_path_factory.mktemp('independent-r12-api')/'review.db'
    url='sqlite:///'+path.as_posix()
    run_migration(url,'db_bootstrap.py','--revision','20261019_client_account_links')
    db=create_engine(url,hide_parameters=True)
    @event.listens_for(db,'connect')
    def fk(c,r):c.execute('PRAGMA foreign_keys=ON')
    configure_tenant_engine(db)
    try:yield db,db
    finally:db.dispose()

@pytest.fixture(params=['web.main_web','api.app'])
def http(case,request,monkeypatch):
    from web import auth
    from web.database import engine as database
    from web.database.models import Usuario
    from web.settings import get_settings
    settings=get_settings()
    monkeypatch.setattr(settings,'BASE_URL','https://member.example.invalid')
    monkeypatch.setattr(settings,'RESEND_API_KEY','re_synthetic_offline_only')
    monkeypatch.setattr(database,'_engine',case['app'])
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=case['app'],autoflush=False,expire_on_commit=False))
    app=importlib.import_module(request.param).create_app()
    with Session(case['app']) as db:
        user=db.get(Usuario,case['person'])
        headers={'Authorization':'Bearer '+auth.crear_access_token(auth.identity_from_user(user,db))}
    peer='192.0.2.'+str(next(_peers))
    return dict(case,asgi=app,headers=headers,factory=request.param,peer=peer)

def save(http,name,response):
    record={'factory':http['factory'],'status':response.status_code,
        'cache_control':response.headers.get('cache-control'), 'referrer_policy':response.headers.get('referrer-policy'),
        'csp':response.headers.get('content-security-policy'),
        'private_marker_echoed':'SYNTHETIC_PRIVATE_BOUNDARY' in response.text,
        'body_keys':sorted(response.json()) if response.headers.get('content-type','').startswith('application/json') else None}
    target=HERE/(name+'-'+http['factory'].replace('.','-')+'.json')
    assert not target.exists();target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')

def private_headers(response):
    assert response.headers.get('cache-control')=='no-store'
    assert response.headers.get('referrer-policy')=='no-referrer'

def test_existing_error_handler_after_real_authenticated_route(http,monkeypatch):
    """Failure during ASGI response serialization occurs after APIRoute's try completes."""
    from web.routes import client_links
    from starlette.responses import Response
    class AfterAuthenticatedResponseFailure(BaseHTTPMiddleware):
        async def dispatch(self,request,call_next):
            response=await call_next(request)
            if request.url.path=='/api/usuario/vinculos':
                assert response.status_code==200
                raise RuntimeError('SYNTHETIC_PRIVATE_BOUNDARY')
            return response
    app=http['asgi'];index=next(i for i,m in enumerate(app.user_middleware) if m.cls is SecurityHeadersMiddleware)
    app.user_middleware.insert(index+1,Middleware(AfterAuthenticatedResponseFailure))
    with TestClient(http['asgi'],raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        assert c.get('/api/auth/me',headers=http['headers']).status_code==200
        response=c.get('/api/usuario/vinculos',headers=http['headers'])
    assert response.status_code==500
    assert 'SYNTHETIC_PRIVATE_BOUNDARY' not in response.text
    save(http,'after-auth-500',response)
    private_headers(response)

def test_inner_middleware_failure_does_not_skip_private_policy(http):
    class BoundaryFailure(BaseHTTPMiddleware):
        async def dispatch(self,request,call_next):
            if request.url.path=='/api/usuario/vinculos':raise RuntimeError('SYNTHETIC_PRIVATE_BOUNDARY')
            return await call_next(request)
    app=http['asgi'];index=next(i for i,m in enumerate(app.user_middleware) if m.cls is SecurityHeadersMiddleware)
    app.user_middleware.insert(index+1,Middleware(BoundaryFailure))
    with TestClient(app,raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        assert c.get('/api/auth/me',headers=http['headers']).status_code==200
        response=c.get('/api/usuario/vinculos',headers=http['headers'])
    assert response.status_code==500 and 'SYNTHETIC_PRIVATE_BOUNDARY' not in response.text
    save(http,'inner-middleware-500',response)
    private_headers(response)

def test_public_accept_page_error_keeps_first_party_policy(http):
    class BrokenPageBoundary(BaseHTTPMiddleware):
        async def dispatch(self,request,call_next):
            if request.url.path=='/auth/accept-client-link':raise RuntimeError('SYNTHETIC_PRIVATE_BOUNDARY')
            return await call_next(request)
    app=http['asgi'];index=next(i for i,m in enumerate(app.user_middleware) if m.cls is SecurityHeadersMiddleware)
    app.user_middleware.insert(index+1,Middleware(BrokenPageBoundary))
    with TestClient(http['asgi'],raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        response=c.get('/auth/accept-client-link',headers={'Accept':'application/json'})
    assert response.status_code==500 and 'SYNTHETIC_PRIVATE_BOUNDARY' not in response.text
    save(http,'page-500',response)
    private_headers(response)
    csp=response.headers.get('content-security-policy','')
    assert "default-src 'none'" in csp and "script-src 'self' 'nonce-" in csp
    assert 'https:' not in csp and 'unsafe' not in csp

def test_body_stream_failure_is_contained_inside_route(http,monkeypatch):
    from starlette.requests import Request
    original=Request.stream
    async def unavailable(self):
        if self.url.path=='/api/usuario/vinculaciones/invitacion':
            raise RuntimeError('SYNTHETIC_PRIVATE_BOUNDARY')
        async for chunk in original(self):yield chunk
    monkeypatch.setattr(Request,'stream',unavailable)
    with TestClient(http['asgi'],raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        response=c.post('/api/usuario/vinculaciones/invitacion',headers=http['headers'],json={'token':'X'*43})
    assert response.status_code==503 and response.json()['detail']['code']=='member_service_unavailable'
    assert 'SYNTHETIC_PRIVATE_BOUNDARY' not in response.text
    private_headers(response)

def test_service_failure_and_adjacent_404_controls(http,monkeypatch):
    from web.routes import client_links
    def unavailable(*a,**kw):raise RuntimeError('SYNTHETIC_PRIVATE_BOUNDARY')
    monkeypatch.setattr(client_links,'_invoke',unavailable)
    with TestClient(http['asgi'],raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        response=c.get('/api/usuario/vinculos',headers=http['headers'])
        assert response.status_code==503 and 'SYNTHETIC_PRIVATE_BOUNDARY' not in response.text
        private_headers(response)
        adjacent=c.get('/auth/accept-client-link-adjacent',headers={'Accept':'application/json'})
        assert adjacent.status_code==404
        assert adjacent.headers.get('referrer-policy')=='strict-origin-when-cross-origin'
        assert "default-src 'self'" in adjacent.headers.get('content-security-policy','')
