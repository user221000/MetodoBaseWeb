"""Professional team API and one-use invitation adapter.

A team membership is separate from a person's independent profile. Revocation
preserves the identity and personal data, clears the team association, and
invalidates existing sessions. Matching an email never creates an association.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from web.auth_deps import get_effective_gym_id, get_usuario_actual
from web.database.engine import get_db
from web.database.models import GymProfile, Usuario, UserRole
from web.services import team_invitation_service as invitations
from web.services.mfa_business import step_up as _step_up, business_session
from web.account_values import normalize_account_email, validate_new_password
from web.services.permissions import (
    can_manage_user, get_assignable_roles, get_role_display_name,
    has_permission, verify_permission,
)

_logger = logging.getLogger(__name__)


def _no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


router = APIRouter(prefix="/gym/team", tags=["Team Management"], dependencies=[Depends(_no_store)])
auth_router = APIRouter(prefix="/auth", tags=["Authentication"], dependencies=[Depends(_no_store)])


class TeamInviteRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    role: UserRole = UserRole.NUTRIOLOGO
    nombre: str = Field(..., min_length=1, max_length=150)
    apellido: str = Field(default="", max_length=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = normalize_account_email(value)
        if any(char.isspace() for char in value) or value.count("@") != 1 or "." not in value.split("@")[-1]:
            raise ValueError("Email inválido")
        return value

    @field_validator("nombre")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Escribe el nombre de la persona")
        return value.strip()


class TeamInviteResponse(BaseModel):
    success: bool
    message: str
    invitation_token: Optional[str] = None
    invitation_link: Optional[str] = None
    expires_at: Optional[datetime] = None
    delivery_status: str = "not_confirmed"
    member_id: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    nombre: str
    apellido: str
    role: str
    role_display: str
    activo: bool
    fecha_registro: datetime
    is_pending: bool = False
    invitation_status: str = "active"
    invitation_expires_at: Optional[datetime] = None
    can_change_role: bool = False
    can_remove: bool = False
    can_resend: bool = False


class TeamListResponse(BaseModel):
    members: list[TeamMemberResponse]
    total: int
    pending_invitations: int
    assignable_roles: list[str]
    capabilities: dict[str, bool]
    invitation_requirement: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    role: UserRole


class InviteInfoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., pattern=r"^[A-Za-z0-9_-]{43}$")


class AcceptInviteRequest(InviteInfoRequest):
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_size(cls, value: str) -> str:
        return validate_new_password(value)


class AcceptInviteResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None


def _gym_name(db: Session, gym_id: str) -> str:
    profile = db.execute(select(GymProfile).where(GymProfile.gym_id == gym_id)).scalar_one_or_none()
    return profile.nombre_negocio if profile and profile.nombre_negocio else "Tu gimnasio en Método Base"


def _target(db: Session, actor: dict, user_id: str) -> Usuario:
    row = db.execute(select(Usuario).where(
        Usuario.id == user_id, Usuario.team_gym_id == get_effective_gym_id(actor),
        Usuario.deleted_at.is_(None),
    )).scalar_one_or_none()
    if row is None:
        invitations.fail(404, "team_member_unavailable", "No se encontró a esa persona en tu equipo.")
    return row


def _member(row: Usuario, actor: dict, *, invitation_allowed: bool = False) -> TeamMemberResponse:
    pending = row.invitation_token is not None and not row.activo
    expires = invitations.utc(row.invitation_expires)
    state = "active" if row.activo else "inactive"
    if pending:
        state = "expired" if expires is None or expires <= datetime.now(timezone.utc) else "pending"
    manageable = row.role != UserRole.OWNER and can_manage_user(actor, {"id":row.id, "role":row.role.value})
    return TeamMemberResponse(
        id=row.id, email=row.email, nombre=row.nombre, apellido=row.apellido,
        role=row.role.value, role_display=get_role_display_name(row.role),
        activo=row.activo, fecha_registro=row.fecha_registro, is_pending=pending,
        invitation_status=state, invitation_expires_at=expires,
        can_change_role=manageable and has_permission(actor, "update_role", "team"),
        can_remove=manageable and has_permission(actor, "remove", "team"),
        can_resend=invitation_allowed and manageable and pending and has_permission(actor, "invite", "team"),
    )


async def _deliver(result: dict, *, email: str, nombre: str, gym_name: str, role: UserRole) -> dict:
    from web.services.email_service import send_team_invitation
    try:
        accepted = await run_in_threadpool(
            send_team_invitation, email=email, nombre=nombre, gym_name=gym_name,
            role=get_role_display_name(role), invite_url=result["invitation_link"],
        )
    except Exception as error:
        _logger.warning("Invitation email not confirmed class=%s", type(error).__name__)
        accepted = False
    if accepted:
        result["delivery_status"] = "provider_accepted"
        result["message"] = "Invitación creada. El proveedor aceptó el correo; su entrega no está confirmada."
    return result


@router.post("/invite", response_model=TeamInviteResponse)
async def invite_team_member(request: TeamInviteRequest, db: Session = Depends(business_session),
                             current_user: dict = Depends(get_usuario_actual), *, http_request: Request):
    verify_permission(current_user, "invite", "team")
    current_user = _step_up(db, current_user, http_request, request.model_dump(mode="json"))
    from web.settings import get_settings
    gym_id = get_effective_gym_id(current_user)
    gym_name = _gym_name(db, gym_id)
    try:
        result = invitations.issue(
            db, actor=current_user, gym_id=gym_id, email=request.email,
            nombre=request.nombre, apellido=request.apellido.strip(), role=request.role,
            base_url=get_settings().BASE_URL,
        )
    except IntegrityError:
        db.rollback()
        invitations.fail(409, "email_already_registered", "Este correo ya tiene una cuenta. No se vinculó al gimnasio.")
    return await _deliver(result, email=request.email, nombre=request.nombre, gym_name=gym_name, role=request.role)


@router.get("", response_model=TeamListResponse)
async def list_team_members(include_pending: bool = True, db: Session = Depends(get_db),
                            current_user: dict = Depends(get_usuario_actual)):
    verify_permission(current_user, "read", "team")
    gym_id = get_effective_gym_id(current_user)
    owner = invitations.ensure_gym(db, gym_id)
    invitation_allowed = invitations.can_issue_invitation(db, gym_id)
    query = select(Usuario).where(Usuario.team_gym_id == gym_id, Usuario.deleted_at.is_(None))
    if not include_pending:
        query = query.where(Usuario.activo.is_(True))
    rows = [owner, *db.execute(query.order_by(Usuario.fecha_registro, Usuario.id)).scalars().all()]
    members = [_member(row, current_user, invitation_allowed=invitation_allowed) for row in rows]
    return TeamListResponse(
        members=members, total=len(members),
        pending_invitations=sum(row.is_pending for row in members),
        assignable_roles=[role.value for role in get_assignable_roles(UserRole(current_user["role"]))],
        capabilities={
            "invite":invitation_allowed and has_permission(current_user,"invite","team"),
            "change_roles":has_permission(current_user,"update_role","team"),
            "remove_members":has_permission(current_user,"remove","team"),
            "revoke_preserves_identity":True,
        },
        invitation_requirement=None if invitation_allowed else "Tu plan actual no permite nuevas incorporaciones. Puedes seguir administrando o retirando los accesos existentes.",
    )


@router.patch("/{user_id}/role", response_model=TeamMemberResponse)
async def update_team_member_role(user_id: str, request: UpdateRoleRequest,
                                  db: Session = Depends(business_session),
                                  current_user: dict = Depends(get_usuario_actual), *, http_request: Request):
    verify_permission(current_user, "update_role", "team")
    current_user = _step_up(db, current_user, http_request, request.model_dump(mode="json"))
    target = _target(db, current_user, user_id)
    invitations.change_role(db, current_user, target, request.role)
    return _member(target, current_user, invitation_allowed=invitations.can_issue_invitation(db, get_effective_gym_id(current_user)))


@router.delete("/{user_id}")
async def remove_team_member(user_id: str, db: Session = Depends(business_session),
                             current_user: dict = Depends(get_usuario_actual), *, http_request: Request):
    verify_permission(current_user, "remove", "team")
    current_user = _step_up(db, current_user, http_request, {})
    target = _target(db, current_user, user_id)
    invitations.revoke_membership(db, current_user, target)
    return {"success":True, "status":"revoked", "message":"Acceso al equipo revocado. La cuenta y los datos personales se conservaron."}


@router.post("/{user_id}/resend-invite", response_model=TeamInviteResponse)
async def resend_invitation(user_id: str, db: Session = Depends(business_session),
                            current_user: dict = Depends(get_usuario_actual), *, http_request: Request):
    verify_permission(current_user, "invite", "team")
    current_user = _step_up(db, current_user, http_request, {})
    target = _target(db, current_user, user_id)
    invitations.manageable(current_user, target)
    if target.activo or not target.invitation_token:
        invitations.fail(404, "invitation_unavailable", "No se encontró una invitación pendiente para esa persona.")
    from web.settings import get_settings
    gym_id = get_effective_gym_id(current_user)
    email, nombre = target.email, target.nombre
    role = target.invitation_role or target.role
    gym_name = _gym_name(db, gym_id)
    result = invitations.issue(
        db, actor=current_user, gym_id=gym_id, email=email, nombre=nombre,
        apellido=target.apellido, role=role, base_url=get_settings().BASE_URL, target=target,
    )
    return await _deliver(result, email=email, nombre=nombre, gym_name=gym_name, role=role)


@auth_router.post("/accept-invite", response_model=AcceptInviteResponse)
async def accept_invitation(request: AcceptInviteRequest, db: Session = Depends(get_db)):
    identity = invitations.consume(db, request.token, request.password)
    from web.auth import crear_token_pair
    tokens = crear_token_pair(identity)
    return AcceptInviteResponse(success=True, message="Invitación aceptada. Tu acceso profesional está confirmado.",
                                access_token=tokens["access_token"], refresh_token=tokens["refresh_token"],
                                user=identity)


def _invitation_info(token: str, db: Session) -> dict:
    user = invitations.find_invitation(db, token)
    if user is None:
        invitations.fail(404, "invitation_unavailable", "La invitación no está disponible. Pide un enlace nuevo.")
    invitations.ensure_gym(db, user.team_gym_id)
    expires = invitations.utc(user.invitation_expires)
    expired = expires is None or expires <= datetime.now(timezone.utc)
    role = user.invitation_role or user.role
    gym_name = "Gimnasio de la invitación"
    can_accept = False
    if not expired:
        from web.database.tenant_context import bind_verified_subject
        try:
            bind_verified_subject(db, user.team_gym_id)
        except ValueError:
            invitations.fail(403, "invitation_context_mismatch", "Cierra la sesión actual para consultar esta invitación.")
        gym_name = _gym_name(db, user.team_gym_id)
        can_accept = invitations.can_issue_invitation(db, user.team_gym_id)
    return {"email":user.email, "nombre":user.nombre, "role":role.value,
            "role_display":get_role_display_name(role), "gym_name":gym_name,
            "is_expired":expired, "status":"expired" if expired else "pending",
            "expires_at":expires, "membership_type":"professional", "can_accept":can_accept,
            "unavailable_reason":None if can_accept or expired else "El plan actual del gimnasio no permite nuevas incorporaciones. Contacta a quien administra el equipo."}


@auth_router.post("/invite-info")
async def post_invitation_info(request: InviteInfoRequest, db: Session = Depends(get_db)):
    return _invitation_info(request.token, db)


@auth_router.get("/invite-info", deprecated=True)
async def get_invitation_info(token: str = Query(..., pattern=r"^[A-Za-z0-9_-]{43}$"),
                              db: Session = Depends(get_db)):
    """Compatibility for outstanding legacy query links until their expiry."""
    return _invitation_info(token, db)
