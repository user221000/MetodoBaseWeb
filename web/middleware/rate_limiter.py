"""
web/middleware/rate_limiter.py — Rate limiting para protección contra abuso.

Implementa un rate limiter basado en token bucket con almacenamiento en memoria.
Para producción con múltiples instancias, usar Redis.

Uso:
    from web.middleware import RateLimiterMiddleware, RateLimitExceeded
    
    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_minute=60,
        burst_size=10,
    )
    
    # O por ruta específica con dependencias:
    from web.middleware.rate_limiter import rate_limit_dependency
    
    @app.get("/api/expensive", dependencies=[Depends(rate_limit_dependency(10, 60))])
    async def expensive_endpoint():
        ...

Configuración via ENV:
    RATE_LIMIT_REQUESTS_PER_MINUTE=60
    RATE_LIMIT_BURST_SIZE=10
    RATE_LIMIT_ENABLED=true
"""

import os
import time
import logging
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Callable, Optional
from threading import Lock

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)
MAX_LOCAL_BUCKETS = 10000


# ── Configuración ────────────────────────────────────────────────────────────

try:
    from web.settings import get_settings as _get_settings
    _is_production = _get_settings().is_production
except Exception:
    _is_production = os.getenv("METODOBASE_ENV", "development") == "production"
_env_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

if _is_production and not _env_enabled:
    logger.warning(
        "RATE_LIMIT_ENABLED=false ignorado en producción – forzando activación"
    )

RATE_LIMIT_ENABLED: bool = True if _is_production else _env_enabled

# Development: generous limits for parallel API calls
# Production: stricter limits for DDoS protection
if _is_production:
    DEFAULT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "300"))
    DEFAULT_BURST_SIZE = int(os.getenv("RATE_LIMIT_BURST_SIZE", "50"))
else:
    DEFAULT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "1000"))
    DEFAULT_BURST_SIZE = int(os.getenv("RATE_LIMIT_BURST_SIZE", "200"))


# ── Excepciones ──────────────────────────────────────────────────────────────

class RateLimitExceeded(HTTPException):
    """Excepción cuando se excede el rate limit."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Demasiadas solicitudes. Por favor, espera antes de intentar de nuevo.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


# ── Token Bucket ─────────────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    """
    Implementación de token bucket para rate limiting.
    
    - capacity: máximo de tokens (burst size)
    - refill_rate: tokens por segundo
    - tokens: tokens actuales
    - last_refill: timestamp del último refill
    """
    capacity: int
    refill_rate: float
    tokens: float = field(default=None)
    last_refill: float = field(default_factory=time.monotonic)
    
    def __post_init__(self):
        if self.tokens is None:
            self.tokens = self.capacity
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Intenta consumir tokens.
        
        Returns:
            True si se pudieron consumir, False si no hay suficientes.
        """
        now = time.monotonic()
        
        # Refill tokens basado en tiempo transcurrido
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calcula segundos hasta que haya tokens disponibles."""
        if self.tokens >= tokens:
            return 0
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


# ── Rate Limiter Store ───────────────────────────────────────────────────────

class RateLimiterStore:
    """
    Almacén de buckets por cliente.
    
    En producción con múltiples instancias, reemplazar con Redis:
        import redis
        r = redis.Redis()
        # Usar MULTI/EXEC para operaciones atómicas
    """
    
    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        burst_size: int = DEFAULT_BURST_SIZE,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        if requests_per_minute < 1 or burst_size < 1:
            raise ValueError("Rate and burst must be positive")
        self.refill_rate = requests_per_minute / 60.0  # tokens por segundo
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300  # 5 minutos
    
    def _create_bucket(self) -> TokenBucket:
        """Crea un nuevo bucket con configuración default."""
        return TokenBucket(
            capacity=self.burst_size,
            refill_rate=self.refill_rate,
            last_refill=time.monotonic(),
        )
    
    def _cleanup_old_buckets(self, *, force: bool = False):
        """Reclaim fully refillable idle buckets; caller must hold the lock."""
        now = time.monotonic()
        if not force and now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        inactive = [key for key, bucket in self._buckets.items()
            if now - bucket.last_refill > max(60, bucket.capacity / bucket.refill_rate)]
        for key in inactive:
            del self._buckets[key]
    
    def is_allowed(self, client_id: str) -> tuple[bool, float]:
        """
        Verifica si el cliente puede hacer una solicitud.
        
        Returns:
            (allowed, retry_after_seconds)
        """
        with self._lock:
            self._cleanup_old_buckets()
            bucket = self._buckets.get(client_id)
            if bucket is None:
                if len(self._buckets) >= MAX_LOCAL_BUCKETS:
                    self._cleanup_old_buckets(force=True)
                if len(self._buckets) >= MAX_LOCAL_BUCKETS:
                    return False, 60
                bucket = self._buckets[client_id] = self._create_bucket()
            if bucket.consume():
                return True, 0
            return False, bucket.time_until_available()


# ── Singleton Store ──────────────────────────────────────────────────────────

_store: Optional[RateLimiterStore] = None


def get_rate_limiter_store(
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
    burst_size: int = DEFAULT_BURST_SIZE,
) -> RateLimiterStore:
    """Obtiene el store singleton."""
    global _store
    if _store is None:
        _store = RateLimiterStore(requests_per_minute, burst_size)
    return _store


# ── Identificación de Cliente ────────────────────────────────────────────────

def get_client_identifier(request: Request) -> str:
    """Use the same configured proxy contract as the global middleware."""
    from web.rate_limiter import _get_client_ip
    return _get_client_ip(request)


# ── Middleware ───────────────────────────────────────────────────────────────

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting para FastAPI.
    
    Aplica rate limiting global a todas las rutas excepto las excluidas.
    
    Args:
        app: Aplicación FastAPI
        requests_per_minute: Solicitudes permitidas por minuto
        burst_size: Solicitudes extra permitidas en ráfagas
        exclude_paths: Rutas a excluir (ej: ["/health", "/docs"])
        enabled: Si el rate limiting está activo
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        burst_size: int = DEFAULT_BURST_SIZE,
        exclude_paths: Optional[list[str]] = None,
        enabled: bool = RATE_LIMIT_ENABLED,
    ):
        super().__init__(app)
        self.store = get_rate_limiter_store(requests_per_minute, burst_size)
        self.exclude_paths = exclude_paths or ["/health", "/health/ready", "/docs", "/redoc", "/openapi.json"]
        self.enabled = enabled
        
        logger.info(
            f"RateLimiter inicializado: {requests_per_minute}/min, "
            f"burst={burst_size}, enabled={enabled}"
        )
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Procesa cada request aplicando rate limiting."""
        # Skip si está deshabilitado
        if not self.enabled:
            return await call_next(request)
        
        # Skip rutas excluidas
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Identificar cliente
        client_id = get_client_identifier(request)
        
        # Verificar rate limit
        allowed, retry_after = self.store.is_allowed(client_id)
        
        if not allowed:
            retry_seconds = int(retry_after) + 1
            logger.warning("rate_limit_exceeded backend=local")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Demasiadas solicitudes. Por favor, espera antes de intentar de nuevo.",
                    "retry_after": retry_seconds,
                },
                headers={
                    "Retry-After": str(retry_seconds),
                    "X-RateLimit-Limit": str(self.store.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )
        
        # Continuar con la request
        response = await call_next(request)
        
        # Agregar headers informativos
        response.headers["X-RateLimit-Limit"] = str(self.store.requests_per_minute)
        # Note: remaining es aproximado porque no tenemos lock durante response
        
        return response


# ── Dependency para rutas específicas ────────────────────────────────────────

def rate_limit_dependency(
    requests_per_minute: int = 10,
    window_seconds: int = 60,
    *,
    account_field: Optional[str] = None,
):
    """Limit attempts per route/IP and optionally normalized JSON account.

    The historical argument name ``requests_per_minute`` is retained for
    callers, but means maximum requests in ``window_seconds``. Redis shares
    counters across workers; its failure returns 503 before sensitive work.
    With no Redis configured, the bounded store is explicitly process-local.
    Account keys use keyed HMAC; raw emails are never stored in Redis/logs.
    This is an abuse control, not proof that the account exists.
    """
    if requests_per_minute < 1 or window_seconds < 1:
        raise ValueError("Rate limit and window must be positive")
    
    async def dependency(request: Request):
        if not RATE_LIMIT_ENABLED:
            return
        
        from web.settings import get_settings
        from web.rate_limiter_redis import check_rate_limit
        settings = get_settings()
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        prefix = f"rl:dependency:{route_path}:{requests_per_minute}:{window_seconds}"
        keys = [f"{prefix}:ip:{get_client_identifier(request)}"]
        if account_field:
            try:
                body = await request.json()
            except ValueError:
                body = None  # The endpoint's DTO still rejects malformed JSON.
            account = body.get(account_field) if isinstance(body, dict) else None
            if isinstance(account, str) and account.strip():
                normalized = account.strip().casefold()
                digest = hmac.new(settings.SECRET_KEY.encode("utf-8"),
                    ("rate-limit-account-v1:" + normalized).encode("utf-8"),
                    hashlib.sha256).hexdigest()
                keys.append(f"{prefix}:account:{digest}")
        for key in keys:
            allowed, info, _ = await check_rate_limit(key, requests_per_minute,
                window_seconds, use_redis=bool(settings.REDIS_URL), sensitive=True)
            if not allowed:
                raise RateLimitExceeded(retry_after=info["retry_after"])
    
    return dependency


# ── Métricas ─────────────────────────────────────────────────────────────────

def get_rate_limiter_metrics() -> dict:
    """
    Obtiene métricas del rate limiter.
    
    Útil para dashboards y alertas.
    """
    store = get_rate_limiter_store()
    
    with store._lock:
        active_buckets = len(store._buckets)
        total_tokens = sum(b.tokens for b in store._buckets.values())
    
    return {
        "active_clients": active_buckets,
        "requests_per_minute_limit": store.requests_per_minute,
        "burst_size": store.burst_size,
        "total_available_tokens": total_tokens,
        "enabled": RATE_LIMIT_ENABLED,
    }
