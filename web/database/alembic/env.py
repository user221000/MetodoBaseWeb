"""
Alembic env.py — Configuración de migraciones para MetodoBase Web.

Resuelve DATABASE_URL desde web/database/engine.py para mantener
una única fuente de verdad.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Asegurar que la raíz del proyecto esté en sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Cargar .env para obtener DATABASE_URL
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

# Alembic Config object
config = context.config

# Embedded callers supply the exact connection and own their process logging.
if config.config_file_name is not None and config.attributes.get("connection") is None:
    fileConfig(config.config_file_name)

# Importar modelos para que Alembic detecte las tablas
from web.database.models import Base  # noqa: E402
target_metadata = Base.metadata

# Resolver URL de BD desde nuestra config (misma lógica que engine.py)
from web.database.engine import _get_database_url  # noqa: E402
config.set_main_option("sqlalchemy.url", _get_database_url().replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        context.configure(connection=supplied_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
