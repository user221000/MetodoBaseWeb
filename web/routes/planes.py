"""
web/routes/planes.py — Generación de planes con multi-tenant.

La generación usa el servicio compartido y el motor core/ en un thread pool.
La cuota se reserva antes de CPU y la publicación vincula plan/consumo en una
transacción. Las descargas requieren el principal vigente y propiedad del plan.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header, Path as PathParam
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from web.schemas import PlanRequest
from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.database.engine import get_db, get_db_readonly
from web.database.tenant_context import tenant_task
from web.database import repository as repo
from web.services.permissions import verify_permission
from web.routes._utils import get_gym_id
from web.constants import (
    DEFAULT_PAGE_SIZE_PLANES, MAX_PAGE_SIZE_PLANES,
    PERIODO_SEMANA_DIAS, PERIODO_MES_DIAS, PERIODO_ANIO_DIAS,
    ERR_CLIENTE_NO_ENCONTRADO,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Planes"])


@router.get("/alimentos/catalogo")
async def listar_catalogo_alimentos():
    """Retorna el catálogo completo de alimentos agrupado por categoría."""
    from web.catalogo import CATALOGO_POR_TIPO
    return {
        "categorias": {
            cat: sorted(items)
            for cat, items in CATALOGO_POR_TIPO.items()
        }
    }


# Compatibility boundary for existing callers and request-level tests.
from web.services.plan_generation import build_plan as _do_generar_plan


@tenant_task("gym_id")
def _generar_plan_sync(id_cliente: str, plan_numero: int, gym_id: str,
                      tipo_plan: str = "menu_fijo", *, reservation_id=None) -> dict:
    from web.services.plan_generation import generate_plan
    return generate_plan(id_cliente, plan_numero, gym_id, tipo_plan,
        reservation_id=reservation_id, builder=_do_generar_plan)


@router.post("/generar-plan", summary="Generar plan nutricional + PDF")
async def generar_plan(
    data: PlanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
    request_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    verify_permission(usuario, "create", "plan")
    gym_id = get_gym_id(usuario)
    from web.services.gym_generation_quota import reserve_gym_generation, complete_gym_generation, compensate_generation_failure
    reservation = reserve_gym_generation(db, gym_id, data.model_dump(), request_key)
    if reservation.status == "completed":
        return json.loads(reservation.result_json)
    reservation_id = reservation.id

    try:
        resultado = await asyncio.to_thread(
            _generar_plan_sync,
            data.id_cliente,
            data.plan_numero,
            gym_id,
            data.tipo_plan,
            reservation_id=reservation_id,
        )
        resultado = complete_gym_generation(db, gym_id, reservation_id, resultado)
        logger.info("Plan generado: %s", data.id_cliente)

        # Email de notificación al gym (background task, no bloquea respuesta)
        from web.services.plan_notifications import notify_plan_generated
        background_tasks.add_task(
            notify_plan_generated,
            email=usuario["email"],
            nombre_cliente=resultado.get("nombre", data.id_cliente),
            gym_id=gym_id,
            plan_id=resultado["plan_id"],
        )

        return resultado
    except ValueError:
        compensate_generation_failure(db, gym_id, reservation_id)
        raise HTTPException(status_code=422, detail={
            "code": "generation_unavailable",
            "message": "No fue posible generar el plan con estos datos y exclusiones. Revisa el perfil.",
        }) from None
    except Exception as exc:
        compensate_generation_failure(db, gym_id, reservation_id)
        # Exception messages can contain SQL parameters, paths or health notes.
        logger.error("Plan generation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail={
            "code": "generation_failed",
            "message": "No fue posible generar el plan. Consulta el historial antes de reintentar.",
        }) from None


@router.get("/descargar-pdf/{id_cliente}", summary="Descargar último PDF")
async def descargar_pdf(
    id_cliente: str,
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "plan")
    gym_id = get_gym_id(usuario)
    planes = repo.obtener_historial_planes(db, gym_id, id_cliente, limite=1)
    if not planes:
        raise HTTPException(404, "No hay planes generados para este cliente")

    return descargar_pdf_plan(plan_id=planes[0]["id"], usuario=usuario, db=db)


@router.get("/planes/{plan_id}/pdf", summary="Descargar PDF de un plan concreto")
def descargar_pdf_plan(
    plan_id: int = PathParam(..., gt=0, le=2147483647),
    usuario: dict = Depends(get_usuario_actual),
    db: Session = Depends(get_db_readonly),
):
    """Authorize the exact plan/client and return a private bounded PDF read."""
    verify_permission(usuario, "read", "plan")
    from web.services.plan_documents import read_plan_pdf
    content = read_plan_pdf(db, get_gym_id(usuario), plan_id)
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="plan.pdf"',
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    })


# ── Listado e historial de planes ───────────────────────────────────────────

from typing import Optional
from fastapi import Query
from sqlalchemy import func
from web.database.models import PlanGenerado, Cliente
from datetime import timedelta


@router.get("/planes", summary="Listar planes generados")
def listar_planes(
    limite: int = Query(DEFAULT_PAGE_SIZE_PLANES, ge=1, le=MAX_PAGE_SIZE_PLANES),
    offset: int = Query(0, ge=0),
    id_cliente: Optional[str] = Query(None, description="Filtrar por cliente"),
    periodo: Optional[str] = Query(None, description="semana|mes|anio"),
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    """Lista planes del gym ordenados por fecha descendente."""
    verify_permission(usuario, "read", "plan")
    gym_id = get_gym_id(usuario)
    
    # Query base
    q = db.query(PlanGenerado).filter(PlanGenerado.gym_id == gym_id)
    
    # Filtro por cliente
    if id_cliente:
        q = q.filter(PlanGenerado.id_cliente == id_cliente)
    
    # Filtro por período
    ahora = datetime.now(timezone.utc)
    if periodo == "semana":
        fecha_inicio = ahora - timedelta(days=PERIODO_SEMANA_DIAS)
        q = q.filter(PlanGenerado.fecha_generacion >= fecha_inicio)
    elif periodo == "mes":
        fecha_inicio = ahora - timedelta(days=PERIODO_MES_DIAS)
        q = q.filter(PlanGenerado.fecha_generacion >= fecha_inicio)
    elif periodo == "anio":
        fecha_inicio = ahora - timedelta(days=PERIODO_ANIO_DIAS)
        q = q.filter(PlanGenerado.fecha_generacion >= fecha_inicio)
    
    total = q.count()
    
    # Ordenar y paginar
    planes = q.order_by(PlanGenerado.fecha_generacion.desc()).offset(offset).limit(limite).all()
    
    # Obtener nombres de clientes en batch
    cliente_ids = list(set(p.id_cliente for p in planes))
    clientes = {}
    if cliente_ids:
        clientes_q = db.query(Cliente.id_cliente, Cliente.nombre).filter(
            Cliente.id_cliente.in_(cliente_ids)
        ).all()
        clientes = {c.id_cliente: c.nombre for c in clientes_q}
    
    result = []
    for p in planes:
        result.append({
            "id": p.id,
            "id_cliente": p.id_cliente,
            "nombre_cliente": clientes.get(p.id_cliente, "—"),
            "fecha_generacion": p.fecha_generacion.isoformat() if p.fecha_generacion else None,
            "kcal_objetivo": round(p.kcal_objetivo, 0) if p.kcal_objetivo else None,
            "proteina_g": round(p.proteina_g, 0) if p.proteina_g else None,
            "carbs_g": round(p.carbs_g, 0) if p.carbs_g else None,
            "grasa_g": round(p.grasa_g, 0) if p.grasa_g else None,
            "objetivo": p.objetivo,
            "plantilla_tipo": p.plantilla_tipo,
            "pdf_url": "/api/planes/" + str(p.id) + "/pdf",
            "tiene_pdf": bool(p.pdf_object_id or p.ruta_pdf),
        })
    
    return {
        "planes": result,
        "total": total,
        "limit": limite,
        "offset": offset,
    }


@router.get("/planes/resumen", summary="Resumen de planes por período")
def resumen_planes(
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    """Resumen de planes generados por período."""
    verify_permission(usuario, "read", "stats")
    gym_id = get_gym_id(usuario)
    ahora = datetime.now(timezone.utc)
    
    # Planes esta semana
    semana = ahora - timedelta(days=PERIODO_SEMANA_DIAS)
    planes_semana = db.query(func.count(PlanGenerado.id)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= semana,
    ).scalar() or 0
    
    # Planes este mes
    mes = ahora - timedelta(days=PERIODO_MES_DIAS)
    planes_mes = db.query(func.count(PlanGenerado.id)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= mes,
    ).scalar() or 0
    
    # Planes totales
    planes_total = db.query(func.count(PlanGenerado.id)).filter(
        PlanGenerado.gym_id == gym_id,
    ).scalar() or 0
    
    # Promedio kcal
    promedio_kcal = db.query(func.avg(PlanGenerado.kcal_objetivo)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= mes,
    ).scalar() or 0
    
    return {
        "planes_semana": planes_semana,
        "planes_mes": planes_mes,
        "planes_total": planes_total,
        "promedio_kcal": round(promedio_kcal, 0),
    }
