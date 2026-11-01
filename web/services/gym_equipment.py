"""Persistent inventory with owner-only writes and revision compare-and-swap."""
import json

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from web.database.models import GymSettings, Usuario
from web.services.routine_catalog import _authorized_actor, _owner

BASE_EQUIPMENT = ["barbell", "bench", "dumbbell", "bodyweight"]
MAX_REVISION = 2147483647


def _catalog():
    from core.gym_equipment_catalog import get_machine_catalog
    return get_machine_catalog()


def _unavailable():
    raise HTTPException(503, {"code": "gym_equipment_unavailable",
                             "message": "No pudimos leer el equipamiento. Vuelve a consultarlo."})


def _decode(raw):
    if raw is None:
        return {"configured": False, "revision": 0, "machine_ids": []}
    try:
        value = json.loads(raw)
        known = {row["id"] for row in _catalog()}
        if (not isinstance(value, dict) or set(value) != {"format_version", "revision", "machine_ids"}
                or type(value["format_version"]) is not int or value["format_version"] != 1
                or type(value["revision"]) is not int or not 1 <= value["revision"] <= MAX_REVISION
                or not isinstance(value["machine_ids"], list) or len(value["machine_ids"]) > 128
                or any(type(item) is not str or item not in known for item in value["machine_ids"])
                or len(set(value["machine_ids"])) != len(value["machine_ids"])):
            _unavailable()
        return {"configured": True, "revision": value["revision"], "machine_ids": sorted(value["machine_ids"])}
    except (TypeError, ValueError):
        _unavailable()


def read_inventory(db, gym_id):
    """Read only the authorised gym selected by the caller; never bootstrap."""
    raw = db.scalar(select(GymSettings.training_equipment_json).where(GymSettings.gym_id == gym_id))
    return _decode(raw)


def _response(state, actor):
    from core.gym_equipment_catalog import get_effective_equipment
    return {"version": 1, "scope": "gym", **state,
            "machines": _catalog(), "base_equipment": list(BASE_EQUIPMENT),
            "effective_equipment": list(get_effective_equipment(state["machine_ids"])), "can_edit": _owner(actor)}


def inventory_for_subject(db, principal, context):
    actor = _authorized_actor(db, principal, context)
    if context != "gym":
        raise HTTPException(403, {"code": "routine_context_forbidden", "message": "Abre el equipamiento desde tu gimnasio."})
    return _response(read_inventory(db, actor.team_gym_id or actor.id), actor)


def _conflict():
    raise HTTPException(409, {"code": "gym_equipment_conflict",
                             "message": "El equipamiento cambió. Recarga la lista antes de guardar."})


def save_inventory_for_subject(db, principal, context, machine_ids, expected_revision):
    """Serialise owner saves, preserve unrelated settings, commit before success."""
    try:
        actor = _authorized_actor(db, principal, context)
        if context != "gym" or not _owner(actor):
            raise HTTPException(403, {"code": "gym_equipment_owner_required",
                                     "message": "Sólo el dueño puede guardar el equipamiento del gimnasio."})
        # Existing owner row serialises first-save races as well as updates on
        # PostgreSQL. CAS remains authority on SQLite and on every update.
        db.execute(select(Usuario.id).where(Usuario.id == actor.id).with_for_update()).one()
        actor = _authorized_actor(db, principal, context)
        if not _owner(actor):
            raise HTTPException(403, {"code": "gym_equipment_owner_required",
                                     "message": "Sólo el dueño puede guardar el equipamiento del gimnasio."})
        known = {row["id"] for row in _catalog()}
        if (type(expected_revision) is not int or not 0 <= expected_revision < MAX_REVISION
                or not isinstance(machine_ids, list) or len(machine_ids) > 128
                or any(type(item) is not str or item not in known for item in machine_ids)
                or len(set(machine_ids)) != len(machine_ids)):
            raise HTTPException(422, {"code": "gym_equipment_invalid", "message": "Revisa las máquinas seleccionadas."})
        row = db.execute(select(GymSettings.id, GymSettings.training_equipment_json)
                         .where(GymSettings.gym_id == actor.id).with_for_update()).first()
        raw = row.training_equipment_json if row else None
        current = _decode(raw)
        if current["revision"] != expected_revision:
            _conflict()
        state = {"configured": True, "revision": expected_revision + 1, "machine_ids": sorted(machine_ids)}
        payload = json.dumps({"format_version": 1, "revision": state["revision"],
                              "machine_ids": state["machine_ids"]}, sort_keys=True, separators=(",", ":"))
        if row is None:
            db.add(GymSettings(gym_id=actor.id, training_equipment_json=payload))
            db.flush()
        else:
            previous = GymSettings.training_equipment_json.is_(None) if raw is None else GymSettings.training_equipment_json == raw
            changed = db.execute(update(GymSettings).where(GymSettings.id == row.id,
                                 GymSettings.gym_id == actor.id, previous).values(training_equipment_json=payload))
            if changed.rowcount != 1:
                _conflict()
        db.commit()
        return _response(state, actor)
    except IntegrityError:
        db.rollback()
        _conflict()
    except Exception:
        db.rollback()
        raise
