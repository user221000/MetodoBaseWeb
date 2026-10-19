"""Observable middleware behavior when the Redis boundary is unavailable."""
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


def _client(monkeypatch, path):
    from web import rate_limiter_redis as module
    app = FastAPI()
    app.add_middleware(module.RedisRateLimitMiddleware)
    calls = []

    @app.api_route(path, methods=["GET", "POST"])
    def endpoint():
        calls.append(True)
        return {"synthetic": True}

    unavailable = AsyncMock(side_effect=ConnectionError("synthetic secret must not be logged"))
    monkeypatch.setattr(module, "_is_allowed_redis", unavailable)
    return TestClient(app), calls, unavailable


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/refresh", "/api/auth/accept-invite",
    "/api/generar-plan", "/api/usuario/generar-plan", "/api/usuario/checkout", "/api/billing/checkout",
    "/api/pagos/stripe/session", "/api/pagos/mp/preference", "/api/billing/portal",
    "/api/usuario/billing-portal", "/api/gym/team/invite"])
def test_redis_failure_rejects_sensitive_work_without_calling_route(monkeypatch, path, caplog):
    client, calls, _ = _client(monkeypatch, path)
    with client:
        response = client.post(path)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "rate_limit_backend_unavailable"
    assert response.headers["Retry-After"] == "5"
    assert not calls
    assert "synthetic secret" not in caplog.text


def test_redis_failure_keeps_read_requests_bounded(monkeypatch):
    from web import rate_limiter, rate_limiter_redis
    with rate_limiter._lock:
        rate_limiter._buckets.clear()
    client, calls, _ = _client(monkeypatch, "/api/clients-read-synthetic")
    monkeypatch.setattr(rate_limiter_redis, "_match_rule", lambda _: {"path_prefix": "/api/", "limit": 2, "window": 60})
    with client:
        statuses = [client.get("/api/clients-read-synthetic").status_code for _ in range(3)]
    assert statuses == [200, 200, 429]
    assert len(calls) == 2


def test_health_does_not_depend_on_redis(monkeypatch):
    client, calls, unavailable = _client(monkeypatch, "/health/ready")
    with client:
        assert client.get("/health/ready").status_code == 200
    unavailable.assert_not_awaited()
    assert len(calls) == 1


def _dependency_client(monkeypatch, redis_url="", account_field=None):
    from fastapi import Depends
    from types import SimpleNamespace
    from web.middleware import rate_limiter as dependency_module
    from web import rate_limiter
    monkeypatch.setattr(dependency_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(
        REDIS_URL=redis_url, SECRET_KEY="synthetic-only-rate-key", TRUSTED_PROXY_COUNT=0))
    with rate_limiter._lock:
        rate_limiter._buckets.clear()
    app = FastAPI()
    options = {"account_field": account_field} if account_field else {}
    dependency = dependency_module.rate_limit_dependency(5, 900, **options)

    @app.post("/synthetic-login", dependencies=[Depends(dependency)])
    def login():
        return {"ok": True}

    return TestClient(app)


def test_dependency_honors_five_requests_per_fifteen_minutes(monkeypatch):
    from web import rate_limiter
    clock = [1000.0]
    monkeypatch.setattr(rate_limiter.time, "monotonic", lambda: clock[0])
    with _dependency_client(monkeypatch) as client:
        assert [client.post("/synthetic-login").status_code for _ in range(6)] == [200] * 5 + [429]
        clock[0] += 301
        rate_limiter._cleanup_expired(force=True)
        assert client.post("/synthetic-login").status_code == 429
        clock[0] += 600
        assert client.post("/synthetic-login").status_code == 200


def test_dependency_redis_outage_rejects_instead_of_using_private_memory(monkeypatch):
    from web import rate_limiter_redis
    unavailable = AsyncMock(side_effect=ConnectionError("synthetic redis credential"))
    monkeypatch.setattr(rate_limiter_redis, "_is_allowed_redis", unavailable)
    with _dependency_client(monkeypatch, redis_url="redis://synthetic-unused") as client:
        response = client.post("/synthetic-login")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "rate_limit_backend_unavailable"
    assert "credential" not in response.text
    unavailable.assert_awaited_once()


def test_account_limit_uses_opaque_normalized_key_across_ips(monkeypatch):
    from web import rate_limiter_redis
    counts, seen = {}, []

    async def shared_counter(key, limit, window):
        seen.append(key)
        counts[key] = counts.get(key, 0) + 1
        return counts[key] <= limit, {"remaining": max(0, limit - counts[key]), "retry_after": 900}

    monkeypatch.setattr(rate_limiter_redis, "_is_allowed_redis", shared_counter)
    with _dependency_client(monkeypatch, redis_url="redis://synthetic-unused", account_field="email") as client:
        for attempt in range(5):
            # Distinct IP keys cannot bypass the same account key.
            monkeypatch.setattr("web.middleware.rate_limiter.get_client_identifier", lambda request, n=attempt: f"192.0.2.{n}")
            assert client.post("/synthetic-login", json={"email": "  Persona@Example.invalid  "}).status_code == 200
        monkeypatch.setattr("web.middleware.rate_limiter.get_client_identifier", lambda request: "192.0.2.99")
        assert client.post("/synthetic-login", json={"email": "persona@example.invalid"}).status_code == 429
    assert all("persona" not in key.lower() and "example" not in key.lower() for key in seen)
    assert len({key for key in seen if ":account:" in key}) == 1


def test_proxy_count_zero_ignores_untrusted_forwarded_headers(monkeypatch):
    from types import SimpleNamespace
    from starlette.requests import Request
    from web.rate_limiter import _get_client_ip
    from web.middleware.rate_limiter import get_client_identifier
    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(TRUSTED_PROXY_COUNT=0))
    request = Request({"type": "http", "headers": [(b"x-forwarded-for", b"192.0.2.55"),
        (b"x-real-ip", b"192.0.2.66")], "client": ("192.0.2.1", 1234)})
    assert _get_client_ip(request) == "192.0.2.1"
    assert get_client_identifier(request) == "192.0.2.1"


@pytest.mark.parametrize("count,header,expected", [
    (1, "192.0.2.55, 192.0.2.1", "192.0.2.1"),
    (2, "192.0.2.55, 192.0.2.1, 192.0.2.2", "192.0.2.1"),
    (2, "192.0.2.55", "192.0.2.10"),
    (1, "invalid", "192.0.2.10"),
])
def test_proxy_chain_selects_last_untrusted_hop(monkeypatch, count, header, expected):
    from types import SimpleNamespace
    from starlette.requests import Request
    from web.rate_limiter import _get_client_ip
    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(TRUSTED_PROXY_COUNT=count))
    request = Request({"type": "http", "headers": [(b"x-forwarded-for", header.encode())],
        "client": ("192.0.2.10", 1234)})
    assert _get_client_ip(request) == expected


def test_local_middleware_store_caps_memory_and_reclaims_idle_buckets(monkeypatch):
    from web.middleware import rate_limiter
    clock = [1000.0]
    monkeypatch.setattr(rate_limiter.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(rate_limiter, "MAX_LOCAL_BUCKETS", 2)
    store = rate_limiter.RateLimiterStore(60, 1)
    assert store.is_allowed("one")[0]
    assert store.is_allowed("two")[0]
    assert not store.is_allowed("three")[0]
    assert len(store._buckets) == 2
    clock[0] += 301
    assert store.is_allowed("three")[0]
    assert len(store._buckets) == 1
