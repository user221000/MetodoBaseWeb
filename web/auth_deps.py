"""
web/auth_deps.py — FastAPI auth dependencies (extracted for reuse).

Shared between web/main_web.py and web/routes/*.
Avoids circular imports.

RBAC: Incluye role en el usuario retornado y helpers para verificar permisos.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_security = HTTPBearer(auto_error=False)


def get_usuario_actual(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> dict:
    """
    Dependency que valida el Bearer token. Lanza 401 si inválido.
    
    Returns:
        dict con: id, email, nombre, tipo, role, team_gym_id
    """
    from web.auth import verificar_token
    token = credentials.credentials if credentials else None
    usuario = verificar_token(token)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Asegurar que role esté presente (legacy compatibility)
    # tipo=usuario es siempre owner de su propia cuenta (sin equipo multi-usuario)
    if "role" not in usuario or usuario.get("tipo") == "usuario":
        usuario["role"] = "owner" if usuario.get("tipo") in ("gym", "usuario") else "viewer"
    
    return usuario


def get_usuario_gym(usuario: dict = Depends(get_usuario_actual)) -> dict:
    """
    Requiere tipo 'gym' o 'admin', o role OWNER.
    
    Para operaciones que solo el owner del gym puede hacer.
    Team members con otros roles son rechazados.
    """
    is_owner = (
        usuario.get("tipo") in ("gym", "admin") or 
        usuario.get("role") == "owner"
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso permitido solo para Socios Comerciales (Propietarios)."
        )
    return usuario


def get_usuario_with_role(
    *allowed_roles: str,
) -> callable:
    """
    Factory para crear dependency que requiere roles específicos.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(get_usuario_with_role("owner", "admin"))])
        async def admin_endpoint():
            ...
    """
    def dependency(usuario: dict = Depends(get_usuario_actual)) -> dict:
        user_role = usuario.get("role", "viewer")
        
        # Legacy: tipo='gym' → role='owner'
        if user_role is None and usuario.get("tipo") == "gym":
            user_role = "owner"
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente. Roles requeridos: {', '.join(allowed_roles)}"
            )
        return usuario
    
    return dependency


def get_effective_gym_id(usuario: dict) -> str:
    """
    Obtiene el gym_id efectivo para queries multi-tenant.
    
    - Si es owner (tipo='gym' o role='owner'), retorna su propio ID
    - Si es team member, retorna team_gym_id
    """
    if usuario.get("tipo") == "gym" or usuario.get("role") == "owner":
        return usuario["id"]
    return usuario.get("team_gym_id") or usuario["id"]


async def with_sentry_context(usuario: dict = Depends(get_usuario_actual)):
    """
    Dependency que setea contexto Sentry después de autenticación.
    
    Usar en endpoints que requieren trazabilidad de usuario en Sentry.
    Se ejecuta DESPUÉS de auth, a diferencia del middleware que corría antes.
    
    Returns:
        dict: El mismo usuario autenticado.
    """
    from web.observability.sentry_setup import set_user_context
    set_user_context(
        user_id=str(usuario.get("id", "")),
        gym_id=str(usuario.get("team_gym_id") or usuario.get("id", "")),
        role=str(usuario.get("role", "unknown")),
    )
    return usuario


# ── Permission helpers ───────────────────────────────────────────────────────

def require_permission(action: str, resource: str):
    """
    Dependency factory que verifica un permiso específico.
    
    Usage:
        @router.post("/clientes", dependencies=[Depends(require_permission("create", "cliente"))])
        async def create_cliente():
            ...
    """
    async def dependency(usuario: dict = Depends(get_usuario_actual)) -> dict:
        from web.services.permissions import verify_permission
        verify_permission(usuario, action, resource)
        return usuario
    
    return dependency
