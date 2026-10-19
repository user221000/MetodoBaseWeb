"""
web/services/subscription_service.py — Servicio compartido de activación de suscripciones.

Single source of truth para activar, actualizar, y cancelar suscripciones.
Usado por:
  - stripe_service.py (webhooks de Stripe)
  - billing.py (webhooks de MercadoPago)

Evita duplicación de lógica entre proveedores de pago.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from web.constants import PLANES_LICENCIA
from web.database.models import Subscription, CheckoutSession, Payment

logger = logging.getLogger(__name__)


def activate_subscription(
    db: Session,
    gym_id: str,
    plan: str,
    *,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    current_period_start: Optional[datetime] = None,
    current_period_end: Optional[datetime] = None,
    provider: str = "stripe",
) -> Subscription:
    """Activa o actualiza la suscripción de un gym.

    Args:
        db: SQLAlchemy session (caller maneja commit).
        gym_id: ID del gym.
        plan: Plan a activar (standard, gym_comercial, clinica).
        stripe_customer_id: Customer ID de Stripe (opcional para MP).
        stripe_subscription_id: Subscription ID de Stripe (opcional para MP).
        current_period_start: Inicio del período de facturación actual.
        current_period_end: Fin del período de facturación actual.
        provider: "stripe" o "mercadopago".

    Returns:
        Subscription activada/actualizada.
    """
    if plan not in PLANES_LICENCIA:
        raise ValueError("Plan de suscripción inválido")
    info = PLANES_LICENCIA[plan]
    max_clientes = info["max_clientes"] or 999999

    # Use FOR UPDATE to prevent race conditions on concurrent requests
    sub = db.query(Subscription).filter(
        Subscription.gym_id == gym_id
    ).with_for_update().first()

    if sub:
        sub.plan = plan
        sub.status = "active"
        sub.max_clientes = max_clientes
        sub.updated_at = datetime.now(timezone.utc)
        sub.provider = provider
        # Only the provider currently funding access may change its status.
        # StripeCustomer retains the historical customer mapping separately.
        if provider == "mercadopago":
            sub.stripe_customer_id = None
            sub.stripe_subscription_id = None
        elif provider == "stripe":
            sub.provider_payment_id = None
        if stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            sub.stripe_subscription_id = stripe_subscription_id
        if current_period_start:
            sub.current_period_start = current_period_start
        if current_period_end:
            sub.current_period_end = current_period_end
    else:
        sub = Subscription(
            gym_id=gym_id,
            plan=plan,
            status="active",
            max_clientes=max_clientes,
            stripe_customer_id=stripe_customer_id or None,
            stripe_subscription_id=stripe_subscription_id or None,
            provider=provider,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        db.add(sub)

    db.flush()
    from web.services.billing_integrity import sync_individual_entitlement
    sync_individual_entitlement(db, sub)
    logger.info(
        "Subscription activated: gym=%s plan=%s provider=%s",
        gym_id, plan, provider,
    )
    return sub


def update_subscription_status(db: Session, sub: Subscription, status: str) -> None:
    """Update canonical/provider status and its B2C projection; caller commits.

    Provider adapters must authenticate the snapshot and resolve its subject.
    Unknown states fail closed instead of becoming an active paid entitlement.
    """
    accepted = {"active", "canceled", "past_due", "trialing", "unpaid", "incomplete",
                "incomplete_expired", "paused"}
    if status not in accepted:
        raise ValueError("Estado de suscripción no soportado")
    sub.status = status
    sub.updated_at = datetime.now(timezone.utc)
    from web.services.billing_integrity import sync_individual_entitlement
    sync_individual_entitlement(db, sub)
    db.flush()


def complete_checkout(
    db: Session,
    gym_id: str,
    plan: str,
    email: str,
    payment_id: str,
) -> CheckoutSession:
    """Completa un checkout pendiente o crea uno nuevo.

    Busca un CheckoutSession pendiente del gym y lo actualiza.
    Si no existe, crea uno nuevo ya completado.

    Args:
        db: SQLAlchemy session (caller maneja commit).
        gym_id: ID del gym.
        plan: Plan comprado.
        email: Email del pagador.
        payment_id: ID del pago (Stripe session_id o MP payment_id).

    Returns:
        CheckoutSession completado.
    """
    import secrets

    # Buscar checkout pendiente del gym
    checkout = db.query(CheckoutSession).filter(
        CheckoutSession.gym_id == gym_id,
        CheckoutSession.status == "pending",
    ).order_by(CheckoutSession.created_at.desc()).first()

    now = datetime.now(timezone.utc)

    if checkout:
        checkout.status = "completed"
        checkout.completed_at = now
        checkout.stripe_session_id = str(payment_id)
    else:
        checkout = CheckoutSession(
            id=secrets.token_urlsafe(32),
            gym_id=gym_id,
            stripe_session_id=str(payment_id),
            plan=plan,
            email=email,
            status="completed",
            completed_at=now,
        )
        db.add(checkout)

    db.flush()
    return checkout


def is_payment_processed(db: Session, payment_id: str) -> bool:
    """Verifica si un payment_id ya fue procesado (idempotencia MP)."""
    existing = db.query(CheckoutSession).filter(
        CheckoutSession.stripe_session_id == str(payment_id),
        CheckoutSession.status == "completed",
    ).first()
    return existing is not None


def record_payment(
    db: Session,
    gym_id: str,
    *,
    amount_cents: int,
    currency: str = "mxn",
    status: str = "succeeded",
    plan: Optional[str] = None,
    stripe_payment_intent_id: Optional[str] = None,
    stripe_invoice_id: Optional[str] = None,
) -> Payment:
    """Registra un pago en la tabla Payment."""
    payment = Payment(
        gym_id=gym_id,
        stripe_payment_intent_id=stripe_payment_intent_id or None,
        stripe_invoice_id=stripe_invoice_id or None,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        plan=plan,
    )
    db.add(payment)
    db.flush()
    return payment
