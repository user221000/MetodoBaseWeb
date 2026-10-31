"""Move browser navigation from known aliases to the configured public site.

API calls, callbacks, health checks and local development keep their existing
transport. No incoming hostname can choose the redirect destination.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from web.public_urls import public_origin

CANONICAL_ORIGIN = "https://metodobase.com.mx"
ALIASES = frozenset({"www.metodobase.com.mx", "metodobase.up.railway.app"})
_MACHINE_PATHS = frozenset({"/api", "/static", "/health", "/metrics", "/alerts",
                            "/docs", "/redoc", "/openapi.json", "/.well-known"})
_MACHINE_PREFIXES = ("/api/", "/static/", "/health/", "/metrics/", "/alerts/",
                     "/docs/", "/redoc/", "/.well-known/")


class CanonicalHostMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        from web.settings import get_settings
        settings = get_settings()
        self.origin = public_origin(settings)
        self.enabled = settings.is_production and self.origin == CANONICAL_ORIGIN

    async def dispatch(self, request, call_next):
        path = request.url.path
        if (self.enabled and request.method in {"GET", "HEAD"}
                and request.url.hostname in ALIASES
                and path not in _MACHINE_PATHS and not path.startswith(_MACHINE_PREFIXES)):
            destination = request.url.replace(scheme="https", netloc="metodobase.com.mx")
            return RedirectResponse(str(destination), status_code=307,
                headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        return await call_next(request)
