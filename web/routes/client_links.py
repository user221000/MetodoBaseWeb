"""Authenticated explicit client links; services own exactly one mutation commit."""
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter,Depends,HTTPException,Path,Query,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,Response
from fastapi.routing import APIRoute
from pydantic import TypeAdapter,ValidationError
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web.client_link_schemas import InvitationAccept,InvitationIssue,InvitationToken,LinkVersion,PlanPublication
from web.services import client_link_invitations as invitations,client_link_plans as plans
from web.services.client_link_context import fail
from web.services.client_link_mail import send_invitation
from web.services.recovery_dispatcher import RecoveryDispatcher

MAX_BODY_BYTES=16*1024
logger=logging.getLogger(__name__)
HEADERS={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'}
UUID_PATTERN=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
CLIENT=Path(min_length=1,max_length=36)
def identity_path():
    # FastAPI assigns the parameter alias on FieldInfo; each distinct path
    # parameter needs its own instance rather than sharing that mutable object.
    return Path(min_length=36,max_length=36,pattern=UUID_PATTERN)


class MemberLinkRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def private_response(request):
            try:response=await original(request)
            except HTTPException as error:
                return JSONResponse({'detail':error.detail},status_code=error.status_code,headers={**HEADERS,**(error.headers or {})})
            except RequestValidationError:
                return JSONResponse({'detail':{'code':'member_invalid_input','message':'Revisa los campos solicitados.'}},status_code=422,headers=HEADERS)
            except Exception as error:
                logger.error('Member route unavailable class=%s',type(error).__name__)
                return JSONResponse({'detail':{'code':'member_service_unavailable','message':'La operacion no esta disponible temporalmente.'}},status_code=503,headers=HEADERS)
            response.headers.update(HEADERS)
            return response
        return private_response


@asynccontextmanager
async def lifespan(app):
    previous=getattr(app.state,'member_link_dispatcher',None)
    dispatcher=previous or RecoveryDispatcher()
    app.state.member_link_dispatcher=dispatcher
    try:yield
    finally:
        if previous is None:dispatcher.close()


router=APIRouter(tags=['Vinculos explicitos de clientes'],route_class=MemberLinkRoute,lifespan=lifespan)


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate input member')
        result[key]=value
    return result


def _constant(_):
    raise ValueError('Nonfinite input')


def body(model):
    adapter=TypeAdapter(model)
    async def parse(request:Request):
        if request.headers.get('content-type','').split(';',1)[0].strip().lower()!='application/json':
            fail(415,'member_invalid_input','Usa una solicitud JSON valida.')
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BODY_BYTES:fail(413,'member_body_limit','La solicitud supera el volumen permitido.')
            raw.extend(chunk)
        try:
            value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=_constant)
            return adapter.validate_python(value)
        except (ValueError,ValidationError,TypeError,UnicodeError,RecursionError,OverflowError):
            fail(422,'member_invalid_input','Revisa los campos solicitados.')
    return parse


def _invoke(function,*args,**kwargs):
    from web.database.engine import SessionLocal
    # This local session has no dependency finalizer that commits a second time.
    with SessionLocal() as db:return function(db,*args,**kwargs)


def mail_configuration():
    from web.services.password_recovery import public_origin
    from web.settings import get_settings
    settings=get_settings()
    try:origin=public_origin(settings)
    except HTTPException:fail(503,'member_mail_unavailable','No es posible solicitar una invitacion en este momento.')
    if not settings.RESEND_API_KEY or (settings.is_production and not settings.REDIS_URL):
        fail(503,'member_mail_unavailable','No es posible solicitar una invitacion en este momento.')
    return origin


async def enforce_limit(request,principal,purpose,*,recipient=None,token=None):
    from web.middleware.rate_limiter import get_client_identifier
    from web.rate_limiter_redis import check_rate_limit
    from web.settings import get_settings
    settings=get_settings()
    if settings.is_production and not settings.REDIS_URL:
        fail(503,'member_service_unavailable','La operacion no esta disponible temporalmente.')
    limits={'issue':10,'resend':10,'inspect':60,'accept':20,'revoke':30,'publish':60,'withdraw':60,'read':240}
    maximum=limits[purpose]
    prefix='rl:client-links-v1:'+purpose
    def private_key(kind,value):
        hashed=hmac.new(settings.SECRET_KEY.encode('utf-8'),(prefix+':'+kind+':'+value).encode('utf-8'),hashlib.sha256).hexdigest()
        return prefix+':'+kind+':'+hashed
    keys=[(private_key('ip',get_client_identifier(request)),maximum),
        (private_key('actor',principal['id']),maximum)]
    if recipient is not None:keys.append((private_key('recipient',recipient),5))
    if token is not None:keys.append((private_key('proof',token),30 if purpose=='inspect' else 10))
    for key,limit in keys:
        allowed,info,_=await check_rate_limit(key,limit,900,use_redis=bool(settings.REDIS_URL),sensitive=True)
        if not allowed:
            raise HTTPException(429,{'code':'member_rate_limited','message':'Espera antes de volver a intentarlo.'},
                headers={'Retry-After':str(info['retry_after'])})


def _enqueue(request,message):
    if message is None:return
    dispatcher=getattr(request.app.state,'member_link_dispatcher',None)
    # Durable pending state is already committed. Queue/ACK uncertainty never
    # fabricates delivery, rotates a token, or rolls that state back.
    if dispatcher is not None:
        try:dispatcher.submit(send_invitation,message)
        except Exception as error:
            logger.error('Member mail admission unconfirmed class=%s',type(error).__name__)


@router.post('/clientes/{client_id}/vinculacion/invitaciones',status_code=202)
async def issue(request:Request,client_id:str=CLIENT,principal=Depends(get_usuario_actual),data=Depends(body(InvitationIssue))):
    origin=mail_configuration()
    await enforce_limit(request,principal,'issue',recipient=data.recipient_email)
    public,message=await run_in_threadpool(_invoke,invitations.issue_invitation,principal,client_id,data,origin)
    _enqueue(request,message)
    return JSONResponse(public,status_code=202,headers=HEADERS)


@router.post('/clientes/{client_id}/vinculacion/invitaciones/{invitation_id}/reenviar',status_code=202)
async def resend(request:Request,client_id:str=CLIENT,invitation_id:str=identity_path(),principal=Depends(get_usuario_actual),data=Depends(body(LinkVersion))):
    origin=mail_configuration()
    await enforce_limit(request,principal,'resend')
    public,message=await run_in_threadpool(_invoke,invitations.resend_invitation,principal,client_id,invitation_id,data.expected_version,origin)
    _enqueue(request,message)
    return JSONResponse(public,status_code=202,headers=HEADERS)


@router.get('/clientes/{client_id}/vinculacion')
async def state(request:Request,client_id:str=CLIENT,principal=Depends(get_usuario_actual),
        limit:int=Query(100,ge=1,le=100),after:str|None=Query(None,min_length=36,max_length=36,pattern=UUID_PATTERN)):
    await enforce_limit(request,principal,'read')
    return await run_in_threadpool(_invoke,plans.professional_link_state,principal,client_id,limit=limit,after=after)


@router.delete('/clientes/{client_id}/vinculacion/{link_id}')
async def professional_revoke(request:Request,client_id:str=CLIENT,link_id:str=identity_path(),principal=Depends(get_usuario_actual),data=Depends(body(LinkVersion))):
    await enforce_limit(request,principal,'revoke')
    return await run_in_threadpool(_invoke,plans.revoke_professional_link,principal,client_id,link_id,data.expected_version)


@router.post('/clientes/{client_id}/vinculacion/{link_id}/publicaciones')
async def publish(request:Request,client_id:str=CLIENT,link_id:str=identity_path(),principal=Depends(get_usuario_actual),data=Depends(body(PlanPublication))):
    await enforce_limit(request,principal,'publish')
    return await run_in_threadpool(_invoke,plans.publish_plan,principal,client_id,link_id,data)


@router.delete('/clientes/{client_id}/vinculacion/{link_id}/publicaciones/{publication_id}')
async def withdraw(request:Request,client_id:str=CLIENT,link_id:str=identity_path(),publication_id:str=identity_path(),principal=Depends(get_usuario_actual),data=Depends(body(LinkVersion))):
    await enforce_limit(request,principal,'withdraw')
    return await run_in_threadpool(_invoke,plans.withdraw_plan,principal,client_id,link_id,publication_id,data.expected_version)


@router.post('/usuario/vinculaciones/invitacion')
async def info(request:Request,principal=Depends(get_usuario_actual),data=Depends(body(InvitationToken))):
    await enforce_limit(request,principal,'inspect',token=data.token)
    return await run_in_threadpool(_invoke,invitations.inspect_invitation,principal,data.token)


@router.post('/usuario/vinculaciones/aceptar')
async def accept(request:Request,principal=Depends(get_usuario_actual),data=Depends(body(InvitationAccept))):
    await enforce_limit(request,principal,'accept',token=data.token)
    return await run_in_threadpool(_invoke,invitations.accept_invitation,principal,data)


@router.get('/usuario/vinculos')
async def memberships(request:Request,principal=Depends(get_usuario_actual),
        limit:int=Query(100,ge=1,le=100),after:str|None=Query(None,min_length=36,max_length=36,pattern=UUID_PATTERN)):
    await enforce_limit(request,principal,'read')
    return await run_in_threadpool(_invoke,plans.list_member_links,principal,limit=limit,after=after)


@router.get('/usuario/vinculos/{link_id}/plan')
async def member_plan(request:Request,link_id:str=identity_path(),principal=Depends(get_usuario_actual)):
    await enforce_limit(request,principal,'read')
    return await run_in_threadpool(_invoke,plans.read_member_plan,principal,link_id)


@router.get('/usuario/vinculos/{link_id}/publicaciones/{publication_id}/pdf')
async def member_pdf(request:Request,link_id:str=identity_path(),publication_id:str=identity_path(),principal=Depends(get_usuario_actual)):
    await enforce_limit(request,principal,'read')
    content=await run_in_threadpool(_invoke,plans.read_member_pdf,principal,link_id,publication_id)
    return Response(content,media_type='application/pdf',headers={**HEADERS,'Content-Disposition':'attachment; filename="plan-publicado.pdf"'})


@router.delete('/usuario/vinculos/{link_id}')
async def member_revoke(request:Request,link_id:str=identity_path(),principal=Depends(get_usuario_actual),data=Depends(body(LinkVersion))):
    await enforce_limit(request,principal,'revoke')
    return await run_in_threadpool(_invoke,plans.revoke_member_link,principal,link_id,data.expected_version)
