"""Authenticated R30 read adapter; no collector, subjects or UI selectors."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web import product_analytics_domain as domain
from web.services import product_analytics as service

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def query_values(request):
    pairs = list(request.query_params.multi_items())
    if any(key not in {"context", "from", "through"} for key, _ in pairs) or len({key for key, _ in pairs}) != len(pairs):
        service.fail(422, "analytics_invalid_input")
    values = dict(pairs)
    if values.get("context") not in ("gym", "personal"):
        service.fail(422, "analytics_invalid_input")
    try:
        domain.period(values.get("from"), values.get("through"))
    except domain.AnalyticsInput:
        service.fail(422, "analytics_invalid_input")
    return values


class AnalyticsRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                # Unknown/duplicated selectors fail before auth dependency I/O.
                request.state.product_analytics_query = query_values(request)
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code,
                    headers={**HEADERS, **(error.headers or {})})
            except Exception as error:
                logger.error("Analytics route unavailable class=%s", type(error).__name__)
                return JSONResponse({"detail": {"code": "analytics_unavailable",
                    "message": "No pudimos confirmar la consulta. Vuelve a consultarla desde tu cuenta."}},
                    status_code=503, headers=HEADERS)
            response.headers.update(HEADERS)
            return response
        return handle


router = APIRouter(tags=["Hechos de uso observados"], route_class=AnalyticsRoute)


@router.get("/analytics/producto")
@router.get("/analytics/producto/", include_in_schema=False)
async def report(request: Request, principal=Depends(get_usuario_actual)):
    values = request.state.product_analytics_query
    # No configured build commit currently exists: explicit unavailable metadata,
    # not a source checkout lookup or hardcoded implementation revision.
    return await run_in_threadpool(service.read_report, principal, values["context"],
                                  values.get("from"), values.get("through"))
