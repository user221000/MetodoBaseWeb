"""Independent route-label and identity-retention regression checks, synthetic only."""

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from fastapi.testclient import TestClient
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.routing import Route

from web.middleware import metrics

PRIVATE = "independent-private-marker"


@pytest.fixture
def store(monkeypatch):
    value = metrics.MetricsStore()
    monkeypatch.setattr(metrics, "_metrics_store", value)
    return value


def material(store):
    return json.dumps(
        {
            "summary": store.get_summary(),
            "errors": store.get_recent_errors(100),
            "memory": [vars(x) for x in store._recent_requests],
            "alerts": store.check_alerts(),
        },
        sort_keys=True,
    )


def no_identity(store):
    text = material(store)
    for value in [
        PRIVATE,
        "192.0.2.88",
        "2001:db8::88",
        "testclient",
        "authorization",
        "client_ip",
        "refresh_token",
    ]:
        assert value not in text


def test_path_converter_and_response_body_never_enter_history_or_alerts(store):
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    @app.post("/records/{tail:path}")
    async def endpoint(tail: str):
        return JSONResponse({"note": PRIVATE}, status_code=422)

    with TestClient(app) as client:
        for tail in ["a", PRIVATE + "@example.test", PRIVATE + "/nested/44"]:
            response = client.post(
                "/records/" + tail + "?refresh_token=" + PRIVATE,
                headers={
                    "X-Forwarded-For": "192.0.2.88, " + PRIVATE,
                    "Forwarded": 'for="[2001:db8::88]"',
                    "Authorization": "Bearer " + PRIVATE,
                    "Cookie": "subject=" + PRIVATE,
                },
                json={"health_note": PRIVATE},
            )
            assert response.status_code == 422
    assert set(store.get_summary()["endpoints"]) == {"/records/{tail}"}
    assert store.get_summary()["total_requests"] == 3
    no_identity(store)


@pytest.mark.parametrize("status", [200, 302, 422, 500])
def test_success_redirect_validation_and_error_keep_declared_route(store, status):
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    @app.get("/operation/{subject}")
    async def endpoint(subject: str):
        return Response(status_code=status, headers={"Location": "/" + PRIVATE})

    with TestClient(app, follow_redirects=False) as client:
        assert client.get("/operation/" + PRIVATE).status_code == status
    summary = store.get_summary()
    assert set(summary["endpoints"]) == {"/operation/{subject}"}
    assert summary["total_requests"] == 1
    assert summary["total_errors"] == int(status >= 400)
    no_identity(store)


def test_method_not_allowed_partial_match_preserves_template_not_subject(store):
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    @app.get("/partial/{subject}")
    async def endpoint(subject: str):
        return {}

    with TestClient(app) as client:
        assert client.post("/partial/" + PRIVATE).status_code == 405
    assert set(store.get_summary()["endpoints"]) == {"/partial/{subject}"}
    no_identity(store)


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        SimpleNamespace(path="/" + PRIVATE, path_format="/" + PRIVATE),
        {"path": "/" + PRIVATE},
    ],
)
def test_no_trusted_router_metadata_uses_one_fixed_fallback(store, metadata):
    async def inner(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if metadata is not None:
            scope["route"] = metadata
        await JSONResponse({"note": PRIVATE}, status_code=409)(scope, receive, send)

    app = metrics.MetricsMiddleware(inner, enabled=True)
    with TestClient(app) as client:
        for suffix in ["one", "two"]:
            assert (
                client.request(
                    "PRIVATE",
                    "/" + PRIVATE + "/" + suffix,
                    headers={"X-Forwarded-For": PRIVATE},
                ).status_code
                == 409
            )
    summary = store.get_summary()
    assert set(summary["endpoints"]) == {"/__unmatched__"}
    assert summary["total_requests"] == 2
    assert {x["method"] for x in store.get_recent_errors()} == {"OTHER"}
    no_identity(store)


@pytest.mark.anyio
async def test_middleware_does_not_read_forwarded_headers_or_client_property(store):
    class GuardHeaders(Headers):
        def get(self, key, default=None):
            if key.lower() in {
                "x-forwarded-for",
                "forwarded",
                "authorization",
                "cookie",
            }:
                raise AssertionError("Identity header was read")
            return super().get(key, default)

    class GuardRequest(Request):
        @property
        def headers(self):
            return GuardHeaders(raw=self.scope["headers"])

        @property
        def client(self):
            raise AssertionError("Connection identity was read")

    async def endpoint(request):
        return Response(status_code=400)

    route = Route("/guard/{subject}", endpoint=endpoint)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "scheme": "http",
        "server": ("testserver", 80),
        "root_path": "",
        "path": "/guard/" + PRIVATE,
        "raw_path": ("/guard/" + PRIVATE).encode(),
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "route": route,
    }
    middleware = metrics.MetricsMiddleware(endpoint, enabled=True)

    async def call_next(request):
        return Response(status_code=400)

    response = await middleware.dispatch(GuardRequest(scope), call_next)
    assert response.status_code == 400
    assert set(store.get_summary()["endpoints"]) == {"/guard/{subject}"}
    no_identity(store)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("disabled", [False, True])
def test_disabled_or_explicitly_excluded_path_retains_nothing(store, disabled):
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=not disabled)

    @app.get("/health/{subject}")
    async def endpoint(subject: str):
        return Response(status_code=500)

    with TestClient(app) as client:
        response = client.get(("/" + PRIVATE) if disabled else ("/health/" + PRIVATE))
    assert "x-response-time" not in response.headers
    assert store.get_summary()["total_requests"] == 0
    assert not store._recent_requests
    assert not store._recent_errors


def test_declared_methods_retained_unknown_methods_collapsed_and_no_body_or_header_identity(
    store,
):
    methods = [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS",
        "TRACE",
        "CONNECT",
    ]
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    async def endpoint(subject: str):
        return Response(status_code=409)

    app.add_api_route("/verbs/{subject}", endpoint, methods=methods + ["PRIVATE"])
    with TestClient(app) as client:
        for method in methods + ["PRIVATE"]:
            assert (
                client.request(
                    method,
                    "/verbs/" + PRIVATE,
                    content=PRIVATE,
                    headers={"X-Forwarded-For": "2001:db8::88"},
                ).status_code
                == 409
            )
    assert {x.method for x in store._recent_requests} == set(methods) | {"OTHER"}
    assert set(store.get_summary()["endpoints"]) == {"/verbs/{subject}"}
    no_identity(store)


def test_existing_history_bounds_and_alerts_retain_counts_without_subjects(monkeypatch):
    monkeypatch.setattr(metrics, "METRICS_HISTORY_SIZE", 5)
    store = metrics.MetricsStore()
    monkeypatch.setattr(metrics, "_metrics_store", store)
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    @app.get("/bounded/{subject}")
    async def endpoint(subject: str):
        return Response(status_code=503)

    with TestClient(app) as client:
        for i in range(111):
            assert client.get("/bounded/" + PRIVATE + "-" + str(i)).status_code == 503
    assert len(store._recent_requests) == 5
    assert len(store._recent_errors) == 100
    assert len(store._endpoints["/bounded/{subject}"].latencies) == 5
    assert (
        store.get_summary()["total_requests"]
        == store.get_summary()["total_errors"]
        == 111
    )
    assert any(x["type"] == "endpoint_errors" for x in store.check_alerts())
    no_identity(store)


def test_unhandled_exception_without_response_is_explicitly_outside_metrics_claim(
    store,
):
    app = FastAPI()
    app.add_middleware(metrics.MetricsMiddleware, enabled=True)

    @app.get("/raises/{subject}")
    async def endpoint(subject: str):
        raise RuntimeError(PRIVATE)

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/raises/" + PRIVATE).status_code == 500
    assert store.get_summary()["total_requests"] == 0
    assert not store._recent_requests
