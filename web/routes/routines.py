"""Generic PPL catalogue API plus inert browser-authenticated page shells."""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web.routes.pages import templates
from web.template_compat import template_response
from web.schemas_routines import RoutineRequirements

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class RoutineRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                if request.method == "POST" and request.url.path.endswith("/rutinas/generar"):
                    receive, received = request.receive, 0

                    async def bounded_receive():
                        nonlocal received
                        message = await receive()
                        if message["type"] == "http.request":
                            received += len(message.get("body", b""))
                            if received > 16384:
                                raise HTTPException(413, {"code": "routine_request_too_large",
                                    "message": "Reduce la selección de ejercicios e inténtalo de nuevo."})
                        return message

                    request = Request(request.scope, receive=bounded_receive)
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code,
                                    headers={**HEADERS, **(error.headers or {})})
            except RequestValidationError:
                generating = request.url.path.endswith("/rutinas/generar")
                return JSONResponse({"detail": {"code": "routine_invalid_requirements" if generating else "routine_invalid_context",
                    "message": "Revisa las opciones de tu rutina." if generating else "Elige el espacio de tu cuenta."}}, status_code=422, headers=HEADERS)
            except Exception as error:
                logger.error("Routine catalogue unavailable class=%s", type(error).__name__)
                return JSONResponse({"detail": {"code": "routine_unavailable",
                    "message": "No pudimos consultar las rutinas. Vuelve a intentarlo desde tu cuenta."}},
                    status_code=503, headers=HEADERS)
            response.headers.update(HEADERS)
            return response
        return handle


router = APIRouter(tags=["Rutinas generales"], route_class=RoutineRoute)
pages_router = APIRouter(include_in_schema=False)


def _operate(operation, principal, context, *args, **kwargs):
    from web.database.engine import SessionLocal
    from web.services import routine_catalog
    db = SessionLocal()
    try:
        result = getattr(routine_catalog, operation)(db, principal, context, *args, **kwargs)
    finally:
        try:
            db.close()
        except Exception:
            try:
                db.invalidate()
            except Exception:
                logger.error("Routine owned-session invalidation unavailable")
            raise RuntimeError("Routine owned-session cleanup unavailable") from None
    if operation == "generate_for_subject" and context == "gym":
        _operate("confirm_inventory_current", principal, context, result["program"]["inventory"])
    return result


def _read(principal, context):
    return _operate("catalog_for_subject", principal, context)


@router.get("/rutinas/catalogo")
async def catalog(context: Literal["gym", "personal"] = Query(...),
                  principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_read, principal, context)


@router.get("/rutinas/ejercicios")
async def exercises(context: Literal["gym", "personal"] = Query(...),
                    principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_operate, "exercises_for_subject", principal, context)


@router.post("/rutinas/generar")
async def generate(requirements: RoutineRequirements,
                   context: Literal["gym", "personal"] = Query(...),
                   principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_operate, "generate_for_subject", principal, context, requirements.model_dump(exclude_none=True))


@router.get("/rutinas/clientes")
async def clients(context: Literal["gym", "personal"] = Query(...),
                  q: str = Query("", max_length=80, pattern=r"^[^\x00-\x1f\x7f]*$"), limit: int = Query(30, ge=1, le=50),
                  offset: int = Query(0, ge=0, le=100000), principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_operate, "clients_for_subject", principal, context,
                                  query=q, limit=limit, offset=offset)


@router.get("/rutinas/requisitos")
async def requirements(context: Literal["gym", "personal"] = Query(...),
                       client_id: str | None = Query(None, min_length=1, max_length=36, pattern=r"^[^\x00-\x1f\x7f]+$"),
                       principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_operate, "requirements_for_subject", principal, context, client_id)


@pages_router.get("/rutinas")
@pages_router.get("/rutinas/")
@pages_router.get("/mis-rutinas")
@pages_router.get("/mis-rutinas/")
async def routine_page(request: Request):
    # No identity, catalogue or secret is embedded; navigation uses RAM bearer
    # bootstrap and the dedicated authenticated API before enabling the panel.
    personal = request.url.path.rstrip("/") == "/mis-rutinas"
    return template_response(templates, request,
        "rutinas_personal.html" if personal else "rutinas.html",
        {"request": request, "routine_scope": "personal" if personal else "gym"},
    )
