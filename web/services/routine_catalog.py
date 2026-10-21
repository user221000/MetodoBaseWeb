"""Read-only routine access. No account/profile bootstrap or new entitlement."""
from fastapi import HTTPException
from sqlalchemy import select

from core.routine_catalog import get_routine_program
from web.database.models import Usuario, UserRole

_FIELDS = (Usuario.id, Usuario.tipo, Usuario.role, Usuario.team_gym_id, Usuario.activo,
           Usuario.deleted_at, Usuario.invitation_token, Usuario.session_version)


def _live(row):
    return (row is not None and row.activo is True and row.deleted_at is None
            and row.invitation_token is None and type(row.session_version) is int
            and 0 <= row.session_version <= 2147483647 and row.role in tuple(UserRole))


def _owner(row):
    return (_live(row) and row.tipo == "gym" and row.role == UserRole.OWNER
            and row.team_gym_id is None)


def catalog_for_subject(db, principal, context):
    """Revalidate actor/parent from persisted fields; emit only generic content."""
    if context not in ("personal", "gym"):
        raise HTTPException(422, {"code": "routine_invalid_context", "message": "Elige el espacio de tu cuenta."})
    actor = db.execute(select(*_FIELDS).where(Usuario.id == principal["id"])).first()
    if (not _live(actor) or type(principal.get("session_version")) is not int
            or actor.session_version != principal["session_version"]
            or actor.tipo != principal.get("tipo") or actor.role.value != principal.get("role")
            or actor.team_gym_id != principal.get("team_gym_id")):
        raise HTTPException(401, {"code": "routine_session_unavailable", "message": "Vuelve a iniciar sesión."})
    team = False
    if actor.team_gym_id:
        parent = db.execute(select(*_FIELDS).where(Usuario.id == actor.team_gym_id)).first()
        team = _owner(parent) and actor.role in (UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER)
        if not team:
            raise HTTPException(403, {"code": "routine_context_forbidden", "message": "Este espacio no está disponible para tu cuenta."})
    allowed = (_owner(actor) or team) if context == "gym" else (
        actor.role != UserRole.OWNER and (team or (actor.tipo == "usuario" and actor.team_gym_id is None)))
    if not allowed:
        raise HTTPException(403, {"code": "routine_context_forbidden", "message": "Este espacio no está disponible para tu cuenta."})
    return {"version": 1, "scope": context, "program": get_routine_program()}
