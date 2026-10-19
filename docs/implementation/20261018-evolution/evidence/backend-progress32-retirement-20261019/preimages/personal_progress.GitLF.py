"""Private R25 adapters; bounded stream input and service-owned transactions."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import TypeAdapter
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web.personal_progress_schemas import MeasurementWrite, MeasurementWithdraw, ConsentGrant, ConsentWithdraw, CivilDate
from web.services import personal_progress as own, progress_share as sharing, progress_readers as readers

MAX_BODY_BYTES=8192
HEADERS={"Cache-Control":"no-store","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff"}
UUID=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
logger=logging.getLogger(__name__)


class ProgressRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def private(request):
            try:response=await original(request)
            except HTTPException as error:return JSONResponse({"detail":error.detail},status_code=error.status_code,headers={**HEADERS,**(error.headers or {})})
            except RequestValidationError:return JSONResponse({"detail":{"code":"progress_invalid_input","message":"Revisa los campos solicitados."}},status_code=422,headers=HEADERS)
            except Exception as error:
                logger.error("Progress route class=%s",type(error).__name__)
                return JSONResponse({"detail":{"code":"progress_unconfirmed","message":"Consulta el estado autorizado antes de continuar."}},status_code=503,headers=HEADERS)
            response.headers.update(HEADERS);return response
        return private


router=APIRouter(tags=["Progreso y consentimiento personal"],route_class=ProgressRoute)


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError("Duplicate progress input")
        result[key]=value
    return result


def _constant(_):raise ValueError("Nonfinite progress input")


def body(schema):
    adapter=TypeAdapter(schema)
    async def parse(request:Request):
        if request.headers.get("content-type","").split(";",1)[0].strip().lower()!="application/json":own.fail(415,"progress_invalid_input")
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BODY_BYTES:own.fail(413,"progress_volume_limit")
            raw.extend(chunk)
        try:return adapter.validate_python(json.loads(raw,object_pairs_hook=_pairs,parse_constant=_constant))
        except (ValueError,TypeError,UnicodeError,RecursionError,OverflowError):own.fail(422,"progress_invalid_input")
    return parse


def _invoke(function,*args,**kwargs):
    from web.database.engine import SessionLocal
    # No autocommit dependency finalizer after the service's confirmed commit.
    with SessionLocal() as db:return function(db,*args,**kwargs)


def key_path():return Path(min_length=36,max_length=36,pattern=UUID)


@router.get("/usuario/progreso/contexto")
async def context(principal=Depends(get_usuario_actual),limit:int=Query(100,ge=1,le=100),after:str|None=Query(None,min_length=1,max_length=36)):
    return await run_in_threadpool(_invoke,own.read_context,principal,limit=limit,after=after)


@router.get("/usuario/progreso/mediciones")
async def measurements(principal=Depends(get_usuario_actual),source_profile_id:str=Query(...,pattern=UUID),
        start:CivilDate|None=Query(None,alias="from"),through:CivilDate|None=None,limit:int=Query(100,ge=1,le=100),cursor:str|None=Query(None,max_length=512)):
    return await run_in_threadpool(_invoke,own.list_measurements,principal,source_profile_id,start=start,end=through,limit=limit,cursor=cursor)


@router.get("/usuario/progreso/mediciones/{record_key}")
async def measurement(record_key:str=key_path(),principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_invoke,own.read_measurement,principal,record_key)


@router.put("/usuario/progreso/mediciones/{record_key}")
async def put_measurement(record_key:str=key_path(),principal=Depends(get_usuario_actual),command=Depends(body(MeasurementWrite))):
    return await run_in_threadpool(_invoke,own.write_measurement,principal,record_key,command)


@router.post("/usuario/progreso/mediciones/{record_key}/retirar")
async def remove_measurement(record_key:str=key_path(),principal=Depends(get_usuario_actual),command=Depends(body(MeasurementWithdraw))):
    return await run_in_threadpool(_invoke,own.withdraw_measurement,principal,record_key,command)


@router.get("/usuario/progreso/completados")
async def completion(principal=Depends(get_usuario_actual),start:CivilDate|None=Query(None,alias="from"),through:CivilDate|None=None):
    return await run_in_threadpool(_invoke,readers.own_completion,principal,start=start,end=through)


@router.get("/usuario/progreso/consentimientos")
async def consents(principal=Depends(get_usuario_actual),limit:int=Query(100,ge=1,le=100),after:str|None=Query(None,pattern=UUID)):
    return await run_in_threadpool(_invoke,sharing.list_own_consents,principal,limit=limit,after=after)


@router.get("/usuario/vinculos/{link_id}/progreso/consentimiento")
async def consent(link_id:str=key_path(),principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_invoke,sharing.read_own_consent,principal,link_id)


@router.put("/usuario/vinculos/{link_id}/progreso/consentimiento")
async def put_consent(link_id:str=key_path(),principal=Depends(get_usuario_actual),command=Depends(body(ConsentGrant))):
    return await run_in_threadpool(_invoke,sharing.grant_consent,principal,link_id,command)


@router.post("/usuario/vinculos/{link_id}/progreso/consentimiento/retirar")
async def remove_consent(link_id:str=key_path(),principal=Depends(get_usuario_actual),command=Depends(body(ConsentWithdraw))):
    return await run_in_threadpool(_invoke,sharing.withdraw_consent,principal,link_id,command)


@router.get("/clientes/{client_id}/progreso")
async def professional_history(client_id:str=Path(min_length=1,max_length=36),principal=Depends(get_usuario_actual),
        limit:int=Query(100,ge=1,le=100),after:int=Query(0,ge=0)):
    return await run_in_threadpool(_invoke,readers.native_progress,principal,client_id,limit=limit,after=after)


@router.get("/clientes/{client_id}/vinculacion/{link_id}/progreso/contexto")
async def professional_consent(client_id:str=Path(min_length=1,max_length=36),link_id:str=key_path(),principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_invoke,sharing.read_professional_consent,principal,client_id,link_id)


@router.get("/clientes/{client_id}/vinculacion/{link_id}/progreso")
async def professional_progress(client_id:str=Path(min_length=1,max_length=36),link_id:str=key_path(),principal=Depends(get_usuario_actual),
        expected_consent_id:str=Query(...,pattern=UUID),expected_version:int=Query(...,ge=1,le=2147483647),
        expected_link_version:int=Query(...,ge=1,le=2147483647),start:CivilDate|None=Query(None,alias="from"),through:CivilDate|None=None,
        limit:int=Query(100,ge=1,le=100),after:str|None=Query(None,pattern=UUID)):
    return await run_in_threadpool(_invoke,readers.shared_projection,principal,client_id,link_id,expected_id=expected_consent_id,
        expected_version=expected_version,expected_link=expected_link_version,start=start,end=through,limit=limit,after=after)
