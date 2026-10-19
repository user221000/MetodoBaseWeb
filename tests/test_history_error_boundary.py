"""Exact history error containment without changing adjacent paths or global handlers."""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from starlette.responses import JSONResponse

from web.middleware.security_headers import SecurityHeadersMiddleware
from tests.test_personal_history_pagination import history_http


def test_real_factory_dependency_failure_keeps_generic_body_and_request_id(history_http,caplog):
    from web.database.engine import get_db
    client = history_http[0]
    def unavailable():
        raise RuntimeError('SYNTHETIC-PRIVATE-DEPENDENCY-MARKER')
    client.app.dependency_overrides[get_db] = unavailable
    try:
        response = client.get('/api/usuario/historial',headers=history_http[2]['history-person'],params={'cursor':'SYNTHETIC-CURSOR'})
    finally:
        client.app.dependency_overrides.pop(get_db)
    assert response.status_code==500
    assert response.json()['detail']=='Error interno del servidor'
    assert response.json()['request_id']==response.headers['x-request-id']
    assert response.headers['referrer-policy']=='no-referrer'
    assert 'no-store' in response.headers['cache-control']
    assert 'SYNTHETIC' not in response.text and 'SYNTHETIC' not in caplog.text
    assert 'class=RuntimeError' in caplog.text


@pytest.mark.parametrize('handler_kind', ['async','sync','missing','raises','wrong_status'])
def test_dependency_failure_has_generic_private_500_with_or_without_working_handler(handler_kind,caplog):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    calls = []
    def unavailable():
        raise RuntimeError('SYNTHETIC-PRIVATE-SQL-AND-CURSOR-MARKER')
    def handled(request,error):
        calls.append(type(error).__name__)
        request.state.request_id = 'synthetic-correlation'
        if handler_kind == 'raises':
            raise ValueError('SYNTHETIC-HANDLER-PRIVATE-MARKER')
        return JSONResponse({'detail':'Error interno del servidor','request_id':request.state.request_id},status_code=200 if handler_kind=='wrong_status' else 500,headers={'Cache-Control':'public, max-age=60'})
    async def handled_async(request,error):
        return handled(request,error)
    if handler_kind != 'missing':
        app.add_exception_handler(Exception,handled_async if handler_kind=='async' else handled)
    @app.get('/api/usuario/historial')
    def history(unused=Depends(unavailable)):
        raise AssertionError('Dependency failure must precede endpoint')
    with TestClient(app,raise_server_exceptions=False) as client:
        response = client.get('/api/usuario/historial?cursor=synthetic-position')
    assert response.status_code == 500
    assert response.json()['detail']=='Error interno del servidor'
    assert response.headers['referrer-policy']=='no-referrer'
    assert 'no-store' in response.headers['cache-control']
    assert 'SYNTHETIC' not in response.text and 'synthetic-position' not in response.text
    assert 'SYNTHETIC' not in caplog.text
    if handler_kind != 'missing':
        assert calls == ['RuntimeError']
        assert response.json()['request_id']=='synthetic-correlation'
    if handler_kind in {'missing','raises','wrong_status'}:
        assert 'class=RuntimeError' in caplog.text


def test_same_exception_on_adjacent_path_reaches_existing_outer_handler_without_private_policy():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    calls = []
    @app.exception_handler(Exception)
    async def existing(request,error):
        calls.append(type(error).__name__)
        return JSONResponse({'detail':'existing-public-body'},status_code=500,headers={'Referrer-Policy':'same-origin'})
    @app.get('/api/usuario/historial-extra')
    def adjacent():
        raise RuntimeError('Synthetic adjacent failure')
    with TestClient(app,raise_server_exceptions=False) as client:
        response = client.get('/api/usuario/historial-extra')
    assert calls==['RuntimeError']
    assert response.status_code==500 and response.json()=={'detail':'existing-public-body'}
    assert response.headers['referrer-policy']=='same-origin'
    assert 'cache-control' not in response.headers


@pytest.mark.parametrize('status', [401,403,422,405])
def test_handled_http_errors_keep_original_status_and_private_policy(status):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    @app.get('/api/usuario/historial')
    def history():
        raise HTTPException(status,'Public controlled detail')
    with TestClient(app) as client:
        response = client.get('/api/usuario/historial')
    assert response.status_code==status
    assert response.json()=={'detail':'Public controlled detail'}
    assert response.headers['referrer-policy']=='no-referrer'
    assert 'no-store' in response.headers['cache-control']
