"""Bounded, projected follow-up reads with explicit double-owner predicates."""
from sqlalchemy import and_, case, func, or_, select

from web.database.models import Cliente, GymGenerationReservation, PlanGenerado, StoredObject


def _eligible(gym_id):
    return (Cliente.gym_id == gym_id, Cliente.activo.is_(True), Cliente.deleted_at.is_(None))


def _plans(gym_id):
    return select(PlanGenerado.id, PlanGenerado.id_cliente, PlanGenerado.fecha_generacion,
                  PlanGenerado.pdf_object_id).join(Cliente, and_(
        Cliente.id_cliente == PlanGenerado.id_cliente, Cliente.gym_id == PlanGenerado.gym_id,
    )).where(PlanGenerado.gym_id == gym_id, PlanGenerado.deleted_at.is_(None), *_eligible(gym_id))


def read_followup(db, gym_id, now, cutoff, limit):
    plans = _plans(gym_id).subquery()
    activity = select(plans.c.id_cliente, func.count(plans.c.id).label('plan_count'),
                      func.max(plans.c.fecha_generacion).label('last_plan_at')).group_by(plans.c.id_cliente).subquery()
    no_plan = activity.c.plan_count.is_(None)
    undated = and_(activity.c.plan_count.is_not(None), activity.c.last_plan_at.is_(None))
    outside_window = activity.c.last_plan_at < cutoff
    # Legacy membership fields are naive; retain their existing UTC comparison
    # convention. They are administrative dates, never payment evidence.
    expired = Cliente.fecha_fin_suscripcion < now.replace(tzinfo=None)
    priority = case((no_plan, 1), (outside_window, 2), (undated, 3), else_=4)
    query = select(Cliente.id_cliente, Cliente.nombre,
        func.coalesce(activity.c.plan_count, 0).label('plan_count'), activity.c.last_plan_at,
        Cliente.fecha_fin_suscripcion.label('membership_end'), priority.label('priority'),
    ).outerjoin(activity, activity.c.id_cliente == Cliente.id_cliente).where(
        *_eligible(gym_id), or_(no_plan, outside_window, undated, expired),
    ).order_by(priority, activity.c.last_plan_at.asc().nullsfirst(), Cliente.id_cliente.asc()).limit(limit + 1)
    rows = db.execute(query).all()
    metrics = db.execute(select(
        func.count(plans.c.id).label('plans_saved'),
        func.count(case((and_(GymGenerationReservation.status == 'completed',
            GymGenerationReservation.persisted_at.is_not(None)), 1))).label('generation_operations_completed'),
        func.count(case((and_(StoredObject.status == 'ready', StoredObject.kind == 'plan_pdf',
            StoredObject.content_type == 'application/pdf'), 1))).label('pdf_metadata_ready'),
    ).select_from(plans).outerjoin(GymGenerationReservation, and_(
        GymGenerationReservation.plan_id == plans.c.id, GymGenerationReservation.gym_id == gym_id,
        GymGenerationReservation.client_id == plans.c.id_cliente,
    )).outerjoin(StoredObject, and_(StoredObject.id == plans.c.pdf_object_id, StoredObject.gym_id == gym_id))
        .where(plans.c.fecha_generacion >= cutoff, plans.c.fecha_generacion <= now)).mappings().one()
    return rows[:limit], len(rows) > limit, dict(metrics)
