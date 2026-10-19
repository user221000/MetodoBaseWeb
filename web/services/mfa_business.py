"""Business adapter: exact request grant, consumed in caller-owned transaction."""
from contextlib import contextmanager
import logging

from sqlalchemy.orm import Session

from web.services import mfa_service

logger = logging.getLogger(__name__)


class BusinessSession(Session):
    """An uncertain business commit never becomes an apparent confirmed ACK."""

    def commit(self):
        try:
            super().commit()
        except Exception as error:
            logger.error("MFA business commit unconfirmed class=%s", type(error).__name__)
            mfa_service.rollback(self)
            mfa_service.fail(503, "mfa_unconfirmed")


@contextmanager
def open_business_session():
    from web.database.engine import get_engine
    with BusinessSession(get_engine(), autoflush=False, expire_on_commit=False) as db:
        try:
            yield db
        except Exception:
            mfa_service.rollback(db)
            raise


def business_session():
    """Existing services commit the mutation; never commit a second finalizer."""
    with open_business_session() as db:
        yield db


def step_up(db, actor, request, body, *, idempotency_key=None):
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        mfa_service.fail(401, "mfa_identity_unavailable")
    return mfa_service.consume_step_up(db, actor, authorization[7:],
        request.headers.get("X-MFA-Grant"), request.method, request.url.path, body,
        idempotency_key=idempotency_key)
