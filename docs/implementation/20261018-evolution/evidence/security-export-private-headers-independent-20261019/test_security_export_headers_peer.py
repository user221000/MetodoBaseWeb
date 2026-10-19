"""Independent exact-path response policy probes; units are not product routes."""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from tests.test_personal_progress_http import progress_db, progress_http  # noqa:F401
from web.middleware.security_headers import SecurityHeadersMiddleware

CANONICAL='/api/usuario/privacidad/exportar'
SENTINEL='SEC_PRIVATE_EXPORT_SENTINEL'


def assert_private(response):
    assert response.headers['referrer-policy']=='no-referrer'
    assert response.headers['cache-control']=='no-store'
    assert response.headers['x-content-type-options']=='nosniff'


def test_real_head_options_delete_and_their_slash_redirects_remain_private(progress_http):
    client=progress_http['client_http'];headers=progress_http['headers']['person']
    for method in ['HEAD','OPTIONS','DELETE']:
        denied=client.request(method,CANONICAL,headers=headers,follow_redirects=False)
        assert denied.status_code==405
        assert_private(denied)
        redirected=client.request(method,CANONICAL+'/?after_progress_consent=INVALID',headers=headers,follow_redirects=False)
        assert redirected.status_code==307
        assert_private(redirected)
        assert redirected.headers['location'].endswith(CANONICAL+'?after_progress_consent=INVALID')
        assert 'progress_consents' not in redirected.text


@pytest.mark.parametrize('broken_handler',['raise','non500'])
def test_private_fallback_survives_broken_generic_handler_without_exporting_error_details(progress_http,monkeypatch,broken_handler):
    from web.routes import privacy
    def fail_export(*args,**kwargs):raise RuntimeError(SENTINEL)
    async def handler(request,error):
        if broken_handler=='raise':raise RuntimeError(SENTINEL)
        return JSONResponse({'detail':SENTINEL},status_code=503,headers={'Referrer-Policy':'unsafe-url','Cache-Control':'public'})
    monkeypatch.setattr(privacy,'export_personal_data',fail_export)
    monkeypatch.setitem(progress_http['client_http'].app.exception_handlers,Exception,handler)
    result=progress_http['client_http'].get(CANONICAL,headers=progress_http['headers']['person'])
    assert result.status_code==500
    assert_private(result)
    assert result.json()['detail']=='Error interno del servidor'
    assert SENTINEL not in result.text and 'progress_consents' not in result.text


@pytest.mark.parametrize('path',[CANONICAL,CANONICAL+'/'])
@pytest.mark.parametrize('status',[202,303,429,503])
def test_exact_policy_does_not_depend_on_success_or_error_class(path,status):
    app=FastAPI();app.add_middleware(SecurityHeadersMiddleware)
    @app.get(path)
    def unit_response():
        return JSONResponse({'synthetic':'inert'},status_code=status,headers={
            'Referrer-Policy':'unsafe-url','Cache-Control':'public, max-age=7',
            'Content-Security-Policy':'default-src https://hostile.example.invalid',
            'Location':'/synthetic-target'})
    with TestClient(app) as client:result=client.get(path,follow_redirects=False)
    assert result.status_code==status
    assert_private(result)
    assert 'hostile.example.invalid' not in result.headers['content-security-policy']
    assert "script-src 'self' 'nonce-" in result.headers['content-security-policy']


@pytest.mark.parametrize('path',[CANONICAL+'-suffix',CANONICAL+'/child',CANONICAL+'//','/api/usuario/privacidad/EXPORTAR'])
def test_neighbor_unit_response_keeps_preexisting_general_policy(path):
    app=FastAPI();app.add_middleware(SecurityHeadersMiddleware)
    @app.get(path)
    def unit_response():
        return JSONResponse({'synthetic':'neighbor'},status_code=422,headers={
            'Referrer-Policy':'unsafe-url','Cache-Control':'public, max-age=7'})
    with TestClient(app) as client:result=client.get(path,follow_redirects=False)
    assert result.status_code==422
    assert result.headers['referrer-policy']=='strict-origin-when-cross-origin'
    assert result.headers['cache-control']=='public, max-age=7'

