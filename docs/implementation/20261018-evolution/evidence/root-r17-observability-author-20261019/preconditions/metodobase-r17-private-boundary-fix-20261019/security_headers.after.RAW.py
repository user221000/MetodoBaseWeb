"""
web/middleware/security_headers.py — Security headers middleware.

Agrega headers de seguridad estándar a todas las respuestas:
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy

Uso:
    from web.middleware import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from web.client_link_paths import is_member_link_private

import inspect
import logging
import secrets

# Primary authentication errors can occur before the successful response helper.
# Match only the mounted APIs; login pages retain their existing GIS policy.
_PRIMARY_API_PATHS = frozenset({"/api/auth/login", "/api/auth/google"})

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega headers de seguridad a todas las respuestas.
    
    Configuración por defecto es segura para producción.
    Puede personalizarse via constructor.
    """
    
    def __init__(
        self,
        app,
        hsts_enabled: bool = True,
        hsts_max_age: int = 31536000,  # 1 año
        hsts_include_subdomains: bool = True,
        csp_enabled: bool = True,
        frame_ancestors: str = "'self'",
        extra_csp_directives: dict | None = None,
    ):
        super().__init__(app)
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.csp_enabled = csp_enabled
        self.frame_ancestors = frame_ancestors
        self.extra_csp = extra_csp_directives or {}
        
        # Pre-build CSP base directives (nonce added per-request)
        self._csp_base_directives = self._build_csp_directives()
    
    def _build_csp_directives(self) -> dict:
        """Builds the base CSP directives dict (without nonce)."""
        directives = {
            "default-src": "'self'",
            "script-src": "'self' https://cdn.jsdelivr.net https://js.stripe.com https://accounts.google.com/gsi/client",
            "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com/gsi/style",
            "font-src": "'self' https://fonts.gstatic.com data:",
            "img-src": "'self' data: https: blob:",
            "connect-src": "'self' https://api.stripe.com https://m.stripe.network https://r.stripe.com https://accounts.google.com https://oauth2.googleapis.com",
            "frame-src": "'self' https://js.stripe.com https://hooks.stripe.com https://accounts.google.com",
            "frame-ancestors": self.frame_ancestors,
            "form-action": "'self'",
            "base-uri": "'self'",
            "object-src": "'none'",
            "upgrade-insecure-requests": "",
        }
        directives.update(self.extra_csp)
        return directives

    def _build_csp_header(self, nonce: str) -> str:
        """Builds the full CSP header value with the per-request nonce."""
        directives = dict(self._csp_base_directives)
        # Inject nonce into script-src and style-src
        directives["script-src"] = f"'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://js.stripe.com https://accounts.google.com/gsi/client"
        directives["style-src"] = f"'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com/gsi/style"
        
        parts = []
        for key, value in directives.items():
            if value:
                parts.append(f"{key} {value}")
            else:
                parts.append(key)
        return "; ".join(parts)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate unique nonce per request for CSP
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        diary_api = (
            request.url.path == "/api/usuario/diario"
            or request.url.path.startswith("/api/usuario/diario/")
        )
        primary_api = request.url.path in _PRIMARY_API_PATHS
        operations = request.url.path in {"/metrics", "/alerts", "/health/circuits"}
        
        try:
            response = await call_next(request)
        except Exception as error:
            if (request.url.path != "/api/usuario/historial"
                    and not is_member_link_private(request.url.path)
                    and not diary_api
                    and not request.url.path.startswith("/api/auth/mfa/")
                    and not primary_api
                    and not operations):
                raise
            # Generic handlers live outside response middleware. Reuse the
            # factory's existing public error body, then apply private headers.
            try:
                handler = request.app.exception_handlers.get(Exception)
                if handler is None:
                    raise LookupError('No generic handler')
                result = handler(request, error)
                response = await result if inspect.isawaitable(result) else result
                if not isinstance(response, Response) or response.status_code != 500:
                    raise ValueError('Invalid generic error response')
            except Exception:
                logging.getLogger(__name__).error("Private request failed class=%s", type(error).__name__)
                body = {"detail": "Error interno del servidor"}
                if getattr(request.state, "request_id", None):
                    body["request_id"] = request.state.request_id
                response = JSONResponse(body, status_code=500)
            response.headers["Cache-Control"] = "no-store"
        
        # ─── HSTS ───────────────────────────────────────────────────────────
        if self.hsts_enabled:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # ─── CSP (with per-request nonce) ────────────────────────────────────
        if self.csp_enabled:
            if request.url.path in {"/auth/reset-password", "/auth/accept-client-link"} or request.url.path.startswith("/api/auth/mfa/"):
                # Fixed first-party policy for the public recovery form. Never
                # accept an arbitrary policy supplied by a downstream handler.
                response.headers["Content-Security-Policy"] = (
                    "default-src 'none'; "
                    f"script-src 'self' 'nonce-{nonce}'; "
                    "style-src 'self'; connect-src 'self'; form-action 'self'; "
                    "frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
                )
            else:
                response.headers["Content-Security-Policy"] = self._build_csp_header(nonce)
        
        # ─── Otros headers de seguridad ─────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        # Private downloads/invitations may require the stricter policy. Do not
        # weaken it globally, or preserve arbitrary policies such as unsafe-url.
        recovery_api = request.url.path in {
            "/api/auth/password-reset/request", "/api/auth/password-reset/confirm",
        }
        response.headers["Referrer-Policy"] = (
            "no-referrer" if (
                recovery_api
                or diary_api
                or primary_api
                or operations
                or request.url.path.startswith("/api/auth/mfa/")
                or request.url.path == "/api/usuario/historial"
                or is_member_link_private(request.url.path)
                or response.headers.get("Referrer-Policy", "").strip().lower() == "no-referrer"
            )
            else "strict-origin-when-cross-origin"
        )
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), usb=()"
        )
        if operations or primary_api or is_member_link_private(request.url.path) or diary_api or request.url.path.startswith("/api/auth/mfa/"):
            response.headers["Cache-Control"] = "no-store"
        
        if operations:
            response.headers["Pragma"] = "no-cache"
        
        # ─── Cache control para APIs ────────────────────────────────────────
        if request.url.path.startswith("/api/"):
            # APIs no deben cachearse por defecto
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "no-store, max-age=0"
        elif request.url.path.startswith("/static/"):
            # Static assets use cache-busting via ?v= query param
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        
        return response
