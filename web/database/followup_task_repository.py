"""Bounded projected reads; every resource query repeats gym/client ownership."""
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import aliased

from web.database.models import Cliente, PlanGenerado, FollowupTask as Task, FollowupTaskEvent as Event


def eligible(gym):
    return Cliente.gym_id == gym, Cliente.activo.is_(True), Cliente.deleted_at.is_(None)


def sources(db, gym, client_ids):
    if not client_ids:
        return {}
    activity = select(PlanGenerado.id_cliente,
        func.count(PlanGenerado.id).label("plan_count"), func.max(PlanGenerado.fecha_generacion).label("last_plan_at"))\
        .where(PlanGenerado.gym_id == gym, PlanGenerado.deleted_at.is_(None), PlanGenerado.id_cliente.in_(client_ids))\
        .group_by(PlanGenerado.id_cliente).subquery()
    rows = db.execute(select(Cliente.id_cliente, Cliente.nombre,
        func.coalesce(activity.c.plan_count, 0).label("plan_count"), activity.c.last_plan_at,
        Cliente.fecha_fin_suscripcion.label("membership_end"))
        .outerjoin(activity, activity.c.id_cliente == Cliente.id_cliente)
        .where(*eligible(gym), Cliente.id_cliente.in_(client_ids))).all()
    return {row.id_cliente: row for row in rows}


def task_query(gym, actor, manager):
    query = select(Task).join(Cliente, and_(Cliente.id_cliente == Task.client_id, Cliente.gym_id == Task.gym_id))\
        .where(Task.gym_id == gym, *eligible(gym))
    return query if manager else query.where(Task.assignee_id == actor)


def task(db, gym, actor, manager, identifier, *, lock=False):
    query = task_query(gym, actor, manager).where(Task.id == identifier).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update(nowait=True, of=Task)
    return db.scalar(query)


def task_page(db, gym, actor, manager, status, limit, cursor):
    query = task_query(gym, actor, manager).where(Task.status == status)
    if cursor:
        at, identifier = cursor
        query = query.where(or_(Task.created_at < at, and_(Task.created_at == at, Task.id < identifier)))
    return db.scalars(query.order_by(Task.created_at.desc(), Task.id.desc()).limit(limit+1)).all()


def event_page(db, gym, task_id, after_version, limit):
    return db.scalars(select(Event).where(Event.gym_id == gym, Event.task_id == task_id, Event.version > after_version)
        .order_by(Event.version).limit(limit+1)).all()


def counters(db, gym, lower, upper):
    current = task_query(gym, None, True).with_only_columns(
        func.count(Task.id).label("open"), func.count(case((Task.assignee_id.is_(None), 1))).label("unassigned"))\
        .where(Task.status == "open")
    previous = aliased(Event)
    events = select(
        func.count(case((Event.kind == "created", 1))).label("created"),
        func.count(case((Event.kind == "completed", 1))).label("completed_declarations"),
        func.count(case((Event.kind == "cancelled", 1))).label("cancelled"),
        func.count(case((and_(Event.kind == "updated", Event.assignee_id.is_distinct_from(previous.assignee_id)), 1))).label("assignment_changes"))\
        .select_from(Event).join(Task, and_(Task.id == Event.task_id, Task.gym_id == Event.gym_id))\
        .join(Cliente, and_(Cliente.id_cliente == Task.client_id, Cliente.gym_id == Task.gym_id))\
        .outerjoin(previous, and_(previous.gym_id == Event.gym_id, previous.task_id == Event.task_id, previous.version == Event.version-1))\
        .where(Event.gym_id == gym, Task.gym_id == gym, *eligible(gym), Event.updated_at >= lower, Event.updated_at < upper)
    return dict(db.execute(current).mappings().one()), dict(db.execute(events).mappings().one())
