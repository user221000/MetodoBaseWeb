"""
db_bootstrap.py — Robust database initialization for Railway/production.

Used as Railway releaseCommand instead of raw 'alembic upgrade head'.
Handles fresh databases and broken migration states gracefully.

Strategy:
1. Create all tables from SQLAlchemy models (CREATE TABLE IF NOT EXISTS)
2. Stamp Alembic version to head (so future migrations work correctly)
3. Then run alembic upgrade head (picks up any data migrations)
"""
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("db_bootstrap")


def main():
    logger.info("=" * 60)
    logger.info("MetodoBase Database Bootstrap")
    logger.info("=" * 60)
    
    # Check DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("FATAL: DATABASE_URL not set")
        logger.error("Configure DATABASE_URL in Railway Dashboard > Variables")
        sys.exit(1)
    
    # Mask password in logs
    safe_url = db_url.split("@")[-1] if "@" in db_url else "(local)"
    logger.info("Database: ...@%s", safe_url)
    
    # 1. Initialize the database engine
    logger.info("Step 1: Initializing database engine...")
    try:
        from web.database.engine import init_db, get_engine
        from web.database.models import Base

        init_db()
        engine = get_engine()
        logger.info("Engine initialized successfully")
    except Exception as e:
        logger.error("FATAL: Failed to initialize database engine: %s", e)
        sys.exit(1)

    # 2. Create all tables from models.py (safe: skips existing tables)
    logger.info("Step 2: Creating/verifying all tables from models...")
    try:
        Base.metadata.create_all(engine)
        logger.info("All tables created/verified successfully")
    except Exception as e:
        # Possible DuplicateObject on indexes if DB is in partial state
        logger.warning("create_all() had issues (may be non-fatal): %s", e)
        logger.info("Continuing with Alembic to handle schema...")

    # 3. Stamp Alembic version to head ONLY for fresh databases
    # For existing databases with pending migrations, stamping first would
    # mark them as already applied (causing them to be silently skipped).
    logger.info("Step 3: Checking Alembic migration state...")
    alembic_cfg = None
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command
        from sqlalchemy import inspect as sa_inspect

        alembic_cfg = AlembicConfig("alembic.ini")
        inspector = sa_inspect(engine)

        if "alembic_version" not in inspector.get_table_names():
            # Fresh DB: tables were just created by create_all().
            # Stamp to head so the initial migrations don't try to re-create them.
            logger.info("Fresh database detected — stamping Alembic to head...")
            command.stamp(alembic_cfg, "head")
            logger.info("Alembic stamped at head (fresh DB)")
        else:
            logger.info("Existing database — skipping stamp, upgrade will apply any pending migrations")
    except Exception as e:
        logger.warning("Alembic stamp check had issues (non-fatal): %s", e)

    # 3b. Safety guard: fix columns that a previous buggy release may have
    # stamped as applied without actually running the migration SQL.
    # Each guard uses ADD COLUMN IF NOT EXISTS (idempotent).
    logger.info("Step 3b: Applying safety column guards...")
    _safety_ddl = [
        # plan_json column — may have been stamped but never created
        "ALTER TABLE planes_generados ADD COLUMN IF NOT EXISTS plan_json TEXT",
    ]
    try:
        from sqlalchemy import text as _text
        with engine.begin() as _conn:
            for _ddl in _safety_ddl:
                try:
                    _conn.execute(_text(_ddl))
                    logger.info("Safety guard applied: %s", _ddl[:60])
                except Exception as _e:
                    logger.warning("Safety guard skipped (non-fatal): %s — %s", _ddl[:60], _e)
    except Exception as e:
        logger.warning("Safety guards section failed (non-fatal): %s", e)

    # 4. Run alembic upgrade head (applies any pending migrations)
    logger.info("Step 4: Running alembic upgrade head (applies pending migrations)...")
    try:
        if alembic_cfg is None:
            from alembic.config import Config as AlembicConfig
            from alembic import command
            alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic upgrade completed successfully")
    except Exception as e:
        logger.warning("Alembic upgrade had issues (non-fatal): %s", e)

    logger.info("=" * 60)
    logger.info("Database bootstrap complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
