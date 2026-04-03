"""
web/services/feature_gate.py — Feature gating centralizado por plan de suscripción.

Este servicio controla qué features están disponibles según el plan del gym.
Centraliza la lógica de límites para evitar inconsistencias.

Uso:
    from web.services.feature_gate import FeatureGate, get_plan_features
    
    # En endpoint de crear cliente:
    gate = FeatureGate(db, gym_id)
    gate.check_can_create_client()  # Raises HTTPException 402 si excede
    
    # Obtener features de un plan:
    features = get_plan_features("profesional")
    print(features.max_clientes)  # 200
    
    # En template Jinja:
    {{ plan_features.can_export_excel }}
"""
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from web.constants import PLANES_LICENCIA, TRIAL_DAYS
from web.database.models import Subscription, Cliente

logger = logging.getLogger(__name__)


# ── Plan Features Definition ─────────────────────────────────────────────────

@dataclass
class PlanFeatures:
    """Features disponibles por plan de suscripción."""
    
    # Nombre del plan
    plan_name: str
    
    # Límites
    max_clientes: int  # 0 = unlimited
    max_planes_por_mes: int  # 0 = unlimited
    max_registros_diarios: int  # 0 = unlimited
    max_planes_por_cliente_dia: int  # 0 = unlimited
    
    # Exportación
    can_export_excel: bool
    can_export_pdf: bool
    can_bulk_export: bool
    
    # Personalización
    can_custom_branding: bool
    can_custom_templates: bool
    
    # Colaboración
    can_multi_user: bool
    max_team_members: int  # 0 = unlimited
    
    # Integración
    can_api_access: bool
    can_webhooks: bool
    
    # Soporte
    support_level: str  # "community" | "email" | "priority" | "dedicated"
    
    # Preferencias de alimentos
    can_food_preferences: bool
    
    # Precio (para mostrar en UI)
    price_mxn: int
    stripe_price_id: Optional[str]


# ── Plan Definitions (derived from config/constantes.PLANES_LICENCIA) ────────

def _build_plan_features() -> dict[str, "PlanFeatures"]:
    """Build PlanFeatures dynamically from the canonical PLANES_LICENCIA."""
    _feature_extras = {
        "free": {
            "can_export_excel": False, "can_export_pdf": True, "can_bulk_export": False,
            "can_custom_branding": False, "can_custom_templates": False,
            "can_multi_user": False, "max_team_members": 1,
            "can_api_access": False, "can_webhooks": False,
            "support_level": "community", "max_planes_por_mes": 20,
            "can_food_preferences": True,
        },
        "standard": {
            "can_export_excel": True, "can_export_pdf": True, "can_bulk_export": True,
            "can_custom_branding": False, "can_custom_templates": False,
            "can_multi_user": False, "max_team_members": 1,
            "can_api_access": True, "can_webhooks": False,
            "support_level": "email", "max_planes_por_mes": 100,
            "can_food_preferences": True,
        },
        "gym_comercial": {
            "can_export_excel": True, "can_export_pdf": True, "can_bulk_export": True,
            "can_custom_branding": True, "can_custom_templates": True,
            "can_multi_user": False, "max_team_members": 1,
            "can_api_access": True, "can_webhooks": True,
            "support_level": "email", "max_planes_por_mes": 0,
            "can_food_preferences": True,
        },
        "clinica": {
            "can_export_excel": True, "can_export_pdf": True, "can_bulk_export": True,
            "can_custom_branding": True, "can_custom_templates": True,
            "can_multi_user": True, "max_team_members": 0,
            "can_api_access": True, "can_webhooks": True,
            "support_level": "priority", "max_planes_por_mes": 0,
            "can_food_preferences": True,
        },
    }
    result = {}
    for plan_key, plan_data in PLANES_LICENCIA.items():
        extras = _feature_extras.get(plan_key, _feature_extras["free"])
        result[plan_key] = PlanFeatures(
            plan_name=plan_key.replace("_", " ").title(),
            max_clientes=plan_data["max_clientes"],
            max_planes_por_mes=extras["max_planes_por_mes"],
            max_registros_diarios=plan_data.get("max_registros_diarios", 0),
            max_planes_por_cliente_dia=plan_data.get("max_planes_por_cliente_dia", 0),
            can_export_excel=extras["can_export_excel"],
            can_export_pdf=extras["can_export_pdf"],
            can_bulk_export=extras["can_bulk_export"],
            can_custom_branding=extras["can_custom_branding"],
            can_custom_templates=extras["can_custom_templates"],
            can_multi_user=plan_data.get("multi_usuario", extras["can_multi_user"]),
            max_team_members=extras["max_team_members"],
            can_api_access=extras["can_api_access"],
            can_webhooks=extras["can_webhooks"],
            support_level=extras["support_level"],
            can_food_preferences=extras["can_food_preferences"],
            price_mxn=plan_data["precio_mxn"],
            stripe_price_id=plan_data.get("stripe_price_id"),
        )
    return result


PLAN_FEATURES = _build_plan_features()

# Trial settings (derived from config/constantes.TRIAL_DAYS)
TRIAL_PLAN_FEATURES = PLAN_FEATURES["standard"]  # Durante trial, features de Standard


# ── Utility Functions ────────────────────────────────────────────────────────

def get_plan_features(plan: str) -> PlanFeatures:
    """
    Obtiene las features de un plan específico.
    
    Args:
        plan: Nombre del plan (free, starter, profesional, clinica)
    
    Returns:
        PlanFeatures con todas las capacidades del plan
    """
    return PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])


def get_all_plans() -> dict[str, PlanFeatures]:
    """Retorna todos los planes disponibles para mostrar en pricing page."""
    return PLAN_FEATURES.copy()


# ── Feature Gate Class ───────────────────────────────────────────────────────

class FeatureGate:
    """
    Verifica permisos basados en plan de suscripción.
    
    Uso típico:
        gate = FeatureGate(db, gym_id)
        
        # Verificar antes de crear cliente
        gate.check_can_create_client()
        
        # Verificar feature específica
        gate.check_feature("can_export_excel")
        
        # Obtener features para UI
        features = gate.features
    """
    
    def __init__(self, db: Session, gym_id: str):
        """
        Inicializa el gate para un gym específico.
        
        Args:
            db: Sesión de SQLAlchemy
            gym_id: ID del gym (tenant)
        """
        self.db = db
        self.gym_id = gym_id
        self._subscription: Optional[Subscription] = None
        self._features: Optional[PlanFeatures] = None
    
    @property
    def subscription(self) -> Optional[Subscription]:
        """Obtiene la suscripción activa del gym (cached)."""
        if self._subscription is None:
            self._subscription = self.db.query(Subscription).filter(
                Subscription.gym_id == self.gym_id,
                Subscription.status.in_(["active", "trialing", "past_due"]),
            ).first()
        return self._subscription
    
    @property
    def plan(self) -> str:
        """Nombre del plan actual."""
        if not self.subscription:
            return "free"
        return self.subscription.plan
    
    @property
    def is_trial(self) -> bool:
        """Si está en período de prueba."""
        return self.subscription is not None and self.subscription.status == "trialing"
    
    @property
    def features(self) -> PlanFeatures:
        """Features disponibles según el plan actual (cached)."""
        if self._features is None:
            if self.is_trial:
                self._features = TRIAL_PLAN_FEATURES
            else:
                self._features = PLAN_FEATURES.get(self.plan, PLAN_FEATURES["free"])
        return self._features
    
    # ── Counts ───────────────────────────────────────────────────────────────
    
    def get_client_count(self) -> int:
        """Cuenta clientes activos del gym."""
        return self.db.query(Cliente).filter(
            Cliente.gym_id == self.gym_id,
            Cliente.activo == True,
        ).count()
    
    def get_remaining_clients(self) -> int:
        """Cuántos clientes más puede crear."""
        if self.features.max_clientes == 0:
            return 999999  # Unlimited
        return max(0, self.features.max_clientes - self.get_client_count())
    
    # ── Checks (raise HTTPException) ─────────────────────────────────────────
    
    def check_can_create_client(self) -> None:
        """
        Verifica si puede crear más clientes.
        
        Raises:
            HTTPException 402: Si excede el límite del plan
        """
        if self.features.max_clientes == 0:
            return  # Unlimited
        
        count = self.get_client_count()
        if count >= self.features.max_clientes:
            logger.warning(
                "Plan limit exceeded: gym=%s, plan=%s, current=%d, limit=%d",
                self.gym_id, self.plan, count, self.features.max_clientes
            )
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "plan_limit_exceeded",
                    "message": f"Tu plan {self.features.plan_name} permite máximo {self.features.max_clientes} clientes",
                    "current": count,
                    "limit": self.features.max_clientes,
                    "upgrade_url": "/suscripciones",
                },
            )
    
    def check_feature(self, feature: str) -> None:
        """
        Verifica si una feature está habilitada.
        
        Args:
            feature: Nombre del atributo en PlanFeatures (ej: "can_export_excel")
        
        Raises:
            HTTPException 402: Si la feature no está disponible
        """
        if not hasattr(self.features, feature):
            raise ValueError(f"Feature desconocida: {feature}")
        
        if not getattr(self.features, feature, False):
            logger.warning(
                "Feature not available: gym=%s, plan=%s, feature=%s",
                self.gym_id, self.plan, feature
            )
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "feature_not_available",
                    "message": f"La función '{feature}' no está disponible en tu plan {self.features.plan_name}",
                    "plan": self.plan,
                    "upgrade_url": "/suscripciones",
                },
            )
    
    def has_feature(self, feature: str) -> bool:
        """
        Verifica si una feature está habilitada (no lanza excepción).
        
        Args:
            feature: Nombre del atributo en PlanFeatures
        
        Returns:
            True si la feature está disponible, False si no
        """
        return getattr(self.features, feature, False)
    
    # ── Status Info ──────────────────────────────────────────────────────────
    
    def get_status_summary(self) -> dict:
        """
        Obtiene resumen del estado de la suscripción para mostrar en UI.
        
        Returns:
            Dict con info del plan, límites y uso actual
        """
        client_count = self.get_client_count()
        
        return {
            "plan": self.plan,
            "plan_name": self.features.plan_name,
            "status": self.subscription.status if self.subscription else "free",
            "is_trial": self.is_trial,
            "trial_days_remaining": self._get_trial_days_remaining(),
            "limits": {
                "max_clientes": self.features.max_clientes or "unlimited",
                "current_clientes": client_count,
                "remaining_clientes": self.get_remaining_clients() if self.features.max_clientes else "unlimited",
                "usage_percent": round(client_count / self.features.max_clientes * 100, 1) if self.features.max_clientes else 0,
            },
            "features": {
                "can_export_excel": self.features.can_export_excel,
                "can_export_pdf": self.features.can_export_pdf,
                "can_custom_branding": self.features.can_custom_branding,
                "can_multi_user": self.features.can_multi_user,
                "can_api_access": self.features.can_api_access,
            },
            "billing": {
                "price_mxn": self.features.price_mxn,
                "period_end": self.subscription.current_period_end.isoformat() if self.subscription and self.subscription.current_period_end else None,
                "cancel_at_period_end": self.subscription.cancel_at_period_end if self.subscription else False,
            },
        }
    
    def _get_trial_days_remaining(self) -> Optional[int]:
        """Calcula días restantes de trial."""
        if not self.is_trial or not self.subscription or not self.subscription.trial_end:
            return None
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        trial_end = self.subscription.trial_end
        
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        
        delta = trial_end - now
        return max(0, delta.days)


# ── Dependency for FastAPI ───────────────────────────────────────────────────

def get_feature_gate(db: Session, gym_id: str) -> FeatureGate:
    """
    Factory function para crear FeatureGate.
    
    Uso como dependency:
        from web.services.feature_gate import get_feature_gate
        
        @router.post("/clientes")
        def crear_cliente(
            ...,
            db: Session = Depends(get_db),
            usuario: dict = Depends(get_usuario_gym),
        ):
            gate = get_feature_gate(db, usuario["id"])
            gate.check_can_create_client()
            ...
    """
    return FeatureGate(db, gym_id)
