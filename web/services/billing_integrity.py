"""Persist purchase identity and project verified individual entitlements.

This module owns SQLAlchemy transactions only where explicitly stated. Provider
adapters validate payment evidence before calling the subscription service.
"""
from datetime import datetime, timezone
from decimal import Decimal
import logging
import uuid
from zoneinfo import ZoneInfo
from core.plan_catalog import get_individual_plan_catalog

from sqlalchemy.orm import Session

from web.constants import PLANES_LICENCIA
from web.database.models import PurchaseIntent, Subscription, UserSubscription, Usuario


def public_failure(operation: str, error: Exception, message: str) -> dict:
    """Log a bounded error class/reference without provider/SQL parameters."""
    reference = uuid.uuid4().hex[:16]
    logging.getLogger(__name__).error("billing_failure operation=%s class=%s reference=%s",
                                     operation, type(error).__name__, reference)
    return {"code": "payment_service_unavailable", "message": message, "request_id": reference}


def current_quota_period(now: datetime | None = None) -> str:
    """Return the calendar quota month in the product's Mexico City timezone."""
    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/Mexico_City")).strftime("%Y-%m")


def price_in_cents(plan: str) -> int:
    """Resolve an existing catalog price without silently substituting a plan."""
    if plan not in PLANES_LICENCIA or not PLANES_LICENCIA[plan].get("precio_mxn"):
        raise ValueError("Plan de pago inválido")
    return int(Decimal(str(PLANES_LICENCIA[plan]["precio_mxn"])) * 100)


def prepare_purchase(db: Session, subject_id: str, provider: str, operation: str,
                     plan: str, request_key: str | None = None) -> PurchaseIntent:
    """Commit a recoverable purchase identity before any external side effect.

    The caller must have authorized the subject. A supplied key is scoped to
    subject/provider/operation and cannot be reused for a different plan. Legacy
    callers without a key reuse an unfinished purchase of the same operation.
    The account row serializes simultaneous attempts across PostgreSQL workers.
    """
    amount = price_in_cents(plan)
    if request_key is not None and not 1 <= len(request_key) <= 128:
        raise ValueError("Clave de idempotencia inválida")
    # A write lock also works on SQLite, whose SELECT FOR UPDATE is ignored.
    found = db.query(Usuario).filter(Usuario.id == subject_id).update({Usuario.id: Usuario.id})
    if not found:
        raise ValueError("Cuenta no disponible")
    query = db.query(PurchaseIntent).filter_by(subject_id=subject_id, provider=provider,
                                              operation=operation)
    if request_key:
        intent = query.filter_by(request_key=request_key).first()
    else:
        intent = query.filter(PurchaseIntent.status.in_(["pending", "provider_created"]),
                              PurchaseIntent.plan == plan).order_by(PurchaseIntent.created_at.desc()).first()
    if intent:
        if intent.plan != plan or intent.amount_cents != amount:
            raise ValueError("La clave de compra pertenece a otra operación")
    else:
        intent = PurchaseIntent(subject_id=subject_id, provider=provider, operation=operation,
                                request_key=request_key or str(uuid.uuid4()), plan=plan,
                                amount_cents=amount, currency="mxn", status="pending")
        db.add(intent)
    db.commit()
    return intent


def sync_individual_entitlement(db: Session, sub: Subscription) -> None:
    """Project canonical provider status to the individual quota record.

    Caller commits. No historical records without a canonical subscription are
    rewritten. Paid access has no invented grace period: only active paid Pro
    grants five plans; other provider states retain Starter's one-plan limit.
    """
    if sub.plan != "pro_usuario":
        return
    projection = db.query(UserSubscription).filter_by(user_id=sub.gym_id).first()
    if projection is None:
        projection = UserSubscription(user_id=sub.gym_id, mes_actual=current_quota_period(),
                                      planes_usados_mes=0)
        db.add(projection)
    paid = sub.status == "active"
    projection.plan = "pro" if paid else "starter"
    projection.max_planes_mes = get_individual_plan_catalog()[projection.plan]["max_planes_mes"]
    projection.status = "active" if paid else "canceled"
    projection.updated_at = datetime.now(timezone.utc)


def get_individual_subscription(db: Session, user_id: str) -> UserSubscription:
    """Return quota/projection for an authorized individual; caller commits.

    Existing pre-migration rights without provider mapping remain unchanged for
    an explicit reconciliation, rather than silently rewriting customer rights.
    """
    # GET can initialize/reset the projection too. Use the same account lock as
    # reservation and provider updates, so an old GET cannot overwrite a newly
    # consumed credit when the local month changes or create duplicate rows.
    if not db.query(Usuario).filter_by(id=user_id).update({Usuario.id: Usuario.id}):
        raise ValueError("Cuenta no disponible")
    projection = db.query(UserSubscription).filter_by(user_id=user_id).populate_existing().first()
    if projection is None:
        projection = UserSubscription(user_id=user_id, plan="starter", max_planes_mes=get_individual_plan_catalog()["starter"]["max_planes_mes"],
                                      planes_usados_mes=0, mes_actual=current_quota_period(), status="active")
        db.add(projection)
        db.flush()
    canonical = db.query(Subscription).filter_by(gym_id=user_id, plan="pro_usuario").first()
    if canonical is not None:
        end = canonical.current_period_end
        if end is not None:
            end = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
            if end <= datetime.now(timezone.utc) and canonical.status == "active":
                canonical.status = "unpaid"
        sync_individual_entitlement(db, canonical)
    period = current_quota_period()
    if projection.mes_actual != period:
        projection.planes_usados_mes = 0
        projection.mes_actual = period
    return projection
