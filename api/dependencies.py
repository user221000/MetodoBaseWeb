"""
api/dependencies.py — Dependency injection para MetodoBase API.

Nota: get_gestor() fue eliminado. Los endpoints ahora usan:
- web.database.engine.get_db() para sesiones SQLAlchemy
- web.auth_deps.get_usuario_gym() para autenticación
- web.database.repository para acceso a datos con aislamiento multi-tenant

RBAC: Incluye funciones de verificación de permisos.
"""
import sys
from pathlib import Path
from typing import Optional, Union

from fastapi import Depends, HTTPException, status

# Asegurar que el root del proyecto está en sys.path
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.modelos import ClienteEvaluacion   # noqa: E402
from core.nutrition_validation import normalize_sex, validate_measurement  # noqa: E402
from config.constantes import FACTORES_ACTIVIDAD  # noqa: E402


def build_cliente_from_dict(data: dict) -> ClienteEvaluacion:
    """
    Convierte un dict (de la API o de la BD) en ClienteEvaluacion con macros
    ya calculados via Katch-McArdle (MotorNutricional.calcular_motor).

    Sólo la grasa ausente/None usa la estimación histórica del 20 %, marcada en el DTO.
    Los valores reportados se validan sin sustituir el 0 ni otros datos inválidos.
    """
    grasa_reportada = data.get("grasa_corporal_pct")
    grasa_estimada = grasa_reportada is None
    grasa = 20.0 if grasa_estimada else float(grasa_reportada)
    validate_measurement("grasa_corporal_pct", grasa)
    sexo = normalize_sex(data.get("sexo"))
    plantilla_tipo = data.get("plantilla_tipo")
    if plantilla_tipo is None:
        plantilla_tipo = "general"

    from core.motor_nutricional import MotorNutricional
    from core.nutrition_restrictions import NutritionRestrictions
    from src.alimentos_base import ALIMENTOS_BASE

    cliente = ClienteEvaluacion(
        nombre=data.get("nombre"),
        telefono=data.get("telefono"),
        edad=data.get("edad"),
        peso_kg=float(data.get("peso_kg") or 0),
        estatura_cm=float(data.get("estatura_cm") or 0),
        grasa_corporal_pct=float(grasa),
        nivel_actividad=data.get("nivel_actividad"),
        objetivo=data.get("objetivo"),
        plantilla_tipo=plantilla_tipo,
        sexo=sexo,
        grasa_corporal_estimada=grasa_estimada,
        nutrition_restrictions=NutritionRestrictions.from_declaration(
            data.get("restricciones_nutricionales"), ALIMENTOS_BASE,
            excluded_foods=data["alimentos_excluidos"] if data.get("alimentos_excluidos") is not None else [],
        ),
    )

    if data.get("id_cliente"):
        cliente.id_cliente = data["id_cliente"]

    cliente.factor_actividad = FACTORES_ACTIVIDAD.get(cliente.nivel_actividad or "", 1.2)
    cliente = MotorNutricional.calcular_motor(cliente)
    return cliente


# ══════════════════════════════════════════════════════════════════════════════
# RBAC / PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_current_user(credentials = None):
    """
    Dependency para obtener el usuario actual con role.
    
    Re-exporta get_usuario_actual de web.auth_deps.
    """
    from web.auth_deps import get_usuario_actual
    return Depends(get_usuario_actual)


def verify_permission(
    user: Union[dict, object],
    action: str,
    resource: str,
    resource_owner_id: Optional[str] = None,
    message: Optional[str] = None
) -> None:
    """
    Verifica que el usuario tenga permiso para la acción.
    
    Lanza HTTPException 403 si no tiene permiso.
    
    Args:
        user: Usuario (dict o objeto con atributo 'role')
        action: Acción a realizar ('create', 'read', 'update', 'delete', etc.)
        resource: Recurso objetivo ('cliente', 'plan', 'team', etc.)
        resource_owner_id: ID del gym dueño del recurso (para multi-tenant)
        message: Mensaje de error personalizado
    
    Raises:
        HTTPException: 403 si no tiene permiso
    
    Usage:
        verify_permission(current_user, "create", "cliente")
        verify_permission(current_user, "delete", "plan", gym_id)
    """
    from web.services.permissions import verify_permission as _verify
    _verify(user, action, resource, resource_owner_id, message)


def has_permission(
    user: Union[dict, object],
    action: str,
    resource: str,
    resource_owner_id: Optional[str] = None
) -> bool:
    """
    Verifica si el usuario tiene permiso (sin lanzar excepción).
    
    Args:
        user: Usuario (dict o objeto)
        action: Acción a realizar
        resource: Recurso objetivo
        resource_owner_id: ID del gym dueño del recurso
    
    Returns:
        True si tiene permiso, False si no.
    """
    from web.services.permissions import has_permission as _has
    return _has(user, action, resource, resource_owner_id)


def get_effective_gym_id(user: Union[dict, object]) -> str:
    """
    Obtiene el gym_id efectivo para queries multi-tenant.
    
    - Si es owner, retorna su propio ID
    - Si es team member, retorna team_gym_id
    """
    from web.auth_deps import get_effective_gym_id as _get
    if hasattr(user, '__dict__'):
        user = {
            "id": getattr(user, "id", None),
            "tipo": getattr(user, "tipo", None),
            "role": getattr(user, "role", None),
            "team_gym_id": getattr(user, "team_gym_id", None),
        }
    return _get(user)


def require_role(*roles: str):
    """
    Dependency factory que requiere uno de los roles especificados.
    
    Usage:
        @router.delete("/plan/{id}", dependencies=[Depends(require_role("owner", "admin"))])
        async def delete_plan():
            ...
    """
    from web.auth_deps import get_usuario_actual
    
    async def dependency(user: dict = Depends(get_usuario_actual)) -> dict:
        user_role = user.get("role", "viewer")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente. Roles requeridos: {', '.join(roles)}"
            )
        return user
    
    return dependency


def require_permission_dep(action: str, resource: str):
    """
    Dependency factory que verifica un permiso específico.
    
    Usage:
        @router.post("/clientes", dependencies=[Depends(require_permission_dep("create", "cliente"))])
        async def create():
            ...
    """
    from web.auth_deps import get_usuario_actual
    
    async def dependency(user: dict = Depends(get_usuario_actual)) -> dict:
        verify_permission(user, action, resource)
        return user
    
    return dependency
