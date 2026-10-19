"""Atomic individual generation reservations shared by every server worker."""
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from web.database.models import GenerationReservation, Usuario, UserSubscription, PlanGenerado
from web.services.billing_integrity import current_quota_period, get_individual_subscription


def reserve_generation(db: Session, user_id: str, request_key: str | None) -> GenerationReservation:
    """Commit one quota credit before generation, or return its completed result.

    The authenticated individual owns the account. Account-row write locking
    serializes quota reset, check, increment and request-key creation across
    processes. An interrupted reserved request remains visible for reconciliation
    and cannot silently start a second generation.
    """
    key = request_key or str(uuid.uuid4())
    if not 1 <= len(key) <= 128:
        raise HTTPException(400, {"code": "invalid_idempotency_key", "message": "Clave de solicitud inválida"})
    if not db.query(Usuario).filter_by(id=user_id).update({Usuario.id: Usuario.id}):
        raise HTTPException(403, "Cuenta no disponible")
    existing = db.query(GenerationReservation).filter_by(user_id=user_id, request_key=key).first()
    if existing:
        if existing.status == "completed":
            db.commit()
            return existing
        raise HTTPException(409, {"code": "generation_in_progress" if existing.status == "reserved" else "generation_failed",
                                  "message": "La solicitud ya fue recibida. Consulta su estado antes de iniciar otra."})
    sub = get_individual_subscription(db, user_id)
    db.flush()
    # Conditional increment is the last enforcement barrier even if a caller
    # bypasses the earlier count or two processes begin at the last credit.
    accepted = db.query(UserSubscription).filter(
        UserSubscription.user_id == user_id,
        UserSubscription.mes_actual == current_quota_period(),
        UserSubscription.planes_usados_mes < UserSubscription.max_planes_mes,
    ).update({UserSubscription.planes_usados_mes: UserSubscription.planes_usados_mes + 1}, synchronize_session=False)
    if accepted != 1:
        db.rollback()
        raise HTTPException(403, {"code": "monthly_plan_limit", "message": "Has utilizado los planes disponibles de este mes.",
                                  "limit": sub.max_planes_mes})
    reservation = GenerationReservation(user_id=user_id, request_key=key, period=current_quota_period(), status="reserved")
    db.add(reservation)
    db.commit()
    return reservation


def finish_generation(db: Session, reservation_id: str, user_id: str, plan_id: int | None,
                      *, success: bool) -> None:
    """Commit the result or refund the same period's credit exactly once.

    A result must belong to the authorized subject. Failed CPU/PDF/storage work
    returns its credit; an old-period refund never decrements a new month.
    """
    db.query(Usuario).filter_by(id=user_id).update({Usuario.id: Usuario.id})
    reservation = db.query(GenerationReservation).filter_by(id=reservation_id, user_id=user_id).one()
    if reservation.status != "reserved":
        db.commit()
        return
    if success:
        if plan_id is None or not db.query(PlanGenerado.id).filter_by(id=plan_id, gym_id=user_id).first():
            raise ValueError("El resultado de generación no se persistió")
        reservation.status = "completed"
        reservation.plan_id = plan_id
    else:
        db.query(UserSubscription).filter(UserSubscription.user_id == user_id,
            UserSubscription.mes_actual == reservation.period,
            UserSubscription.planes_usados_mes > 0).update(
                {UserSubscription.planes_usados_mes: UserSubscription.planes_usados_mes - 1}, synchronize_session=False)
        reservation.status = "released"
    reservation.updated_at = datetime.now(timezone.utc)
    db.commit()
