"""Atomic individual generation reservations shared by every server worker."""
from datetime import datetime, timezone
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from web.database.models import Cliente, GenerationReservation, Usuario, UserSubscription, PlanGenerado
from web.services.billing_integrity import current_quota_period, get_individual_subscription


def reconciliation_required() -> HTTPException:
    return HTTPException(503, {"code": "generation_reconciliation_required",
        "message": "No fue posible confirmar la generacion. Consulta el historial antes de reintentar."})


def read_individual_plan_result(db: Session, user_id: str, plan_id: int | None) -> PlanGenerado | None:
    """Read only a live Plan and client owned by the same personal subject.

    Historical single-column FKs do not establish tenant consistency. Inactive
    clients retain readable history; soft-deleted or mixed associations do not.
    """
    return db.query(PlanGenerado).join(Cliente, Cliente.id_cliente == PlanGenerado.id_cliente).filter(
        PlanGenerado.id == plan_id, PlanGenerado.gym_id == user_id,
        Cliente.gym_id == user_id, PlanGenerado.deleted_at.is_(None), Cliente.deleted_at.is_(None),
    ).populate_existing().first()


def _lock_account(db: Session, user_id: str) -> None:
    if db.query(Usuario).filter_by(id=user_id).update(
            {Usuario.id: Usuario.id}, synchronize_session=False) != 1:
        raise HTTPException(403, "Cuenta no disponible")


def require_publishable_generation(db: Session, user_id: str, reservation_id: str) -> GenerationReservation:
    """Hold the account lock until Plan, object readiness and ledger commit.

    The repository repeats this check so a direct caller cannot attach a Plan
    after compensation, or to a legacy/foreign/completed reservation.
    """
    _lock_account(db, user_id)
    reservation = db.query(GenerationReservation).filter_by(
        id=reservation_id, user_id=user_id).populate_existing().one_or_none()
    if (reservation is None or reservation.publication_protocol != 1
            or reservation.status != "reserved" or reservation.plan_id is not None
            or reservation.persisted_at is not None):
        raise ValueError("Individual publication reservation is unavailable")
    return reservation


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
    _lock_account(db, user_id)
    existing = db.query(GenerationReservation).filter_by(user_id=user_id, request_key=key).populate_existing().first()
    if existing:
        if existing.status == "completed":
            db.commit()
            return existing
        raise HTTPException(409, {"code": "generation_in_progress" if existing.status == "reserved" else "generation_failed",
                                  "message": "La solicitud ya fue recibida. Consulta su estado antes de iniciar otra."})
    sub = get_individual_subscription(db, user_id)
    db.flush()
    # The locked projection defines the period being debited. Reading the clock
    # again could label an October debit as November and refund another request.
    period = sub.mes_actual
    # Conditional increment is the last enforcement barrier even if a caller
    # bypasses the earlier count or two processes begin at the last credit.
    accepted = db.query(UserSubscription).filter(
        UserSubscription.user_id == user_id,
        UserSubscription.mes_actual == period,
        UserSubscription.planes_usados_mes < UserSubscription.max_planes_mes,
    ).update({UserSubscription.planes_usados_mes: UserSubscription.planes_usados_mes + 1}, synchronize_session=False)
    if accepted != 1:
        db.rollback()
        raise HTTPException(403, {"code": "monthly_plan_limit", "message": "Has utilizado los planes disponibles de este mes.",
                                  "limit": sub.max_planes_mes})
    reservation = GenerationReservation(user_id=user_id, request_key=key, period=period,
        status="reserved", publication_protocol=1)
    db.add(reservation)
    db.commit()
    return reservation


def finish_generation(db: Session, reservation_id: str, user_id: str, plan_id: int | None,
                      *, success: bool) -> None:
    """Verify atomic publication or compensate a proven unpublished request.

    A Plan ID passed by a caller never establishes publication. Consumption
    survives SET NULL on its FK; ambiguous legacy requests require review.
    """
    _lock_account(db, user_id)
    reservation = db.query(GenerationReservation).filter_by(
        id=reservation_id, user_id=user_id).populate_existing().one_or_none()
    if reservation is None:
        raise reconciliation_required()
    if success:
        if (reservation.status != "completed" or plan_id is None or reservation.plan_id != plan_id
                or (reservation.publication_protocol == 1 and reservation.persisted_at is None)
                or read_individual_plan_result(db, user_id, plan_id) is None):
            raise reconciliation_required()
        db.commit()
        return
    else:
        if reservation.status == "completed" or reservation.persisted_at is not None:
            db.commit()
            return
        if reservation.status == "released":
            db.commit()
            return
        if reservation.publication_protocol != 1 or reservation.plan_id is not None:
            raise reconciliation_required()
        db.query(UserSubscription).filter(UserSubscription.user_id == user_id,
            UserSubscription.mes_actual == reservation.period,
            UserSubscription.planes_usados_mes > 0).update(
                {UserSubscription.planes_usados_mes: UserSubscription.planes_usados_mes - 1}, synchronize_session=False)
        reservation.status = "released"
    reservation.updated_at = datetime.now(timezone.utc)
    db.commit()


def compensate_individual_generation_failure(db: Session, reservation_id: str, user_id: str) -> None:
    """Read durable state after a protected rollback, never assume a refund."""
    try:
        db.rollback()
        finish_generation(db, reservation_id, user_id, None, success=False)
    except Exception as error:
        logging.getLogger(__name__).error("Individual compensation failed class=%s", type(error).__name__)
        raise reconciliation_required() from None
