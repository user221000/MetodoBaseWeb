"""
web/middleware/tenant.py — Middleware para contexto de tenant en multi-tenancy.

Detecta gym_id del JWT y configura contexto para aislamiento de datos.
RLS activation happens inside get_db() which reads the ContextVar set here.
"""
import logging
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from web.browser_session import HEADERS, admit, browser_request, is_browser_session_private
from web.database.tenant_context import current_tenant

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Context var para tenant actual (usado por RLS en PostgreSQL via get_db())


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Detecta tenant desde JWT y configura contexto.
    
    Flujo:
    1. Extrae gym_id del token JWT (si existe)
    2. Almacena en contextvars (read by get_db() for RLS)
    3. Almacena en request.state para dependencies
    """
    
    def __init__(self, app, exclude_paths: list[str] | None = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health", "/health/ready", "/docs", "/redoc", "/openapi.json",
            "/web/", "/static/", "/metrics"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip para rutas públicas
        path = request.url.path
        # Browser admission must precede even the optional Bearer lookup. The
        # API and SaaS have different public exclusions; neither may perform
        # authentication I/O for a rejected cookie-transport request.
        if browser_request(request) and is_browser_session_private(path):
            try:
                admit(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code,
                                    headers={**(error.headers or {}), **HEADERS})
        excluded = any(path.startswith(item) for item in self.exclude_paths)
        tenant_id = None if excluded else await self._extract_tenant(request)
        token = current_tenant.set(tenant_id or "")
        request.state.tenant_id = tenant_id
        try:
            return await call_next(request)
        finally:
            current_tenant.reset(token)
    
    async def _extract_tenant(self, request: Request) -> str | None:
        """Extrae tenant_id del JWT token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        try:
            from web.auth import verificar_token
            token = auth_header[7:]
            payload = verificar_token(token)
            if payload:
                # A professional member retains an independent personal space.
                if request.url.path.startswith("/api/usuario/"):
                    return payload.get("id")
                # Persisted association takes precedence over historical tipo.
                return payload.get("team_gym_id") or payload.get("id")
        except Exception as e:
            logger.debug("Tenant principal unavailable class=%s", type(e).__name__)
        
        return None


def get_current_tenant() -> str:
    """Obtiene el tenant actual del contexto."""
    return current_tenant.get()
