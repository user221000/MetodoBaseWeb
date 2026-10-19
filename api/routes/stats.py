"""
api/routes/stats.py — Endpoint de estadísticas /api/estadisticas con autenticación multi-tenant.

Todas las estadísticas están aisladas por gym_id del usuario autenticado.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from web.database.engine import get_db
from web.auth_deps import get_usuario_gym
from web.database import repository as repo
from config.constantes import PERIODO_SEMANA_DIAS, PERIODO_MES_DIAS, PERIODO_ANIO_DIAS

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Estadísticas"])


@router.get("/estadisticas", summary="KPIs del dashboard")
def obtener_estadisticas(
    periodo: Optional[str] = Query(None, description="semana|mes|anio"),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """
    Retorna métricas del período solicitado (default: 30 días).
    Solo incluye datos del gym autenticado.
    Incluye planes_por_dia para el gráfico de evolución.
    """
    gym_id = usuario["id"]
    
    try:
        ahora = datetime.now(timezone.utc)
        if periodo == "semana":
            fecha_inicio = ahora - timedelta(days=PERIODO_SEMANA_DIAS)
            dias_graf = 7
        elif periodo == "anio":
            fecha_inicio = ahora - timedelta(days=PERIODO_ANIO_DIAS)
            dias_graf = 7  # Últimos 7 días para gráfico
        else:
            fecha_inicio = ahora - timedelta(days=PERIODO_MES_DIAS)
            dias_graf = 7

        # Estadísticas principales
        stats = repo.obtener_estadisticas(
            db, gym_id, fecha_inicio=fecha_inicio, fecha_fin=ahora
        )
        
        # Planes por día para gráfico
        planes_dia = repo.obtener_planes_por_dia(db, gym_id, dias=dias_graf)
        stats["planes_por_dia"] = [p["cantidad"] for p in planes_dia]
        stats["planes_labels"] = [p["fecha"] for p in planes_dia]

        return stats
    except Exception as exc:
        logger.error("Statistics unavailable class=%s", type(exc).__name__)
        raise HTTPException(503, {"code": "statistics_unavailable",
            "message": "No fue posible consultar las estadísticas. Vuelve a intentar."}) from None
