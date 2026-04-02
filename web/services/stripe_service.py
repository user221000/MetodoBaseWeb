"""
web/services/stripe_service.py — Stripe billing service layer.

Centraliza TODA la interacción con Stripe API.
Los routes solo llaman funciones de este módulo.

Flujo:
  1. create_checkout_session() → usuario selecciona plan y paga
  2. handle_webhook() → Stripe confirma pago y cambia estado
  3. create_portal_session() → usuario gestiona suscripción
  4. get_subscription_status() → consulta estado actual
  
Idempotencia:
  - Los event_id de Stripe se almacenan en stripe_webhook_events
  - Webhooks duplicados se ignoran sin error
  - Eventos antiguos se purgan periódicamente
"""
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from web.constants import PLANES_LICENCIA
from web.services.resilience import retry_with_backoff, stripe_circuit
from web.settings import get_settings
from web.database.models import Subscription, Payment, Usuario, StripeWebhookEvent, StripeCustomer
from web.services.subscription_service import activate_subscription, record_payment

logger = logging.getLogger(__name__)

# ── Inicialización ────────────────────────────────────────────────────────────

def _init_stripe() -> bool:
    """Configura stripe.api_key con timeout. Retorna True si está configurado."""
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.max_network_retries = 0  # Manejamos retries con circuit breaker

    # Configurar timeout (stripe-python usa requests internamente)
    try:
        stripe.default_http_client = stripe.http_client.RequestsClient(
            timeout=settings.STRIPE_TIMEOUT
        )
        logger.info("Stripe configured with timeout=%ss", settings.STRIPE_TIMEOUT)
    except Exception as e:
        logger.warning("Could not set Stripe timeout: %s", e)

    return True


# ── Product cache (for Subscription.create which requires product ID) ─────────

_product_cache: dict[str, stripe.Product] = {}


def _get_or_create_product(plan: str, info: dict) -> stripe.Product:
    """Get or create a Stripe Product for the given plan. Cached per process."""
    if plan in _product_cache:
        return _product_cache[plan]

    # Search for existing product by metadata
    products = stripe.Product.search(query=f"metadata['plan']:'{plan}'", limit=1)
    if products.data:
        _product_cache[plan] = products.data[0]
        return products.data[0]

    # Create new product
    product = stripe.Product.create(
        name=f"Método Base — {plan.replace('_', ' ').title()}",
        description=f"Hasta {info.get('max_clientes') or '∞'} clientes/mes",
        metadata={"plan": plan},
    )
    _product_cache[plan] = product
    return product


# ── Checkout ──────────────────────────────────────────────────────────────────

@retry_with_backoff(max_retries=3, circuit=stripe_circuit)
def create_checkout_session(
    db: Session,
    gym_id: str,
    plan: str,
    email: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Crea una Stripe Checkout Session para suscripción."""
    if not _init_stripe():
        raise RuntimeError("Stripe no configurado — falta STRIPE_SECRET_KEY")

    if plan not in PLANES_LICENCIA:
        raise ValueError(f"Plan inválido: {plan}")

    info = PLANES_LICENCIA[plan]

    # Reutilizar customer si ya existe
    sub = db.query(Subscription).filter(
        Subscription.gym_id == gym_id
    ).first()

    if sub and sub.status in {"active", "trialing", "past_due"}:
        raise ValueError("Ya existe una suscripción activa. Usa el portal para cambios.")

    customer_id = sub.stripe_customer_id if sub else None

    # Usar Price ID real de Stripe si está configurado (producción)
    price_id = info.get("stripe_price_id")
    if price_id:
        line_items = [{"price": price_id, "quantity": 1}]
    else:
        # Fallback a price_data dinámico (solo desarrollo)
        line_items = [{
            "price_data": {
                "currency": "mxn",
                "unit_amount": round(info["precio_mxn"] * 100),
                "recurring": {"interval": "month"},
                "product_data": {
                    "name": f"Método Base — {plan.title()}",
                    "description": f"Hasta {info['max_clientes'] or '∞'} clientes/mes",
                },
            },
            "quantity": 1,
        }]

    # Stripe requires absolute URLs
    settings = get_settings()
    base = settings.BASE_URL.rstrip("/")
    abs_success = base + success_url + "?session_id={CHECKOUT_SESSION_ID}"
    abs_cancel = base + cancel_url

    kwargs = {
        "payment_method_types": ["card"],
        "mode": "subscription",
        "line_items": line_items,
        "success_url": abs_success,
        "cancel_url": abs_cancel,
        "metadata": {"plan": plan, "gym_id": gym_id},
        "idempotency_key": f"checkout_{gym_id}_{plan}_{date.today().isoformat()}",
    }

    if customer_id:
        kwargs["customer"] = customer_id
    else:
        kwargs["customer_email"] = email

    session = stripe.checkout.Session.create(**kwargs)
    return {"session_id": session.id, "url": session.url}


# ── Customer Portal ──────────────────────────────────────────────────────────

@retry_with_backoff(max_retries=3, circuit=stripe_circuit)
def create_portal_session(db: Session, gym_id: str, return_url: str) -> dict:
    """Crea un portal Stripe para que el gym gestione su suscripción."""
    if not _init_stripe():
        raise RuntimeError("Stripe no configurado")

    sub = db.query(Subscription).filter(Subscription.gym_id == gym_id).first()
    if not sub or not sub.stripe_customer_id:
        raise ValueError("No hay suscripción activa")

    portal = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=get_settings().BASE_URL.rstrip("/") + return_url,
    )
    return {"url": portal.url}


# ── Elements (PaymentMethod) ───────────────────────────────────────────────

@retry_with_backoff(max_retries=3, circuit=stripe_circuit)
def create_subscription_with_payment_method(
    db: Session,
    gym_id: str,
    plan: str,
    email: str,
    payment_method_id: str,
) -> dict:
    """Crea suscripción usando un PaymentMethod ya tokenizado (Stripe Elements)."""
    if not _init_stripe():
        raise RuntimeError("Stripe no configurado — falta STRIPE_SECRET_KEY")

    if plan not in PLANES_LICENCIA:
        raise ValueError(f"Plan inválido: {plan}")

    info = PLANES_LICENCIA[plan]

    sub = db.query(Subscription).filter(
        Subscription.gym_id == gym_id
    ).first()

    customer_id = sub.stripe_customer_id if sub else None

    # Also check StripeCustomer table for existing customer
    if not customer_id:
        stripe_cust = db.query(StripeCustomer).filter(
            StripeCustomer.gym_id == gym_id
        ).first()
        if stripe_cust:
            customer_id = stripe_cust.stripe_customer_id

    if not customer_id:
        customer = stripe.Customer.create(
            email=email,
            payment_method=payment_method_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )
        customer_id = customer.id

        # Persist StripeCustomer record in DB
        stripe_cust = StripeCustomer(
            gym_id=gym_id,
            stripe_customer_id=customer_id,
            email=email,
            default_payment_method=payment_method_id,
        )
        db.add(stripe_cust)
        db.flush()
        logger.info("StripeCustomer created: gym=%s customer=%s", gym_id, customer_id)
    else:
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )
        # Update StripeCustomer record if exists
        stripe_cust = db.query(StripeCustomer).filter(
            StripeCustomer.gym_id == gym_id
        ).first()
        if stripe_cust:
            stripe_cust.default_payment_method = payment_method_id
            stripe_cust.updated_at = datetime.now(timezone.utc)
        else:
            stripe_cust = StripeCustomer(
                gym_id=gym_id,
                stripe_customer_id=customer_id,
                email=email,
                default_payment_method=payment_method_id,
            )
            db.add(stripe_cust)
        db.flush()

    price_id = info.get("stripe_price_id")
    if price_id:
        items = [{"price": price_id}]
    else:
        # Subscription.create requires product ID, not inline product_data
        product = _get_or_create_product(plan, info)
        items = [{
            "price_data": {
                "currency": "mxn",
                "unit_amount": round(info["precio_mxn"] * 100),
                "recurring": {"interval": "month"},
                "product": product.id,
            },
        }]

    idempotency_key = f"sub_{gym_id}_{plan}_{payment_method_id}"

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=items,
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
        metadata={"plan": plan, "gym_id": gym_id},
        idempotency_key=idempotency_key,
    )

    payment_intent = subscription.latest_invoice.payment_intent
    client_secret = payment_intent.client_secret if payment_intent else ""

    return {
        "subscription_id": subscription.id,
        "client_secret": client_secret,
        "status": subscription.status,
    }


# ── Confirm Subscription (client-side fallback) ─────────────────────────────

def confirm_subscription(db: Session, gym_id: str, subscription_id: str) -> dict:
    """Verifica con Stripe que la suscripción está activa y la activa en BD.

    Fallback para cuando el webhook no llega (desarrollo sin webhook secret,
    o retraso en la entrega del webhook).
    
    Also handles race condition where subscription is still "incomplete" but
    payment intent already succeeded (confirmCardPayment returned success).
    """
    if not _init_stripe():
        raise RuntimeError("Stripe no configurado")

    sub_stripe = stripe.Subscription.retrieve(
        subscription_id,
        expand=["latest_invoice.payment_intent"],
    )

    # Verify the subscription belongs to this gym
    if sub_stripe.metadata.get("gym_id") != str(gym_id):
        raise ValueError("La suscripción no pertenece a este gym")

    # Check if subscription is active directly
    is_active = sub_stripe.status in ("active", "trialing")

    # Also accept "incomplete" if payment intent already succeeded
    # (race condition: confirmCardPayment returned success but Stripe
    # hasn't updated the subscription status yet)
    if not is_active and sub_stripe.status == "incomplete":
        pi = getattr(sub_stripe.latest_invoice, "payment_intent", None)
        if pi and getattr(pi, "status", None) == "succeeded":
            is_active = True
            logger.info(
                "Subscription %s still incomplete but payment_intent succeeded — activating",
                subscription_id,
            )

    if not is_active:
        return {
            "status": sub_stripe.status,
            "message": "La suscripción aún no está activa",
            "activated": False,
        }

    plan = sub_stripe.metadata.get("plan", "standard")

    # Extract billing period dates from Stripe
    period_start = None
    period_end = None
    if sub_stripe.current_period_start:
        period_start = datetime.fromtimestamp(
            sub_stripe.current_period_start, tz=timezone.utc
        )
    if sub_stripe.current_period_end:
        period_end = datetime.fromtimestamp(
            sub_stripe.current_period_end, tz=timezone.utc
        )

    from web.services.subscription_service import activate_subscription

    activate_subscription(
        db,
        gym_id=gym_id,
        plan=plan,
        stripe_customer_id=sub_stripe.customer,
        stripe_subscription_id=subscription_id,
        current_period_start=period_start,
        current_period_end=period_end,
        provider="stripe",
    )

    # Ensure StripeCustomer record exists
    if sub_stripe.customer:
        stripe_cust = db.query(StripeCustomer).filter(
            StripeCustomer.gym_id == gym_id
        ).first()
        if not stripe_cust:
            user = db.query(Usuario).filter(Usuario.id == gym_id).first()
            stripe_cust = StripeCustomer(
                gym_id=gym_id,
                stripe_customer_id=sub_stripe.customer,
                email=user.email if user else "",
            )
            db.add(stripe_cust)
            db.flush()

    logger.info("Subscription confirmed via client fallback: gym=%s plan=%s", gym_id, plan)

    return {
        "status": "active",
        "plan": plan,
        "activated": True,
    }


# ── Webhook Processing ───────────────────────────────────────────────────────

def verify_webhook(payload: bytes, sig_header: str) -> dict:
    """Verifica firma del webhook y retorna el evento."""
    settings = get_settings()
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET not set")
        return None

    _init_stripe()
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )


def _is_event_processed(db: Session, event_id: str) -> bool:
    """Verifica si un evento ya fue procesado (idempotencia)."""
    exists = db.query(StripeWebhookEvent.event_id).filter(
        StripeWebhookEvent.event_id == event_id
    ).first()
    return exists is not None


def _mark_event_processed(db: Session, event_id: str, event_type: str, result: str) -> None:
    """Marca un evento como procesado."""
    webhook_event = StripeWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        result=result[:255] if result else None,
    )
    db.add(webhook_event)


def purge_old_webhook_events(db: Session, days: int = 7) -> int:
    """
    Elimina eventos procesados hace más de `days` días.
    
    Llamar periódicamente (ej: cron diario) para limpiar la tabla.
    Returns número de eventos eliminados.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = db.query(StripeWebhookEvent).filter(
        StripeWebhookEvent.processed_at < cutoff
    ).delete()
    return deleted


def handle_webhook_event(db: Session, event: dict) -> str:
    """
    Procesa un evento de Stripe webhook con idempotencia.
    
    - Verifica si el event_id ya fue procesado
    - Si es duplicado, retorna sin procesar
    - Si es nuevo, procesa y marca como procesado
    
    Returns descripción de acción tomada.
    """
    event_id = event.get("id", "")
    event_type = event["type"]
    
    # ── Idempotencia: verificar si ya fue procesado ──
    if _is_event_processed(db, event_id):
        logger.info("Webhook duplicado ignorado: event_id=%s type=%s", event_id, event_type)
        return f"duplicate:{event_type}"
    
    data = event["data"]["object"]

    handlers = {
        "checkout.session.completed": _on_checkout_completed,
        "customer.subscription.updated": _on_subscription_updated,
        "customer.subscription.deleted": _on_subscription_deleted,
        "invoice.payment_succeeded": _on_invoice_paid,
        "invoice.payment_failed": _on_invoice_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        result = handler(db, data)
    else:
        result = f"ignored:{event_type}"
    
    # ── Marcar como procesado ──
    _mark_event_processed(db, event_id, event_type, result)
    
    return result


def _infer_plan_from_subscription(subscription_id: str) -> str:
    """Dado un stripe subscription_id, infiere el nombre del plan por price_id."""
    try:
        sub = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])
        for item in (sub.get("items", {}).get("data") or []):
            price_id = (item.get("price") or {}).get("id", "")
            if price_id:
                for plan_key, info in PLANES_LICENCIA.items():
                    if info.get("stripe_price_id") == price_id:
                        logger.info("Plan inferido desde price_id %s → %s", price_id, plan_key)
                        return plan_key
    except Exception as e:
        logger.warning("No se pudo inferir plan desde subscription %s: %s", subscription_id, e)
    return ""


def _on_checkout_completed(db: Session, session: dict) -> str:
    """Checkout completado: crea o actualiza suscripción y StripeCustomer.
    
    Soporta dos flujos:
      1. Checkout Session clásico: gym_id y plan en session.metadata
      2. Payment Link: gym_id en client_reference_id, plan inferido desde price_id
    """
    meta = session.get("metadata", {}) or {}
    gym_id = meta.get("gym_id", "")
    plan = meta.get("plan", "")
    customer_id = session.get("customer", "")
    subscription_id = session.get("subscription", "")
    customer_email = session.get("customer_email", "")

    # Payment Links: gym_id viene en client_reference_id
    if not gym_id:
        gym_id = session.get("client_reference_id", "")
    if not gym_id:
        logger.warning("checkout.session.completed sin gym_id en metadata ni client_reference_id")
        return "error:no_gym_id"

    # Payment Links: inferir plan desde el price_id de la suscripción creada
    if not plan and subscription_id:
        plan = _infer_plan_from_subscription(subscription_id)
    if not plan:
        plan = "standard"

    # ── Crear o actualizar StripeCustomer ──
    if customer_id:
        stripe_cust = db.query(StripeCustomer).filter(
            StripeCustomer.gym_id == gym_id
        ).first()
        
        if stripe_cust:
            stripe_cust.stripe_customer_id = customer_id
            stripe_cust.email = customer_email or stripe_cust.email
            stripe_cust.updated_at = datetime.now(timezone.utc)
        else:
            stripe_cust = StripeCustomer(
                gym_id=gym_id,
                stripe_customer_id=customer_id,
                email=customer_email,
            )
            db.add(stripe_cust)
        db.flush()
        logger.info("StripeCustomer created/updated: gym=%s customer=%s", gym_id, customer_id)

    # ── Activar suscripción (shared service) ──
    activate_subscription(
        db, gym_id, plan,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        provider="stripe",
    )

    # Notificar por email
    _notify_subscription_activated(db, gym_id, plan)

    return f"activated:{plan}"


def _on_subscription_updated(db: Session, subscription: dict) -> str:
    """Suscripción actualizada (cambio de plan, pausa, etc.)."""
    stripe_sub_id = subscription.get("id", "")
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()
    if not sub:
        return "ignored:subscription_not_found"

    sub.status = subscription.get("status", sub.status)
    sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)

    period = subscription.get("current_period_start")
    if period:
        sub.current_period_start = datetime.fromtimestamp(period, tz=timezone.utc)
    period_end = subscription.get("current_period_end")
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    # Detectar cambio de plan
    items = subscription.get("items", {}).get("data", [])
    if items:
        new_plan = items[0].get("price", {}).get("metadata", {}).get("plan")
        if new_plan and new_plan in PLANES_LICENCIA:
            sub.plan = new_plan
            sub.max_clientes = PLANES_LICENCIA[new_plan]["max_clientes"] or 999999

    sub.updated_at = datetime.now(timezone.utc)
    db.flush()
    return f"updated:{sub.status}"


def _on_subscription_deleted(db: Session, subscription: dict) -> str:
    """Suscripción cancelada definitivamente."""
    stripe_sub_id = subscription.get("id", "")
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()
    if not sub:
        return "ignored:subscription_not_found"

    sub.status = "canceled"
    sub.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("Subscription canceled: gym=%s", sub.gym_id)

    # Notificar por email
    _notify_subscription_canceled(db, sub.gym_id)

    return "canceled"


def _on_invoice_paid(db: Session, invoice: dict) -> str:
    """Factura pagada — registrar payment."""
    customer_id = invoice.get("customer", "")
    sub = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    gym_id = sub.gym_id if sub else ""

    if not gym_id:
        logger.warning("No subscription found for customer %s — skipping payment record", customer_id)
        return "skipped:no_gym_id"

    payment = record_payment(
        db, gym_id,
        amount_cents=invoice.get("amount_paid", 0),
        currency=invoice.get("currency", "usd"),
        status="succeeded",
        plan=sub.plan if sub else None,
        stripe_payment_intent_id=invoice.get("payment_intent", ""),
        stripe_invoice_id=invoice.get("id", ""),
    )
    logger.info("Payment recorded: gym=%s amount=%s", gym_id, payment.amount_cents)
    return f"paid:{payment.amount_cents}"


def _on_invoice_failed(db: Session, invoice: dict) -> str:
    """Pago fallido — registrar y actualizar estado."""
    customer_id = invoice.get("customer", "")
    sub = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    gym_id = sub.gym_id if sub else ""

    if not gym_id:
        logger.warning("No subscription found for customer %s — skipping failed payment record", customer_id)
        return "skipped:no_gym_id"

    record_payment(
        db, gym_id,
        amount_cents=invoice.get("amount_due", 0),
        currency=invoice.get("currency", "usd"),
        status="failed",
        plan=sub.plan if sub else None,
        stripe_payment_intent_id=invoice.get("payment_intent", ""),
        stripe_invoice_id=invoice.get("id", ""),
    )

    if sub:
        sub.status = "past_due"
        sub.updated_at = datetime.now(timezone.utc)

    db.flush()
    logger.warning("Payment failed: gym=%s", gym_id)

    # Notificar por email
    _notify_payment_failed(db, gym_id)

    return f"failed:{gym_id}"


# ── Queries ───────────────────────────────────────────────────────────────────

def _get_gym_email_and_name(db: Session, gym_id: str) -> tuple[str, str]:
    """Obtiene email y nombre del gym desde SA (Usuario)."""
    user = db.query(Usuario).filter(Usuario.id == gym_id).first()
    if user:
        return user.email, user.nombre or ""
    return "", ""


def _notify_subscription_activated(db: Session, gym_id: str, plan: str) -> None:
    from web.services import email_service
    email, nombre = _get_gym_email_and_name(db, gym_id)
    if email:
        email_service.send_subscription_activated(email, nombre, plan)


def _notify_subscription_canceled(db: Session, gym_id: str) -> None:
    from web.services import email_service
    email, nombre = _get_gym_email_and_name(db, gym_id)
    if email:
        email_service.send_subscription_canceled(email, nombre)


def _notify_payment_failed(db: Session, gym_id: str) -> None:
    from web.services import email_service
    email, nombre = _get_gym_email_and_name(db, gym_id)
    if email:
        email_service.send_payment_failed(email, nombre)


def get_subscription(db: Session, gym_id: str) -> Optional[dict]:
    """Obtiene suscripción activa del gym."""
    sub = db.query(Subscription).filter(Subscription.gym_id == gym_id).first()
    if not sub:
        return None

    # Frontend expects Unix timestamps (seconds since epoch) for period dates
    period_end = None
    if sub.current_period_end:
        period_end = int(sub.current_period_end.replace(tzinfo=timezone.utc).timestamp()) \
            if sub.current_period_end.tzinfo is None \
            else int(sub.current_period_end.timestamp())

    return {
        "plan": sub.plan,
        "status": sub.status,
        "max_clientes": sub.max_clientes,
        "current_period_end": period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "stripe_customer_id": sub.stripe_customer_id,
    }


def get_payment_history(db: Session, gym_id: str, limit: int = 20) -> list[dict]:
    """Historial de pagos del gym."""
    rows = db.query(Payment).filter(
        Payment.gym_id == gym_id
    ).order_by(Payment.created_at.desc()).limit(limit).all()
    return [
        {
            "id": p.id,
            "amount_cents": p.amount_cents,
            "currency": p.currency,
            "status": p.status,
            "plan": p.plan,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "stripe_invoice_id": p.stripe_invoice_id,
        }
        for p in rows
    ]
