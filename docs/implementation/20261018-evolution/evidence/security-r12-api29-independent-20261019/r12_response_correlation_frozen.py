"""Correlation at each boundary affected by final RequestID registration order."""
import importlib
import pytest
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from test_r12_headers_security import http,case,link_db,private_headers
from web.middleware.security_headers import SecurityHeadersMiddleware

@pytest.mark.parametrize('status',[500,429,503])
def test_existing_request_id_survives_private_fallback_and_early_rejections(http,monkeypatch,status):
    app=http['asgi'];identifier='synthetic-correlation-'+str(status)
    if status==500:
        def broken_handler(request,error):raise ValueError('SYNTHETIC_PRIVATE_FAILURE')
        monkeypatch.setitem(app.exception_handlers,Exception,broken_handler)
        class FailAfterRoute(BaseHTTPMiddleware):
            async def dispatch(self,request,call_next):
                response=await call_next(request)
                if request.url.path=='/api/usuario/vinculos':
                    assert response.status_code==200
                    raise RuntimeError('SYNTHETIC_PRIVATE_FAILURE')
                return response
        index=next(i for i,m in enumerate(app.user_middleware) if m.cls is SecurityHeadersMiddleware)
        app.user_middleware.insert(index+1,Middleware(FailAfterRoute))
    elif status==429:
        from web.middleware import rate_limiter
        store=rate_limiter.RateLimiterStore(1,1)
        monkeypatch.setattr(rate_limiter,'get_rate_limiter_store',lambda *a,**k:store)
        next(m for m in app.user_middleware if m.cls is rate_limiter.RateLimiterMiddleware).kwargs['enabled']=True
    else:
        from web.settings import get_settings
        from web import rate_limiter_redis
        monkeypatch.setattr(get_settings(),'REDIS_URL','redis://synthetic.invalid:6379/0')
        async def unavailable():raise ConnectionError('SYNTHETIC_PRIVATE_FAILURE')
        monkeypatch.setattr(rate_limiter_redis,'_get_redis',unavailable)
        app=importlib.import_module(http['factory']).create_app()
    with TestClient(app,raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        if status==429:assert c.get('/api/auth/me',headers=http['headers']).status_code==200
        response=c.get('/api/usuario/vinculos',headers={**http['headers'],'X-Request-ID':identifier})
    assert response.status_code==status and 'SYNTHETIC_PRIVATE_FAILURE' not in response.text
    private_headers(response)
    assert response.headers.get('x-request-id')==identifier
    if status==500:assert response.json()['request_id']==identifier
