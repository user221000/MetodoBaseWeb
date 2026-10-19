"""FastAPI application factory para MetodoBase."""
import os
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.exceptions import MetodoBaseException
from web.middleware import (
    SecurityHeadersMiddleware,
    RequestIDMiddleware,
    CSRFMiddleware,
    RateLimiterMiddleware,
    MetricsMiddleware,
    TenantMiddleware,
    get_metrics_summary,
    check_metrics_alerts,
    track_error,
    get_error_alerter,
)
from api.routes import clientes as clientes_routes
from api.routes import stats as stats_routes
from api.routes import planes as planes_routes
from api.routes import licencias as licencias_routes
from api.routes import pagos as pagos_routes
from web.routes import pages as web_pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

_BASE_DIR = Path(__file__).parent.parent
_STATIC_DIR = _BASE_DIR / "static"
_WEB_STATIC_DIR = _BASE_DIR / "web" / "static"


def create_app() -> FastAPI:
    # Docs deshabilitados en producción salvo override explícito
    from config.settings import get_settings
    _s = get_settings()
    _docs = "/docs" if _s.DOCS_ENABLED else None
    _redoc = "/redoc" if _s.DOCS_ENABLED else None
    from web.storage.runtime import get_object_store
    private_store = get_object_store()

    # ── Sentry: inicializar antes de crear la app ────────────────────────────
    if _s:
        from web.observability.sentry_setup import init_sentry
        init_sentry(
            dsn=_s.SENTRY_DSN,
            environment=_s.SENTRY_ENVIRONMENT,
            traces_rate=_s.SENTRY_TRACES_SAMPLE_RATE,
            profiles_rate=_s.SENTRY_PROFILES_SAMPLE_RATE,
        )

    # ── Auth: inicializar antes de cualquier endpoint que use tokens ────────
    from web.database.engine import get_engine
    from web.database.schema_control import verify_runtime_schema
    from web.database.tenant_policy import verify_application_database_role
    verify_runtime_schema(get_engine(), require_revision=not (_s and _s.ENV == "testing"))
    verify_application_database_role(get_engine())
    from web.auth import init_auth
    init_auth()

    # ── DB: inicializar engine + session factory ──────────────────────────────

    from config.constantes import VERSION

    app = FastAPI(
        title="MetodoBase API",
        description="API para gestión de planes nutricionales en gimnasios",
        version=VERSION,
        docs_url=_docs,
        redoc_url=_redoc,
    )
    app.state.private_object_store = private_store

    # ── CORS ─────────────────────────────────────────────────────────────────
    try:
        from config.settings import get_settings
        _settings = get_settings()
        allowed = _settings.CORS_ORIGINS
    except Exception:
        allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:8001").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Security Headers ─────────────────────────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # ── CSRF Protection ────────────────────────────────────────────────────
    try:
        _secret = _settings.SECRET_KEY if _s else "dev-csrf-key"
    except Exception:
        _secret = "dev-csrf-key"
    app.add_middleware(
        CSRFMiddleware,
        secret_key=_secret,
        exempt_paths=["/api/"],
        cookie_secure=_s.is_production if _s else False,
    )

    # ── Rate Limiting ────────────────────────────────────────────────────────
    _rl_cls = RateLimiterMiddleware
    if _s and _s.REDIS_URL:
        try:
            from web.rate_limiter_redis import RedisRateLimitMiddleware
            _rl_cls = RedisRateLimitMiddleware
        except ImportError:
            pass
    if _s and _s.REDIS_URL and _rl_cls is not RateLimiterMiddleware:
        # Redis uses the same path rules as SaaS; the local middleware's
        # constructor options are not accepted by BaseHTTPMiddleware.
        app.add_middleware(_rl_cls)
    else:
        app.add_middleware(
            _rl_cls,
            requests_per_minute=60,
            burst_size=10,
            exclude_paths=["/health", "/health/ready", "/health/circuits", "/docs", "/redoc", "/openapi.json", "/static/"],
        )
    
    # ── Metrics ──────────────────────────────────────────────────────────────
    app.add_middleware(
        MetricsMiddleware,
        exclude_paths=["/metrics", "/health", "/health/ready"],
    )
    
    # ── Tenant Context ───────────────────────────────────────────────────────
    app.add_middleware(
        TenantMiddleware,
        exclude_paths=[
            "/health", "/health/ready", "/docs", "/redoc", "/openapi.json",
            "/static/", "/metrics", "/alerts",
            "/api/auth/password-reset/",
        ],
    )

    # Nota: Sentry Context se setea via dependency (with_sentry_context) después de auth

    # ── Global error handlers ─────────────────────────────────────────────────
    @app.exception_handler(MetodoBaseException)
    async def _metodobase_error(request: Request, exc: MetodoBaseException):
        logging.getLogger("api").warning(
            "MetodoBaseException [%s]: %s", exc.error_code, exc.message
        )
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def _global_error(request: Request, exc: Exception):
        logging.getLogger("api").error("Unhandled class=%s", type(exc).__name__)
        # Track error for alerting
        # Raw paths can contain subject IDs; automatic alerts need no client IP.
        track_error(exc, extra_context={"method": request.method})
        request_id = getattr(request.state, "request_id", None)
        headers = {"X-Request-ID": request_id} if request_id else {}
        body: dict = {"detail": "Error interno del servidor"}
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(status_code=500, content=body, headers=headers)

    # ── Health Check ──────────────────────────────────────────────────────────
    _health_logger = logging.getLogger("api.health")

    @app.get("/health", tags=["System"])
    async def health_check():
        """
        Health check endpoint para monitoreo.
        Verifica: BD, versión. No expone detalles internos.
        """
        from datetime import datetime, timezone
        from sqlalchemy import text
        
        is_healthy = True
        checks = {}
        
        # Check BD SQLAlchemy
        try:
            from web.database.engine import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = {"status": "ok"}
        except Exception:
            from config.settings import get_settings as _gs
            _health_logger.error("Health check DB failed", exc_info=_gs().DEBUG)
            checks["database"] = {"status": "error"}
            is_healthy = False
        
        checks["version"] = VERSION
        
        status_str = "healthy" if is_healthy else "degraded"
        http_code = 200 if is_healthy else 503
        
        return JSONResponse(
            status_code=http_code,
            content={
                "status": status_str,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            },
        )
    
    @app.get("/health/ready", tags=["System"])
    async def readiness_check():
        """Readiness probe para Kubernetes/Railway."""
        from sqlalchemy import text
        try:
            from web.database.engine import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"ready": True}
        except Exception:
            return JSONResponse(status_code=503, content={"ready": False})

    # ── Metrics (protected by API key) ────────────────────────────────────────
    from fastapi import Depends
    import hmac as _hmac
    
    _METRICS_API_KEY = os.getenv("METRICS_API_KEY", "")
    
    async def _verify_metrics_key(request: Request):
        """Verifica API key para endpoints de métricas/alertas."""
        key = request.headers.get("X-Metrics-Key", "")
        if not key or not _METRICS_API_KEY or not _hmac.compare_digest(key, _METRICS_API_KEY):
            raise HTTPException(status_code=403, detail="Forbidden")
    
    @app.get("/metrics", tags=["System"], dependencies=[Depends(_verify_metrics_key)])
    async def metrics_endpoint():
        """
        Métricas de latencia y rendimiento. Requiere X-Metrics-Key header.
        """
        summary = get_metrics_summary()
        summary["alerts"] = check_metrics_alerts()
        return summary
    
    @app.get("/alerts", tags=["System"], dependencies=[Depends(_verify_metrics_key)])
    async def alerts_endpoint():
        """
        Estado del sistema de alertas. Requiere X-Metrics-Key header.
        """
        alerter = get_error_alerter()
        return {
            "status": alerter.get_status(),
            "metrics_alerts": check_metrics_alerts(),
            "recent_alerts": alerter.get_alert_history(limit=10),
        }

    @app.get("/health/circuits", tags=["System"], dependencies=[Depends(_verify_metrics_key)])
    async def circuit_status():
        """
        Estado de los circuit breakers. Requiere X-Metrics-Key header.
        """
        from web.services.resilience import get_all_circuit_status
        return {"circuits": get_all_circuit_status()}

    # ── Static files ──────────────────────────────────────────────────────────
    # Prefer web/static for the web app assets; fallback to root static if present.
    static_dir = _WEB_STATIC_DIR if _WEB_STATIC_DIR.exists() else _STATIC_DIR
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ── API routes ────────────────────────────────────────────────────────────
    app.include_router(clientes_routes.router, prefix="/api")
    app.include_router(stats_routes.router, prefix="/api")
    app.include_router(planes_routes.router, prefix="/api")
    app.include_router(licencias_routes.router, prefix="/api")
    app.include_router(pagos_routes.router, prefix="/api")

    # ── Gym profile + food catalog (used by clientes page) ────────────────────
    from web.routes import gym_profile as gym_profile_routes
    app.include_router(gym_profile_routes.router, prefix="/api")

    # ── Billing routes (subscription, config, payments) ───────────────────────
    from web.routes import billing as billing_routes
    app.include_router(billing_routes.router, prefix="/api")
    
    # ── Auth routes (login, registro, refresh, logout, me) ────────────────────
    from web.routes.auth import router as web_auth_router
    app.include_router(web_auth_router, prefix="/api")

    from web.routes.privacy import router as privacy_router
    app.include_router(privacy_router, prefix="/api")

    from web.routes.personal_diary import router as personal_diary_router
    app.include_router(personal_diary_router, prefix="/api")
    from web.routes.password_recovery import router as password_recovery_router
    app.include_router(password_recovery_router, prefix="/api")
    from web.routes.client_links import router as client_links_router
    app.include_router(client_links_router, prefix="/api")

    # Share only the reviewed personal history GET and its canonical dependencies.
    from web.routes.usuario import historial_planes
    app.add_api_route("/api/usuario/historial", historial_planes, methods=["GET"], tags=["Usuario Individual"])

    # ── Planes history routes (web) ───────────────────────────────────────────
    from web.routes import planes as web_planes_routes
    app.include_router(web_planes_routes.router, prefix="/api")

    # ── Web page routes ───────────────────────────────────────────────────────
    app.include_router(web_pages.router)

    return app
