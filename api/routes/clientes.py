"""
api/routes/clientes.py — CRUD endpoints /api/clientes con autenticación multi-tenant.

Todos los endpoints requieren autenticación y filtran por gym_id del usuario.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from api.schemas import ClienteCreate, ClienteUpdate
from api.dependencies import build_cliente_from_dict
from web.database.engine import get_db
from web.auth_deps import get_usuario_gym
from web.database import repository as repo
from config.constantes import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ERR_CLIENTE_NO_ENCONTRADO
from web.nutrition_http import NutritionRoute

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Clientes"], route_class=NutritionRoute)


@router.get("/clientes", summary="Listar clientes")
def listar_clientes(
    q: Optional[str] = Query(None, description="Busca por nombre, teléfono o ID"),
    filter: Optional[str] = Query(None, description="activos|inactivos"),
    limite: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """Lista clientes del gym; acepta búsqueda y filtro de actividad."""
    gym_id = usuario["id"]
    termino = q.strip() if q else ""
    solo_activos = None
    if filter == "activos":
        solo_activos = True
    elif filter == "inactivos":
        solo_activos = False
    clientes, total = repo.listar_clientes(
        db, gym_id, termino=termino, solo_activos=solo_activos, limite=limite, offset=offset
    )
    return {"clientes": clientes, "total": total, "limit": limite, "offset": offset, "filter": filter}


@router.get("/clientes/{id_cliente}", summary="Obtener cliente por ID")
def obtener_cliente(
    id_cliente: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """Retorna todos los datos de un cliente que pertenece al gym."""
    gym_id = usuario["id"]
    cliente = repo.obtener_cliente(db, gym_id, id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)
    return cliente


@router.post("/clientes", status_code=201, summary="Crear nuevo cliente")
def crear_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """
    Crea un nuevo cliente asignado al gym del usuario autenticado.
    Calcula macros (Katch-McArdle) automáticamente.
    """
    gym_id = usuario["id"]
    try:
        # Calcular macros usando el motor nutricional
        cliente_calc = build_cliente_from_dict(data.model_dump())
        
        # Preparar datos con macros calculados
        cliente_data = data.model_dump()
        cliente_data.update({
            "tmb": cliente_calc.tmb,
            "get_total": cliente_calc.get_total,
            "kcal_objetivo": cliente_calc.kcal_objetivo,
            "proteina_g": cliente_calc.proteina_g,
            "carbs_g": cliente_calc.carbs_g,
            "grasa_g": cliente_calc.grasa_g,
        })
        
        nuevo = repo.crear_cliente(db, gym_id, cliente_data)
        
        logger.info("Cliente creado id=%s gym_id=%s", nuevo["id_cliente"], gym_id)
        return {
            "success": True,
            "id_cliente": nuevo["id_cliente"],
            "message": f"Cliente '{nuevo['nombre']}' creado correctamente",
            "macros": {
                "tmb": round(cliente_calc.tmb or 0, 1),
                "get_total": round(cliente_calc.get_total or 0, 1),
                "kcal_objetivo": round(cliente_calc.kcal_objetivo or 0, 0),
                "proteina_g": round(cliente_calc.proteina_g or 0, 1),
                "carbs_g": round(cliente_calc.carbs_g or 0, 1),
                "grasa_g": round(cliente_calc.grasa_g or 0, 1),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Client creation failed class=%s", type(exc).__name__)
        raise HTTPException(status_code=400, detail={"code": "client_create_failed",
            "message": "No se pudo crear el cliente. Revisa los datos e intenta de nuevo."}) from None


@router.put("/clientes/{id_cliente}", summary="Actualizar cliente existente")
def actualizar_cliente(
    id_cliente: str,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """Persist submitted profile fields for this gym, including incomplete ones.

    Progressive onboarding does not require or invent the remaining engine
    inputs. The generation use case validates the complete persisted profile
    and computes its macros. This update neither generates plans nor consumes
    quota; the request session owns its transaction.
    """
    gym_id = usuario["id"]
    existing = repo.obtener_cliente(db, gym_id, id_cliente)
    if not existing:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)

    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        
        updated = repo.actualizar_cliente(db, gym_id, id_cliente, update_dict)
        if not updated:
            raise HTTPException(status_code=500, detail="Error actualizando cliente")

        logger.info("Cliente actualizado: %s", id_cliente)
        return {"success": True, "message": "Cliente actualizado correctamente"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Client update failed class=%s", type(exc).__name__)
        raise HTTPException(status_code=400, detail={"code": "client_update_failed",
            "message": "No se pudo actualizar el cliente. Revisa los datos e intenta de nuevo."}) from None


@router.delete("/clientes/{id_cliente}", summary="Desactivar cliente (soft delete)")
def desactivar_cliente(
    id_cliente: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """Desactiva un cliente (lo oculta del listado; sus datos se conservan)."""
    gym_id = usuario["id"]
    existing = repo.obtener_cliente(db, gym_id, id_cliente)
    if not existing:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)

    exito = repo.eliminar_cliente(db, gym_id, id_cliente)
    if not exito:
        raise HTTPException(status_code=500, detail="Error desactivando cliente")
    logger.info("Cliente desactivado: %s", id_cliente)
    return {"success": True, "message": "Cliente desactivado"}
