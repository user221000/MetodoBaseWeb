"""Focal exact-path header and non-destructive EXPLAIN harness regressions."""
from pathlib import Path
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from starlette.responses import JSONResponse

from tests.test_personal_history_pagination import history_http, _write_explain_if_requested
from web.middleware.security_headers import SecurityHeadersMiddleware


def test_history_auth_failures_keep_private_headers(history_http, test_gym_user):
    client = history_http[0]
    for headers, status in [({},401),(test_gym_user['auth_headers'],403)]:
        response = client.get('/api/usuario/historial',headers=headers)
        assert response.status_code == status
        assert response.headers['referrer-policy'] == 'no-referrer'
        assert 'no-store' in response.headers['cache-control']


@pytest.mark.parametrize('method', ['GET','POST','PATCH','DELETE','HEAD','OPTIONS','PUT'])
def test_exact_history_path_requires_private_policy_for_every_method(method):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_api_route('/api/usuario/historial',lambda:JSONResponse({},status_code=403),methods=[method])
    with TestClient(app) as client:
        response = client.request(method,'/api/usuario/historial?cursor=synthetic')
    assert response.status_code == 403
    assert response.headers['referrer-policy'] == 'no-referrer'


@pytest.mark.parametrize('path', ['/api/usuario/historial-next','/api/usuario/historial/',
    '/api/usuario/historial/next','/api/usuario/HISTORIAL','/api/usuario/historiales','/api/usuario/mi-plan'])
def test_adjacent_paths_do_not_inherit_exact_history_policy(path):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_api_route(path,lambda:JSONResponse({},status_code=422),methods=['POST'])
    with TestClient(app) as client:
        response = client.post(path)
    assert response.status_code == 422
    assert response.headers['referrer-policy'] == 'strict-origin-when-cross-origin'


def test_explain_writer_has_no_default_side_effects(monkeypatch):
    monkeypatch.delenv('METODOBASE_HISTORY_EXPLAIN_OUTPUT',raising=False)
    def forbidden(*args,**kwargs):
        raise AssertionError('Default EXPLAIN attempted a filesystem write')
    monkeypatch.setattr(Path,'open',forbidden)
    monkeypatch.setattr(Path,'mkdir',forbidden)
    assert _write_explain_if_requested('Synthetic',{}) is None


@pytest.mark.parametrize('value', ['docs/implementation/20261018-evolution/evidence/history-pagination',tempfile.gettempdir()])
def test_explain_writer_rejects_historical_or_shared_output(monkeypatch,value):
    monkeypatch.setenv('METODOBASE_HISTORY_EXPLAIN_OUTPUT',value)
    with pytest.raises(ValueError):
        _write_explain_if_requested('Synthetic',{})


def test_explain_writer_uses_explicit_temp_and_never_overwrites(monkeypatch,tmp_path):
    monkeypatch.setenv('METODOBASE_HISTORY_EXPLAIN_OUTPUT',str(tmp_path))
    _write_explain_if_requested('Synthetic',{'sql':'synthetic'})
    path = tmp_path/'explain-Synthetic.json'
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        _write_explain_if_requested('Synthetic',{'sql':'replacement'})
    assert path.read_bytes() == original
