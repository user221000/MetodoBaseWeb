"""
web/main_web.py — MetodoBase Web App v2 (dark premium fitness theme)
BUILD_VERSION: 2026-04-01-v7-TEMPLATECOMPAT

Uso:
    python web/main_web.py                      # puerto 8001
    python web/main_web.py --port 8000          # puerto 8000
    python web/main_web.py --no-browser         # sin abrir browser
"""
# BUILD MARKER: v7-20260401-2210
import argparse
import hashlib
import inspect
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

# Raíz del proyecto en sys.path para reutilizar core/ src/ api/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from web.template_compat import template_response

from web.middleware import (
    SecurityHeadersMiddleware,
    RequestIDMiddleware,
    CSRFMiddleware,
    TenantMiddleware,
    get_csrf_token,
)

# Directorios locales al módulo web/
_WEB_DIR    = Path(__file__).parent
_STATIC_DIR = _WEB_DIR / "static"
_TMPL_DIR   = _WEB_DIR / "templates"

logger = logging.getLogger("web")

# ── Dependency de autenticación ───────────────────────────────────────────
# Extraídas a web/auth_deps.py para reutilizar en web/routes/ sin circular imports.
from web.auth_deps import get_usuario_actual, get_usuario_gym  # noqa: F401


# ── Sincronización auth → SQLAlchemy ─────────────────────────────────────
# Extracted to web/sync_user.py — single source of truth.
from web.sync_user import sync_user_to_sa as _sync_user_to_sa  # noqa: E402
from web.sync_user import sync_all_auth_users_to_sa as _sync_all_auth_users_to_sa  # noqa: E402


# ── App factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    from contextlib import asynccontextmanager
    import asyncio
    from web.auth import init_auth, cleanup_expired_tokens
    from web.settings import get_settings
    from web.constants import ensure_data_dirs
    
    settings = get_settings()
    from web.storage.runtime import get_object_store
    private_store = get_object_store()
    ensure_data_dirs()
    logger.info(
        "[BOOT] BUILD_VERSION=%s | TemplateResponse signature=%s",
        "2026-04-01-v7-TEMPLATECOMPAT",
        inspect.signature(Jinja2Templates.TemplateResponse),
    )

    # ── Sentry: inicializar antes de crear la app ────────────────────────────
    from web.observability.sentry_setup import init_sentry
    init_sentry(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
    )

    # Schema is prepared by the blocking migration command, never by workers.
    from web.database.engine import get_engine
    from web.database.schema_control import verify_runtime_schema
    from web.database.tenant_policy import verify_application_database_role
    _sa_engine = get_engine()
    verify_runtime_schema(_sa_engine, require_revision=settings.ENV != "testing")
    verify_application_database_role(_sa_engine)

    init_auth()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # PostgreSQL always requires head, including synthetic/staging runtime.
        # Unit SQLite fixtures explicitly prepare their schema through R05.
        verify_runtime_schema(get_engine(), require_revision=settings.ENV != "testing")
        verify_application_database_role(get_engine())

        # Startup: initial token cleanup (graceful if tables don't exist yet)
        try:
            cleaned = cleanup_expired_tokens()
            logger.info("[AUTH] Cleaned %d expired tokens on startup", cleaned)
        except Exception as exc:
            logger.warning("[AUTH] Token cleanup skipped class=%s", type(exc).__name__)
        
        # Periodic cleanup every 6 hours
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(6 * 3600)
                try:
                    count = cleanup_expired_tokens()
                    if count > 0:
                        logger.info("[AUTH] Periodic cleanup: %d tokens removed", count)
                except Exception:
                    logger.error("[AUTH] Cleanup failed")
        
        task = asyncio.create_task(periodic_cleanup())
        yield
        task.cancel()

    from web.constants import VERSION

    app = FastAPI(
        title="MetodoBase Web",
        version=VERSION,
        description="Sistema de Planes Nutricionales — Fitness Dark Theme",
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.private_object_store = private_store

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Security Headers + Compression ───────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # ── CSRF Protection ──────────────────────────────────────────────────────
    # Exento: rutas de API que usan Bearer tokens (verificación automática)
    # Exento: webhooks de Stripe que usan firma en header
    app.add_middleware(
        CSRFMiddleware,
        secret_key=settings.SECRET_KEY,
        exempt_paths=["/api/billing/webhook", "/api/billing/mp/webhook", "/api/auth/"],
        cookie_secure=settings.is_production,
    )

    # ── Tenant Context ────────────────────────────────────────────────────
    app.add_middleware(
        TenantMiddleware,
        exclude_paths=[
            "/health", "/health/ready", "/docs", "/redoc", "/openapi.json",
            "/static/", "/metrics", "/alerts", "/api/auth/",
        ],
    )

    # Rate limiting — usa Redis si REDIS_URL está configurado (distribuido entre workers).
    # Sin Redis: in-memory por proceso (cada worker cuenta independiente → efectivo N×límite).
    from web.settings import get_settings as _rl_cfg
    if _rl_cfg().REDIS_URL:
        from web.rate_limiter_redis import RedisRateLimitMiddleware as _RLM
        logger.info("[RATE_LIMIT] Using Redis-backed rate limiter (distributed)")
    else:
        from web.middleware.rate_limiter import RateLimiterMiddleware as _RLM
        logger.info("[RATE_LIMIT] Using in-memory rate limiter (single-worker safe)")
    app.add_middleware(_RLM)

    # Nota: Sentry Context se setea via dependency (with_sentry_context) después de auth

    # Archivos estáticos de web/
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(_TMPL_DIR))

    # Cache-busting: hash of all static JS/CSS files so browsers reload on changes
    def _compute_static_version() -> str:
        h = hashlib.md5()
        if _STATIC_DIR.exists():
            for f in sorted(_STATIC_DIR.rglob("*")):
                if f.is_file() and f.suffix in (".js", ".css"):
                    h.update(f.read_bytes())
        return h.hexdigest()[:10]

    templates.env.globals["static_version"] = _compute_static_version()

    # Helper para obtener CSRF token en templates
    # Uso: {{ csrf_token(request) }} o en hidden input
    templates.env.globals["csrf_token"] = get_csrf_token

    # CSP nonce is available as request.state.csp_nonce in templates
    # (set by SecurityHeadersMiddleware per-request)

    # ── Reutilizar routers multi-tenant (SA + gym_id isolation) ─────────────
    from web.routes import clientes as web_clientes_router
    from web.routes import planes   as web_planes_router
    from web.routes import stats    as web_stats_router
    from web.routes import billing  as web_billing_router
    from web.routes import gym_profile as web_gym_profile_router
    from web.routes import usuario as web_usuario_router
    from web.routes.team import router as web_team_router, auth_router as web_team_auth_router
    from web.exceptions import MetodoBaseException

    # Sync existing auth users to SA database (fixes FK constraint issue)
    _sync_all_auth_users_to_sa()

    # Todos los endpoints de datos requieren autenticación (RBAC a nivel de route)
    _api_auth = [Depends(get_usuario_actual)]
    app.include_router(web_clientes_router.router, prefix="/api", dependencies=_api_auth)
    app.include_router(web_planes_router.router,   prefix="/api", dependencies=_api_auth)
    app.include_router(web_stats_router.router,    prefix="/api", dependencies=_api_auth)
    from web.routes.followup import router as followup_router
    app.include_router(followup_router, prefix="/api")
    from web.routes import followup_tasks
    app.include_router(followup_tasks.router, prefix="/api")
    app.include_router(web_gym_profile_router.router, prefix="/api", dependencies=_api_auth)

    # Usuario individual routes
    app.include_router(web_usuario_router.router, prefix="/api", dependencies=_api_auth)

    from web.routes.personal_diary import router as personal_diary_router
    app.include_router(personal_diary_router, prefix="/api")
    from web.routes.password_recovery import router as password_recovery_router
    app.include_router(password_recovery_router, prefix="/api")
    from web.routes.mfa import router as mfa_router
    app.include_router(mfa_router, prefix="/api")
    from web.routes.client_links import router as client_links_router
    app.include_router(client_links_router, prefix="/api")

    from web.routes.privacy import router as privacy_router
    app.include_router(privacy_router, prefix="/api")

    # Team management (RBAC) - auth manejada internamente por permissions.py
    app.include_router(web_team_router, prefix="/api")
    app.include_router(web_team_auth_router, prefix="/api")  # /api/auth/accept-invite

    # Billing: webhook NO tiene auth (verificación por firma Stripe)
    app.include_router(web_billing_router.router, prefix="/api")

    # ── Auth routes (login, registro, refresh, logout, me) ───────────────────
    from web.routes.auth import router as web_auth_router
    app.include_router(web_auth_router, prefix="/api")

    # ── HTML page routes ─────────────────────────────────────────────────────
    from web.routes.pages import router as web_pages_router
    # Inject shared template globals (static_version, csrf_token) into pages router
    from web.routes import pages as _pages_mod
    _pages_mod.templates.env.globals["static_version"] = templates.env.globals["static_version"]
    _pages_mod.templates.env.globals["csrf_token"] = get_csrf_token
    app.include_router(web_pages_router)

    # ── Manejadores de errores ────────────────────────────────────────────────
    from starlette.exceptions import HTTPException as StarletteHTTPException

    def _wants_html(request: Request) -> bool:
        accept = request.headers.get("accept", "")
        return "text/html" in accept and "/api/" not in request.url.path

    def _render_error(request: Request, code: int, title: str, message: str):
        return template_response(
            templates,
            request,
            "error.html",
            {"request": request, "code": code, "title": title, "message": message},
            status_code=code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and _wants_html(request):
            return _render_error(request, 404, "Página no encontrada",
                "La página que buscas no existe o ha sido movida.")
        if exc.status_code == 403 and _wants_html(request):
            return _render_error(request, 403, "Acceso denegado",
                "No tienes permiso para acceder a este recurso.")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail or "Error"},
        )

    @app.exception_handler(MetodoBaseException)
    async def _mbe(request: Request, exc: MetodoBaseException):
        error_dict = exc.to_dict()
        # E2: Agregar request_id para correlación con logs
        if hasattr(request.state, "request_id"):
            error_dict["request_id"] = request.state.request_id
        if _wants_html(request):
            return _render_error(request, exc.status_code, "Error",
                error_dict.get("detail", "Ha ocurrido un error inesperado."))
        return JSONResponse(status_code=exc.status_code, content=error_dict)

    @app.exception_handler(Exception)
    async def _generic(request: Request, exc: Exception):
        # SQL exception strings/tracebacks can contain parameters and health data.
        logger.error("Unhandled class=%s", type(exc).__name__)
        if _wants_html(request):
            return _render_error(request, 500, "Error interno",
                "Algo salió mal en el servidor. Si el problema persiste, contáctanos.")
        error_response = {"detail": "Error interno del servidor"}
        # E2: Agregar request_id para correlación
        if hasattr(request.state, "request_id"):
            error_response["request_id"] = request.state.request_id
        return JSONResponse(status_code=500, content=error_response)

    # ── Health check (para Railway, load balancers, uptime monitors) ──────────
    @app.get("/health", tags=["Sistema"], summary="Health check")
    async def health_check():
        """Verifica que el servidor está vivo y la BD accesible."""
        try:
            from sqlalchemy import text
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as e:
            logger.warning("[HEALTH] Database check failed class=%s", type(e).__name__)
            db_ok = False

        status = "healthy" if db_ok else "degraded"
        # Railway healthcheck: retornamos 200 aunque BD falle para que no reinicie el container
        # El status "degraded" indica el problema pero permite que la app siga corriendo
        return JSONResponse(
            status_code=200,
            content={
                "status": status,
                "version": VERSION,
                "database": "ok" if db_ok else "error",
            },
        )

    @app.get("/health/ready", tags=["Sistema"], summary="Readiness check")
    async def readiness_check():
        """Verifica que el servidor está listo para recibir tráfico (BD conectada)."""
        try:
            from sqlalchemy import text
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return JSONResponse(status_code=200, content={"ready": True})
        except Exception as e:
            logger.warning("[HEALTH] Readiness check failed class=%s", type(e).__name__)
            return JSONResponse(status_code=503, content={"ready": False, "error": "database_unavailable"})

    # ── Rutas HTML (páginas) — now served by web/routes/pages.py ────────────

    # Starlette wraps the last registered middleware around earlier ones.
    # Include early rate/CSRF/tenant responses in the same security policy and
    # assign the nonce before any inner middleware or template can use it.
    app.add_middleware(SecurityHeadersMiddleware)
    # Keep correlation around responses created by the private error boundary.
    app.add_middleware(RequestIDMiddleware)
    from web.observability.routes import configure_observability
    from web.routes.personal_progress import router as personal_progress_router
    app.include_router(personal_progress_router, prefix="/api")

    configure_observability(app)
    return app


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # ── Validar env vars críticas antes de arrancar ──────────────────────
    from web.env_validator import validate_env_vars
    try:
        validate_env_vars()
    except SystemExit:
        logger.critical("❌ Environment validation failed. Server cannot start.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="MetodoBase Web App")
    # Railway inyecta PORT; WEB_PORT es nuestro override; --port es CLI
    default_port = int(os.getenv("PORT", os.getenv("WEB_PORT", 8001)))
    default_host = os.getenv("WEB_HOST", "127.0.0.1")
    # En producción/staging/Railway/Docker, siempre 0.0.0.0
    from web.settings import get_settings as _gs2
    if _gs2().is_production or os.getenv("RAILWAY_ENVIRONMENT") or _gs2().ENV == "staging":
        default_host = "0.0.0.0"

    parser.add_argument("--port",       type=int, default=default_port, help="Puerto")
    parser.add_argument("--host",       default=default_host)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload",     action="store_true", help="Hot-reload (solo desarrollo)")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    print(f"\n{'='*52}")
    print(f"  🚀 MetodoBase Web App v2.0  — Dark Premium")
    print(f"  Dashboard : {url}")
    print(f"  API Docs  : {url}/docs")
    print(f"  Host      : {args.host}:{args.port}")
    print(f"{'='*52}\n")

    if not args.no_browser:
        def _open():
            import time; time.sleep(1.8)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    import uvicorn
    if args.reload:
        uvicorn.run("web.main_web:create_app", host=args.host, port=args.port,
                    reload=True, factory=True, reload_dirs=[str(_ROOT)])
    else:
        # Use multiple workers in production for parallelism (plan generation is CPU-bound).
        # Railway has 2+ vCPUs; 4 workers handles ~100 concurrent users comfortably.
        # Override via WEB_WORKERS env var (e.g. WEB_WORKERS=4 on Railway).
        _is_prod = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("WEB_WORKERS"))
        workers = int(os.getenv("WEB_WORKERS", "4" if _is_prod else "1"))
        if workers > 1:
            uvicorn.run(
                "web.main_web:create_app",
                host=args.host,
                port=args.port,
                log_level="info",
                workers=workers,
                factory=True,
            )
        else:
            uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
