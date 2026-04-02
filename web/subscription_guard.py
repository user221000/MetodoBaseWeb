"""
web/subscription_guard.py — Guard de suscripción para endpoints protegidos.

Verifica que el gym tiene suscripción activa y no excede límite de clientes.
En desarrollo (sin STRIPE_SECRET_KEY), el guard es permisivo.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.database.engine import get_db
from web.database.models import Subscription, Cliente, PlanGenerado

logger = logging.getLogger(__name__)


def _is_stripe_configured() -> bool:
    from web.settings import get_settings
    return bool(get_settings().STRIPE_SECRET_KEY)


def require_active_subscription(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
) -> dict:
    """
    Verifica suscripción activa. En dev (sin Stripe), pasa sin restricción.
    Si no hay suscripción activa, usa el plan 'free' (10 clientes) en lugar de bloquear.
    Retorna el usuario enriquecido con info de suscripción.
    C3 FIX: Usar get_effective_gym_id para soportar team members.
    """
    if not _is_stripe_configured():
        # Dev mode: sin Stripe, sin restricción
        usuario["subscription"] = {"plan": "clinica", "status": "dev", "max_clientes": 999999}
        return usuario

    # C3 FIX: Usar gym_id efectivo, no ID personal
    gym_id = get_effective_gym_id(usuario)
    sub = db.query(Subscription).filter(
        Subscription.gym_id == gym_id
    ).first()

    if not sub or sub.status not in ("active", "trialing"):
        # Sin suscripción activa → plan free (limitado, pero no bloqueado)
        from web.constants import PLANES_LICENCIA
        free_cfg = PLANES_LICENCIA.get("free", {})
        usuario["subscription"] = {
            "plan": "free",
            "status": "free",
            "max_clientes": free_cfg.get("max_clientes", 10),
        }
        return usuario

    usuario["subscription"] = {
        "plan": sub.plan,
        "status": sub.status,
        "max_clientes": sub.max_clientes,
    }
    return usuario


def check_client_limit(
    db: Session = Depends(get_db),
    usuario: dict = Depends(require_active_subscription),
) -> dict:
    """
    Verifica que el gym no exceda el límite de clientes de su plan.
    Solo relevante al crear clientes nuevos.
    C3 FIX: Usar get_effective_gym_id para soportar team members.
    """
    max_clientes = usuario.get("subscription", {}).get("max_clientes", 999999)

    if max_clientes > 0:  # 0 = ilimitado (plan clinica)
        # C3 FIX: Usar gym_id efectivo, no ID personal
        gym_id = get_effective_gym_id(usuario)
        count = db.query(Cliente).filter(
            Cliente.gym_id == gym_id,
            Cliente.activo == True,  # noqa: E712
        ).count()

        if count >= max_clientes:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "client_limit_reached",
                    "message": f"Límite de {max_clientes} clientes alcanzado. Actualiza tu plan.",
                    "current": count,
                    "limit": max_clientes,
                },
            )

    return usuario


def _get_plan_config(plan_name: str) -> dict:
    """Obtiene la configuración del plan desde PLANES_LICENCIA."""
    from web.constants import PLANES_LICENCIA
    return PLANES_LICENCIA.get(plan_name, PLANES_LICENCIA["free"])


def _today_start() -> datetime:
    """Retorna el inicio del día actual en UTC."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def check_daily_registration_limit(
    db: Session = Depends(get_db),
    usuario: dict = Depends(require_active_subscription),
) -> dict:
    """
    Verifica que el gym no exceda el límite de registros de clientes por día.
    También verifica el límite total de clientes activos.
    """
    plan_name = usuario.get("subscription", {}).get("plan", "free")
    plan_cfg = _get_plan_config(plan_name)

    # 1. Verificar límite total de clientes activos
    max_clientes = plan_cfg.get("max_clientes", 0)
    gym_id = get_effective_gym_id(usuario)

    if max_clientes > 0:
        total_activos = db.query(Cliente).filter(
            Cliente.gym_id == gym_id,
            Cliente.activo == True,  # noqa: E712
        ).count()

        if total_activos >= max_clientes:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "client_limit_reached",
                    "message": f"Límite de {max_clientes} clientes activos alcanzado. Actualiza tu plan.",
                    "current": total_activos,
                    "limit": max_clientes,
                },
            )

    # 2. Verificar límite diario de registros
    max_diarios = plan_cfg.get("max_registros_diarios", 0)
    if max_diarios > 0:
        hoy = _today_start()
        registros_hoy = db.query(Cliente).filter(
            Cliente.gym_id == gym_id,
            Cliente.fecha_registro >= hoy,
        ).count()

        if registros_hoy >= max_diarios:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "daily_registration_limit",
                    "message": f"Límite de {max_diarios} registros de clientes por día alcanzado.",
                    "current": registros_hoy,
                    "limit": max_diarios,
                    "upgrade_url": "/suscripciones",
                },
            )

    return usuario


def check_daily_plan_limit(db: Session, gym_id: str, id_cliente: str, plan_name: str) -> None:
    """
    Verifica que no se exceda el límite de planes por cliente por día.
    Lanza HTTPException 403 si se excede.
    """
    plan_cfg = _get_plan_config(plan_name)
    max_por_cliente = plan_cfg.get("max_planes_por_cliente_dia", 0)

    if max_por_cliente > 0:
        hoy = _today_start()
        planes_hoy = db.query(PlanGenerado).filter(
            PlanGenerado.gym_id == gym_id,
            PlanGenerado.id_cliente == id_cliente,
            PlanGenerado.fecha_generacion >= hoy,
        ).count()

        if planes_hoy >= max_por_cliente:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "daily_plan_limit",
                    "message": f"Límite de {max_por_cliente} plan(es) por cliente por día alcanzado.",
                    "current": planes_hoy,
                    "limit": max_por_cliente,
                    "upgrade_url": "/suscripciones",
                },
            )


def check_food_preferences_allowed(plan_name: str) -> bool:
    """Retorna True si el plan permite usar preferencias de alimentos."""
    plan_cfg = _get_plan_config(plan_name)
    return plan_cfg.get("preferencias_alimentos", False)


def _get_gym_plan(db: Session, gym_id: str) -> str:
    """Obtiene el nombre del plan activo del gym. Retorna 'free' si no tiene."""
    if not _is_stripe_configured():
        return "clinica"  # Dev mode: sin restricciones
    sub = db.query(Subscription).filter(
        Subscription.gym_id == gym_id,
        Subscription.status.in_(["active", "trialing"]),
    ).first()
    return sub.plan if sub else "free"
