"""Diary privacy applies to failures and cannot be relaxed by endpoint headers."""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from web.middleware.security_headers import SecurityHeadersMiddleware


@pytest.mark.parametrize('path', ['/api/usuario/diario', '/api/usuario/diario/2026-10-19'])
@pytest.mark.parametrize('status', [401, 404, 503])
def test_diary_errors_override_unsafe_downstream_headers(path, status):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.patch(path)
    async def endpoint():
        return JSONResponse({'detail': 'synthetic'}, status_code=status, headers={
            'Referrer-Policy': 'unsafe-url', 'Cache-Control': 'public, max-age=300'})

    with TestClient(app) as client:
        response = client.patch(path)
    assert response.status_code == status
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('registered_handler', [False, True])
def test_unhandled_diary_error_remains_private_and_opaque(registered_handler):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    if registered_handler:
        @app.exception_handler(Exception)
        async def public_error(request, error):
            return JSONResponse({'detail': 'factory generic error'}, status_code=500)

    @app.patch('/api/usuario/diario/2026-10-19')
    async def endpoint():
        raise RuntimeError('synthetic-private-diary-value')

    with TestClient(app) as client:
        response = client.patch('/api/usuario/diario/2026-10-19')
    assert response.status_code == 500
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert response.headers['cache-control'] == 'no-store'
    assert 'synthetic-private-diary-value' not in response.text
    assert response.json()['detail'] == (
        'factory generic error' if registered_handler else 'Error interno del servidor')


@pytest.mark.parametrize('path', ['/api/usuario/diarios', '/api/usuario/diario-export',
                                  '/api/usuario/DIARIO/2026-10-19'])
def test_adjacent_paths_keep_existing_policy(path):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get(path)
    async def endpoint():
        return JSONResponse({}, status_code=404)

    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 404
    assert response.headers['referrer-policy'] == 'strict-origin-when-cross-origin'
