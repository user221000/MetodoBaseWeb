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
    actor = _authorized_actor(db, principal, context)
    program = get_routine_program()
    if context == "gym":
        from core.gym_equipment_catalog import get_effective_equipment
        from web.services.gym_equipment import read_inventory
        inventory = read_inventory(db, actor.team_gym_id or actor.id)
        program.update(inventory=inventory, requires_generation=True)
        program["requirements"]["equipment"] = get_effective_equipment(inventory["machine_ids"])
        program["summary"] = "Genera tus sesiones con las máquinas disponibles en tu gimnasio."
        for session in program["sessions"]:
            session["exercises"] = []
            session.pop("estimated_minutes", None)
    return {"version": 1, "scope": context, "program": program}


def exercises_for_subject(db, principal, context):
    actor = _authorized_actor(db, principal, context)
    from core.routine_catalog import get_exercise_catalog
    exercises = get_exercise_catalog()
    result = {"version": 1, "scope": context, "exercises": exercises}
    if context == "gym":
        from core.gym_equipment_catalog import annotate_inventory
        from web.services.gym_equipment import read_inventory
        inventory = read_inventory(db, actor.team_gym_id or actor.id)
        result.update(exercises=annotate_inventory(exercises, inventory["machine_ids"]), inventory=inventory)
    return result


def generate_for_subject(db, principal, context, requirements):
    actor = _authorized_actor(db, principal, context)
    from core.routine_generator import build_routine, RoutineGenerationError
    requirements = dict(requirements)
    expected_revision = requirements.pop("expected_inventory_revision", None)
    inventory = None
    if context == "gym":
        from core.gym_equipment_catalog import get_effective_equipment
        from web.services.gym_equipment import read_inventory
        inventory = read_inventory(db, actor.team_gym_id or actor.id)
        if type(expected_revision) is not int:
            raise HTTPException(422, {"code": "routine_inventory_required",
                "message": "Consulta el equipamiento del gimnasio antes de generar."})
        if inventory["revision"] != expected_revision:
            _inventory_changed()
        # Inventory is authority. Client JSON cannot enable an absent machine
        # or remove the basic free-weight equipment supplied by every gym.
        requirements["equipment"] = get_effective_equipment(inventory["machine_ids"])
    elif expected_revision is not None:
        raise HTTPException(422, {"code": "routine_invalid_requirements",
            "message": "Elige tu equipo desde el espacio personal."})
    try:
        program = build_routine(requirements, available_machine_ids=None if inventory is None else inventory["machine_ids"])
    except RoutineGenerationError as error:
        message = error.message
        if context == "gym" and error.code in ("insufficient_equipment", "insufficient_exercises"):
            message = "El inventario actual no permite cubrir estas sesiones. Revisa las máquinas disponibles y tus requisitos."
        raise HTTPException(422, {"code": error.code, "message": message}) from None
    if inventory is not None:
        program["inventory"] = inventory
    return {"version": 1, "scope": context, "program": program}


def _inventory_changed():
    raise HTTPException(409, {"code": "routine_inventory_changed",
        "message": "Cambió el equipamiento del gimnasio. Actualízalo antes de generar de nuevo."})


def confirm_inventory_current(db, principal, context, expected):
    """Called in a fresh, separately owned session before publishing a result."""
    from web.services.gym_equipment import read_inventory
    actor = _authorized_actor(db, principal, context)
    current = read_inventory(db, actor.team_gym_id or actor.id)
    if current != expected:
        _inventory_changed()


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
