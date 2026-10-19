"""Public fresh-proof entry, exposing no general account/session capability."""
import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from web.middleware.rate_limiter import get_client_identifier
from web.progress_retirement_schemas import Metadata, Withdrawal
from web.services import progress_retirement as service

logger = logging.getLogger(__name__)


async def admission(request: Request):
    from web.rate_limiter_redis import check_rate_limit
    from web.settings import get_settings
    settings = get_settings()
    if settings.is_production and not settings.REDIS_URL:
        service.fail(503, "progress_retirement_unconfirmed")
    allowed, _, _ = await check_rate_limit("rl:consent-retirement:ip:" + get_client_identifier(request),
        30, 300, use_redis=bool(settings.REDIS_URL), sensitive=True)
    if not allowed:
        service.fail(429, "progress_retirement_throttled")


async def invoke(request, schema, operation):
    # Use the existing bounded stream decoder, never request.body()/json().
    from web.routes.personal_progress import body
    command = await body(schema)(request)
    from web.rate_limiter_redis import check_rate_limit
    from web.settings import get_settings
    settings = get_settings()
    account = command.primary.email or "unsupported-google"
    digest = hmac.new(settings.SECRET_KEY.encode(), ("consent-retirement:" + account).encode(), hashlib.sha256).hexdigest()
    allowed, _, _ = await check_rate_limit("rl:consent-retirement:account:" + digest,
        10, 300, use_redis=bool(settings.REDIS_URL), sensitive=True)
    if not allowed:
        service.fail(429, "progress_retirement_throttled")
    return await run_in_threadpool(_execute, command, operation)


def _execute(command, operation):
    """Fresh proof owns a fresh session, never a retagged ambient session.

    In particular api.app may have selected a tenant from an incidental general
    bearer. It has no authority for this purpose and must not select the actor.
    The prior context is restored even after admission/commit uncertainty.
    """
    from web.database.engine import SessionLocal
    from web.database.tenant_context import current_tenant
    token = current_tenant.set("")
    try:
        with SessionLocal() as db:
            return service.perform(db, command, operation=operation)
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001 -- include session-close uncertainty without exposing parameters
        logger.error("Consent retirement session class=%s", type(error).__name__)
        service.fail(503, "progress_retirement_unconfirmed")
    finally:
        current_tenant.reset(token)


router = APIRouter(dependencies=[Depends(admission)])


@router.post("/auth/progress-retirement/metadata")
async def metadata(request: Request):
    return await invoke(request, Metadata, "metadata")


@router.post("/auth/progress-retirement/withdraw")
async def withdraw(request: Request):
    return await invoke(request, Withdrawal, "withdraw")
