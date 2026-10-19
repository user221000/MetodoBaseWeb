"""Migrate only an explicitly configured synthetic PostgreSQL database.

No create_all or stamp fallback is allowed. The CI service owns a fresh database;
local runs must provide dedicated loopback URLs for migrator and restricted app.
"""
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.isolation import prepare_environment, validate_postgres_test_url


def main():
    """Provision test-only least privileges and return the migration exit status."""
    migrator = os.environ["METODOBASE_TEST_MIGRATOR_URL"]
    app = os.environ["METODOBASE_TEST_POSTGRES_URL"]
    validate_postgres_test_url(migrator)
    validate_postgres_test_url(app)
    admin_parts, app_parts = urlsplit(migrator), urlsplit(app)
    if (admin_parts.hostname, admin_parts.port, admin_parts.path) != (app_parts.hostname, app_parts.port, app_parts.path):
        raise ValueError("Migrator and app must use the same synthetic database")
    import psycopg2
    from psycopg2 import sql
    dsn = migrator.replace("postgresql+psycopg2://", "postgresql://", 1)
    with psycopg2.connect(dsn, connect_timeout=5) as db, db.cursor() as cursor:
        role = unquote(app_parts.username or "")
        cursor.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=%s", (role,))
        existing = cursor.fetchone()
        if existing and any(existing):
            raise ValueError("Existing synthetic app role has forbidden privileges")
        if not existing:
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD %s").format(sql.Identifier(role)), (unquote(app_parts.password or ""),))
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {}").format(sql.Identifier(role)))
        cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO {}").format(sql.Identifier(role)))
    os.environ["METODOBASE_TEST_DATABASE_URL"] = migrator
    prepare_environment(discard_inherited=True)
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=False)
    if result.returncode:
        return result.returncode
    with psycopg2.connect(dsn, connect_timeout=5) as db, db.cursor() as cursor:
        cursor.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(role)))
        cursor.execute(sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(role)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
