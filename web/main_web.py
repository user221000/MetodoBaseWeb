"""
web/main_web.py — MetodoBase Web App v2 (dark premium fitness theme)

Uso:
    python web/main_web.py                      # puerto 8001
    python web/main_web.py --port 8000          # puerto 8000
    python web/main_web.py --no-browser         # sin abrir browser
"""
import argparse
import hashlib
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

def _migrate_subscription_constraints(engine) -> None:
    """Recreate subscriptions table if CHECK constraint uses old plan names (SQLite only)."""
    import sqlalchemy
    # Only applies to SQLite — Postgres uses Alembic migrations
    if "sqlite" not in str(engine.url):
        return
    with engine.connect() as conn:
        row = conn.execute(sqlalchemy.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='subscriptions'"
        )).scalar()
        if not row or "'starter'" not in row:
            return  # already up-to-date or table doesn't exist
        logger.warning("[MIGRATION] Updating subscriptions CHECK constraint (old plan names)")
        conn.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS subscriptions_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                gym_id VARCHAR(36) NOT NULL,
                "plan" VARCHAR(30) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                stripe_customer_id VARCHAR(255),
                stripe_subscription_id VARCHAR(255) UNIQUE,
                current_period_start DATETIME,
                current_period_end DATETIME,
                cancel_at_period_end BOOLEAN DEFAULT 0,
                max_clientes INTEGER NOT NULL DEFAULT 10,
                created_at DATETIME,
                updated_at DATETIME,
                trial_start DATETIME,
                trial_end DATETIME,
                canceled_at DATETIME,
                stripe_price_id VARCHAR(255),
                ended_at DATETIME,
                CONSTRAINT ck_subscription_plan CHECK (plan IN ('free', 'standard', 'gym_comercial', 'clinica')),
                CONSTRAINT ck_subscription_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete', 'incomplete_expired', 'paused')),
                FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
                UNIQUE (gym_id)
            )
        """))
        conn.execute(sqlalchemy.text("INSERT INTO subscriptions_new SELECT * FROM subscriptions"))
        conn.execute(sqlalchemy.text("DROP TABLE subscriptions"))
        conn.execute(sqlalchemy.text("ALTER TABLE subscriptions_new RENAME TO subscriptions"))
        conn.execute(sqlalchemy.text("CREATE INDEX IF NOT EXISTS ix_subscriptions_gym_id ON subscriptions (gym_id)"))
        conn.execute(sqlalchemy.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_subscriptions_stripe_sub ON subscriptions (stripe_subscription_id)"))
        conn.commit()
        logger.info("[MIGRATION] subscriptions CHECK constraint updated successfully")


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager
    import asyncio
    from web.auth import init_auth, cleanup_expired_tokens
    from web.settings import get_settings
    from web.constants import ensure_data_dirs
    
    # Crear directorios de datos (lazy, no en import)
    ensure_data_dirs()
    
    settings = get_settings()

    # ── Sentry: inicializar antes de crear la app ────────────────────────────
    from web.observability.sentry_setup import init_sentry
    init_sentry(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
    )

    # Inicializar base de datos SA BEFORE auth (auth needs tables to exist)
    # NOTE: create_all() is handled by db_bootstrap.py (Railway releaseCommand)
    # Running it here too as safety net for non-Railway environments
    from web.database.engine import init_db, get_engine
    from web.database.models import Base
    init_db()
    _sa_engine = get_engine()
    try:
        Base.metadata.create_all(bind=_sa_engine)
    except Exception as exc:
        logger.warning("[DB] create_all() issue (non-fatal if tables exist): %s", exc)

    init_auth()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Check alembic migration version in production
        if settings.ENV == "production" and not settings.SKIP_MIGRATION_CHECK:
            try:
                from alembic.config import Config as AlembicConfig
                from alembic.script import ScriptDirectory
                from web.database.engine import get_engine
                from sqlalchemy import text, inspect as sa_inspect
                engine = get_engine()
                with engine.connect() as conn:
                    inspector = sa_inspect(engine)
                    if "alembic_version" in inspector.get_table_names():
                        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                        current = row[0] if row else None
                        alembic_cfg = AlembicConfig("alembic.ini")
                        script_dir = ScriptDirectory.from_config(alembic_cfg)
                        head = script_dir.get_current_head()
                        if current != head:
                            logger.warning(
                                "[MIGRATION] DB version %s != head %s — run alembic upgrade",
                                current, head,
                            )
                        else:
                            logger.info("[MIGRATION] DB is at head: %s", head)
                    else:
                        logger.warning("[MIGRATION] alembic_version table not found")
            except Exception as exc:
                logger.warning("[MIGRATION] Could not verify alembic version: %s", exc)

        # Startup: initial token cleanup (graceful if tables don't exist yet)
        try:
            cleaned = cleanup_expired_tokens()
            logger.info("[AUTH] Cleaned %d expired tokens on startup", cleaned)
        except Exception as exc:
            logger.warning("[AUTH] Token cleanup skipped at startup: %s", exc)
        
        # Periodic cleanup every 6 hours
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(6 * 3600)
                try:
                    count = cleanup_expired_tokens()
                    if count > 0:
                        logger.info("[AUTH] Periodic cleanup: %d tokens removed", count)
                except Exception:
                    logger.exception("[AUTH] Cleanup failed")
        
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Security Headers + Compression ───────────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
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

    # Rate limiting — antes de procesar la lógica de negocio
    from web.middleware.rate_limiter import RateLimiterMiddleware as _RLM
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

    # Migrate subscriptions CHECK constraint if DB has old plan names
    _migrate_subscription_constraints(get_engine())

    # Sync existing auth users to SA database (fixes FK constraint issue)
    _sync_all_auth_users_to_sa()

    # Todos los endpoints de datos requieren autenticación (RBAC a nivel de route)
    _api_auth = [Depends(get_usuario_actual)]
    app.include_router(web_clientes_router.router, prefix="/api", dependencies=_api_auth)
    app.include_router(web_planes_router.router,   prefix="/api", dependencies=_api_auth)
    app.include_router(web_stats_router.router,    prefix="/api", dependencies=_api_auth)
    app.include_router(web_gym_profile_router.router, prefix="/api", dependencies=_api_auth)

    # Usuario individual routes
    app.include_router(web_usuario_router.router, prefix="/api", dependencies=_api_auth)

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
        return templates.TemplateResponse(
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
        # E3: exc_info solo en non-production para evitar stack traces en logs de producción
        from web.settings import get_settings as _gs
        logger.error(
            "Unhandled: %s", exc,
            exc_info=not _gs().is_production
        )
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
            logger.warning("[HEALTH] Database check failed: %s", e)
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
            logger.warning("[HEALTH] Readiness check failed: %s", e)
            return JSONResponse(status_code=503, content={"ready": False, "error": str(e)})

    # ── Rutas HTML (páginas) — now served by web/routes/pages.py ────────────

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
        uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
