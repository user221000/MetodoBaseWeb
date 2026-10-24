"""Shared Web/API adapter: self requests, explicit closure and bounded export."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from web.auth_deps import get_usuario_actual
from web.database.engine import get_db_readonly
from web.routes.account_security import AccountRoute, parse, rate_limit
from web.routes.mfa import access
from web.privacy_schemas import PrivacyRequestInput, PrivacyClosureInput
from web.services import account_privacy
from web.services.privacy_facts_export import export_personal_facts
from web.services.privacy_export import MAX_PAGE_SIZE

router=APIRouter(prefix='/account/privacy',tags=['Privacidad de cuenta'],route_class=AccountRoute)
Actor=Annotated[dict,Depends(get_usuario_actual)]
RequestId=Annotated[str,Path(pattern=r'^[0-9a-f]{32}$')]


@router.post('/requests',status_code=201)
async def request_disposition(request:Request,actor:Actor):
    data=await parse(request,PrivacyRequestInput)
    await rate_limit(request,actor=actor)
    return await run_in_threadpool(account_privacy.create_request,actor,data.idempotency_key)


@router.get('/requests/{request_id}')
def request_status(request_id:RequestId,actor:Actor):
    return account_privacy.read_request(actor,request_id)


@router.post('/requests/{request_id}/close-account')
async def close_account(request:Request,request_id:RequestId,actor:Actor):
    data=await parse(request,PrivacyClosureInput)
    await rate_limit(request,actor=actor)
    provider=getattr(request.app.state,'privacy_policy_provider',None)
    return await run_in_threadpool(account_privacy.close_account,actor,access(request),request_id,
        data.expected_version,data.reauthentication_token,code=data.code,recovery_code=data.recovery_code,
        policy_provider=provider)


@router.get('/personal-facts')
def personal_facts(actor:Actor,db:Annotated[Session,Depends(get_db_readonly)],
    limit:Annotated[int,Query(ge=1,le=MAX_PAGE_SIZE)]=100,
    after:Annotated[str|None,Query(pattern=r'^[0-9A-Fa-f]{32}$')]=None):
    return JSONResponse(export_personal_facts(db,actor['id'],limit=limit,after=after),headers={
        'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff',
        'Content-Disposition':'attachment; filename="metodobase-hechos-personales.json"'})
