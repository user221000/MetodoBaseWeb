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

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class RoutineRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code,
                                    headers={**HEADERS, **(error.headers or {})})
            except RequestValidationError:
                return JSONResponse({"detail": {"code": "routine_invalid_context",
                    "message": "Elige el espacio de tu cuenta."}}, status_code=422, headers=HEADERS)
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


def _read(principal, context):
    from web.database.engine import SessionLocal
    from web.services.routine_catalog import catalog_for_subject
    db = SessionLocal()
    try:
        result = catalog_for_subject(db, principal, context)
    finally:
        try:
            db.close()
        except Exception:
            try:
                db.invalidate()
            except Exception:
                logger.error("Routine owned-session invalidation unavailable")
            raise RuntimeError("Routine owned-session cleanup unavailable") from None
    return result


@router.get("/rutinas/catalogo")
async def catalog(context: Literal["gym", "personal"] = Query(...),
                  principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_read, principal, context)


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
