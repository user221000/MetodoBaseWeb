"""Persisted professional invitations; email transport never grants membership.

The current schema stores one professional association on Usuario. Removing
that association preserves the independent personal profile and its data.
No existing account is attached to a gym by matching its email address.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from web.constants import INVITATION_EXPIRY_DAYS
from web.database.models import RefreshToken, Subscription, Usuario, UserRole
from web.services.permissions import can_manage_user, get_assignable_roles


def utc(value: datetime | None) -> datetime | None:
    """Legacy DateTime columns store UTC without an offset on SQLite/PG."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def fail(status: int, code: str, message: str):
    raise HTTPException(status, detail={"code": code, "message": message})


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def invitation_url(base_url: str, token: str) -> str:
    parsed = urlsplit(base_url.strip())
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})):
        fail(503, "invitation_url_unavailable", "No se pudo preparar el enlace de invitación.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/auth/accept-invite", "", urlencode({"token": token})))


def ensure_gym(db: Session, gym_id: str) -> Usuario:
    gym = db.execute(select(Usuario).where(
        Usuario.id == gym_id, Usuario.tipo == "gym", Usuario.role == UserRole.OWNER,
        Usuario.activo.is_(True), Usuario.deleted_at.is_(None),
    )).scalar_one_or_none()
    if gym is None:
        fail(403, "gym_unavailable", "La pertenencia al gimnasio ya no está disponible.")
    return gym


def manageable(actor: dict, target: Usuario) -> None:
    if target.role == UserRole.OWNER or not can_manage_user(actor, {"id": target.id, "role": target.role.value}):
        fail(403, "team_action_forbidden", "No tienes permiso para modificar a esta persona.")


def can_issue_invitation(db: Session, gym_id: str) -> bool:
    """Canonical persisted subscription policy and catalog own this right."""
    from web.services.feature_gate import FeatureGate
    return FeatureGate(db, gym_id).has_feature("can_multi_user")


def require_invitation_entitlement(db: Session, gym_id: str) -> None:
    # Match billing's account -> subscription lock order, including the owner
    # referenced by a new member's FK. Reversing it can deadlock a callback.
    locked = db.query(Usuario).filter_by(id=gym_id).update(
        {Usuario.id: Usuario.id}, synchronize_session=False,
    )
    if locked != 1:
        fail(403, "gym_unavailable", "La pertenencia al gimnasio ya no está disponible.")
    # Serialize entitlement consumption against provider subscription changes.
    # This no-op acquires a row write lock on PG and a writer lock on SQLite,
    # without changing billing timestamps, money or rights. Reads remain free
    # of this lock. The transaction commits with the invitation mutation.
    db.execute(update(Subscription).where(Subscription.gym_id == gym_id).values(
        updated_at=Subscription.updated_at,
    ).execution_options(synchronize_session=False))
    # Refresh only the locked subscription. Expiring invitation/user objects
    # would discard the observed bearer or membership used by the later CAS.
    db.query(Subscription).filter_by(gym_id=gym_id).populate_existing().first()
    if not can_issue_invitation(db, gym_id):
        fail(402, "team_plan_required", "Tu plan actual no permite nuevas incorporaciones al equipo. Consulta las opciones de suscripción.")


def issue(db: Session, *, actor: dict, gym_id: str, email: str, nombre: str,
          apellido: str, role: UserRole, base_url: str, target: Usuario | None = None) -> dict:
    """Commit the invitation before contacting email; rotate by compare-and-set."""
    ensure_gym(db, gym_id)
    if role not in get_assignable_roles(UserRole(actor["role"])):
        fail(403, "role_forbidden", "No puedes asignar ese rol.")
    require_invitation_entitlement(db, gym_id)
    token = secrets.token_urlsafe(32)
    link = invitation_url(base_url, token)
    expires = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
    if target is None:
        if db.execute(select(Usuario.id).where(Usuario.email == email)).first():
            fail(409, "email_already_registered", "Este correo ya tiene una cuenta. No se vinculó al gimnasio.")
        target = Usuario(email=email, nombre=nombre, apellido=apellido,
                         password_hash="PENDING_INVITATION", tipo="usuario", role=role,
                         team_gym_id=gym_id, invited_by=actor["id"], activo=False,
                         invitation_token=token_digest(token), invitation_expires=expires,
                         invitation_role=role)
        db.add(target)
        db.flush()
    else:
        manageable(actor, target)
        previous = target.invitation_token
        result = db.execute(update(Usuario).where(
            Usuario.id == target.id, Usuario.team_gym_id == gym_id,
            Usuario.activo.is_(False), Usuario.invitation_token == previous,
            Usuario.invitation_token.isnot(None),
            Usuario.session_version == target.session_version,
            Usuario.invitation_role == target.invitation_role,
        ).values(invitation_token=token_digest(token), invitation_expires=expires,
                 invitation_role=role).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            db.rollback()
            fail(409, "invitation_changed", "La invitación cambió. Consulta el equipo antes de reintentar.")
    subject = target.id
    db.commit()
    return {"success": True, "message": "Invitación creada. La entrega del correo no está confirmada.",
            "invitation_token": token, "invitation_link": link, "expires_at": expires,
            "delivery_status": "not_confirmed", "member_id": subject}


def find_invitation(db: Session, token: str) -> Usuario | None:
    # Existing generated legacy tokens have 43 URL-safe characters. Only that
    # length can be a bearer token: a stored 64-character digest cannot be used.
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    return db.execute(select(Usuario).where(
        or_(Usuario.invitation_token == token_digest(token), Usuario.invitation_token == token),
        Usuario.activo.is_(False), Usuario.team_gym_id.isnot(None),
        Usuario.deleted_at.is_(None),
    )).scalar_one_or_none()


def consume(db: Session, token: str, password: str) -> dict:
    """One conditional UPDATE wins even when two readers observed the token."""
    from web.auth import hash_password, identity_from_user

    user = find_invitation(db, token)
    if user is None:
        fail(400, "invitation_unavailable", "La invitación no está disponible. Pide un enlace nuevo.")
    now = datetime.now(timezone.utc)
    if utc(user.invitation_expires) is None or utc(user.invitation_expires) <= now:
        fail(410, "invitation_expired", "La invitación venció. Pide un enlace nuevo.")
    ensure_gym(db, user.team_gym_id)
    # A bearer is verified against persisted digest and expiry before using its
    # gym identity. Public callers carry no authority from an arbitrary input.
    from web.database.tenant_context import bind_verified_subject
    try:
        bind_verified_subject(db, user.team_gym_id)
    except ValueError:
        fail(403, "invitation_context_mismatch", "Cierra la sesión actual para aceptar esta invitación.")
    require_invitation_entitlement(db, user.team_gym_id)
    role = user.invitation_role or user.role
    if role not in {UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER}:
        fail(403, "role_unavailable", "No se pudo confirmar el rol de la invitación.")
    result = db.execute(update(Usuario).where(
        Usuario.id == user.id, Usuario.invitation_token == user.invitation_token,
        Usuario.team_gym_id == user.team_gym_id, Usuario.activo.is_(False),
        Usuario.session_version == user.session_version,
        Usuario.role == user.role, Usuario.invitation_role == user.invitation_role,
        Usuario.invitation_expires > now.replace(tzinfo=None),
    ).values(password_hash=hash_password(password), activo=True, role=role,
             invitation_token=None, invitation_expires=None, invitation_role=None,
             tipo="usuario").execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        fail(409, "invitation_consumed", "La invitación cambió o ya se utilizó. Inicia sesión o pide un enlace nuevo.")
    db.expire_all()
    current = db.get(Usuario, user.id)
    identity = identity_from_user(current, db)
    if not identity:
        db.rollback()
        fail(403, "membership_unavailable", "La pertenencia al gimnasio ya no está disponible.")
    db.commit()
    return identity


def _change_membership(db: Session, actor: dict, user: Usuario, changes: dict) -> None:
    """Apply one authorized observed membership and invalidate its sessions.

    A stale management request cannot alter a later association, role or
    session generation. Refresh revocation follows the same conditional write
    and is committed in its transaction; rejected writes revoke no sessions.
    """
    manageable(actor, user)
    gym_id = actor.get("team_gym_id") or actor["id"]
    if not user.team_gym_id or user.team_gym_id != gym_id:
        fail(404, "membership_unavailable", "No se encontró esa pertenencia en el equipo.")
    result = db.execute(update(Usuario).where(
        Usuario.id == user.id, Usuario.team_gym_id == gym_id,
        Usuario.role == user.role,
        func.coalesce(Usuario.session_version, 0) == (user.session_version or 0),
        Usuario.activo == user.activo, Usuario.deleted_at.is_(None),
        Usuario.invitation_token == user.invitation_token,
        Usuario.invitation_role == user.invitation_role,
    ).values(**changes, session_version=func.coalesce(Usuario.session_version, 0) + 1)
      .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        fail(409, "membership_changed", "La pertenencia cambió. Consulta el equipo antes de reintentar.")
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.expire(user)


def change_role(db: Session, actor: dict, user: Usuario, role: UserRole) -> None:
    """Change role by compare-and-set; never flush an unguarded ORM mutation."""
    if role not in get_assignable_roles(UserRole(actor["role"])):
        fail(403, "role_forbidden", "No puedes asignar ese rol.")
    changes = {"role": role}
    if user.invitation_token:
        changes["invitation_role"] = role
    _change_membership(db, actor, user, changes)
    db.commit()
    db.refresh(user)


def revoke_membership(db: Session, actor: dict, user: Usuario) -> None:
    """Detach an explicit professional membership, keeping personal identity."""
    _change_membership(db, actor, user, {
        "team_gym_id": None, "role": UserRole.VIEWER, "tipo": "usuario",
        "invitation_token": None, "invitation_expires": None, "invitation_role": None,
    })
    db.commit()
