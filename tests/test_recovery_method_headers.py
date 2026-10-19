"""Recovery privacy headers are exact-path middleware policy, for every method."""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from web.middleware.security_headers import SecurityHeadersMiddleware


@pytest.mark.parametrize('method',['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'])
@pytest.mark.parametrize('path,expected',[
    ('/api/auth/password-reset/request','no-referrer'),
    ('/api/auth/password-reset/confirm','no-referrer'),
    ('/api/auth/password-reset/request/','strict-origin-when-cross-origin'),
    ('/api/auth/password-reset/request-extra','strict-origin-when-cross-origin'),
    ('/api/auth/password-reset/other','strict-origin-when-cross-origin'),
    ('/api/ordinary','strict-origin-when-cross-origin'),
])
def test_exact_api_policy_never_trusts_downstream_policy_or_changes_other_paths(method,path,expected):
    app=FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    @app.api_route('/{path:path}',methods=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'])
    async def endpoint(path:str):
        return JSONResponse({'synthetic':True},headers={'Referrer-Policy':'unsafe-url',
            'Content-Security-Policy':'script-src https://attacker.example.invalid'})
    with TestClient(app) as client:response=client.request(method,path)
    assert response.status_code==200
    assert response.headers['referrer-policy']==expected
    assert 'no-store' in response.headers['cache-control']
    assert 'attacker.example.invalid' not in response.headers['content-security-policy']
    assert 'https://accounts.google.com' in response.headers['content-security-policy']
