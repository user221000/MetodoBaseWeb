"""Canonical navigation never changes API authority, callbacks or local access."""
import hashlib
from types import SimpleNamespace
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from web.browser_session import BrowserAuthRoute
from web.middleware.canonical_host import CanonicalHostMiddleware
from web.middleware.security_headers import SecurityHeadersMiddleware

CANONICAL = "https://metodobase.com.mx"


@pytest.fixture(scope="module")
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture
def build(monkeypatch):
    def create(*, base=CANONICAL, production=True):
        from web import settings
        monkeypatch.setattr(settings, "get_settings", lambda: SimpleNamespace(
            BASE_URL=base, is_production=production))
        app, calls = FastAPI(docs_url=None, redoc_url=None, openapi_url=None), []
        router = APIRouter(route_class=BrowserAuthRoute)

        @router.post("/api/auth/google/verify-email")
        async def verification():
            calls.append({"path": "/api/auth/google/verify-email"})
            return JSONResponse({"code": "synthetic_code_invalid"}, status_code=400)

        app.include_router(router)

        @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
        async def destination(request: Request):
            record = {"method": request.method, "path": request.url.path,
                "body_sha256": hashlib.sha256(await request.body()).hexdigest(),
                "signature": request.headers.get("Stripe-Signature")}
            calls.append(record)
            return record

        # Match the factory order: security headers wrap canonical redirects.
        app.add_middleware(CanonicalHostMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(app, follow_redirects=False), calls

    return create


@pytest.mark.parametrize("host", ["www.metodobase.com.mx", "metodobase.up.railway.app"])
@pytest.mark.parametrize("scheme", ["http", "https"])
@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_known_alias_navigation_reaches_only_https_apex_and_keeps_url(build, host, scheme, method):
    client, calls = build()
    query = "tipo=gym&next=https%3A%2F%2Fattacker.invalid%2F"
    with client:
        response = client.request(method, f"{scheme}://{host}:8443/registro?{query}")
    assert response.status_code == 307
    target = urlsplit(response.headers["location"])
    assert (target.scheme, target.netloc, target.path, target.query) == (
        "https", "metodobase.com.mx", "/registro", query)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "content-security-policy" in response.headers
    assert "set-cookie" not in response.headers
    assert calls == []


@pytest.mark.parametrize("path", [
    "/api", "/api/auth/google", "/api/billing/webhook", "/api/billing/mp/webhook",
    "/static", "/static/img/logo.png", "/health", "/health/ready",
    "/metrics", "/alerts", "/docs", "/redoc", "/openapi.json",
    "/.well-known/acme-challenge/synthetic",
])
def test_machine_get_paths_are_not_canonicalized(build, path):
    client, calls = build()
    with client:
        response = client.get("https://www.metodobase.com.mx" + path)
    assert response.status_code == 200 and "location" not in response.headers
    assert len(calls) == 1 and calls[0]["path"] == path


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def test_non_navigation_methods_and_webhook_body_are_preserved(build, method):
    client, calls = build()
    raw, signature = b'{"id":"synthetic-event","value":"unchanged"}', "t=123,v1=synthetic"
    with client:
        response = client.request(method, "https://metodobase.up.railway.app/api/billing/webhook",
            content=raw, headers={"Content-Type": "application/json", "Stripe-Signature": signature})
    assert response.status_code == 200 and "location" not in response.headers
    assert calls == [{"method": method, "path": "/api/billing/webhook",
        "body_sha256": hashlib.sha256(raw).hexdigest(), "signature": signature}]


@pytest.mark.parametrize("host", [
    "metodobase.com.mx", "attacker.invalid", "www.metodobase.com.mx.attacker.invalid", "localhost:8000",
])
def test_other_hosts_and_forwarded_headers_cannot_choose_or_loop_redirects(build, host):
    client, calls = build()
    with client:
        response = client.get("http://" + host + "/registro", headers={
            "X-Forwarded-Host": "www.metodobase.com.mx", "X-Forwarded-Proto": "https"})
    assert response.status_code == 200 and "location" not in response.headers
    assert len(calls) == 1


@pytest.mark.parametrize("base,production", [
    ("http://localhost:8000", False), (CANONICAL, False),
    ("https://metodobase.up.railway.app", True),
])
def test_preparation_and_local_configuration_do_not_activate_domain_cutover(build, base, production):
    client, calls = build(base=base, production=production)
    with client:
        response = client.get("https://www.metodobase.com.mx/registro")
    assert response.status_code == 200 and "location" not in response.headers
    assert len(calls) == 1


@pytest.mark.parametrize("path", ["//attacker.invalid/escape", "/%2Fattacker.invalid/escape"])
def test_path_cannot_replace_the_fixed_redirect_authority(build, path):
    client, calls = build()
    with client:
        response = client.get("https://www.metodobase.com.mx" + path)
    assert response.status_code == 307
    target = urlsplit(response.headers["location"])
    assert target.scheme == "https" and target.netloc == "metodobase.com.mx"
    assert target.username is None and target.password is None
    assert calls == []


@pytest.mark.parametrize("origin,status,count", [
    (CANONICAL, 400, 1), ("https://www.metodobase.com.mx", 403, 0),
    ("https://metodobase.up.railway.app", 403, 0),
])
def test_api_keeps_exact_browser_origin_admission_instead_of_redirecting(build, origin, status, count):
    client, calls = build()
    with client:
        response = client.post("https://metodobase.up.railway.app/api/auth/google/verify-email", json={},
            headers={"Origin": origin, "X-MetodoBase-Browser": "1"})
    assert response.status_code == status and "location" not in response.headers
    assert len(calls) == count
    assert "token" not in response.json() and "refresh_token" not in response.json()
