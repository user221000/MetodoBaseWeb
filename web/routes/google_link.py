"""Explicit Google linking, never portable primary proof from matching email."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute

from web.auth_deps import get_usuario_actual
from web.google_link_schemas import LinkConfirm, LinkStart, Unlink
from web.routes.mfa import access, parse
from web.database.engine import SessionLocal
from web.services import google_link as service

logger=logging.getLogger(__name__)


def session():
    # Function-scoped dependency closes before the HTTP response can escape.
    # Read-only operations also have no success-then-finalizer commit.
    try:
        db=SessionLocal()
        try:
            try:
                yield db
            except Exception:
                service.rollback(db)
                raise
        finally:
            service.close_owned_session(db)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Google link session unconfirmed class=%s",type(error).__name__)
        service.fail(503,"google_link_unconfirmed")


class LinkRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def handle(request):
            try:
                return await original(request)
            except HTTPException:
                raise
            except Exception as error:
                logger.error("Google linking unconfirmed class=%s",type(error).__name__)
                service.fail(503,"google_link_unconfirmed")
        return handle


async def limit(request: Request):
    from web.middleware.rate_limiter import get_client_identifier
    from web.rate_limiter_redis import check_rate_limit
    from web.settings import get_settings
    settings=get_settings()
    if settings.is_production and not settings.REDIS_URL:
        service.fail(503,"google_link_unavailable")
    allowed,info,_=await check_rate_limit("rl:google33:"+request.url.path+":"+get_client_identifier(request),
        30,300,use_redis=bool(settings.REDIS_URL),sensitive=True)
    if not allowed:
        raise HTTPException(429,{"code":"google_link_throttled","message":"Espera antes de volver a verificar."},
            headers={"Retry-After":str(info["retry_after"])})


router=APIRouter(prefix="/auth/google/link",tags=["Google binding"],route_class=LinkRoute,dependencies=[Depends(limit)])


@router.get("/status")
def status(after: str | None=None,actor=Depends(get_usuario_actual),db=Depends(session,scope="function")):
    import re
    if after is not None and not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",after):
        service.fail(422,"google_link_invalid_input")
    return service.status(db,actor,after=after)


@router.post("/start")
async def start(request: Request,actor=Depends(get_usuario_actual),db=Depends(session,scope="function")):
    data=await parse(request,LinkStart)
    service.admit(db,actor,access(request),phase="start")
    # No transaction or account lock remains over provider I/O.
    from web.services.google_identity import verified_google_reauthentication
    primary=await verified_google_reauthentication(data.google_credential)
    return service.start(db,actor,access(request),data,primary)


@router.post("/confirm")
async def confirm(request: Request,actor=Depends(get_usuario_actual),db=Depends(session,scope="function")):
    data=await parse(request,LinkConfirm)
    if data.confirm is not True:
        service.fail(422,"google_link_invalid_input")
    service.admit(db,actor,access(request),phase="confirm")
    return service.confirm(db,actor,access(request),data.intent)


@router.post("/unlink")
async def unlink(request: Request,actor=Depends(get_usuario_actual),db=Depends(session,scope="function")):
    data=await parse(request,Unlink)
    service.admit(db,actor,access(request),phase="unlink")
    return service.unlink(db,actor,access(request),data)
