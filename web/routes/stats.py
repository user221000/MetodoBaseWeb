"""
web/routes/stats.py — Estadísticas con aislamiento multi-tenant.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.database.engine import get_db_readonly
from web.database import repository as repo
from web.services.permissions import verify_permission
from web.routes._utils import get_gym_id
from web.constants import PERIODO_SEMANA_DIAS, PERIODO_MES_DIAS, PERIODO_ANIO_DIAS

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Estadísticas"])


@router.get("/estadisticas", summary="KPIs del dashboard")
def obtener_estadisticas(
    periodo: Optional[str] = Query(None, description="semana|mes|anio"),
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "stats")
    try:
        ahora = datetime.now(timezone.utc)
        if periodo == "semana":
            fecha_inicio = ahora - timedelta(days=PERIODO_SEMANA_DIAS)
        elif periodo == "anio":
            fecha_inicio = ahora - timedelta(days=PERIODO_ANIO_DIAS)
        else:
            fecha_inicio = ahora - timedelta(days=PERIODO_MES_DIAS)

        gym_id = get_gym_id(usuario)
        stats = repo.obtener_estadisticas(db, gym_id, fecha_inicio, ahora)

        # Planes por día para gráfico
        planes_dia = repo.obtener_planes_por_dia(db, gym_id)
        stats["planes_por_dia"] = [d["cantidad"] for d in planes_dia]
        stats["planes_labels"] = [d["fecha"] for d in planes_dia]

        return stats
    except Exception as exc:
        from web.settings import get_settings as _gs
        logger.error(
            "Error estadísticas: %s", exc,
            exc_info=not _gs().is_production
        )
        return {
            "total_clientes": 0, "clientes_nuevos": 0,
            "planes_periodo": 0, "promedio_kcal": 0,
            "clientes_activos": 0, "tasa_retencion": 0.0,
            "top_clientes": [], "objetivos": {},
            "planes_por_dia": [0]*7,
            "planes_labels": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
        }


@router.get("/estadisticas/objetivos", summary="Distribución de objetivos")
def stats_objetivos(
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "stats")
    gym_id = get_gym_id(usuario)
    stats = repo.obtener_estadisticas(db, gym_id)
    objetivos = stats.get("objetivos", {})
    total = sum(objetivos.values()) or 1
    return {
        "deficit_cantidad":       objetivos.get("deficit", 0),
        "deficit_porcentaje":     round(objetivos.get("deficit", 0) / total * 100, 1),
        "mantenimiento_cantidad": objetivos.get("mantenimiento", 0),
        "mantenimiento_porcentaje": round(objetivos.get("mantenimiento", 0) / total * 100, 1),
        "superavit_cantidad":     objetivos.get("superavit", 0),
        "superavit_porcentaje":   round(objetivos.get("superavit", 0) / total * 100, 1),
    }


@router.get("/estadisticas/planes-tiempo", summary="Planes por día (última semana)")
def stats_planes_tiempo(
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "stats")
    gym_id = get_gym_id(usuario)
    return repo.obtener_planes_por_dia(db, gym_id)


@router.get("/estadisticas/suscripciones", summary="KPIs de suscripciones de clientes")
def stats_suscripciones(
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    """Retorna conteos de suscripciones de clientes: nuevas este mes, activas, inactivas."""
    verify_permission(usuario, "read", "stats")
    gym_id = get_gym_id(usuario)
    ahora = datetime.now(timezone.utc)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from web.database.models import Cliente
    base = db.query(Cliente).filter(
        Cliente.gym_id == gym_id,
        Cliente.activo == True,  # noqa: E712
    )

    nuevas = base.filter(
        Cliente.fecha_suscripcion.isnot(None),
        Cliente.fecha_suscripcion >= inicio_mes,
    ).count()

    activas = base.filter(
        Cliente.fecha_fin_suscripcion.isnot(None),
        Cliente.fecha_fin_suscripcion >= ahora,
    ).count()

    inactivas = base.filter(
        (Cliente.fecha_fin_suscripcion.is_(None)) |
        (Cliente.fecha_fin_suscripcion < ahora)
    ).count()

    return {
        "nuevas_este_mes": nuevas,
        "activas": activas,
        "inactivas": inactivas,
    }
