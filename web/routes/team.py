"""
web/routes/team.py — Endpoints para gestión de equipos RBAC.

Permite a owners y admins:
- Invitar miembros al equipo
- Ver miembros del equipo
- Cambiar roles
- Eliminar miembros

Multi-tenant: Todas las operaciones están aisladas al gym del usuario.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from web.database.engine import get_db
from web.database.models import Usuario
from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.auth import hash_password
from web.services.permissions import (
    require_role,
    require_permission,
    has_permission,
    verify_permission,
    can_manage_user,
    get_assignable_roles,
    get_role_display_name,
    ROLE_HIERARCHY,
    UserRole,
)
from web.constants import INVITATION_EXPIRY_DAYS

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gym/team", tags=["Team Management"])


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class TeamInviteRequest(BaseModel):
    """Request para invitar a un miembro del equipo."""
    email: str = Field(..., description="Email del usuario a invitar")
    role: UserRole = Field(default=UserRole.NUTRIOLOGO, description="Rol a asignar")
    nombre: str = Field(..., min_length=1, max_length=150, description="Nombre del invitado")
    apellido: str = Field(default="", max_length=150, description="Apellido del invitado")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Valida formato de email básico."""
        v = v.strip().lower()
        if not v or '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Email inválido')
        return v


class TeamInviteResponse(BaseModel):
    """Response de invitación creada."""
    success: bool
    message: str
    invitation_token: Optional[str] = None
    invitation_link: Optional[str] = None
    expires_at: Optional[datetime] = None


class TeamMemberResponse(BaseModel):
    """Respuesta con datos de un miembro del equipo."""
    id: str
    email: str
    nombre: str
    apellido: str
    role: str
    role_display: str
    activo: bool
    fecha_registro: datetime
    is_pending: bool = False
    
    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    """Lista de miembros del equipo."""
    members: List[TeamMemberResponse]
    total: int
    pending_invitations: int


class UpdateRoleRequest(BaseModel):
    """Request para cambiar rol de un miembro."""
    role: UserRole = Field(..., description="Nuevo rol a asignar")


class AcceptInviteRequest(BaseModel):
    """Request para aceptar invitación."""
    token: str = Field(..., min_length=32, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class AcceptInviteResponse(BaseModel):
    """Response de invitación aceptada."""
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _get_effective_gym_id(user: dict) -> str:
    """Obtiene el gym_id efectivo del usuario (propio si es owner, team_gym_id si es member)."""
    return get_effective_gym_id(user)


def _generate_invitation_token() -> str:
    """Genera un token seguro para invitaciones."""
    return secrets.token_urlsafe(32)


async def _send_invitation_email(
    to_email: str,
    inviter_name: str,
    gym_name: str,
    role: str,
    invitation_link: str
) -> None:
    """
    Envía email de invitación vía Resend (si configurado).
    """
    from web.services.email_service import send_team_invitation
    from web.settings import get_settings

    base_url = get_settings().BASE_URL
    invite_url = f"{base_url}/auth/accept-invite?token={invitation_link}"
    sent = send_team_invitation(
        email=to_email,
        nombre=inviter_name,
        gym_name=gym_name,
        role=role,
        invite_url=invite_url,
    )
    if sent:
        _logger.info("[TEAM] Invitation email sent to %s", to_email)
    else:
        _logger.warning(
            "[TEAM] Could not send invitation email to %s (email service not configured)",
            to_email,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/invite", response_model=TeamInviteResponse)
async def invite_team_member(
    request: TeamInviteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_usuario_actual),
):
    """
    Invita a un nuevo miembro al equipo del gym.
    
    - Solo OWNER y ADMIN pueden invitar
    - ADMIN no puede invitar con rol ADMIN o superior
    - El invitado recibe un token para crear su cuenta
    """
    # Verificar permiso de invitar
    verify_permission(current_user, "invite", "team")
    
    # Verificar que el rol a asignar es válido
    current_role = UserRole(current_user.get("role", "viewer"))
    assignable = get_assignable_roles(current_role)
    
    if request.role not in assignable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No puedes asignar el rol {request.role.value}. Roles permitidos: {[r.value for r in assignable]}"
        )
    
    # Verificar que el email no existe ya
    existing = db.execute(
        select(Usuario).where(Usuario.email == request.email.lower())
    ).scalar_one_or_none()
    
    if existing:
        if existing.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con ese email"
            )
        # Si está inactivo, podría reactivarse - pero eso es otro flujo
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese email ya está registrado (cuenta inactiva)"
        )
    
    # Obtener gym_id efectivo
    gym_id = _get_effective_gym_id(current_user)
    
    # Generar token de invitación
    token = _generate_invitation_token()
    expires = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
    
    # Crear usuario pendiente (sin password, con token)
    new_user = Usuario(
        email=request.email.lower().strip(),
        password_hash="PENDING_INVITATION",  # Placeholder, se setea al aceptar
        nombre=request.nombre.strip(),
        apellido=request.apellido.strip(),
        tipo="usuario",
        role=request.role,
        team_gym_id=gym_id,
        invited_by=current_user["id"],
        invitation_token=token,
        invitation_expires=expires,
        invitation_role=request.role,
        activo=False,  # Inactivo hasta que acepte
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generar link de invitación
    # TODO: Usar settings.BASE_URL
    invitation_link = f"/auth/accept-invite?token={token}"
    
    # Enviar email en background
    gym_profile = getattr(current_user, 'gym_profile', None)
    gym_name = gym_profile.nombre_negocio if gym_profile else "MetodoBase Gym"
    
    background_tasks.add_task(
        _send_invitation_email,
        to_email=request.email,
        inviter_name=current_user.get("nombre", "Admin"),
        gym_name=gym_name,
        role=get_role_display_name(request.role),
        invitation_link=invitation_link
    )
    
    _logger.info(
        f"[TEAM] User {current_user['id']} invited {request.email} as {request.role.value} to gym {gym_id}"
    )
    
    return TeamInviteResponse(
        success=True,
        message=f"Invitación enviada a {request.email}",
        invitation_token=token,
        invitation_link=invitation_link,
        expires_at=expires
    )


@router.get("", response_model=TeamListResponse)
async def list_team_members(
    include_pending: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_usuario_actual),
):
    """
    Lista los miembros del equipo del gym.
    
    - Solo OWNER y ADMIN pueden ver el equipo
    - Incluye invitaciones pendientes si include_pending=True
    """
    verify_permission(current_user, "read", "team")
    
    gym_id = _get_effective_gym_id(current_user)
    
    # Query miembros activos del equipo
    query = select(Usuario).where(
        Usuario.team_gym_id == gym_id
    )
    
    if not include_pending:
        query = query.where(Usuario.activo == True)
    
    results = db.execute(query).scalars().all()
    
    members = []
    pending_count = 0
    
    for user in results:
        is_pending = user.invitation_token is not None and not user.activo
        if is_pending:
            pending_count += 1
        
        members.append(TeamMemberResponse(
            id=user.id,
            email=user.email,
            nombre=user.nombre,
            apellido=user.apellido,
            role=user.role.value if user.role else UserRole.VIEWER.value,
            role_display=get_role_display_name(user.role or UserRole.VIEWER),
            activo=user.activo,
            fecha_registro=user.fecha_registro,
            is_pending=is_pending
        ))
    
    # Incluir al owner también (para referencia)
    owner = db.execute(
        select(Usuario).where(Usuario.id == gym_id)
    ).scalar_one_or_none()
    
    if owner:
        members.insert(0, TeamMemberResponse(
            id=owner.id,
            email=owner.email,
            nombre=owner.nombre,
            apellido=owner.apellido,
            role=UserRole.OWNER.value,
            role_display=get_role_display_name(UserRole.OWNER),
            activo=owner.activo,
            fecha_registro=owner.fecha_registro,
            is_pending=False
        ))
    
    return TeamListResponse(
        members=members,
        total=len(members),
        pending_invitations=pending_count
    )


@router.patch("/{user_id}/role", response_model=TeamMemberResponse)
async def update_team_member_role(
    user_id: str,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_usuario_actual),
):
    """
    Actualiza el rol de un miembro del equipo.
    
    - Solo OWNER puede cambiar roles
    - No se puede cambiar el rol del owner
    """
    verify_permission(current_user, "update_role", "team")
    
    gym_id = _get_effective_gym_id(current_user)
    
    # Buscar el usuario target
    target = db.execute(
        select(Usuario).where(
            Usuario.id == user_id,
            Usuario.team_gym_id == gym_id
        )
    ).scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Miembro no encontrado en tu equipo"
        )
    
    # No se puede modificar al owner
    if target.id == gym_id or target.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede modificar el rol del propietario"
        )
    
    # Verificar que el rol es asignable
    current_role = UserRole(current_user.get("role", "viewer"))
    assignable = get_assignable_roles(current_role)
    
    if request.role not in assignable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No puedes asignar el rol {request.role.value}"
        )
    
    # Actualizar rol
    old_role = target.role
    target.role = request.role
    
    # Si hay invitación pendiente, actualizar también invitation_role
    if target.invitation_token:
        target.invitation_role = request.role
    
    db.commit()
    db.refresh(target)
    
    _logger.info(
        f"[TEAM] User {current_user['id']} changed role of {user_id} from {old_role} to {request.role.value}"
    )
    
    return TeamMemberResponse(
        id=target.id,
        email=target.email,
        nombre=target.nombre,
        apellido=target.apellido,
        role=target.role.value if target.role else UserRole.VIEWER.value,
        role_display=get_role_display_name(target.role or UserRole.VIEWER),
        activo=target.activo,
        fecha_registro=target.fecha_registro,
        is_pending=target.invitation_token is not None and not target.activo
    )


@router.delete("/{user_id}")
async def remove_team_member(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_usuario_actual),
):
    """
    Elimina un miembro del equipo.
    
    - OWNER puede eliminar a cualquiera
    - ADMIN puede eliminar a NUTRIOLOGO y VIEWER
    - No se puede auto-eliminar (usar logout/deactivate)
    """
    verify_permission(current_user, "remove", "team")
    
    gym_id = _get_effective_gym_id(current_user)
    
    # No se puede auto-eliminar
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminarte a ti mismo. Usa la opción de salir del equipo."
        )
    
    # Buscar el usuario target
    target = db.execute(
        select(Usuario).where(
            Usuario.id == user_id,
            Usuario.team_gym_id == gym_id
        )
    ).scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Miembro no encontrado en tu equipo"
        )
    
    # No se puede eliminar al owner
    if target.id == gym_id or target.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede eliminar al propietario del gimnasio"
        )
    
    # Verificar jerarquía (ADMIN no puede eliminar a otro ADMIN)
    if not can_manage_user(current_user, {"role": target.role.value if target.role else "viewer", "id": target.id}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar a este usuario"
        )
    
    # Eliminar usuario
    target_email = target.email
    db.delete(target)
    db.commit()
    
    _logger.info(
        f"[TEAM] User {current_user['id']} removed {user_id} ({target_email}) from gym {gym_id}"
    )
    
    return {"success": True, "message": f"Usuario {target_email} eliminado del equipo"}


@router.post("/{user_id}/resend-invite")
async def resend_invitation(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_usuario_actual),
):
    """
    Reenvía la invitación a un miembro pendiente.
    
    - Solo para usuarios con invitación pendiente
    - Regenera el token y extiende la expiración
    """
    verify_permission(current_user, "invite", "team")
    
    gym_id = _get_effective_gym_id(current_user)
    
    # Buscar usuario pendiente
    target = db.execute(
        select(Usuario).where(
            Usuario.id == user_id,
            Usuario.team_gym_id == gym_id,
            Usuario.activo == False,
            Usuario.invitation_token.isnot(None)
        )
    ).scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación pendiente no encontrada"
        )
    
    # Regenerar token
    new_token = _generate_invitation_token()
    new_expires = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
    
    target.invitation_token = new_token
    target.invitation_expires = new_expires
    
    db.commit()
    
    invitation_link = f"/auth/accept-invite?token={new_token}"
    
    # Reenviar email
    background_tasks.add_task(
        _send_invitation_email,
        to_email=target.email,
        inviter_name=current_user.get("nombre", "Admin"),
        gym_name="MetodoBase Gym",
        role=get_role_display_name(target.invitation_role or target.role or UserRole.VIEWER),
        invitation_link=invitation_link
    )
    
    _logger.info(f"[TEAM] Invitation resent to {target.email} by {current_user['id']}")
    
    return {
        "success": True,
        "message": f"Invitación reenviada a {target.email}",
        "expires_at": new_expires
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINT (Accept Invite) - Registrado en router separado
# ══════════════════════════════════════════════════════════════════════════════

# Este endpoint se monta en /auth/accept-invite
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/accept-invite", response_model=AcceptInviteResponse)
async def accept_invitation(
    request: AcceptInviteRequest,
    db: Session = Depends(get_db),
):
    """
    Acepta una invitación de equipo y activa la cuenta.
    
    - Valida el token
    - Verifica que no haya expirado
    - Setea el password y activa el usuario
    - Retorna tokens de autenticación
    """
    # Buscar usuario por token
    user = db.execute(
        select(Usuario).where(
            Usuario.invitation_token == request.token,
            Usuario.activo == False
        )
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de invitación inválido"
        )
    
    # Verificar expiración
    if user.invitation_expires and user.invitation_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La invitación ha expirado. Solicita una nueva invitación."
        )
    
    # Validar password
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    # C5 FIX: Invalidar token ANTES de procesar para prevenir race condition
    # Si dos requests llegan simultáneamente, solo la primera tendrá el token
    old_token = user.invitation_token
    user.invitation_token = None
    user.invitation_expires = None
    db.flush()  # Escribir inmediatamente para bloquear otras transacciones
    
    # Activar usuario
    user.password_hash = hash_password(request.password)
    user.activo = True
    
    # Si hay invitation_role, asegurarse de que el role esté seteado
    if user.invitation_role:
        user.role = user.invitation_role
        user.invitation_role = None
    
    db.commit()
    db.refresh(user)
    
    # Generar tokens
    from web.auth import crear_token_pair, identity_from_user

    user_data = identity_from_user(user, db)
    if not user_data:
        raise HTTPException(403, "La membresía ya no está disponible.")
    
    tokens = crear_token_pair(user_data)
    
    _logger.info(f"[TEAM] Invitation accepted by {user.email}, role: {user.role}")
    
    return AcceptInviteResponse(
        success=True,
        message="¡Bienvenido al equipo! Tu cuenta ha sido activada.",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"]
    )


@auth_router.get("/invite-info")
async def get_invitation_info(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Obtiene información sobre una invitación (para mostrar en UI de registro).
    
    No requiere autenticación.
    """
    user = db.execute(
        select(Usuario).where(
            Usuario.invitation_token == token,
            Usuario.activo == False
        )
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación no encontrada"
        )
    
    # Verificar expiración
    is_expired = user.invitation_expires and user.invitation_expires < datetime.now(timezone.utc)
    
    # Obtener info del gym
    gym = db.execute(
        select(Usuario).where(Usuario.id == user.team_gym_id)
    ).scalar_one_or_none()
    
    gym_name = "MetodoBase Gym"
    if gym and hasattr(gym, 'gym_profile') and gym.gym_profile:
        gym_name = gym.gym_profile.nombre_negocio or gym_name
    
    return {
        "email": user.email,
        "nombre": user.nombre,
        "role": user.invitation_role.value if user.invitation_role else (user.role.value if user.role else "viewer"),
        "role_display": get_role_display_name(user.invitation_role or user.role or UserRole.VIEWER),
        "gym_name": gym_name,
        "is_expired": is_expired,
        "expires_at": user.invitation_expires
    }
