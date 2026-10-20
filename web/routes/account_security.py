"""Account37 HTTP: finite browser admission, closed inputs, purpose-only links."""
import hashlib
import hmac
import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from web.account_security_schemas import EmailConfirmation, Empty, PasswordChange
from web.auth_deps import get_usuario_actual
from web.browser_session import HEADERS, BrowserAuthRoute
from web.middleware.rate_limiter import get_client_identifier
from web.services import account_security as service

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 8192
Actor = Annotated[dict, Depends(get_usuario_actual)]


class AccountRoute(BrowserAuthRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                response = await original(request)
                response.headers.update(HEADERS)
                return response
            except HTTPException:
                raise
            except Exception as error:
                logger.exception("Account security request unconfirmed class=%s", type(error).__name__, exc_info=False)
                service.fail(503, "account_security_unconfirmed")
        return handle


router = APIRouter(prefix="/account/security", tags=["Seguridad de cuenta"], route_class=AccountRoute)
public_router = APIRouter(route_class=AccountRoute)


async def parse(request, schema):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY_BYTES:
            service.fail(413, "account_security_input_too_large")
        raw.extend(chunk)
    try:
        def pairs(items):
            value = {}
            for key, item in items:
                if key in value:
                    raise ValueError("Duplicate field")
                value[key] = item
            return value
        data = json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite")))
        return schema.model_validate(data)
    except ValidationError as error:
        # Only known field names; never echo inputs, unknown keys or Pydantic's
        # value-bearing error messages. UI can attach these to accessible fields.
        fields = sorted({item["loc"][0] for item in error.errors(include_input=False)
                         if item["loc"] and item["loc"][0] in schema.model_fields})
        raise HTTPException(422, {"code": "account_security_invalid_input",
                                 "message": "Revisa los campos de la solicitud.", "fields": fields}) from None
    except (ValueError, TypeError, RecursionError):
        service.fail(422, "account_security_invalid_input")


async def rate_limit(request, *, actor=None, proof=None):
    from web.rate_limiter_redis import check_rate_limit
    from web.settings import get_settings
    settings = get_settings()
    if settings.is_production and not settings.REDIS_URL:
        service.fail(503, "account_security_service_unavailable")
    prefix = "rl:account37:" + request.url.path
    keys = [prefix + ":ip:" + get_client_identifier(request)]
    subject = actor["id"] if actor is not None else proof
    if subject:
        hashed = hmac.new(settings.SECRET_KEY.encode(), (prefix + ":" + subject).encode(), hashlib.sha256).hexdigest()
        keys.append(prefix + ":subject:" + hashed)
    for key in keys:
        allowed, info, _ = await check_rate_limit(key, 10, 900, use_redis=bool(settings.REDIS_URL), sensitive=True)
        if not allowed:
            raise HTTPException(429, {"code": "account_security_throttled", "message": "Espera antes de volver a intentar."},
                                headers={"Retry-After": str(info["retry_after"])})


@router.get("")
def status(actor: Actor):
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        return service.email_status(db, actor)


@router.post("/email/request")
async def request_email(request: Request, actor: Actor):
    await parse(request, Empty)
    await rate_limit(request, actor=actor)
    return await run_in_threadpool(service.issue_email, actor)


@router.post("/email/confirm")
async def confirm_email(request: Request):
    data = await parse(request, EmailConfirmation)
    await rate_limit(request, proof=data.token)
    return await run_in_threadpool(service.confirm_email, data.token)


@router.post("/password")
async def change_password(request: Request, actor: Actor):
    data = await parse(request, PasswordChange)
    await rate_limit(request, actor=actor)
    from web.routes.mfa import access
    return await run_in_threadpool(service.change_password, actor, access(request),
                                  data.reauthentication_token, data.new_password,
                                  code=data.code, recovery_code=data.recovery_code)


@public_router.get("/auth/verify-email", response_class=HTMLResponse)
def confirmation_page():
    content = (Path(__file__).resolve().parents[1] / "templates" / "email_verification37.html").read_text(encoding="utf-8")
    return HTMLResponse(content, headers=HEADERS)
