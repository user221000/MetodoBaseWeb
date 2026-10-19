"""Real adapters for wire34; bounded input and no success after cleanup failure."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import TypeAdapter
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web.followup_schemas import CreateTask, EditTask, CompleteTask, CancelTask, CivilDate, ResourceId, Status, KEY
from web.services import followup_tasks as service
from web.services.followup_domain import UUID

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class TaskRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def private(request):
            try:
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code, headers={**HEADERS, **(error.headers or {})})
            except RequestValidationError:
                return JSONResponse({"detail": {"code": "followup_invalid_input", "message": "Revisa los campos solicitados."}}, status_code=422, headers=HEADERS)
            except Exception as error:
                logger.error("Follow-up route unconfirmed class=%s", type(error).__name__)
                return JSONResponse({"detail": {"code": "followup_unconfirmed", "message": "Consulta el estado autorizado antes de continuar."}}, status_code=503, headers=HEADERS)
            response.headers.update(HEADERS)
            return response
        return private


router = APIRouter(prefix="/seguimiento", tags=["Tareas operativas"], route_class=TaskRoute)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate task input")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Nonfinite task input")


def body(schema):
    adapter = TypeAdapter(schema)
    async def parse(request: Request):
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            service.fail(415, "followup_invalid_input")
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk) > 8192:
                service.fail(413, "followup_body_limit")
            raw.extend(chunk)
        try:
            return adapter.validate_python(json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs, parse_constant=_constant))
        except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
            service.fail(422, "followup_invalid_input")
    return parse


def request_key(request: Request):
    keys = request.headers.getlist("Idempotency-Key")
    if len(keys) != 1 or not UUID.fullmatch(keys[0]):
        service.fail(422, "followup_invalid_input")
    return keys[0]


def _invoke(function, *args, **kwargs):
    from web.database.engine import SessionLocal
    # This Session never escapes. No yield finalizer/commit follows headers.
    db = SessionLocal()
    db.expire_on_commit = True
    try:
        try:
            return function(db, *args, **kwargs)
        except Exception as error:
            service.rollback(db)
            try:
                service.classify_error(error)
            except HTTPException:
                raise
            except Exception:
                if function is not service.mutate:
                    logger.error("Follow-up read unavailable class=%s", type(error).__name__)
                    service.fail(503, "followup_unavailable")
                raise
    finally:
        service.close_owned_session(db)


def identifier():
    return Path(min_length=36, max_length=36, pattern=KEY)


@router.get("/contexto")
async def context(principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_invoke, service.context, principal)


@router.get("/clientes/{client_id}/candidatos")
async def candidates(client_id: ResourceId, principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_invoke, service.candidates, principal, client_id)


@router.get("/responsables")
async def assignees(principal=Depends(get_usuario_actual), limit: int=Query(20, ge=1, le=50), after: ResourceId | None=None):
    return await run_in_threadpool(_invoke, service.assignees, principal, limit, after)


@router.get("/metricas")
async def metrics(principal=Depends(get_usuario_actual), start: CivilDate | None=Query(None, alias="from"), through: CivilDate | None=None):
    return await run_in_threadpool(_invoke, service.metrics, principal, start, through)


@router.get("/tareas")
async def tasks(principal=Depends(get_usuario_actual), status: Status="open", limit: int=Query(50, ge=1, le=100), after: str | None=Query(None, max_length=256)):
    return await run_in_threadpool(_invoke, service.list_tasks, principal, status, limit, after)


@router.get("/tareas/{task_id}")
async def read(task_id: str=identifier(), principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_invoke, service.read_task, principal, task_id)


@router.get("/tareas/{task_id}/historial")
async def history(task_id: str=identifier(), principal=Depends(get_usuario_actual), limit: int=Query(20, ge=1, le=50), after_version: int=Query(0, ge=0, le=2147483647)):
    return await run_in_threadpool(_invoke, service.history, principal, task_id, limit, after_version)


@router.post("/tareas")
async def create(principal=Depends(get_usuario_actual), command=Depends(body(CreateTask)), key=Depends(request_key)):
    return await run_in_threadpool(_invoke, service.mutate, principal, "created", command, key, "/api/seguimiento/tareas")


@router.patch("/tareas/{task_id}")
async def edit(task_id: str=identifier(), principal=Depends(get_usuario_actual), command=Depends(body(EditTask)), key=Depends(request_key)):
    return await run_in_threadpool(_invoke, service.mutate, principal, "updated", command, key, "/api/seguimiento/tareas/"+task_id, identifier=task_id)


@router.post("/tareas/{task_id}/completar")
async def complete(task_id: str=identifier(), principal=Depends(get_usuario_actual), command=Depends(body(CompleteTask)), key=Depends(request_key)):
    return await run_in_threadpool(_invoke, service.mutate, principal, "completed", command, key, "/api/seguimiento/tareas/"+task_id+"/completar", identifier=task_id)


@router.post("/tareas/{task_id}/cancelar")
async def cancel(task_id: str=identifier(), principal=Depends(get_usuario_actual), command=Depends(body(CancelTask)), key=Depends(request_key)):
    return await run_in_threadpool(_invoke, service.mutate, principal, "cancelled", command, key, "/api/seguimiento/tareas/"+task_id+"/cancelar", identifier=task_id)
