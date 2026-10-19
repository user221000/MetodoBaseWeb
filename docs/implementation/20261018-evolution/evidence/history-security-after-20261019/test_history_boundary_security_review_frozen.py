"""Own focal error-boundary controls, synthetic runtime and metadata only."""
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from starlette.responses import JSONResponse

from tests.test_personal_history_pagination import history_http
from web.middleware.security_headers import SecurityHeadersMiddleware

MARKER = 'INDEPENDENT_PRIVATE_VALUE_NOT_FOR_OUTPUT'


def private(response):
    assert response.status_code == 500
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "object-src 'none'" in response.headers['content-security-policy']
    assert "'nonce-" in response.headers['content-security-policy']
    assert MARKER not in response.text


def test_real_DI_failure_invokes_existing_factory_handler_once(history_http, caplog):
    from web.database.engine import get_db
    client = history_http[0]
    handler = client.app.exception_handlers[Exception]
    calls = []
    async def observed(request, error):
        calls.append(type(error).__name__)
        return await handler(request, error)
    def unavailable():
        raise RuntimeError(MARKER)
    client.app.exception_handlers[Exception] = observed
    client.app.dependency_overrides[get_db] = unavailable
    try:
        with caplog.at_level(logging.ERROR):
            response = client.get('/api/usuario/historial', params={'cursor': MARKER}, headers=history_http[2]['history-person'])
    finally:
        client.app.exception_handlers[Exception] = handler
        client.app.dependency_overrides.pop(get_db)
    private(response)
    assert calls == ['RuntimeError']
    assert response.json() == {'detail': 'Error interno del servidor', 'request_id': response.headers['x-request-id']}
    assert 'class=RuntimeError' in caplog.text
    assert MARKER not in caplog.text


@pytest.mark.parametrize('mode', ['missing', 'raises'])
def test_real_factory_fallback_preserves_correlation_without_exception_details(history_http, caplog, mode):
    from web.database.engine import get_db
    client = history_http[0]
    original = client.app.exception_handlers.pop(Exception)
    calls = []
    def unavailable():
        raise RuntimeError(MARKER)
    async def broken(request, error):
        calls.append(type(error).__name__)
        raise ValueError(MARKER + '_HANDLER')
    if mode == 'raises':
        client.app.exception_handlers[Exception] = broken
    client.app.dependency_overrides[get_db] = unavailable
    try:
        with caplog.at_level(logging.ERROR):
            response = client.get('/api/usuario/historial', params={'cursor': MARKER}, headers=history_http[2]['history-person'])
    finally:
        client.app.exception_handlers[Exception] = original
        client.app.dependency_overrides.pop(get_db)
    private(response)
    assert response.json() == {'detail': 'Error interno del servidor', 'request_id': response.headers['x-request-id']}
    assert calls == ([] if mode == 'missing' else ['RuntimeError'])
    assert MARKER not in caplog.text and 'class=RuntimeError' in caplog.text


@pytest.mark.parametrize('mode', ['sync', 'sync_awaitable', 'invalid_type', 'wrong_status', 'async_raises'])
def test_middleware_handlers_fail_closed_and_overwrite_public_cache_and_referrer(mode, caplog):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    calls = []
    def response(request, error):
        calls.append(type(error).__name__)
        request.state.request_id = 'independent-correlation'
        if mode == 'invalid_type':
            return {'unexpected': MARKER}
        return JSONResponse({'detail': 'Error interno del servidor', 'request_id': request.state.request_id},
            status_code=503 if mode == 'wrong_status' else 500,
            headers={'Cache-Control': 'public, max-age=600', 'Referrer-Policy': 'unsafe-url', 'Content-Security-Policy': 'default-src *'})
    async def awaitable(request, error):
        if mode == 'async_raises':
            calls.append(type(error).__name__)
            request.state.request_id = 'independent-correlation'
            raise TypeError(MARKER + '_HANDLER')
        return response(request, error)
    def sync_awaitable(request, error):
        return awaitable(request, error)
    app.add_exception_handler(Exception, sync_awaitable if mode == 'sync_awaitable' else awaitable if mode == 'async_raises' else response)
    @app.get('/api/usuario/historial')
    def endpoint():
        raise RuntimeError(MARKER)
    with TestClient(app, raise_server_exceptions=False) as client:
        with caplog.at_level(logging.ERROR):
            result = client.get('/api/usuario/historial?cursor=' + MARKER)
    private(result)
    assert result.json() == {'detail': 'Error interno del servidor', 'request_id': 'independent-correlation'}
    assert calls == ['RuntimeError']
    assert MARKER not in caplog.text
    assert 'default-src *' not in result.headers['content-security-policy']
    if mode in {'invalid_type', 'wrong_status', 'async_raises'}:
        assert 'class=RuntimeError' in caplog.text


def test_adjacent_error_keeps_existing_outer_handler_status_body_and_policy():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    calls = []
    @app.exception_handler(Exception)
    def existing(request, error):
        calls.append(type(error).__name__)
        return JSONResponse({'detail': 'existing-adjacent-body'}, status_code=502,
            headers={'Cache-Control': 'private, max-age=7', 'Referrer-Policy': 'same-origin'})
    @app.get('/api/usuario/historial-extra')
    def endpoint():
        raise RuntimeError(MARKER)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/usuario/historial-extra')
    assert response.status_code == 502
    assert response.json() == {'detail': 'existing-adjacent-body'}
    assert calls == ['RuntimeError']
    assert response.headers['cache-control'] == 'private, max-age=7'
    assert response.headers['referrer-policy'] == 'same-origin'


def test_controlled_503_remains_503_and_receives_private_headers():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    @app.get('/api/usuario/historial')
    def endpoint():
        raise HTTPException(503, 'controlled-public-unavailable')
    with TestClient(app) as client:
        response = client.get('/api/usuario/historial')
    assert response.status_code == 503
    assert response.json() == {'detail': 'controlled-public-unavailable'}
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert 'no-store' in response.headers['cache-control']


def test_normal_adjacent_response_retains_default_referrer_and_nonce_CSP():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    @app.get('/api/usuario/historial-extra')
    def endpoint():
        return {'status': 'synthetic-public'}
    with TestClient(app) as client:
        first = client.get('/api/usuario/historial-extra')
        second = client.get('/api/usuario/historial-extra')
    assert first.status_code == 200
    assert first.headers['referrer-policy'] == 'strict-origin-when-cross-origin'
    assert 'no-store' in first.headers['cache-control']
    assert first.headers['content-security-policy'] != second.headers['content-security-policy']
    assert "object-src 'none'" in first.headers['content-security-policy']
