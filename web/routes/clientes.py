"""
web/routes/clientes.py — CRUD clientes con aislamiento multi-tenant.

Cada operación filtra por gym_id extraído del usuario autenticado.
Un gym NUNCA ve los clientes de otro gym.
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from web.schemas import ClienteCreate, ClienteUpdate
from web.database.engine import get_db, get_db_readonly
from web.database import repository as repo
from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.subscription_guard import check_daily_registration_limit, check_food_preferences_allowed
from web.services.permissions import verify_permission
from web.routes._utils import get_gym_id
from web.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ERR_CLIENTE_NO_ENCONTRADO

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Clientes"])


@router.get("/clientes", summary="Listar clientes activos")
def listar_clientes(
    q: Optional[str] = Query(None, description="Busca por nombre, teléfono o ID"),
    filter: Optional[str] = Query(None, description="activos|inactivos|sub-nuevas|sub-activas|sub-inactivas"),
    limite: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "cliente")
    termino = q.strip() if q else ""
    
    solo_activos = None
    filtro_suscripcion = None

    if filter == "activos":
        solo_activos = True
    elif filter == "inactivos":
        solo_activos = False
    elif filter in ("sub-nuevas", "sub-activas", "sub-inactivas"):
        filtro_suscripcion = filter

    clientes, total = repo.listar_clientes(
        db, get_gym_id(usuario), termino,
        limite=limite, offset=offset,
        solo_activos=solo_activos,
        filtro_suscripcion=filtro_suscripcion,
    )
    return {"clientes": clientes, "total": total, "limit": limite, "offset": offset, "filter": filter}


@router.get("/clientes/{id_cliente}", summary="Obtener cliente por ID")
def obtener_cliente(
    id_cliente: str,
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "cliente")
    cliente = repo.obtener_cliente(db, get_gym_id(usuario), id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)
    return cliente


@router.post("/clientes", status_code=201, summary="Crear nuevo cliente")
def crear_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(check_daily_registration_limit),
):
    try:
        # Bloquear alimentos_excluidos si el plan no soporta preferencias
        plan_name = usuario.get("subscription", {}).get("plan", "free")
        if not check_food_preferences_allowed(plan_name):
            if data.alimentos_excluidos:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "food_preferences_not_available",
                        "message": "Las preferencias de alimentos no están disponibles en tu plan. Actualiza a Gym Comercial o Clínica.",
                        "upgrade_url": "/suscripciones",
                    },
                )
        from web.dependencies import build_cliente_from_dict
        cliente_eval = build_cliente_from_dict(data.model_dump())
        # Persist via SA repository
        cliente_dict = data.model_dump()
        # Add computed macros from evaluation
        cliente_dict.update({
            "masa_magra_kg": getattr(cliente_eval, "masa_magra_kg", None),
        })
        result = repo.crear_cliente(db, get_gym_id(usuario), cliente_dict)
        logger.info("Cliente creado: %s", result["id_cliente"])
        return {
            "success": True,
            "id_cliente": result["id_cliente"],
            "cliente": result,
            "message": f"Cliente '{result['nombre']}' creado correctamente",
            "macros": {
                "tmb": round(getattr(cliente_eval, "tmb", 0) or 0, 1),
                "get_total": round(getattr(cliente_eval, "get_total", 0) or 0, 1),
                "kcal_objetivo": round(getattr(cliente_eval, "kcal_objetivo", 0) or 0, 0),
                "proteina_g": round(getattr(cliente_eval, "proteina_g", 0) or 0, 1),
                "carbs_g": round(getattr(cliente_eval, "carbs_g", 0) or 0, 1),
                "grasa_g": round(getattr(cliente_eval, "grasa_g", 0) or 0, 1),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        from web.settings import get_settings as _gs
        logger.error(
            "Error creando cliente: %s", exc,
            exc_info=not _gs().is_production
        )
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/clientes/{id_cliente}", summary="Actualizar cliente existente")
def actualizar_cliente(
    id_cliente: str,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "cliente")
    existing = repo.obtener_cliente(db, get_gym_id(usuario), id_cliente)
    if not existing:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)

    try:
        # Bloquear alimentos_excluidos si el plan no soporta preferencias
        if data.alimentos_excluidos is not None and data.alimentos_excluidos:
            from web.subscription_guard import check_food_preferences_allowed, _get_gym_plan
            plan_name = _get_gym_plan(db, get_gym_id(usuario))
            if not check_food_preferences_allowed(plan_name):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "food_preferences_not_available",
                        "message": "Las preferencias de alimentos no están disponibles en tu plan. Actualiza a Gym Comercial o Clínica.",
                        "upgrade_url": "/suscripciones",
                    },
                )

        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = repo.actualizar_cliente(db, get_gym_id(usuario), id_cliente, update_dict)
        if not result:
            raise HTTPException(status_code=500, detail="Error actualizando cliente")
        logger.info("Cliente actualizado: %s", id_cliente)
        return {"success": True, "message": "Cliente actualizado correctamente"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error actualizando: %s", exc,
            exc_info=not _gs().is_production
        )
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/clientes/{id_cliente}", summary="Desactivar cliente (soft delete)")
def desactivar_cliente(
    id_cliente: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "delete", "cliente")
    ok = repo.eliminar_cliente(db, get_gym_id(usuario), id_cliente)
    if not ok:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)
    logger.info("Cliente desactivado: %s", id_cliente)
    return {"success": True, "message": "Cliente desactivado"}
