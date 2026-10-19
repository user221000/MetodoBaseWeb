"""Focal controls for moving the single existing header middleware outward."""
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from tests import integration_client_link_services as shared
from test_r12_headers_security import http,case,link_db,private_headers
from web.middleware.security_headers import SecurityHeadersMiddleware

def test_cors_preflight_actual_authenticated_response_and_gzip_remain_coherent(http):
    app=http['asgi']
    security=[m for m in app.user_middleware if m.cls is SecurityHeadersMiddleware]
    assert len(security)==1 and app.user_middleware[0].cls is SecurityHeadersMiddleware
    cors=next(m for m in app.user_middleware if m.cls is CORSMiddleware)
    allowed=next(o for o in cors.kwargs['allow_origins'] if o!='*')
    issue,token=shared.issue(http);link=shared.accept(http,issue,token)
    marker='Published food '+('Q'*120)
    plan,_,_=shared.source(http,pdf=False,marker=marker)
    shared.publish(http,link,plan)
    with TestClient(app,raise_server_exceptions=False,client=(http['peer'],50000)) as client:
        preflight=client.options('/api/usuario/vinculos',headers={'Origin':allowed,
            'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'})
        assert preflight.status_code==200
        assert preflight.headers['access-control-allow-origin']==allowed
        assert preflight.headers['access-control-allow-credentials']=='true'
        private_headers(preflight)
        rejected=client.options('/api/usuario/vinculos',headers={'Origin':'https://untrusted.example.invalid',
            'Access-Control-Request-Method':'GET'})
        assert rejected.status_code==400 and 'access-control-allow-origin' not in rejected.headers
        private_headers(rejected)
        response=client.get('/api/usuario/vinculos/'+link['link_id']+'/plan',
            headers={**http['headers'],'Origin':allowed,'Accept-Encoding':'gzip'})
        assert response.status_code==200
        assert response.json()['publication']['plan']['desayuno']['alimentos']=={marker:50}
        assert response.headers['access-control-allow-origin']==allowed
        assert response.headers['content-encoding']=='gzip'
        assert 'accept-encoding' in response.headers['vary'].lower()
        assert 0<int(response.headers['content-length'])<len(response.content)
        assert 'nonce-' in response.headers['content-security-policy']
        private_headers(response)

def test_private_boundary_handler_failure_keeps_generic_body_id_and_class_only_log(http,monkeypatch,caplog):
    app=http['asgi']
    def broken_handler(request,error):raise ValueError('SYNTHETIC_PRIVATE_HANDLER_ARGUMENT')
    monkeypatch.setitem(app.exception_handlers,Exception,broken_handler)
    class FailureAfterRoute(BaseHTTPMiddleware):
        async def dispatch(self,request,call_next):
            response=await call_next(request)
            if request.url.path=='/api/usuario/vinculos':
                assert response.status_code==200
                raise RuntimeError('SYNTHETIC_PRIVATE_ORIGINAL_ARGUMENT')
            return response
    index=next(i for i,m in enumerate(app.user_middleware) if m.cls is SecurityHeadersMiddleware)
    app.user_middleware.insert(index+1,Middleware(FailureAfterRoute))
    with TestClient(app,raise_server_exceptions=False,client=(http['peer'],50000)) as client:
        response=client.get('/api/usuario/vinculos',headers={**http['headers'],'X-Request-ID':'synthetic-r12-control-id'})
    assert response.status_code==500
    assert response.json()=={'detail':'Error interno del servidor','request_id':'synthetic-r12-control-id'}
    private_headers(response)
    assert 'class=RuntimeError' in caplog.text
    assert 'SYNTHETIC_PRIVATE_HANDLER_ARGUMENT' not in response.text+caplog.text
    assert 'SYNTHETIC_PRIVATE_ORIGINAL_ARGUMENT' not in response.text+caplog.text
