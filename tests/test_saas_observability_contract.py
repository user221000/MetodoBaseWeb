"""Real factory mounting, private operations routes and safe failure metrics."""

import importlib
import json

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest


FACTORIES = ["web.main_web", "api.app"]
ENDPOINTS = ["/metrics", "/alerts", "/health/circuits"]


@pytest.fixture
def observed_app(request, monkeypatch):
    monkeypatch.setenv("METRICS_ENABLED", "true")
    from web.middleware import metrics

    store = metrics.MetricsStore()
    monkeypatch.setattr(metrics, "_metrics_store", store)
    monkeypatch.setenv("METRICS_API_KEY", "synthetic-operations-key")
    module = importlib.import_module(request.param)
    # Provider delivery is outside this contract; an exception still propagates
    # through the actual generic handler and MetricsMiddleware.
    if hasattr(module, "track_error"):
        monkeypatch.setattr(module, "track_error", lambda *a, **k: None)
    return module.create_app(), store


@pytest.mark.parametrize("observed_app", FACTORIES, indirect=True)
def test_both_factories_record_declared_labels_without_request_values(observed_app):
    app, store = observed_app

    @app.get("/operations-probe/{subject}")
    async def probe(subject: str):
        return JSONResponse({"ok": False}, status_code=422)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/operations-probe/synthetic-private-person?note=synthetic-private-query",
            headers={
                "X-Forwarded-For": "synthetic-private-address",
                "X-Metrics-Key": "synthetic-operations-key",
            },
        )
    assert response.status_code == 422
    summary = store.get_summary()
    assert summary["total_requests"] == summary["total_errors"] == 1
    assert set(summary["endpoints"]) == {"/operations-probe/{subject}"}
    material = json.dumps(
        {"summary": summary, "memory": [vars(r) for r in store._recent_requests]}
    )
    assert "synthetic-private" not in material
    assert "synthetic-operations-key" not in material


@pytest.mark.parametrize("observed_app", FACTORIES, indirect=True)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("key", ["", "wrong-key"])
def test_operations_endpoints_deny_missing_or_wrong_keys(observed_app, endpoint, key):
    app, _ = observed_app
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(endpoint, headers={"X-Metrics-Key": key})
    assert response.status_code == 403
    assert response.headers.get("cache-control") == "no-store"
    assert "synthetic-operations-key" not in response.text


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_operations_endpoints_remain_closed_without_configured_key(
    factory, endpoint, monkeypatch
):
    monkeypatch.delenv("METRICS_API_KEY", raising=False)
    app = importlib.import_module(factory).create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            endpoint, headers={"X-Metrics-Key": "synthetic-operations-key"}
        )
    assert response.status_code == 403


@pytest.mark.parametrize("observed_app", FACTORIES, indirect=True)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_operations_success_is_private_and_not_cached(observed_app, endpoint):
    app, _ = observed_app
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            endpoint, headers={"X-Metrics-Key": "synthetic-operations-key"}
        )
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"
    assert isinstance(response.json(), dict)
    assert "synthetic-operations-key" not in response.text


@pytest.mark.parametrize("observed_app", FACTORIES, indirect=True)
def test_unhandled_exceptions_record_only_500_and_declared_route(observed_app):
    app, store = observed_app

    @app.get("/operations-failure/{subject}")
    async def fail(subject: str):
        raise RuntimeError("synthetic-private-error-detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/operations-failure/synthetic-private-person?secret=synthetic-private-query"
        )
    assert response.status_code == 500
    assert "synthetic-private-error-detail" not in response.text
    summary = store.get_summary()
    assert summary["total_requests"] == summary["total_errors"] == 1
    assert set(summary["endpoints"]) == {"/operations-failure/{subject}"}
    material = json.dumps(
        {"summary": summary, "memory": [vars(r) for r in store._recent_requests]}
    )
    assert "synthetic-private" not in material


@pytest.mark.parametrize("observed_app", FACTORIES, indirect=True)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_nonascii_key_is_a_denial_without_server_error(observed_app, endpoint):
    app, _ = observed_app
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(endpoint, headers={b"X-Metrics-Key": b"\xff\xfe"})
    assert response.status_code == 403
