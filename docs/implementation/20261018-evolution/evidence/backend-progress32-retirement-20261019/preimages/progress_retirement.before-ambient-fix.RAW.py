"""Public fresh-proof entry, exposing no general account/session capability."""
import hashlib
import hmac

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from web.middleware.rate_limiter import get_client_identifier
from web.progress_retirement_schemas import Metadata, Withdrawal
from web.services import progress_retirement as service


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
    from web.routes.personal_progress import _invoke, body
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
    return await run_in_threadpool(_invoke, service.perform, command, operation=operation)


router = APIRouter(dependencies=[Depends(admission)])


@router.post("/auth/progress-retirement/metadata")
async def metadata(request: Request):
    return await invoke(request, Metadata, "metadata")


@router.post("/auth/progress-retirement/withdraw")
async def withdraw(request: Request):
    return await invoke(request, Withdrawal, "withdraw")
