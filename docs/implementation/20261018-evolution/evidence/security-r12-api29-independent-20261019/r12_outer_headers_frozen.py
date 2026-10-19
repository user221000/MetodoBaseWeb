"""Actual early returns of the factory-selected rate middleware, no Redis I/O."""
import importlib,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from test_r12_headers_security import link_db,case,http,private_headers

HERE=Path(__file__).parent

def record(http,kind,response):
    p=HERE/(kind+'-'+http['factory'].replace('.','-')+'.json');assert not p.exists()
    p.write_text(json.dumps({'factory':http['factory'],'status':response.status_code,
        'cache-control':response.headers.get('cache-control'),'referrer-policy':response.headers.get('referrer-policy'),
        'content-security-policy':response.headers.get('content-security-policy'),
        'marker_echoed':'PRIVATE_SYNTHETIC_REDIS_DETAIL' in response.text},indent=2)+'\n',encoding='utf8')

@pytest.mark.parametrize('path',['/api/usuario/vinculos','/auth/accept-client-link'])
def test_real_local_bucket_429_has_private_headers_on_api_and_page(http,monkeypatch,path):
    from web.middleware import rate_limiter
    store=rate_limiter.RateLimiterStore(1,1)
    monkeypatch.setattr(rate_limiter,'get_rate_limiter_store',lambda *a,**k:store)
    configured=[m for m in http['asgi'].user_middleware if m.cls is rate_limiter.RateLimiterMiddleware]
    assert len(configured)==1
    configured[0].kwargs['enabled']=True
    with TestClient(http['asgi'],raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        assert c.get('/api/auth/me',headers=http['headers']).status_code==200
        result=c.get(path,headers={**http['headers'],'Accept':'application/json'})
    assert result.status_code==429 and int(result.headers['retry-after'])>0
    record(http,'local-api-429' if path.startswith('/api/') else 'local-page-429',result)
    private_headers(result)
    if path=='/auth/accept-client-link':
        csp=result.headers.get('content-security-policy','')
        assert "default-src 'none'" in csp and "script-src 'self' 'nonce-" in csp
        assert 'https:' not in csp and 'unsafe' not in csp

def test_factory_selected_redis_outage503_has_private_headers(http,monkeypatch,caplog):
    from web.settings import get_settings
    from web import rate_limiter_redis
    settings=get_settings()
    monkeypatch.setattr(settings,'REDIS_URL','redis://synthetic.invalid:6379/0')
    async def unavailable():raise ConnectionError('PRIVATE_SYNTHETIC_REDIS_DETAIL')
    monkeypatch.setattr(rate_limiter_redis,'_get_redis',unavailable)
    app=importlib.import_module(http['factory']).create_app()
    assert any(m.cls is rate_limiter_redis.RedisRateLimitMiddleware for m in app.user_middleware)
    with TestClient(app,raise_server_exceptions=False,client=(http['peer'],50000)) as c:
        assert c.get('/api/auth/me',headers=http['headers']).status_code==200
        result=c.get('/api/usuario/vinculos',headers=http['headers'])
    assert result.status_code==503 and result.json()['detail']['code']=='rate_limit_backend_unavailable'
    assert 'PRIVATE_SYNTHETIC_REDIS_DETAIL' not in result.text+caplog.text
    record(http,'redis-api-503',result)
    private_headers(result)
