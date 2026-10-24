"""Explicit v2 routes; v1 parser, dictionary and validation remain unchanged."""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual
from web.routes.client_links import body
from web.routes.product_analytics import HEADERS, query_values, unavailable
from web.services import product_analytics_v2 as service

logger = logging.getLogger(__name__)


class OriginChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Literal["unknown", "demo", "customer"]
    expected_version: StrictInt = Field(ge=0, le=2147483646)


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                request.state.product_v2_query = query_values(request) if self.name == 'report' else _origin_query(request)
                response = await original(request)
            except HTTPException as error:
                if error.status_code >= 500:
                    return unavailable()
                return JSONResponse({"detail": error.detail}, status_code=error.status_code, headers=HEADERS)
            except RequestValidationError:
                return JSONResponse({"detail": {"code": "analytics_invalid_input"}}, status_code=422, headers=HEADERS)
            except Exception as error:  # noqa: BLE001 -- private boundary never reflects values or driver errors
                logger.error("Product v2 unavailable class=%s", type(error).__name__)
                return unavailable()
            response.headers.update(HEADERS)
            return response
        return handle


router = APIRouter(tags=["Procedencia y hechos observados v2"], route_class=PrivateRoute)


def _origin_query(request):
    pairs = list(request.query_params.multi_items())
    if any(k not in ("context", "client") for k, _ in pairs) or len(dict(pairs)) != len(pairs):
        service.authority.fail(422, "analytics_invalid_input")
    values = dict(pairs)
    if values.get("context") not in ("gym", "personal"):
        service.authority.fail(422, "analytics_invalid_input")
    return values


def _origin(principal, values, change=None):
    from web.database.engine import SessionLocal
    token = service.current_tenant.set('')
    try:
        with SessionLocal() as db:
            return service.origin(db, principal, values["context"], values.get("client"),
                **({"value": change.origin, "expected_version": change.expected_version} if change else {}))
    finally:
        service.current_tenant.reset(token)


@router.get("/analytics/producto/v2")
async def report(request: Request, principal=Depends(get_usuario_actual)):
    values = request.state.product_v2_query
    return await run_in_threadpool(service.read_report, principal, values["context"], values.get("from"), values.get("through"))


@router.get("/analytics/procedencia")
async def origin(request: Request, principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_origin, principal, request.state.product_v2_query)


@router.post("/analytics/procedencia")
async def declare_origin(request: Request, principal=Depends(get_usuario_actual), change=Depends(body(OriginChange))):
    return await run_in_threadpool(_origin, principal, request.state.product_v2_query, change)
