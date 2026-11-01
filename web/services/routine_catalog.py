"""Read-only routine access. No account/profile bootstrap or new entitlement."""
from fastapi import HTTPException
from sqlalchemy import select

from core.routine_catalog import get_routine_program
from web.database.models import Cliente, Usuario, UserRole

_FIELDS = (Usuario.id, Usuario.tipo, Usuario.role, Usuario.team_gym_id, Usuario.activo,
           Usuario.deleted_at, Usuario.invitation_token, Usuario.session_version)


def _live(row):
    return (row is not None and row.activo is True and row.deleted_at is None
            and row.invitation_token is None and type(row.session_version) is int
            and 0 <= row.session_version <= 2147483647 and row.role in tuple(UserRole))


def _owner(row):
    return (_live(row) and row.tipo == "gym" and row.role == UserRole.OWNER
            and row.team_gym_id is None)


def _authorized_actor(db, principal, context):
    """Revalidate actor and parent before reading any client or deriving a guide."""
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
    return actor


def catalog_for_subject(db, principal, context):
    """Emit the default guide without account or client data."""
    _authorized_actor(db, principal, context)
    return {"version": 1, "scope": context, "program": get_routine_program()}


def exercises_for_subject(db, principal, context):
    _authorized_actor(db, principal, context)
    from core.routine_catalog import get_exercise_catalog
    return {"version": 1, "scope": context, "exercises": get_exercise_catalog()}


def generate_for_subject(db, principal, context, requirements):
    _authorized_actor(db, principal, context)
    from core.routine_generator import build_routine, RoutineGenerationError
    try:
        program = build_routine(requirements)
    except RoutineGenerationError as error:
        raise HTTPException(422, {"code": error.code, "message": error.message}) from None
    return {"version": 1, "scope": context, "program": program}


def _active_clients(owner_id):
    return (Cliente.gym_id == owner_id, Cliente.activo.is_(True), Cliente.deleted_at.is_(None))


def clients_for_subject(db, principal, context, *, query="", limit=30, offset=0):
    actor = _authorized_actor(db, principal, context)
    if context != "gym":
        raise HTTPException(403, {"code": "routine_context_forbidden", "message": "Abre este selector desde tu espacio comercial."})
    owner_id = actor.team_gym_id or actor.id
    statement = select(Cliente.id_cliente, Cliente.nombre).where(*_active_clients(owner_id))
    term = query.strip()
    if term:
        # Search only the displayed name; wildcards are literal user text.
        term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Cliente.nombre.ilike("%" + term + "%", escape="\\"))
    rows = db.execute(statement.order_by(Cliente.nombre, Cliente.id_cliente).offset(offset).limit(limit + 1)).all()
    return {"version": 1, "scope": context,
            "clients": [{"id": row.id_cliente, "name": row.nombre} for row in rows[:limit]],
            "has_more": len(rows) > limit, "offset": offset, "limit": limit}


def requirements_for_subject(db, principal, context, client_id=None):
    actor = _authorized_actor(db, principal, context)
    if context == "gym":
        if client_id is None:
            raise HTTPException(422, {"code": "routine_client_required", "message": "Elige un cliente de tu cuenta."})
        rows = db.execute(select(Cliente.nivel_actividad).where(
            *_active_clients(actor.team_gym_id or actor.id), Cliente.id_cliente == client_id)).all()
        if not rows:
            raise HTTPException(404, {"code": "routine_client_unavailable", "message": "Este cliente no está disponible."})
    else:
        if client_id is not None:
            raise HTTPException(422, {"code": "routine_invalid_requirements", "message": "Usa tu propio perfil desde este espacio."})
        # Read only. An absent or ambiguous personal profile never bootstraps
        # or adopts a gym's clients, including for team members.
        rows = db.execute(select(Cliente.nivel_actividad).where(*_active_clients(actor.id)).limit(2)).all()
    available = len(rows) == 1
    value = rows[0].nivel_actividad if available else None
    activity = value.strip().lower() if isinstance(value, str) else None
    if activity == "normal":
        activity = "moderada"
    if activity not in {"nula", "leve", "moderada", "intensa"}:
        activity = None
    return {"version": 1, "scope": context, "requirements": {"activity_level": activity},
            "source": "client" if context == "gym" else "personal", "available": available}
