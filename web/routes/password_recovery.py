"""Public bounded credential recovery; no token is returned to the caller."""
from contextlib import asynccontextmanager
import hashlib
import hmac
import re

from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel,ConfigDict,Field,TypeAdapter,ValidationError,field_validator,model_validator

from web.account_values import normalize_account_email,validate_new_password
from web.middleware.rate_limiter import get_client_identifier
from web.services import password_recovery as service
from web.services.recovery_dispatcher import RecoveryDispatcher

MAX_BODY_BYTES=4096
HEADERS={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'}


class RecoveryRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def private_response(request):
            try:
                response=await original(request)
            except HTTPException as error:
                # The web factory's historical HTTP handler omits exception
                # headers. Own this new route's generic errors so privacy and
                # Retry-After survive without changing existing routes.
                return JSONResponse({'detail':error.detail},status_code=error.status_code,
                    headers={**HEADERS,**(error.headers or {})})
            response.headers.update(HEADERS)
            return response
        return private_response


@asynccontextmanager
async def lifespan(app):
    existing=getattr(app.state,'recovery_dispatcher',None)
    dispatcher=existing or RecoveryDispatcher()
    app.state.recovery_dispatcher=dispatcher
    try:
        yield
    finally:
        if existing is None:
            dispatcher.close()


router=APIRouter(prefix='/auth/password-reset',tags=['Recuperacion de cuenta'],lifespan=lifespan,
    route_class=RecoveryRoute)


class RecoveryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email:str=Field(min_length=3,max_length=255)

    @field_validator('email')
    @classmethod
    def email_value(cls,value):
        value=normalize_account_email(value)
        if len(value)>255 or value.count('@')!=1 or not all(value.split('@')) or any(ord(c)<33 or ord(c)==127 for c in value):
            raise ValueError('Invalid account email')
        return value


class RecoveryConfirm(BaseModel):
    model_config=ConfigDict(extra='forbid')
    token:str=Field(min_length=1,max_length=256)
    new_password:str=Field(min_length=12,max_length=128)
    confirm_password:str=Field(min_length=12,max_length=128)

    @field_validator('new_password','confirm_password')
    @classmethod
    def password_value(cls,value):
        return validate_new_password(value)

    @model_validator(mode='after')
    def confirmation(self):
        if self.new_password!=self.confirm_password:
            raise ValueError('Password confirmation differs')
        return self


def bounded_body(model):
    adapter=TypeAdapter(model)
    async def parse(request:Request):
        if request.headers.get('content-type','').split(';',1)[0].strip().lower()!='application/json':
            raise HTTPException(415,{'code':'password_reset_invalid_input','message':'Usa una solicitud JSON valida.'})
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BODY_BYTES:
                raise HTTPException(413,{'code':'password_reset_body_limit','message':'La solicitud supera el volumen permitido.'})
            raw.extend(chunk)
        try:
            return adapter.validate_json(raw)
        except (ValidationError,ValueError,TypeError):
            raise HTTPException(422,{'code':'password_reset_invalid_input','message':'Revisa los campos y la contraseña (12 caracteres y hasta 72 bytes UTF-8).'}) from None
    return parse


async def enforce_limit(request,*,account=None,token=None):
    from web.settings import get_settings
    from web.rate_limiter_redis import check_rate_limit
    settings=get_settings()
    if settings.is_production and not settings.REDIS_URL:
        raise HTTPException(503,{'code':'password_reset_service_unavailable','message':'La recuperacion no esta disponible temporalmente.'})
    purpose='request' if account is not None else 'confirm'
    prefix='rl:recovery-v1:'+purpose
    keys=[(prefix+':ip:'+get_client_identifier(request),5 if account is not None else 10)]
    value=account if account is not None else token
    kind='account' if account is not None else 'token'
    hashed=hmac.new(settings.SECRET_KEY.encode('utf-8'),(prefix+':'+value).encode('utf-8'),hashlib.sha256).hexdigest()
    keys.append((prefix+':'+kind+':'+hashed,3 if account is not None else 10))
    for key,limit in keys:
        allowed,info,_=await check_rate_limit(key,limit,900,use_redis=bool(settings.REDIS_URL),sensitive=True)
        if not allowed:
            raise HTTPException(429,{'code':'password_reset_rate_limited','message':'Espera antes de volver a intentarlo.'},
                headers={'Retry-After':str(info['retry_after'])})


@router.post('/request',status_code=202)
async def request_reset(request:Request,data=Depends(bounded_body(RecoveryRequest))):
    from web.settings import get_settings
    origin=service.request_configuration(get_settings())
    await enforce_limit(request,account=data.email)
    dispatcher=getattr(request.app.state,'recovery_dispatcher',None)
    if dispatcher is None or not dispatcher.submit(service.issue_request,data.email,origin):
        raise HTTPException(503,{'code':'password_reset_service_unavailable','message':'La recuperacion no esta disponible temporalmente.'})
    return JSONResponse({'code':'password_reset_request_received',
        'message':'Si la cuenta puede recuperarse, se intentara enviar un enlace.'},status_code=202,headers=HEADERS)


@router.post('/confirm')
async def confirm_reset(request:Request,data=Depends(bounded_body(RecoveryConfirm))):
    await enforce_limit(request,token=data.token)
    # Database/bcrypt are synchronous work; keep them out of the event loop.
    from starlette.concurrency import run_in_threadpool
    def change():
        from web.database.engine import SessionLocal
        with SessionLocal() as db:
            return service.consume(db,data.token,data.new_password)
    recipient,name=await run_in_threadpool(change)
    dispatcher=getattr(request.app.state,'recovery_dispatcher',None)
    if dispatcher is None or not dispatcher.submit(service.notify_changed,recipient,name):
        service.note('notification_unconfirmed')
    return JSONResponse({'code':'password_reset_complete','message':'La contraseña fue actualizada. Inicia sesion.'},headers=HEADERS)
