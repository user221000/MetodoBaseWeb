import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from web.middleware.security_headers import SecurityHeadersMiddleware


@pytest.mark.parametrize('path', ['/api/auth/mfa/status', '/api/usuario/diario/2026-10-19', '/api/usuario/historial'])
@pytest.mark.parametrize('failure', [False, True])
def test_composed_private_families_preserve_parent_policies(path, failure):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.post(path)
    async def endpoint():
        if failure:
            raise ValueError('synthetic-private-merged-marker')
        headers = {
            'Cache-Control': 'public, max-age=300', 'Referrer-Policy': 'unsafe-url',
            'Content-Security-Policy': 'script-src https://attacker.example.invalid'}
        if path == '/api/usuario/historial':
            # Match the real historical handler's explicit no-store header
            # (web/routes/usuario.py), while diary/MFA test an unsafe override.
            headers['Cache-Control'] = 'no-store'
        return JSONResponse({'detail': 'unavailable'}, status_code=404, headers=headers)

    with TestClient(app) as client:
        response = client.post(path)
    assert response.status_code == (500 if failure else 404)
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert 'synthetic-private-merged-marker' not in response.text
    assert 'attacker.example.invalid' not in response.headers['content-security-policy']
    if path.startswith('/api/auth/mfa/'):
        assert "default-src 'none'" in response.headers['content-security-policy']
        assert 'https://accounts.google.com' not in response.headers['content-security-policy']
    else:
        assert 'https://accounts.google.com' in response.headers['content-security-policy']


@pytest.mark.parametrize('path', ['/api/auth/mfa-extra', '/api/usuario/diario-export'])
def test_adjacent_paths_preserve_existing_default_policy(path):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get(path)
    async def endpoint():
        return JSONResponse({}, status_code=404)

    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 404
    assert response.headers['referrer-policy'] == 'strict-origin-when-cross-origin'
