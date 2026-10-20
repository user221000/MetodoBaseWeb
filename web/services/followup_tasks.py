"""Purpose-specific task transactions. No outbound action or implicit staffing.

Rows and authority stay inside the owned Session. Responses are bounded inert
values captured before commit, returned only after ACK and route cleanup.
"""
import logging
import sqlite3
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import Integer, cast, or_, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import load_only

from web.database import followup_task_repository as repo
from web.database.followup_schema_v1 import SNAPSHOT
from web.database.models import Cliente, FollowupTask as Task, FollowupTaskEvent as Event, Usuario, UserRole
from web.database.tenant_context import bind_verified_subject
from web.services import followup_domain as domain
from web.services.permissions import has_permission

logger = logging.getLogger(__name__)


def fail(status, code):
    raise HTTPException(status, {"code": code, "message": {
        "followup_unconfirmed": "No pudimos confirmar el resultado. Consulta el estado autorizado antes de continuar.",
        "followup_version_conflict": "La tarea cambió. Consulta su estado antes de confirmar otra acción.",
        "followup_busy": "El contexto está cambiando. Vuelve a consultar antes de continuar.",
    }.get(code, "No fue posible completar esta operación de seguimiento.")})


def bounded(value, limit=131072):
    if len(domain.canonical(value)) > limit:
        fail(503, "followup_unavailable")
    return value


def rollback(db):
    try:
        db.rollback()
    except Exception as error:
        logger.error("Follow-up rollback unconfirmed class=%s", type(error).__name__)
        fail(503, "followup_unconfirmed")


def close_owned_session(db):
    try:
        db.close()
    except Exception as error:
        logger.error("Follow-up close unconfirmed class=%s", type(error).__name__)
        try:
            db.invalidate()
        except Exception as invalidation:
            logger.error("Follow-up invalidate unconfirmed class=%s", type(invalidation).__name__)
        raise RuntimeError("Follow-up owned-session cleanup unconfirmed") from None


def _live(user):
    return (user is not None and user.activo and user.deleted_at is None and user.invitation_token is None
        and type(user.session_version) is int and 0 <= user.session_version <= domain.MAX_VERSION)


def _gym(user):
    return _live(user) and user.tipo == "gym" and user.role == UserRole.OWNER and user.team_gym_id is None


def _eligible(user, gym):
    return _live(user) and ((_gym(user) and user.id == gym) or
        (user.team_gym_id == gym and user.role in (UserRole.ADMIN, UserRole.NUTRIOLOGO)))


def authority(db, expected, *, lock=False, extra=()):
    """Lock every account in total NOWAIT order before resources; no late User."""
    if db.in_nested_transaction():
        fail(409, "followup_busy")
    if db.get_bind().dialect.name == "sqlite":
        connection = db.connection()
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE" if lock else "BEGIN")
    hint = db.get(Usuario, expected["id"], populate_existing=True)
    if not _live(hint):
        fail(401, "followup_identity_unavailable")
    gym = hint.team_gym_id if hint.team_gym_id else hint.id
    ids = sorted({hint.id, gym, *(identifier for identifier in extra if identifier)})
    # Locks require eligibility only. In particular, a historical assignee
    # outside this gym must never hydrate its current name/contact/credential.
    query = select(Usuario).options(load_only(
        Usuario.id, Usuario.activo, Usuario.deleted_at, Usuario.invitation_token,
        Usuario.session_version, Usuario.tipo, Usuario.role, Usuario.team_gym_id,
        raiseload=True,
    )).where(Usuario.id.in_(ids)).order_by(Usuario.id).execution_options(populate_existing=True)
    if db.get_bind().dialect.name == "postgresql":
        query = query.with_for_update(nowait=True, read=not lock)
    users = {u.id: u for u in db.scalars(query).all()}
    user, parent = users.get(expected["id"]), users.get(gym)
    if (not _live(user) or not _gym(parent) or (user.team_gym_id or user.id) != gym
            or not _eligible(user, gym)):
        fail(403, "followup_forbidden")
    role = expected.get("role")
    role = getattr(role, "value", role)
    version = expected.get("session_version", expected.get("sv", 0))
    if (type(version) is not int or version != user.session_version
            or expected.get("team_gym_id") != user.team_gym_id or role != user.role.value
            or expected.get("tipo") != user.tipo):
        fail(401, "followup_identity_unavailable")
    manager = has_permission(user, "manage", "followup_task", gym)
    if not manager and not has_permission(user, "read", "followup_assigned", gym):
        fail(403, "followup_forbidden")
    bind_verified_subject(db, gym)
    return user, gym, manager, users


def _require_manager(manager):
    if not manager:
        fail(403, "followup_forbidden")


def _identities(db, ids, gym):
    # An unavailable historical ID must NOT retrieve its new-context name,
    # email or contacts. Filter current same-gym eligibility in SQL first.
    return {u.id: u for u in db.scalars(select(Usuario).where(Usuario.id.in_(set(ids)),
        Usuario.activo.is_(True), Usuario.deleted_at.is_(None), Usuario.invitation_token.is_(None),
        Usuario.session_version.between(0, domain.MAX_VERSION), cast(Usuario.session_version, Integer) == Usuario.session_version,
        or_((Usuario.id == gym) & (Usuario.tipo == "gym") & (Usuario.role == UserRole.OWNER) & Usuario.team_gym_id.is_(None),
            (Usuario.team_gym_id == gym) & Usuario.role.in_((UserRole.ADMIN, UserRole.NUTRIOLOGO))))).all()} if ids else {}


def _person(users, identifier, gym):
    if identifier is None:
        return None
    user = users.get(identifier)
    eligible = bool(_eligible(user, gym))
    return {"id": identifier, "display_name": user.nombre if eligible else None, "eligible": eligible}


def _task_dto(task, source, users, actor, manager, now):
    responsible = _person(users, task.assignee_id, task.gym_id)
    active = task.status == "open"
    return {"id": task.id, "version": task.version, "client": {"id": task.client_id, "display_name": source.nombre},
        "cause": task.cause, "priority": task.priority_at_creation,
        "source": {"observed_at": domain.iso(task.observed_at), "plan_count": task.plan_count,
            "last_plan_at": domain.iso(task.last_plan_at), "membership_end": task.membership_end.isoformat() if task.membership_end else None},
        "cause_currently_present": any(c["cause"] == task.cause for c in domain.causes(source, task.gym_id, now)),
        "next_step": task.next_step, "responsible": responsible, "status": task.status,
        "created_at": domain.iso(task.created_at), "updated_at": domain.iso(task.updated_at),
        "outcome": task.outcome, "cancel_reason": task.cancel_reason,
        "capabilities": {"edit": manager and active, "cancel": manager and active, "history": True,
            "complete": bool(active and responsible and responsible["eligible"] and (manager or task.assignee_id == actor))}}


def _dtos(db, rows, gym, actor, manager, now):
    sources = repo.sources(db, gym, [r.client_id for r in rows])
    users = _identities(db, [r.assignee_id for r in rows if r.assignee_id], gym)
    # Hidden/deleted sources are never converted into a partial success result.
    if len(sources) != len({r.client_id for r in rows}):
        fail(409, "followup_busy")
    return [_task_dto(row, sources[row.client_id], users, actor, manager, now) for row in rows]


def context(db, expected, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    from zoneinfo import ZoneInfo
    return {"scope": "gym" if manager else "assigned", "timezone": domain.REPORT_TIMEZONE,
        "today": now.astimezone(ZoneInfo(domain.REPORT_TIMEZONE)).date().isoformat(), "as_of": domain.iso(now),
        "capabilities": {"read_tasks": True, "create_task": manager, "manage_tasks": manager,
            "read_assignees": manager, "read_metrics": manager, "complete_assigned": not manager},
        "limits": {"tasks": 100, "history": 50, "assignees": 50, "report_days": 62}}


def candidates(db, expected, client_id, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    _require_manager(manager)
    source = repo.sources(db, gym, [client_id]).get(client_id)
    if source is None:
        fail(404, "followup_task_unavailable")
    existing = db.scalars(repo.task_query(gym, user.id, True).where(Task.client_id == client_id, Task.status == "open")).all()
    summaries = {row.cause: value for row, value in zip(existing, _dtos(db, existing, gym, user.id, True, now))}
    values = [{**value, "next_steps": ["review_client_record", "review_membership_date" if value["cause"] == "membership_date_passed" else "review_plan_history"],
        "open_task": summaries.get(value["cause"])} for value in domain.causes(source, gym, now)]
    return bounded({"client": {"id": source.id_cliente, "display_name": source.nombre}, "observed_at": domain.iso(now), "candidates": values})


def list_tasks(db, expected, status, limit, after, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    try:
        cursor = domain.cursor_decode(after) if after is not None else None
    except (ValueError, TypeError, UnicodeError, OverflowError):
        fail(422, "followup_invalid_input")
    rows = repo.task_page(db, gym, user.id, manager, status, limit, cursor)
    page = rows[:limit]
    return bounded({"items": _dtos(db, page, gym, user.id, manager, now), "limit": limit,
        "next_after": domain.cursor_encode(page[-1].created_at, page[-1].id) if len(rows) > limit else None,
        "scope": "gym" if manager else "assigned", "as_of": domain.iso(now)})


def read_task(db, expected, identifier, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    row = repo.task(db, gym, user.id, manager, identifier)
    if row is None:
        fail(404, "followup_task_unavailable")
    return bounded(_dtos(db, [row], gym, user.id, manager, now)[0])


def history(db, expected, identifier, limit, after_version, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    task = repo.task(db, gym, user.id, manager, identifier)
    if task is None:
        fail(404, "followup_task_unavailable")
    rows = repo.event_page(db, gym, identifier, after_version, limit)
    users = _identities(db, [identity for r in rows for identity in (r.actor_id, r.assignee_id) if identity], gym)
    page = rows[:limit]
    items = [{"id": r.id, "version": r.version, "kind": r.kind, "occurred_at": domain.iso(r.updated_at),
        "actor": _person(users, r.actor_id, gym), "next_step": r.next_step, "responsible": _person(users, r.assignee_id, gym),
        "status": r.status, "outcome": r.outcome, "cancel_reason": r.cancel_reason} for r in page]
    return bounded({"items": items, "limit": limit, "next_after": page[-1].version if len(rows) > limit else None,
        "scope": "gym" if manager else "assigned", "as_of": domain.iso(now)})


def assignees(db, expected, limit, after, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    _require_manager(manager)
    query = select(Usuario).where(Usuario.activo.is_(True), Usuario.deleted_at.is_(None), Usuario.invitation_token.is_(None),
        Usuario.session_version.between(0, domain.MAX_VERSION), cast(Usuario.session_version, Integer) == Usuario.session_version,
        or_((Usuario.id == gym) & (Usuario.tipo == "gym") & (Usuario.role == UserRole.OWNER) & Usuario.team_gym_id.is_(None),
            (Usuario.team_gym_id == gym) & Usuario.role.in_((UserRole.ADMIN, UserRole.NUTRIOLOGO))))
    if after is not None:
        query = query.where(Usuario.id > after)
    rows = db.scalars(query.order_by(Usuario.id).limit(limit+1)).all()
    return bounded({"items": [{"id": r.id, "display_name": r.nombre, "role": r.role.value, "eligible": True} for r in rows[:limit]],
        "limit": limit, "next_after": rows[limit-1].id if len(rows) > limit else None, "scope": "gym", "as_of": domain.iso(now)})


def metrics(db, expected, start, through, *, now=None):
    now = domain.instant(now)
    user, gym, manager, _ = authority(db, expected)
    _require_manager(manager)
    try:
        start, through, lower, upper = domain.period(start, through, now)
    except (ValueError, TypeError):
        fail(422, "followup_invalid_input")
    state, events = repo.counters(db, gym, lower, upper)
    return bounded({"as_of": domain.iso(now), "timezone": domain.REPORT_TIMEZONE, "scope": "gym",
        "range": {"from": start.isoformat(), "through": through.isoformat(), "inclusive": True},
        "state_now": state, "event_period": events, "sources": {"state": "followup_tasks", "events": "followup_task_events"},
        "coverage": "current_active_clients_only", "meaning": "actor_declarations_not_contact_delivery_payment_or_retention"}, 16384)


def dashboard(db, expected, limit):
    """Preserve original fact metrics; add bounded evidence/tasks without N+1."""
    from web.services.followup_service import get_followup
    user, gym, manager, _ = authority(db, expected)
    _require_manager(manager)
    value = get_followup(db, gym, limit)
    now = domain.instant(datetime.fromisoformat(value["as_of"]))
    ids = [item["id_cliente"] for item in value["items"]]
    sources = repo.sources(db, gym, ids)
    rows = db.scalars(repo.task_query(gym, user.id, True).where(Task.client_id.in_(ids), Task.status == "open")).all() if ids else []
    summaries = {}
    for row, dto in zip(rows, _dtos(db, rows, gym, user.id, True, now)):
        summaries.setdefault(row.client_id, []).append({key: dto[key] for key in
            ("id", "version", "cause", "status", "next_step", "responsible", "capabilities")})
    for item in value["items"]:
        source = sources.get(item["id_cliente"])
        if source is None:
            fail(409, "followup_busy")
        item["cause_candidates"] = [{**c, "next_steps": ["review_client_record",
            "review_membership_date" if c["cause"] == "membership_date_passed" else "review_plan_history"]}
            for c in domain.causes(source, gym, now)]
        item["per_cause_tasks"] = sorted(summaries.get(item["id_cliente"], []), key=lambda t: t["cause"])
    value["responsibility"] = "per_cause_tasks"
    value["task_coverage"] = "current_open_tasks_by_cause"
    return bounded(value, 524288)


def _operation(event, *, replay):
    return {"id": event.id, "request_key": event.request_key, "replayed": replay,
        "applied_version": event.version, "occurred_at": domain.iso(event.updated_at)}


def mutate(db, expected, kind, command, request_key, path, *, identifier=None, now=None):
    now = domain.instant(now)
    # Hints are never authority, and no User lock is taken after resources.
    actor_hint = db.get(Usuario, expected["id"], populate_existing=True)
    if not _live(actor_hint):
        fail(401, "followup_identity_unavailable")
    gym_hint = actor_hint.team_gym_id or actor_hint.id
    bind_verified_subject(db, gym_hint)
    manager_hint = has_permission(actor_hint, "manage", "followup_task", gym_hint)
    # Restrict discovery before deriving any other account's lock. Hints only
    # narrow access; authority still revalidates the locked persistent context.
    hint = repo.task(db, gym_hint, actor_hint.id, manager_hint, identifier) if identifier else None
    old_assignee = hint.assignee_id if hint else None
    extra = (old_assignee, getattr(command, "assignee_id", None) if manager_hint else None)
    user, gym, manager, users = authority(db, expected, lock=True, extra=extra)
    if kind != "completed":
        _require_manager(manager)
    if identifier and not manager and (hint is None or hint.assignee_id != user.id):
        fail(404, "followup_task_unavailable")
    digest = domain.request_hash(user.id, gym, "PATCH" if kind == "updated" else "POST", path, command)
    replay = db.scalar(select(Event).where(Event.gym_id == gym, Event.actor_id == user.id, Event.request_key == request_key))
    if replay is not None:
        if replay.request_hash != digest:
            fail(409, "followup_key_reused")
        if repo.task(db, gym, user.id, manager, replay.task_id) is None:
            fail(404, "followup_task_unavailable")
        return {"ack": True, "operation": _operation(replay, replay=True), "task": None, "read_required": True}
    client_id = command.client_id if kind == "created" else hint.client_id if hint and hint.gym_id == gym else None
    client_query = select(Cliente).where(Cliente.id_cliente == client_id, *repo.eligible(gym)).execution_options(populate_existing=True)
    if db.get_bind().dialect.name == "postgresql":
        client_query = client_query.with_for_update(nowait=True, read=True)
    if db.scalar(client_query) is None:
        fail(404, "followup_task_unavailable")
    source = repo.sources(db, gym, [client_id]).get(client_id)
    task = repo.task(db, gym, user.id, manager, identifier, lock=True) if identifier else None
    if kind == "created":
        selected = next((c for c in domain.causes(source, gym, now) if c["cause"] == command.cause), None)
        if selected is None or selected["cause_evidence_hash"] != command.cause_evidence_hash:
            fail(409, "followup_cause_changed")
        if db.scalar(select(Task.id).where(Task.gym_id == gym, Task.client_id == client_id, Task.cause == command.cause, Task.status == "open")):
            fail(409, "followup_open_task_exists")
        values = {"gym_id": gym, "client_id": client_id, "cause": command.cause,
            "cause_evidence_hash": selected["cause_evidence_hash"], "observed_at": now,
            "plan_count": source.plan_count, "last_plan_at": source.last_plan_at, "membership_end": source.membership_end,
            "priority_at_creation": selected["priority"], "status": "open", "version": 1,
            "next_step": command.next_step, "assignee_id": command.assignee_id, "created_by": user.id, "created_at": now,
            "completed_by": None, "completed_at": None, "outcome": None, "cancelled_by": None, "cancelled_at": None, "cancel_reason": None}
        identifier = str(uuid.uuid4())
    else:
        if task is None:
            fail(404, "followup_task_unavailable")
        if task.assignee_id != old_assignee:
            fail(409, "followup_busy")
        if task.version != command.expected_version or task.status != "open":
            fail(409, "followup_version_conflict")
        if task.version >= domain.MAX_VERSION:
            fail(409, "followup_version_exhausted")
        values = {name: getattr(task, name) for name in SNAPSHOT}
        values["version"] += 1
        if kind == "updated":
            if task.next_step == command.next_step and task.assignee_id == command.assignee_id:
                fail(422, "followup_invalid_input")
            values.update(next_step=command.next_step, assignee_id=command.assignee_id)
        elif kind == "completed":
            if not manager and not has_permission(user, "update", "followup_assigned", gym):
                fail(403, "followup_forbidden")
            if not task.assignee_id or not _eligible(users.get(task.assignee_id), gym):
                fail(409, "followup_assignee_unavailable")
            values.update(status="completed", completed_by=user.id, completed_at=now, outcome=command.outcome)
        else:
            values.update(status="cancelled", cancelled_by=user.id, cancelled_at=now, cancel_reason=command.reason)
    if not domain.allowed_step(values["cause"], values["next_step"]):
        fail(422, "followup_invalid_input")
    if kind in ("created", "updated") and values["assignee_id"] and not _eligible(users.get(values["assignee_id"]), gym):
        fail(409, "followup_assignee_unavailable")
    values["updated_at"] = now
    event = Event(id=str(uuid.uuid4()), task_id=identifier, actor_id=user.id, actor_role=user.role.value,
        kind=kind, request_key=request_key, request_hash=digest, **values)
    db.add(event)
    try:
        db.flush()
        db.expire_all()
        task = repo.task(db, gym, user.id, manager, identifier)
        result = bounded({"ack": True, "operation": _operation(event, replay=False),
            "task": _dtos(db, [task], gym, user.id, manager, now)[0]})
    except IntegrityError as error:
        rollback(db)
        conflict = _constraint_conflict(error)
        if conflict is not None:
            fail(409, conflict)
        logger.error("Follow-up write unconfirmed class=%s", type(error.orig).__name__)
        fail(503, "followup_unconfirmed")
    try:
        db.commit()
    except Exception as error:
        logger.error("Follow-up commit unconfirmed class=%s", type(error).__name__)
        rollback(db)
        fail(503, "followup_unconfirmed")
    return result


def _constraint_conflict(error):
    """Only typed driver diagnostics for the two closed constraint conflicts."""
    original = error.orig
    code = getattr(original, "pgcode", None)
    diagnostics = getattr(original, "diag", None)
    if code == "23505" and getattr(diagnostics, "constraint_name", None) == "uq_followup_open_cause":
        return "followup_open_task_exists"
    source_messages = {"Follow-up source changed", "Follow-up cause absent"}
    if code == "23514" and getattr(diagnostics, "message_primary", None) in source_messages:
        return "followup_cause_changed"
    if isinstance(original, sqlite3.IntegrityError):
        code = getattr(original, "sqlite_errorcode", None)
        if code == sqlite3.SQLITE_CONSTRAINT_UNIQUE and str(original) == (
                "UNIQUE constraint failed: followup_tasks.gym_id, followup_tasks.client_id, followup_tasks.cause"):
            return "followup_open_task_exists"
        if code == sqlite3.SQLITE_CONSTRAINT_TRIGGER and str(original) in source_messages:
            return "followup_cause_changed"
    return None


def classify_error(error):
    if isinstance(error, DBAPIError):
        original = error.orig
        sqlite_code = getattr(original, "sqlite_errorcode", None)
        sqlite_busy = (isinstance(original, sqlite3.Error) and type(sqlite_code) is int
            and sqlite_code & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))
        if getattr(original, "pgcode", None) == "55P03" or sqlite_busy:
            fail(409, "followup_busy")
    raise error
