"""Real ASGI metrics retain bounded route labels without request identities."""
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest


@pytest.mark.parametrize('mode', ['matched', 'unmatched'])
def test_metrics_store_only_declared_route_label_and_no_client_identity(mode, monkeypatch):
    from web.middleware import metrics

    store = metrics.MetricsStore()
    monkeypatch.setattr(metrics, '_metrics_store', store)
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    @app.get('/probe/{subject}')
    async def failed(subject: str):
        return JSONResponse({'synthetic': True}, status_code=422)

    with TestClient(app) as client:
        for index in range(4):
            path = ('/probe/' if mode == 'matched' else '/unknown/') + 'synthetic-private-subject-' + str(index)
            response = client.get(path + '?note=synthetic-private-query', headers={
                'X-Forwarded-For': 'synthetic-private-header, 192.0.2.1'})
            assert response.status_code == (422 if mode == 'matched' else 404)
    summary, recent = store.get_summary(), store.get_recent_errors()
    expected = '/probe/{subject}' if mode == 'matched' else '/__unmatched__'
    assert set(summary['endpoints']) == {expected}
    assert summary['total_requests'] == summary['total_errors'] == 4
    assert len(recent) == 4 and all(row['path'] == expected for row in recent)
    assert all('client_ip' not in row for row in recent)
    material = json.dumps({'summary': summary, 'recent': recent,
        'memory': [vars(row) for row in store._recent_requests]})
    assert 'synthetic-private' not in material
    assert '192.0.2.1' not in material and 'testclient' not in material


def test_metrics_never_store_unknown_http_method_or_raw_path(monkeypatch):
    from web.middleware import metrics

    store = metrics.MetricsStore()
    monkeypatch.setattr(metrics, '_metrics_store', store)
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)
    with TestClient(app) as client:
        response = client.request('PRIVATE', '/synthetic-private-subject')
    assert response.status_code == 404
    recent = store.get_recent_errors()
    assert len(recent) == 1
    assert recent[0]['path'] == '/__unmatched__'
    assert recent[0]['method'] == 'OTHER'
    assert 'client_ip' not in recent[0]
