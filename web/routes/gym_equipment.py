"""Bounded per-gym inventory; owners save, authorised team members read."""
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_usuario_actual

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}
MachineId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")]


class InventoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    machine_ids: list[MachineId] = Field(max_length=128)
    expected_revision: Annotated[int, Field(strict=True, ge=0, le=2147483646)]

    @field_validator("machine_ids")
    @classmethod
    def unique(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Repeated machine")
        return value


class EquipmentRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                if request.method == "PUT":
                    receive, received = request.receive, 0

                    async def bounded_receive():
                        nonlocal received
                        message = await receive()
                        if message["type"] == "http.request":
                            received += len(message.get("body", b""))
                            if received > 16384:
                                raise HTTPException(413, {"code": "gym_equipment_too_large",
                                    "message": "Reduce la selección de máquinas e inténtalo de nuevo."})
                        return message

                    request = Request(request.scope, receive=bounded_receive)
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code,
                                    headers={**HEADERS, **(error.headers or {})})
            except RequestValidationError:
                return JSONResponse({"detail": {"code": "gym_equipment_invalid",
                    "message": "Revisa la selección de máquinas."}}, status_code=422, headers=HEADERS)
            except Exception as error:
                logger.error("Gym equipment unavailable class=%s", type(error).__name__)
                return JSONResponse({"detail": {"code": "gym_equipment_unavailable",
                    "message": "No pudimos consultar el equipamiento. Vuelve a intentarlo."}},
                    status_code=503, headers=HEADERS)
            response.headers.update(HEADERS)
            return response
        return handle


router = APIRouter(tags=["Equipamiento del gimnasio"], route_class=EquipmentRoute)


def _operate(save, principal, context, data=None):
    from web.database.engine import SessionLocal
    from web.services.gym_equipment import inventory_for_subject, save_inventory_for_subject
    db = SessionLocal()
    try:
        if save:
            return save_inventory_for_subject(db, principal, context, data.machine_ids, data.expected_revision)
        return inventory_for_subject(db, principal, context)
    finally:
        try:
            db.close()
        except Exception:
            try:
                db.invalidate()
            except Exception:
                logger.error("Gym equipment owned-session invalidation unavailable")
            raise RuntimeError("Gym equipment owned-session cleanup unavailable") from None


@router.get("/rutinas/equipamiento")
async def get_inventory(context: Literal["gym"] = Query(...), principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_operate, False, principal, context)


@router.put("/rutinas/equipamiento")
async def put_inventory(data: InventoryUpdate, context: Literal["gym"] = Query(...),
                        principal=Depends(get_usuario_actual)):
    return await run_in_threadpool(_operate, True, principal, context, data)
