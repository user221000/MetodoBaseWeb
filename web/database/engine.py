"""
web/database/engine.py — SQLAlchemy engine + session factory.

Soporta SQLite (desarrollo) y PostgreSQL (producción) via DATABASE_URL.

Uso:
    from web.database.engine import get_db, init_db
    # En startup:
    init_db()
    # En endpoint:
    def endpoint(db: Session = Depends(get_db)): ...
"""
import logging
import os
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

_logger = logging.getLogger(__name__)
_engine = None
_SessionLocal = None


def normalize_database_url(url: str) -> str:
    """Select the installed synchronous PostgreSQL driver explicitly.

    SQLAlchemy 2.1 changed the bare postgresql:// default to psycopg3; this
    runtime resolves psycopg2-binary. Preserve explicit driver selections and
    never render or log connection credentials while normalizing the scheme.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


def _get_database_url() -> str:
    """Resuelve la URL de la base de datos desde settings."""
    from web.settings import get_settings
    settings = get_settings()

    # DATABASE_URL explícita tiene prioridad
    import os
    url = os.getenv("DATABASE_URL", "")
    if url:
        return normalize_database_url(url)

    # En producción, PostgreSQL es obligatorio — no permitir fallback a SQLite
    if settings.is_production:
        raise RuntimeError(
            "FATAL: DATABASE_URL no está configurada o está vacía. "
            "PostgreSQL es obligatorio en producción. "
            "Configure DATABASE_URL en las variables de entorno del despliegue."
        )

    # Fallback: SQLite local (solo desarrollo — no desktop dependency)
    from pathlib import Path
    data_dir = os.getenv("METODOBASE_DATA_DIR")
    if data_dir:
        base = Path(data_dir) / "registros"
    else:
        _xdg = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        base = Path(_xdg) / "MetodoBase" / "registros"
    db_path = base / "metodobase_web.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def get_engine():
    """Retorna el engine singleton."""
    global _engine
    if _engine is None:
        init_db()
    return _engine


def init_db() -> None:
    """Inicializa engine y session factory. Llamar en app startup."""
    global _engine, _SessionLocal

    url = _get_database_url()
    # Railway uses postgres:// but SQLAlchemy needs postgresql://
    url = normalize_database_url(url)
    is_sqlite = url.startswith("sqlite")

    kwargs = {}
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Para 100 usuarios concurrentes con 4 workers:
        # pool_size=20 + max_overflow=10 → hasta 30 conexiones por worker.
        # Con 4 workers: hasta 120 conexiones totales en PostgreSQL.
        # Ajustar WEB_WORKERS si Railway limita el plan de Postgres.
        kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "20"))
        kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        kwargs["pool_timeout"] = 30
        kwargs["pool_recycle"] = 1800  # Recycle every 30 min — prevents stale connections

    _engine = create_engine(
        url,
        pool_pre_ping=True,
        echo=False,
        **kwargs,
    )

    # SQLite: habilitar WAL + foreign keys
    if is_sqlite:
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:
    """Create a new DB session from the connection pool. Caller must close it."""
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, commits on success, rollbacks on error."""
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        # Set RLS tenant context on PostgreSQL (SQLite doesn't support RLS)
        if _engine and "postgresql" in str(_engine.url):
            try:
                from web.middleware.tenant import current_tenant
                tenant_id = current_tenant.get(None)
                if tenant_id:
                    # set_config with is_local=true -> scoped to current transaction only
                    db.execute(
                        text("SELECT set_config('app.current_tenant', :tenant, true)"),
                        {"tenant": str(tenant_id)},
                    )
                else:
                    _logger.debug("[DB] No tenant context available for RLS")
            except Exception as exc:
                _logger.warning("[DB] Failed to set RLS tenant context: %s", exc)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_readonly() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a read-only session (no auto-commit)."""
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        # Set RLS tenant context on PostgreSQL
        if _engine and "postgresql" in str(_engine.url):
            try:
                from web.middleware.tenant import current_tenant
                tenant_id = current_tenant.get(None)
                if tenant_id:
                    db.execute(
                        text("SELECT set_config('app.current_tenant', :tenant, true)"),
                        {"tenant": str(tenant_id)},
                    )
            except Exception as exc:
                _logger.warning("[DB] Failed to set RLS tenant context (readonly): %s", exc)
        yield db
    finally:
        db.close()
