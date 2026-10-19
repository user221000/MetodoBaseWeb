"""Run reviewed Alembic upgrades; fail closed instead of hiding schema drift.

Existing unversioned databases are rejected by default. Explicit adoption
assigns a known historical revision only after exact structural comparison,
then executes real migrations. No ORM table creation or safety DDL fallback.
"""
import argparse
import logging
import os
import sys

logger = logging.getLogger("db_bootstrap")


def _migration_engine():
    """Create a dedicated short-lived connection; never borrow the app pool.

    Production requires separate application/migrator roles targeting the same
    database. Explicit DATABASE_URL remains a local testing/development CLI
    convenience, independent from application SessionLocal initialization.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from web.database.engine import normalize_database_url
    from web.settings import get_settings
    production = get_settings().is_production
    app_url = os.environ.get("DATABASE_URL", "")
    migration_url = os.environ.get("MIGRATOR_DATABASE_URL", "")
    if production:
        if not app_url or not migration_url:
            raise RuntimeError("Production migration requires explicit application and migrator database URLs")
        app = make_url(normalize_database_url(app_url))
        migrator = make_url(normalize_database_url(migration_url))
        if any(not value or not value.strip() for url in (app, migrator) for value in (url.host, url.database)):
            raise RuntimeError("Production URLs require explicit host and database")
        # Driver kwargs can override URL authority fields (including user and
        # dbname). Accept only explicit TLS options before comparing targets.
        tls_options = {"sslmode", "sslcert", "sslkey", "sslrootcert", "sslcrl", "sslcrldir",
            "ssl_min_protocol_version", "ssl_max_protocol_version", "channel_binding"}
        if set(app.query) - tls_options or set(migrator.query) - tls_options:
            raise RuntimeError("Database URL query accepts only reviewed TLS options")
        if app.get_backend_name() != "postgresql" or migrator.get_backend_name() != "postgresql":
            raise RuntimeError("Production migration requires PostgreSQL")
        def destination(url):
            return (url.host, url.port or 5432, url.database)
        if destination(app) != destination(migrator):
            raise RuntimeError("Application and migrator must target the same database")
        if not app.username or not migrator.username or app.username == migrator.username:
            raise RuntimeError("Application and migrator must use separate database roles")
    else:
        migration_url = migration_url or app_url
    if not migration_url:
        raise RuntimeError("Migration requires an explicit database URL")
    return create_engine(normalize_database_url(migration_url), pool_pre_ping=True, echo=False)


def main(argv=()) -> int:
    """Migrate an explicitly configured database and return a blocking exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt-verified-legacy", action="store_true")
    parser.add_argument("--revision", default="head", help="Reviewed revision for historical rehearsal; releases default to head")
    args = parser.parse_args(argv)
    engine = None
    try:
        from alembic import command
        from sqlalchemy import inspect, text
        from web.database.schema_control import alembic_config, expected_head, verify_legacy_signature, verify_runtime_schema, SCHEMA_CONTRACTS
        engine = _migration_engine()
        target_revision = expected_head() if args.revision == "head" else args.revision
        if target_revision not in SCHEMA_CONTRACTS:
            raise RuntimeError("Migration target has no reviewed structural contract")
        config = alembic_config()
        with engine.connect() as connection:
            sqlite = connection.dialect.name == "sqlite"
            if sqlite:
                # SQLite table rebuilds must not cascade-delete children while
                # replacing a parent. Only this migration connection suspends
                # enforcement; verify every FK before committing the rebuild.
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
            try:
                with connection.begin():
                    if sqlite:
                        connection.exec_driver_sql("BEGIN IMMEDIATE")
                    elif connection.dialect.name == "postgresql":
                        connection.execute(text("SELECT pg_advisory_xact_lock(1296192051)"))
                    tables = set(inspect(connection).get_table_names())
                    unversioned = bool(tables - {"alembic_version"}) and "alembic_version" not in tables
                    if unversioned:
                        if not args.adopt_verified_legacy:
                            raise RuntimeError("Unversioned existing schema requires reviewed baseline adoption")
                        verify_legacy_signature(connection)
                    config.attributes["connection"] = connection
                    if unversioned:
                        command.stamp(config, "20260402_plan_json")
                    command.upgrade(config, target_revision)
                    if sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                        raise RuntimeError("Migration would leave invalid foreign keys")
            finally:
                if sqlite:
                    connection.rollback()
                    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                    connection.commit()
        verify_runtime_schema(engine, expected_revision=target_revision)
        logger.info("Migration completed and verified at revision %s", target_revision)
        return 0
    except Exception as error:
        logger.error("Migration aborted class=%s; database not accepted for release", type(error).__name__)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main(sys.argv[1:]))
