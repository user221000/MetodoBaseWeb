"""Independent uncommon verbs, exact-path fences and duplicate header checks."""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from web.middleware.security_headers import SecurityHeadersMiddleware

@pytest.mark.parametrize('method,path,downstream,expected',[
 ('TRACE','/api/auth/password-reset/request','unsafe-url','no-referrer'),
 ('CONNECT','/api/auth/password-reset/confirm','unsafe-url','no-referrer'),
 ('PRIVATE','/api/auth/password-reset/request','strict-origin-when-cross-origin','no-referrer'),
 ('OPTIONS','/api/auth/password-reset/confirm','unsafe-url','no-referrer'),
 ('GET','/api/auth/password-reset/request/','unsafe-url','strict-origin-when-cross-origin'),
 ('POST','/api/auth/password-reset/confirm-extra','unsafe-url','strict-origin-when-cross-origin'),
 ('DELETE','/api/auth/password-reset/Request','unsafe-url','strict-origin-when-cross-origin'),
 ('PATCH','/api/auth/password-reset/other','unsafe-url','strict-origin-when-cross-origin'),
 ('GET','/api/ordinary','no-referrer','no-referrer'),
 ('GET','/api/auth/password-reset','unsafe-url','strict-origin-when-cross-origin'),
])
def test_uncommon_methods_exact_and_adjacent_paths_and_header_replacement(method,path,downstream,expected):
 app=FastAPI();app.add_middleware(SecurityHeadersMiddleware)
 @app.api_route('/{path:path}',methods=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS','TRACE','CONNECT','PRIVATE'])
 async def endpoint(path:str):
  response=JSONResponse({'synthetic':True},headers={'Referrer-Policy':downstream,'Content-Security-Policy':'script-src https://attacker.example.invalid'})
  # Actual duplicate fields exercise replacement, not get() over a combined string.
  response.raw_headers.append((b'referrer-policy',b'unsafe-url'))
  response.raw_headers.append((b'content-security-policy',b"default-src *"))
  return response
 with TestClient(app) as client:response=client.request(method,path)
 assert response.status_code==200
 assert response.headers['referrer-policy']==expected
 assert len(response.headers.get_list('referrer-policy'))==1
 assert len(response.headers.get_list('content-security-policy'))==1
 assert 'attacker.example.invalid' not in response.headers['content-security-policy']
 assert 'default-src *' not in response.headers['content-security-policy']
 assert 'https://accounts.google.com' in response.headers['content-security-policy']
 assert 'no-store' in [value.strip() for value in response.headers['cache-control'].split(',')]
