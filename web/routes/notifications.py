"""Common web/API36 adapters, bounded parse and cleanup before response."""
import hashlib,hmac,json,logging
from datetime import date
import re

from fastapi import APIRouter,Depends,HTTPException,Query,Request,Path
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse,HTMLResponse
from pydantic import TypeAdapter
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web.notification_schemas import (Context,Purpose,KEY,PreferenceWrite,QueueWrite,CancelWrite,ObserveWrite,ExclusionWrite)
from web.services import notifications as service
from web.services.notification_domain import UUID,DisabledPort

HEADERS={"Cache-Control":"no-store","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff"}
logger=logging.getLogger(__name__)


class NotificationRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def private(request):
            try:response=await original(request)
            except HTTPException as error:
                detail=error.detail
                if error.status_code==500:
                    detail={"code":"notification_unconfirmed","message":"No pudimos confirmar la operación."}
                return JSONResponse({"detail":detail},status_code=error.status_code,headers={**(error.headers or {}),**HEADERS})
            except RequestValidationError:return JSONResponse({"detail":{"code":"notification_invalid_input","message":"Revisa los campos solicitados."}},status_code=422,headers=HEADERS)
            except Exception as error:
                logger.error("Notification request unconfirmed class=%s",type(error).__name__)
                return JSONResponse({"detail":{"code":"notification_unconfirmed","message":"No pudimos confirmar la operación."}},status_code=503,headers=HEADERS)
            response.headers.update(HEADERS);return response
        return private


router=APIRouter(prefix="/notificaciones",tags=["Preferencias y recordatorios propios"],route_class=NotificationRoute)
public_router=APIRouter(route_class=NotificationRoute)


def _pairs(pairs):
    values={}
    for key,value in pairs:
        if key in values:raise ValueError("Duplicate input")
        values[key]=value
    return values


def _constant(_):raise ValueError("Nonfinite input")


def body(schema):
    adapter=TypeAdapter(schema)
    async def parse(request:Request):
        if request.headers.get("content-type","").split(";",1)[0].strip().lower()!="application/json":service.fail(415,"notification_invalid_input")
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>8192:service.fail(413,"notification_body_limit")
            raw.extend(chunk)
        try:return adapter.validate_python(json.loads(raw.decode("utf-8","strict"),object_pairs_hook=_pairs,parse_constant=_constant))
        except (ValueError,TypeError,UnicodeError,RecursionError,OverflowError):service.fail(422,"notification_invalid_input")
    return parse


def key(request:Request):
    values=request.headers.getlist("Idempotency-Key")
    if len(values)!=1 or not UUID.fullmatch(values[0]):service.fail(422,"notification_invalid_input")
    return values[0]


def civil(value):
    if value is None:return None
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",value):service.fail(422,"notification_invalid_input")
    try:return date.fromisoformat(value)
    except ValueError:service.fail(422,"notification_invalid_input")


@router.get("/contexto")
async def context(context:Context,principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(service.context,principal,context)


@router.get("/preferencias")
async def preferences(context:Context,principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(service.preferences,principal,context)


@router.put("/preferencias/{purpose}")
async def preference(purpose:Purpose,context:Context,principal=Depends(get_usuario_actual),command=Depends(body(PreferenceWrite)),request_key=Depends(key)):
    return await run_in_threadpool(service.set_preference,principal,context,purpose,command,request_key)


@router.post("/observar")
async def observe(request:Request,context:Context,principal=Depends(get_usuario_actual),command=Depends(body(ObserveWrite)),request_key=Depends(key)):
    port=getattr(request.app.state,"notification_billing_port",None) or DisabledPort()
    return await run_in_threadpool(service.observe,principal,context,request_key,port)


@router.get("/candidatos")
async def candidates(context:Context,principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(service.candidates,principal,context)


@router.post("/outbox")
async def queue(context:Context,principal=Depends(get_usuario_actual),command=Depends(body(QueueWrite)),request_key=Depends(key)):
    return await run_in_threadpool(service.queue,principal,context,command,request_key)


@router.get("/outbox")
async def outbox(context:Context,principal=Depends(get_usuario_actual),limit:int=Query(20,ge=1,le=50),after:str|None=Query(None,pattern=KEY)):
    return await run_in_threadpool(service.list_outbox,principal,context,limit,after)


@router.post("/outbox/{identifier}/cancelar")
async def cancel(context:Context,identifier:str=Path(pattern=KEY),principal=Depends(get_usuario_actual),command=Depends(body(CancelWrite)),request_key=Depends(key)):
    return await run_in_threadpool(service.cancel,principal,context,identifier,command,request_key)


@router.get("/metricas")
async def metrics(context:Context,principal=Depends(get_usuario_actual),start:str|None=Query(None,alias="from",max_length=10),through:str|None=Query(None,max_length=10)):
    if (start is None)!=(through is None):service.fail(422,"notification_invalid_input")
    return await run_in_threadpool(service.metrics,principal,context,civil(start),civil(through))


@router.post("/excluir")
async def exclude(request:Request,command=Depends(body(ExclusionWrite))):
    from web.settings import get_settings
    from web.rate_limiter_redis import check_rate_limit
    from web.middleware.rate_limiter import get_client_identifier
    settings=get_settings()
    if settings.is_production and not settings.REDIS_URL:service.fail(503,"notification_disabled")
    prefix="rl:notification-exclude36:v1:"
    token_hash=hmac.new(settings.SECRET_KEY.encode(),command.token.encode(),hashlib.sha256).hexdigest()
    for value in ("ip:"+get_client_identifier(request),"token:"+token_hash):
        allowed,info,_=await check_rate_limit(prefix+value,10,900,use_redis=bool(settings.REDIS_URL),sensitive=True)
        if not allowed:service.fail(429,"notification_frequency_limited")
    return await run_in_threadpool(service.exclude,command.token)


@public_router.get("/notificaciones/excluir",response_class=HTMLResponse)
async def confirmation(request:Request):
    # No GET mutation, provider, external asset, PII or account-state lookup.
    nonce=getattr(request.state,"csp_nonce","")
    return HTMLResponse('''<!doctype html><html lang="es"><head><meta charset="utf-8"><script nonce="'''+nonce+'''">(()=>{let token=new URLSearchParams(location.hash.slice(1)).get('token');history.replaceState(null,'',location.pathname);addEventListener('DOMContentLoaded',()=>{const button=document.getElementById('exclude');button.disabled=!/^[A-Za-z0-9_-]{43}$/.test(token||'');button.onclick=async()=>{button.disabled=true;const value=token;token=null;try{const response=await fetch('/api/notificaciones/excluir',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:value})});document.getElementById('result').textContent=response.ok?'Solicitud recibida.':'No pudimos confirmar la solicitud. Abre tus preferencias para revisarla.';}catch{document.getElementById('result').textContent='No pudimos confirmar la solicitud. Abre tus preferencias para revisarla.';}};});addEventListener('pagehide',()=>{token=null;});})();</script><title>Excluir recordatorios</title></head><body><h1>Excluir estos recordatorios</h1><p>Confirma que deseas excluir los recordatorios indicados por este enlace.</p><button id="exclude" disabled>Confirmar exclusión</button><p id="result" role="status"></p></body></html>''',headers=HEADERS)
