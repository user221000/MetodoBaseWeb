"""The real middleware's outer-error boundary, without sockets or fake routes."""
import asyncio

import pytest
from starlette.requests import Request
from starlette.responses import Response

from web.middleware.security_headers import SecurityHeadersMiddleware


@pytest.mark.parametrize("path", ["/api/analytics/producto", "/api/analytics/producto/"])
def test_outer_failure_is_generic_private_and_does_not_trust_downstream_csp(path):
    class Application:
        def __init__(self):
            self.exception_handlers = {}
    request = Request({"type": "http", "method": "GET", "path": path, "headers": [],
                       "scheme": "http", "server": ("testserver", 80), "query_string": b"", "app": Application()})
    async def failed(_request):
        raise RuntimeError("SYNTHETIC_PRIVATE_SQL_DETAIL")
    middleware = SecurityHeadersMiddleware(None)
    response = asyncio.run(middleware.dispatch(request, failed))
    assert response.status_code == 500
    assert b"SYNTHETIC_PRIVATE_SQL_DETAIL" not in response.body
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    async def arbitrary(_request):
        return Response(headers={"Content-Security-Policy": "default-src https://untrusted.invalid", "Referrer-Policy": "unsafe-url"})
    response = asyncio.run(middleware.dispatch(request, arbitrary))
    assert "untrusted.invalid" not in response.headers["content-security-policy"]
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("path", ["/api/analytics/producto-old", "/api/analytics/producto/detail", "/cuenta/google"])
def test_analytics_does_not_capture_neighbour_or_existing_gis_exception_boundaries(path):
    request = Request({"type": "http", "method": "GET", "path": path, "headers": [],
                       "scheme": "http", "server": ("testserver", 80), "query_string": b""})
    async def existing(_request):
        return Response()
    response = asyncio.run(SecurityHeadersMiddleware(None).dispatch(request, existing))
    assert "https://accounts.google.com" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == (
        "no-referrer" if path == "/cuenta/google" else "strict-origin-when-cross-origin")
