"""
web/rate_limiter_redis.py — Redis-backed rate limiting middleware.

Drop-in replacement for the in-memory RateLimitMiddleware when REDIS_URL is set.
Uses redis.asyncio and an atomic Lua fixed-window counter.

Key format: rl:{client_ip}:{path_prefix}
TTL: window_seconds (auto-expires keys)
"""
import logging
from threading import Lock

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from web.rate_limiter import RATE_RULES, _get_client_ip, _match_rule, _is_allowed

logger = logging.getLogger(__name__)

_redis_pool = None
_health_lock = Lock()
_health = {"state": "unobserved", "failures": 0, "recoveries": 0,
    "rejected_sensitive": 0, "local_fallback_requests": 0}

# INCR and TTL initialization are one atomic server operation. Subsequent
# requests do not extend the window, including rejected requests.
_FIXED_WINDOW_LUA = """
local count = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if count == 1 or ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end
return {count, ttl}
"""


def get_rate_limit_status() -> dict:
    """Return process-local outage counters without IPs, paths or secrets."""
    with _health_lock:
        from web.settings import get_settings
        return {"backend": "redis" if get_settings().REDIS_URL else "local",
            "counter_scope": "process", **_health}


def _note_failure(error: Exception) -> None:
    with _health_lock:
        transitioned = _health["state"] != "degraded"
        _health["state"] = "degraded"
        _health["failures"] += 1
    if transitioned:
        logger.warning("rate_limit_backend_unavailable backend=redis class=%s", type(error).__name__)


def _note_recovery() -> None:
    with _health_lock:
        transitioned = _health["state"] == "degraded"
        if transitioned:
            _health["recoveries"] += 1
        _health["state"] = "available"
    if transitioned:
        logger.info("rate_limit_backend_recovered backend=redis")


def _sensitive_path(path: str) -> bool:
    """Keep authentication and costly/financial writes closed during outage."""
    if path.startswith("/api/auth/") and path not in {"/api/auth/logout", "/api/auth/me"}:
        return True
    return path.startswith(("/api/generar-plan", "/api/usuario/generar-plan",
        "/api/usuario/checkout", "/api/usuario/stripe-", "/api/usuario/confirm-subscription",
        "/api/usuario/mp-preference", "/api/usuario/billing-portal",
        "/api/billing/checkout", "/api/billing/stripe/subscribe",
        "/api/billing/confirm-subscription", "/api/billing/mp/preference",
        "/api/billing/portal", "/api/pagos/stripe/session", "/api/pagos/mp/preference",
        "/api/gym/team/invite"))


async def _get_redis():
    """Lazy-init Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        import redis.asyncio as aioredis
        from web.settings import get_settings
        url = getattr(get_settings(), "REDIS_URL", "")
        if not url:
            raise RuntimeError("REDIS_URL not configured")
        _redis_pool = aioredis.from_url(url, decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1, max_connections=100)
    return _redis_pool


async def _is_allowed_redis(key: str, limit: int, window: int) -> tuple[bool, dict]:
    """Atomically count a fixed window without extending TTL on each request."""
    r = await _get_redis()
    current, ttl = await r.eval(_FIXED_WINDOW_LUA, 1, key, window)
    current, ttl = int(current), int(ttl)

    if current > limit:
        retry_after = max(ttl, 1)
        return False, {"remaining": 0, "retry_after": retry_after}

    remaining = limit - current
    return True, {"remaining": remaining, "retry_after": 0}


async def check_rate_limit(key: str, limit: int, window: int, *,
        use_redis: bool, sensitive: bool) -> tuple[bool, dict, str]:
    """Check one bucket; sensitive work fails closed on Redis uncertainty.

    Local mode is bounded but process-scoped. During a Redis outage only
    nonsensitive traffic can use that fallback. No identity is logged.
    """
    if not use_redis:
        allowed, info = _is_allowed(key, limit, window)
        return allowed, info, "local"
    try:
        allowed, info = await _is_allowed_redis(key, limit, window)
        _note_recovery()
        return allowed, info, "redis"
    except Exception as error:
        _note_failure(error)
        if sensitive:
            with _health_lock:
                _health["rejected_sensitive"] += 1
            raise HTTPException(status_code=503, detail={
                "code": "rate_limit_backend_unavailable",
                "message": "No podemos verificar el límite de esta acción. Intenta de nuevo en unos segundos.",
            }, headers={"Retry-After": "5", "X-RateLimit-Backend": "unavailable"}) from None
        allowed, info = _is_allowed("fallback:" + key, limit, window)
        with _health_lock:
            _health["local_fallback_requests"] += 1
        return allowed, info, "local-degraded"


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware backed by Redis for multi-pod deployments."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        rule = _match_rule(path)

        limit = rule.get("limit", 0)
        if limit == 0:
            return await call_next(request)

        window = rule.get("window", 60)
        client_ip = _get_client_ip(request)
        bucket_key = f"rl:{client_ip}:{rule['path_prefix']}"

        try:
            allowed, info, backend = await check_rate_limit(bucket_key, limit, window,
                use_redis=True, sensitive=_sensitive_path(path))
        except HTTPException as error:
            return JSONResponse(status_code=error.status_code,
                content={"detail": error.detail}, headers=error.headers)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Demasiadas solicitudes. Intenta de nuevo más tarde.",
                    "retry_after": info["retry_after"],
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Backend": backend,
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Backend"] = backend
        return response
