"""Independent review of actual payment endpoint names under Redis outage."""
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.mark.parametrize("path", [
    "/api/billing/stripe/subscribe",
    "/api/billing/confirm-subscription",
    "/api/billing/mp/preference",
    "/api/billing/portal",
    "/api/usuario/billing-portal",
])
def test_actual_b2b_payment_routes_fail_closed_before_side_effect(monkeypatch, path):
    from web import rate_limiter_redis as limiter

    app = FastAPI()
    app.add_middleware(limiter.RedisRateLimitMiddleware)
    calls = []

    @app.post(path)
    async def payment_endpoint():
        calls.append(True)
        return {"side_effect": "synthetic-provider-call"}

    monkeypatch.setattr(limiter, "_is_allowed_redis",
        AsyncMock(side_effect=ConnectionError("synthetic unavailable boundary")))
    with TestClient(app) as client:
        response = client.post(path)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "rate_limit_backend_unavailable"
    assert not calls


def test_standalone_factory_selects_redis_without_local_constructor_options(monkeypatch):
    from copy import copy
    from config import settings as config_settings
    from web import settings as web_settings
    from web import rate_limiter_redis as limiter
    from api.app import create_app

    config = copy(config_settings.get_settings())
    web = copy(web_settings.get_settings())
    config.REDIS_URL = web.REDIS_URL = "redis://127.0.0.1:56379/15"
    monkeypatch.setattr(config_settings, "get_settings", lambda: config)
    monkeypatch.setattr(web_settings, "get_settings", lambda: web)
    unavailable = AsyncMock(side_effect=ConnectionError("synthetic unavailable boundary"))
    monkeypatch.setattr(limiter, "_is_allowed_redis", unavailable)
    with TestClient(create_app()) as client:
        assert client.get("/health/ready").status_code == 200
        response = client.post("/api/billing/stripe/subscribe", json={})
        assert response.status_code == 503
        assert response.headers["X-RateLimit-Backend"] == "unavailable"
    unavailable.assert_awaited_once()
