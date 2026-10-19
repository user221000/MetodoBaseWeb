"""Independent exact recovery CSP and declared all-response privacy headers."""
import pytest
from fastapi.responses import JSONResponse
from test_recovery_security import engine,old_hash,clean,seeded,case,privacy

@pytest.mark.parametrize('method,suffix,status',[('GET','request',405),('GET','confirm',405),('POST','request',422),('POST','confirm',422)])
def test_recovery_api_errors_preserve_declared_privacy_headers_for_every_response(case,method,suffix,status):
 response=case.client.request(method,'/api/auth/password-reset/'+suffix,content=b'{}',headers={'Content-Type':'application/json'})
 assert response.status_code==status
 privacy(response)

def test_first_party_csp_is_exact_route_only_and_downstream_policy_is_never_trusted(case):
 @case.app.get('/independent-csp-control')
 async def control():return JSONResponse({'synthetic':True},headers={'Content-Security-Policy':'script-src https://attacker.example.invalid'})
 page=case.client.get('/auth/reset-password');assert page.status_code==200
 policy=page.headers['content-security-policy']
 for expected in ["default-src 'none'","script-src 'self' 'nonce-","style-src 'self'","connect-src 'self'","form-action 'self'","frame-ancestors 'none'","base-uri 'none'","object-src 'none'"]:assert expected in policy
 assert 'https:' not in policy and 'unsafe-' not in policy
 adjacent=case.client.get('/auth/reset-password/',follow_redirects=False)
 assert adjacent.status_code==307;assert adjacent.headers['content-security-policy']!=policy
 ordinary=case.client.get('/independent-csp-control')
 assert 'attacker.example.invalid' not in ordinary.headers['content-security-policy']
 assert 'https://accounts.google.com' in ordinary.headers['content-security-policy']
