"""
web/middleware/csrf.py — CSRF Protection Middleware

Protección contra Cross-Site Request Forgery para la aplicación web.
Genera tokens firmados con HMAC y valida en métodos mutantes (POST/PUT/DELETE/PATCH).

Uso:
    from web.middleware.csrf import CSRFMiddleware, get_csrf_token
    
    app.add_middleware(CSRFMiddleware, secret_key="...", exempt_paths=["/api/"])
    
En templates Jinja2:
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    
En JavaScript:
    fetch(url, {
        headers: { "X-CSRF-Token": document.querySelector('meta[name=csrf-token]').content }
    })
"""
import hashlib
import hmac
import os
import secrets
import time
from typing import Callable, Optional, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# ── Constantes ────────────────────────────────────────────────────────────

CSRF_TOKEN_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "_csrf"
TOKEN_EXPIRY_SECONDS = 3600  # 1 hora (hardened for payment flows)


# ── Funciones de Token ────────────────────────────────────────────────────

def _generate_token_raw() -> str:
    """Genera un token aleatorio de 32 bytes en hex."""
    return secrets.token_hex(32)


def _sign_token(token: str, secret_key: str, timestamp: int) -> str:
    """
    Firma un token con HMAC-SHA256.
    
    Formato: timestamp.token.signature
    """
    message = f"{timestamp}.{token}".encode()
    signature = hmac.new(
        secret_key.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return f"{timestamp}.{token}.{signature}"


def _verify_token(signed_token: str, secret_key: str, max_age: int = TOKEN_EXPIRY_SECONDS) -> bool:
    """
    Verifica un token firmado.
    
    Returns:
        True si el token es válido y no ha expirado.
    """
    if not signed_token:
        return False
    
    parts = signed_token.split(".")
    if len(parts) != 3:
        return False
    
    timestamp_str, token, signature = parts
    
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False
    
    # Verificar expiración
    if time.time() - timestamp > max_age:
        return False
    
    # Verificar firma
    message = f"{timestamp}.{token}".encode()
    expected_signature = hmac.new(
        secret_key.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Comparación constante para evitar timing attacks
    return hmac.compare_digest(signature, expected_signature)


def generate_csrf_token(secret_key: str) -> str:
    """
    Genera un nuevo token CSRF firmado.
    
    Args:
        secret_key: Clave secreta para firmar el token.
        
    Returns:
        Token firmado listo para usar en forms/headers.
    """
    token = _generate_token_raw()
    timestamp = int(time.time())
    return _sign_token(token, secret_key, timestamp)


def verify_csrf_token(token: str, secret_key: str) -> bool:
    """
    Verifica un token CSRF.
    
    Args:
        token: Token firmado a verificar.
        secret_key: Clave secreta usada para firmar.
        
    Returns:
        True si el token es válido.
    """
    return _verify_token(token, secret_key)


# ── Middleware ────────────────────────────────────────────────────────────

class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware de protección CSRF para FastAPI/Starlette.
    
    Características:
    - Genera tokens firmados con HMAC-SHA256
    - Verifica en métodos POST, PUT, DELETE, PATCH
    - Acepta token en header X-CSRF-Token o form field csrf_token
    - Permite eximir rutas específicas (ej: APIs con bearer token)
    - Inyecta token en request.state para uso en templates
    
    Args:
        app: Aplicación ASGI.
        secret_key: Clave secreta para firmar tokens (requerido).
        exempt_paths: Lista de prefijos de path a eximir (ej: ["/api/"]).
        exempt_methods: Métodos HTTP a eximir (default: GET, HEAD, OPTIONS).
        cookie_secure: Si la cookie debe ser Secure (default: True en prod).
        cookie_samesite: Valor de SameSite (default: "strict").
    """
    
    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
    
    def __init__(
        self,
        app,
        secret_key: str,
        exempt_paths: Optional[Sequence[str]] = None,
        exempt_methods: Optional[Sequence[str]] = None,
        cookie_secure: bool = True,
        cookie_samesite: str = "strict",
        exact_exempt_paths: Optional[Sequence[str]] = None,
    ):
        super().__init__(app)
        
        if not secret_key or len(secret_key) < 32:
            raise ValueError("CSRF secret_key debe tener al menos 32 caracteres")
        
        self.secret_key = secret_key
        self.exempt_paths = tuple(exempt_paths or [])
        self.exact_exempt_paths = frozenset(exact_exempt_paths or [])
        self.exempt_methods = frozenset(exempt_methods or self.SAFE_METHODS)
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
    
    def _is_exempt(self, request: Request) -> bool:
        """Determina si la request está exenta de verificación CSRF."""
        # Métodos seguros siempre exentos
        if request.method in self.exempt_methods:
            return True
        
        # Rutas exentas
        path = request.url.path
        if path in self.exact_exempt_paths:
            return True
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        # Requests con Authorization header (API con token) exentas
        if request.headers.get("Authorization", "").startswith("Bearer "):
            return True
        
        return False
    
    def _get_submitted_token(self, request: Request, form_data: dict) -> Optional[str]:
        """Obtiene el token CSRF enviado en la request."""
        # Primero intentar header
        token = request.headers.get(CSRF_HEADER_NAME)
        if token:
            return token
        
        # Luego form field
        token = form_data.get(CSRF_TOKEN_NAME)
        if token:
            return token
        
        return None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Procesa la request, verificando CSRF si es necesario."""
        
        # Generar o recuperar token para esta sesión
        csrf_token = generate_csrf_token(self.secret_key)
        request.state.csrf_token = csrf_token
        
        # Si está exento, pasar directamente
        if self._is_exempt(request):
            response = await call_next(request)
            # Añadir cookie con token para requests futuras
            self._set_csrf_cookie(response, csrf_token)
            return response
        
        # Verificar token en métodos mutantes
        form_data = {}
        content_type = request.headers.get("content-type", "")
        
        # Solo parsear form si es form-urlencoded o multipart
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            try:
                form_data = dict(await request.form())
            except Exception:
                pass
        
        submitted_token = self._get_submitted_token(request, form_data)
        
        if not submitted_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"}
            )
        
        if not verify_csrf_token(submitted_token, self.secret_key):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token invalid or expired"}
            )
        
        # Token válido, continuar
        response = await call_next(request)
        self._set_csrf_cookie(response, csrf_token)
        return response
    
    def _set_csrf_cookie(self, response: Response, token: str) -> None:
        """Establece la cookie CSRF en la response."""
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=token,
            max_age=TOKEN_EXPIRY_SECONDS,
            httponly=True,  # Prevent JS access — token provided via meta tag instead
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
        )


# ── Helper para Templates ─────────────────────────────────────────────────

def get_csrf_token(request: Request) -> str:
    """
    Obtiene el token CSRF de la request actual.
    
    Para usar en dependency injection de FastAPI o en context de templates.
    
    Ejemplo en ruta:
        @app.get("/form")
        def show_form(request: Request, csrf: str = Depends(get_csrf_token)):
            return templates.TemplateResponse("form.html", {"csrf_token": csrf})
    """
    return getattr(request.state, "csrf_token", "")


def csrf_input_html(request: Request) -> str:
    """
    Genera el HTML del input hidden para CSRF.
    
    Ejemplo en template Jinja2:
        {{ csrf_input | safe }}
    """
    token = get_csrf_token(request)
    return f'<input type="hidden" name="{CSRF_TOKEN_NAME}" value="{token}">'
