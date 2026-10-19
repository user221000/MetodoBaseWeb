"""
api/routes/planes.py — Generación de planes nutricionales con autenticación multi-tenant.

Endpoints:
- POST /api/generar-plan: Genera plan nutricional + PDF
- GET /api/descargar-pdf/{id_cliente}: Descarga último PDF del cliente
"""
import asyncio
import json
import logging
import os

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.schemas import PlanRequest
from web.database.engine import get_db, get_db_readonly
from web.database.tenant_context import tenant_task
from web.auth_deps import get_usuario_actual
from web.database import repository as repo
from web.routes._utils import get_gym_id
from web.services.permissions import verify_permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Planes"])


@router.get("/alimentos/catalogo")
async def listar_catalogo_alimentos():
    """Retorna el catálogo completo de alimentos agrupado por categoría."""
    from config.catalogo_alimentos import CATALOGO_POR_TIPO
    return {
        "categorias": {
            cat: sorted(items)
            for cat, items in CATALOGO_POR_TIPO.items()
        }
    }


@tenant_task("gym_id")
def _generar_plan_sync(gym_id: str, id_cliente: str, plan_numero: int,
                      tipo_plan: str = "menu_fijo", *, reservation_id=None) -> dict:
    from web.services.plan_generation import generate_plan
    return generate_plan(id_cliente, plan_numero, gym_id, tipo_plan, reservation_id=reservation_id)


@router.post("/generar-plan", summary="Generar plan nutricional + PDF")
async def generar_plan(
    data: PlanRequest,
    usuario: dict = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
    request_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """
    Genera un plan nutricional diario para un cliente del gym autenticado.
    La generación es CPU-bound (~5–15 seg); se ejecuta en un thread executor.
    """
    verify_permission(usuario, "create", "plan")
    gym_id = get_gym_id(usuario)
    from web.services.gym_generation_quota import reserve_gym_generation, complete_gym_generation, compensate_generation_failure
    reservation = reserve_gym_generation(db, gym_id, data.model_dump(), request_key)
    if reservation.status == "completed":
        return json.loads(reservation.result_json)
    reservation_id = reservation.id
    try:
        resultado = await asyncio.to_thread(
            _generar_plan_sync, gym_id, data.id_cliente, data.plan_numero, data.tipo_plan,
            reservation_id=reservation_id,
        )
        resultado = complete_gym_generation(db, gym_id, reservation_id, resultado)
        logger.info("Plan generado para cliente: %s (gym: %s)", data.id_cliente, gym_id)
        return resultado
    except ValueError:
        compensate_generation_failure(db, gym_id, reservation_id)
        raise HTTPException(status_code=422, detail={"code": "generation_unavailable",
            "message": "No fue posible generar el plan con estos datos."}) from None
    except Exception as exc:
        compensate_generation_failure(db, gym_id, reservation_id)
        logger.error("Plan generation failed class=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail={"code": "generation_failed",
            "message": "No fue posible generar el plan. Consulta el historial antes de reintentar."}) from None


@router.get("/descargar-pdf/{id_cliente}", summary="Descargar último PDF del cliente")
async def descargar_pdf(
    id_cliente: str,
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    """Descarga el PDF del plan más reciente del cliente (verificando pertenencia al gym)."""
    verify_permission(usuario, "read", "plan")
    gym_id = get_gym_id(usuario)
    
    # Verificar que el cliente pertenece al gym
    cliente = repo.obtener_cliente(db, gym_id, id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener historial de planes
    historial = repo.obtener_historial_planes(db, gym_id, id_cliente, limite=1)
    if not historial:
        raise HTTPException(
            status_code=404, detail="No hay planes generados para este cliente"
        )

    from web.routes.planes import descargar_pdf_plan
    return descargar_pdf_plan(plan_id=historial[0]["id"], usuario=usuario, db=db)
