"""Manual cleanup with existing 30-day token and 90-day audit parameters.

Refresh expiry is Unix epoch seconds; audit instants use the typed UTC column.
No scheduler or retention policy is created. Failure exits nonzero without
exposing SQL, parameters or credentials.
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from sqlalchemy import delete
from web.database.engine import get_engine
from web.database.models import AuthAuditLog, RefreshToken

logger = logging.getLogger(__name__)


class CleanupFailure(RuntimeError):
    """Cleanup did not confirm success; callers must not report zero."""


def _cutoff(days_to_keep):
    if type(days_to_keep) is not int or days_to_keep < 0:
        raise ValueError('days_to_keep must be a nonnegative integer')
    try:
        return datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    except OverflowError:
        raise ValueError('days_to_keep is outside the supported calendar') from None


def _delete_rows(statement, operation):
    try:
        with get_engine().begin() as connection:
            count = connection.execute(statement).rowcount
            if count < 0:
                raise CleanupFailure('cleanup_count_unavailable')
        # Emit success only after the transaction context confirmed its commit.
        logger.info('Cleanup confirmed operation=%s count=%d', operation, count)
        return count
    except Exception as error:
        logger.error('Cleanup failed operation=%s class=%s', operation, type(error).__name__)
        raise CleanupFailure('cleanup_not_confirmed') from None


def cleanup_expired_tokens(days_to_keep: int = 30) -> int:
    """Delete only tokens expired strictly before the existing age cutoff."""
    cutoff = _cutoff(days_to_keep).timestamp()
    return _delete_rows(delete(RefreshToken).where(RefreshToken.expires_at < cutoff), 'refresh_tokens')


def cleanup_old_audit_logs(days_to_keep: int = 90) -> int:
    """Use UTCDateTime binding so database timezone cannot move the cutoff."""
    cutoff = _cutoff(days_to_keep)
    return _delete_rows(delete(AuthAuditLog).where(AuthAuditLog.created_at < cutoff), 'auth_audit')


def main():
    """Main entry point for cleanup job."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("CLEANUP JOB STARTED")
    try:
        tokens_deleted = cleanup_expired_tokens(days_to_keep=30)
        logs_deleted = cleanup_old_audit_logs(days_to_keep=90)
    except Exception as error:
        logger.error('CLEANUP JOB FAILED class=%s', type(error).__name__)
        return 1
    logger.info('CLEANUP JOB COMPLETED tokens=%d audit=%d', tokens_deleted, logs_deleted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
