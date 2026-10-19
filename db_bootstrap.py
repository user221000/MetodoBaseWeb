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


def main(argv=()) -> int:
    """Migrate an explicitly configured database and return a blocking exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt-verified-legacy", action="store_true")
    args = parser.parse_args(argv)
    if not os.environ.get("DATABASE_URL"):
        logger.error("Migration requires explicit DATABASE_URL")
        return 1
    try:
        from alembic import command
        from sqlalchemy import inspect, text
        from web.database.engine import get_engine
        from web.database.schema_control import alembic_config, expected_head, verify_legacy_signature, verify_runtime_schema
        engine = get_engine()
        expected_head()
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
                    command.upgrade(config, "head")
                    if sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                        raise RuntimeError("Migration would leave invalid foreign keys")
            finally:
                if sqlite:
                    connection.rollback()
                    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                    connection.commit()
        verify_runtime_schema(engine)
        logger.info("Migration completed and verified at revision %s", expected_head())
        return 0
    except Exception as error:
        logger.error("Migration aborted class=%s; database not accepted for release", type(error).__name__)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main(sys.argv[1:]))
