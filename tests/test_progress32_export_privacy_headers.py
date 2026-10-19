"""Exact export privacy boundary, real factories plus hostile middleware responses.

The mounted exporter remains GET-only and keeps its cursor/DTO/authorization.
Synthetic downstream unit responses exercise policy; real factories exercise
routing, validation, authentication and exception handlers separately.
"""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from tests.test_personal_progress_http import progress_db,progress_http
from web.middleware.security_headers import SecurityHeadersMiddleware

EXPORT='/api/usuario/privacidad/exportar'
PRIVATE='synthetic-export-private-parameter'


def private(response):
    assert response.headers['referrer-policy']=='no-referrer'
    assert response.headers['cache-control']=='no-store'
    assert response.headers['x-content-type-options']=='nosniff'
    # Export keeps the existing normal policy; it cannot adopt downstream CSP.
    assert 'https://accounts.google.com/gsi/client' in response.headers['content-security-policy']
    assert 'unsafe.example.invalid' not in response.headers['content-security-policy']


def test_real_export_methods_auth_and_slash_redirect_keep_exact_private_boundary(progress_http):
    c=progress_http;client=c['client_http']
    cases=[('GET',EXPORT,{},401),('POST',EXPORT,c['headers']['person'],405),
        ('PUT',EXPORT,c['headers']['person'],405),('GET',EXPORT+'/',{},307)]
    for method,path,headers,status in cases:
        response=client.request(method,path,headers=headers,follow_redirects=False)
        assert response.status_code==status
        private(response)
        if status==307:assert response.headers['location'].endswith(EXPORT)


def test_real_export_unhandled_failure_is_private_and_opaque(progress_http,monkeypatch):
    from web.routes import privacy
    def fail(*args,**kwargs):raise RuntimeError(PRIVATE)
    monkeypatch.setattr(privacy,'export_personal_data',fail)
    response=progress_http['client_http'].get(EXPORT,headers=progress_http['headers']['person'])
    assert response.status_code==500
    assert response.json()['detail']=='Error interno del servidor'
    assert PRIVATE not in response.text
    private(response)


def test_real_adjacent_routes_do_not_inherit_export_privacy_or_become_exporters(progress_http):
    client=progress_http['client_http']
    for path in [EXPORT+'-extra',EXPORT+'/extra',EXPORT+'//','/api/usuario/privacidad/EXPORTAR','/api/usuario/privacidad/export']:
        response=client.get(path,follow_redirects=False)
        assert response.status_code in (404,307)
        assert response.headers['referrer-policy']=='strict-origin-when-cross-origin'
        assert 'progress_consents' not in response.text


@pytest.mark.parametrize('path',[EXPORT,EXPORT+'/'])
@pytest.mark.parametrize('status',[401,405,422,500])
def test_middleware_overrides_hostile_downstream_headers_for_exact_export_paths(path,status):
    app=FastAPI();app.add_middleware(SecurityHeadersMiddleware)
    @app.get(path)
    def response():
        return JSONResponse({'detail':'synthetic'},status_code=status,headers={
            'Referrer-Policy':'unsafe-url','Cache-Control':'public, max-age=300',
            'Content-Security-Policy':"default-src https://unsafe.example.invalid"})
    with TestClient(app) as client:result=client.get(path)
    assert result.status_code==status
    private(result)
