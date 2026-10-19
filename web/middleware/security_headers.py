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
from starlette.responses import Response

import secrets

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
            "img-src": "'self' data: https:",
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
        
        response = await call_next(request)
        
        # ─── HSTS ───────────────────────────────────────────────────────────
        if self.hsts_enabled:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # ─── CSP (with per-request nonce) ────────────────────────────────────
        if self.csp_enabled:
            response.headers["Content-Security-Policy"] = self._build_csp_header(nonce)
        
        # ─── Otros headers de seguridad ─────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        # Private downloads/invitations may require the stricter policy. Do not
        # weaken it globally, or preserve arbitrary policies such as unsafe-url.
        response.headers["Referrer-Policy"] = (
            "no-referrer" if response.headers.get("Referrer-Policy", "").strip().lower() == "no-referrer"
            else "strict-origin-when-cross-origin"
        )
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), usb=()"
        )
        
        # ─── Cache control para APIs ────────────────────────────────────────
        if request.url.path.startswith("/api/"):
            # APIs no deben cachearse por defecto
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "no-store, max-age=0"
        elif request.url.path.startswith("/static/"):
            # Static assets use cache-busting via ?v= query param
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        
        return response
