"""
web/services/permissions.py — Sistema de permisos RBAC para MetodoBase SaaS.

Implementa control de acceso basado en roles (RBAC) con:
- Jerarquía de roles: OWNER > ADMIN > NUTRIOLOGO > VIEWER
- Permisos granulares por acción y recurso
- Decoradores y dependencies para FastAPI

Uso:
    from web.services.permissions import require_role, has_permission, verify_permission
    
    @router.get("/clientes", dependencies=[Depends(require_role(UserRole.NUTRIOLOGO))])
    async def list_clientes(...):
        ...
    
    # O verificación manual:
    if has_permission(user, "create", "cliente"):
        ...
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, List, Optional, Set, Union, TYPE_CHECKING

from fastapi import Depends, HTTPException, status

if TYPE_CHECKING:
    from web.database.models import Usuario

from web.database.models import UserRole

_logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ROLE HIERARCHY
# ══════════════════════════════════════════════════════════════════════════════

ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.OWNER: 4,
    UserRole.ADMIN: 3,
    UserRole.NUTRIOLOGO: 2,
    UserRole.VIEWER: 1,
}


def role_level(role: UserRole) -> int:
    """Retorna el nivel numérico de un rol."""
    return ROLE_HIERARCHY.get(role, 0)


def has_higher_or_equal_role(user_role: UserRole, required_role: UserRole) -> bool:
    """Verifica si user_role tiene nivel >= required_role."""
    return role_level(user_role) >= role_level(required_role)


# ══════════════════════════════════════════════════════════════════════════════
# PERMISSION DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

# Permisos mapeados por (acción, recurso) -> set de roles permitidos
PERMISSIONS: dict[tuple[str, str], Set[UserRole]] = {
    # ── Clientes ──
    ("create", "cliente"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO},
    ("read", "cliente"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER},
    ("update", "cliente"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO},
    ("delete", "cliente"): {UserRole.OWNER, UserRole.ADMIN},
    ("export", "cliente"): {UserRole.OWNER, UserRole.ADMIN},
    
    # ── Planes ──
    ("create", "plan"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO},
    ("read", "plan"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER},
    ("regenerate", "plan"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO},
    ("delete", "plan"): {UserRole.OWNER, UserRole.ADMIN},
    ("export", "plan"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO},
    
    # ── Dashboard / Stats ──
    ("read", "dashboard"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER},
    ("read", "stats"): {UserRole.OWNER, UserRole.ADMIN},
    ("read", "analytics"): {UserRole.OWNER, UserRole.ADMIN},
    
    # ── Gym Profile ──
    ("read", "gym_profile"): {UserRole.OWNER, UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER},
    ("update", "gym_profile"): {UserRole.OWNER, UserRole.ADMIN},
    
    # ── Team Management ──
    ("read", "team"): {UserRole.OWNER, UserRole.ADMIN},
    ("invite", "team"): {UserRole.OWNER, UserRole.ADMIN},
    ("update_role", "team"): {UserRole.OWNER},  # Solo owner puede cambiar roles
    ("remove", "team"): {UserRole.OWNER, UserRole.ADMIN},
    
    # ── Billing / Subscription ──
    ("read", "billing"): {UserRole.OWNER},
    ("update", "subscription"): {UserRole.OWNER},
    ("read", "invoices"): {UserRole.OWNER},
    
    # ── Settings ──
    ("read", "settings"): {UserRole.OWNER, UserRole.ADMIN},
    ("update", "settings"): {UserRole.OWNER},
    
    # ── Audit Log ──
    ("read", "audit_log"): {UserRole.OWNER, UserRole.ADMIN},
}


# ══════════════════════════════════════════════════════════════════════════════
# PERMISSION CHECKING
# ══════════════════════════════════════════════════════════════════════════════

def has_permission(
    user: Union["Usuario", dict], 
    action: str, 
    resource: str,
    resource_owner_id: Optional[str] = None
) -> bool:
    """
    Verifica si un usuario tiene permiso para realizar una acción sobre un recurso.
    
    Args:
        user: Usuario o dict con 'role' (y opcionalmente 'id', 'team_gym_id')
        action: Acción a realizar ('create', 'read', 'update', 'delete', etc.)
        resource: Recurso objetivo ('cliente', 'plan', 'team', etc.)
        resource_owner_id: ID del gym dueño del recurso (para verificar multi-tenant)
    
    Returns:
        True si tiene permiso, False si no.
    
    Examples:
        >>> has_permission(user, "create", "cliente")
        True
        >>> has_permission(viewer, "delete", "cliente")
        False
    """
    # Extraer role del usuario
    if hasattr(user, 'role'):
        user_role = user.role
        user_id = getattr(user, 'id', None)
        team_gym_id = getattr(user, 'team_gym_id', None)
        tipo = getattr(user, 'tipo', None)
    else:
        user_role = user.get('role')
        user_id = user.get('id')
        team_gym_id = user.get('team_gym_id')
        tipo = user.get('tipo')
    
    # Convert string role to enum if needed
    if isinstance(user_role, str):
        try:
            user_role = UserRole(user_role)
        except ValueError:
            # Legacy: tipo='gym' o tipo='usuario' sin role explícito → OWNER
            if tipo in ('gym', 'usuario'):
                user_role = UserRole.OWNER
            else:
                _logger.warning(f"Unknown role: {user_role}, defaulting to VIEWER")
                user_role = UserRole.VIEWER
    
    # Si no hay role definido y es tipo gym o usuario, es OWNER
    if user_role is None:
        if tipo in ('gym', 'usuario'):
            user_role = UserRole.OWNER
        else:
            user_role = UserRole.VIEWER
    
    # Override: tipo=usuario siempre es OWNER (dueño de su propia cuenta)
    if tipo == 'usuario' and user_role != UserRole.OWNER:
        user_role = UserRole.OWNER
    
    # Obtener permisos para esta acción+recurso
    permission_key = (action, resource)
    allowed_roles = PERMISSIONS.get(permission_key)
    
    if allowed_roles is None:
        _logger.warning(f"Permission not defined: {permission_key}")
        # Por seguridad, denegar si no está definido
        return user_role == UserRole.OWNER
    
    # Verificar si el rol está permitido
    if user_role not in allowed_roles:
        return False
    
    # Si hay resource_owner_id, verificar que el usuario pertenece a ese gym
    if resource_owner_id is not None:
        effective_gym_id = team_gym_id if team_gym_id else user_id
        if effective_gym_id != resource_owner_id:
            _logger.warning(
                f"Multi-tenant violation: user {user_id} (gym {effective_gym_id}) "
                f"attempted to access resource owned by {resource_owner_id}"
            )
            return False
    
    return True


def verify_permission(
    user: Union["Usuario", dict],
    action: str,
    resource: str,
    resource_owner_id: Optional[str] = None,
    message: Optional[str] = None
) -> None:
    """
    Verifica permiso y lanza HTTPException 403 si no tiene.
    
    Args:
        user: Usuario o dict con 'role'
        action: Acción a realizar
        resource: Recurso objetivo
        resource_owner_id: ID del gym dueño del recurso
        message: Mensaje de error personalizado
    
    Raises:
        HTTPException: 403 si no tiene permiso
    """
    if not has_permission(user, action, resource, resource_owner_id):
        detail = message or f"No tienes permiso para {action} {resource}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════

def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Crea un dependency que verifica que el usuario tenga uno de los roles permitidos.
    
    Args:
        allowed_roles: Roles permitidos para acceder al endpoint
    
    Returns:
        Dependency function para FastAPI
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.OWNER, UserRole.ADMIN))])
        async def admin_endpoint():
            ...
    """
    async def dependency(
        current_user = Depends(_get_current_user_dep())
    ):
        user_role = _extract_role(current_user)
        
        if user_role not in allowed_roles:
            allowed_names = ", ".join(r.value for r in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente. Roles requeridos: {allowed_names}"
            )
        
        return current_user
    
    return dependency


def require_min_role(min_role: UserRole) -> Callable:
    """
    Crea un dependency que verifica que el usuario tenga un rol >= min_role.
    
    Usa la jerarquía: OWNER > ADMIN > NUTRIOLOGO > VIEWER
    
    Args:
        min_role: Rol mínimo requerido
    
    Usage:
        @router.delete("/plan/{id}", dependencies=[Depends(require_min_role(UserRole.ADMIN))])
        async def delete_plan():
            ...
    """
    async def dependency(
        current_user = Depends(_get_current_user_dep())
    ):
        user_role = _extract_role(current_user)
        
        if not has_higher_or_equal_role(user_role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente. Rol mínimo requerido: {min_role.value}"
            )
        
        return current_user
    
    return dependency


def require_permission(action: str, resource: str) -> Callable:
    """
    Crea un dependency que verifica un permiso específico.
    
    Args:
        action: Acción a verificar
        resource: Recurso objetivo
    
    Usage:
        @router.post("/clientes", dependencies=[Depends(require_permission("create", "cliente"))])
        async def create_cliente():
            ...
    """
    async def dependency(
        current_user = Depends(_get_current_user_dep())
    ):
        if not has_permission(current_user, action, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso para {action} {resource}"
            )
        
        return current_user
    
    return dependency


def require_owner() -> Callable:
    """Shortcut for require_role(UserRole.OWNER)."""
    return require_role(UserRole.OWNER)


def require_admin_or_owner() -> Callable:
    """Shortcut for require_role(UserRole.OWNER, UserRole.ADMIN)."""
    return require_role(UserRole.OWNER, UserRole.ADMIN)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_current_user_dep():
    """
    Lazy import para evitar circular imports.
    Retorna el dependency get_usuario_actual.
    """
    from web.auth_deps import get_usuario_actual
    return get_usuario_actual


def _extract_role(user: Union["Usuario", dict]) -> UserRole:
    """Extrae el role de un usuario (objeto o dict)."""
    if hasattr(user, 'role'):
        role = user.role
        tipo = getattr(user, 'tipo', None)
    else:
        role = user.get('role')
        tipo = user.get('tipo')
    
    # Convert string to enum
    if isinstance(role, str):
        try:
            return UserRole(role)
        except ValueError:
            pass
    elif isinstance(role, UserRole):
        return role
    
    # Fallback: legacy tipo='gym' → OWNER
    if tipo == 'gym':
        return UserRole.OWNER
    
    return UserRole.VIEWER


def get_user_permissions(user: Union["Usuario", dict]) -> List[tuple[str, str]]:
    """
    Retorna lista de permisos que tiene un usuario.
    
    Returns:
        Lista de tuplas (action, resource) que el usuario puede ejecutar.
    """
    user_role = _extract_role(user)
    permissions = []
    
    for (action, resource), allowed_roles in PERMISSIONS.items():
        if user_role in allowed_roles:
            permissions.append((action, resource))
    
    return sorted(permissions)


def can_manage_user(manager: Union["Usuario", dict], target: Union["Usuario", dict]) -> bool:
    """
    Verifica si manager puede modificar/eliminar a target.
    
    Rules:
    - OWNER puede gestionar a todos en su gym
    - ADMIN puede gestionar a NUTRIOLOGO y VIEWER (no a otros ADMIN ni OWNER)
    - Nadie puede gestionarse a sí mismo (excepto logout, etc.)
    """
    manager_role = _extract_role(manager)
    target_role = _extract_role(target)
    
    # Extraer IDs
    manager_id = manager.id if hasattr(manager, 'id') else manager.get('id')
    target_id = target.id if hasattr(target, 'id') else target.get('id')
    
    # No puedes gestionarte a ti mismo (para operaciones destructivas)
    if manager_id == target_id:
        return False
    
    # OWNER puede gestionar a todos
    if manager_role == UserRole.OWNER:
        return True
    
    # ADMIN puede gestionar a roles inferiores (no a OWNER ni otros ADMIN)
    if manager_role == UserRole.ADMIN:
        return target_role in (UserRole.NUTRIOLOGO, UserRole.VIEWER)
    
    return False


# ══════════════════════════════════════════════════════════════════════════════
# ROLE DISPLAY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

ROLE_DISPLAY_NAMES = {
    UserRole.OWNER: "Propietario",
    UserRole.ADMIN: "Administrador",
    UserRole.NUTRIOLOGO: "Nutriólogo",
    UserRole.VIEWER: "Solo Lectura",
}

ROLE_DESCRIPTIONS = {
    UserRole.OWNER: "Control total del gimnasio, facturación y equipo",
    UserRole.ADMIN: "Gestión completa excepto facturación y cambios de rol",
    UserRole.NUTRIOLOGO: "Gestionar clientes y generar planes nutricionales",
    UserRole.VIEWER: "Ver información sin poder modificar",
}


def get_role_display_name(role: UserRole) -> str:
    """Retorna nombre para mostrar del rol."""
    return ROLE_DISPLAY_NAMES.get(role, role.value)


def get_role_description(role: UserRole) -> str:
    """Retorna descripción del rol."""
    return ROLE_DESCRIPTIONS.get(role, "")


def get_assignable_roles(assigner_role: UserRole) -> List[UserRole]:
    """
    Retorna los roles que un usuario puede asignar.
    
    - OWNER puede asignar: ADMIN, NUTRIOLOGO, VIEWER
    - ADMIN puede asignar: NUTRIOLOGO, VIEWER
    - Otros: ninguno
    """
    if assigner_role == UserRole.OWNER:
        return [UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER]
    elif assigner_role == UserRole.ADMIN:
        return [UserRole.NUTRIOLOGO, UserRole.VIEWER]
    return []
