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
from web.database.models import Subscription, Payment, Usuario, StripeWebhookEvent, StripeCustomer, PurchaseIntent
from web.services.subscription_service import activate_subscription, record_payment, update_subscription_status
from web.services.billing_integrity import prepare_purchase, price_in_cents
from web.database.tenant_context import bind_verified_subject
from web.services.provider_subjects import provider_subject, record_provider_subject

logger = logging.getLogger(__name__)

# ── Inicialización ────────────────────────────────────────────────────────────

def _init_stripe() -> bool:
    """Configura stripe.api_key con timeout. Retorna True si está configurado."""
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    # The existing Elements flow uses Invoice.payment_intent/charge. Basil
    # removed those fields; keep an explicit supported API contract until its
    # sandbox-tested migration to Invoice Payments is delivered.
    stripe.api_version = "2024-06-20"
    stripe.max_network_retries = 0  # Manejamos retries con circuit breaker

    # Configurar timeout (stripe-python usa requests internamente)
    try:
        stripe.default_http_client = stripe.http_client.RequestsClient(
            timeout=settings.STRIPE_TIMEOUT
        )
        logger.info("Stripe configured with timeout=%ss", settings.STRIPE_TIMEOUT)
    except Exception as e:
        logger.warning("Could not set Stripe timeout class=%s", type(e).__name__)

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
    request_key: Optional[str] = None,
) -> dict:
    """Crea una Stripe Checkout Session para suscripción."""
    if not _init_stripe():
        raise RuntimeError("Stripe no configurado — falta STRIPE_SECRET_KEY")

    if plan not in PLANES_LICENCIA:
        raise ValueError(f"Plan inválido: {plan}")

    info = PLANES_LICENCIA[plan]
    intent = prepare_purchase(db, gym_id, "stripe", "checkout", plan, request_key)

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
    abs_success = base + success_url + ("&" if "?" in success_url else "?") + "session_id={CHECKOUT_SESSION_ID}"
    abs_cancel = base + cancel_url

    kwargs = {
        "payment_method_types": ["card"],
        "mode": "subscription",
        "line_items": line_items,
        "success_url": abs_success,
        "cancel_url": abs_cancel,
        "metadata": {"plan": plan, "gym_id": gym_id, "purchase_intent_id": intent.id},
        "subscription_data": {"metadata": {"plan": plan, "gym_id": gym_id, "purchase_intent_id": intent.id}},
        "idempotency_key": f"purchase_{intent.id}_checkout",
    }

    if customer_id:
        kwargs["customer"] = customer_id
    else:
        kwargs["customer_email"] = email

    session = stripe.checkout.Session.create(**kwargs)
    intent.provider_reference_id = session.id
    intent.status = "provider_created"
    db.commit()
    return {"session_id": session.id, "url": session.url, "purchase_intent_id": intent.id}


# ── Customer Portal ──────────────────────────────────────────────────────────

def create_portal_session(db: Session, gym_id: str, return_url: str) -> dict:
    """Reject invalid input before it can affect the shared provider circuit."""
    from web.services.return_paths import private_return_path
    return_url = private_return_path(return_url)
    return _create_portal_session(db, gym_id, return_url)


@retry_with_backoff(max_retries=3, circuit=stripe_circuit)
def _create_portal_session(db: Session, gym_id: str, return_url: str) -> dict:
    """Only a valid application return path enters provider retry/circuit."""
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
    request_key: Optional[str] = None,
) -> dict:
    """Crea suscripción usando un PaymentMethod ya tokenizado (Stripe Elements)."""
    if not _init_stripe():
        raise RuntimeError("Stripe no configurado — falta STRIPE_SECRET_KEY")

    if plan not in PLANES_LICENCIA:
        raise ValueError(f"Plan inválido: {plan}")

    info = PLANES_LICENCIA[plan]
    intent = prepare_purchase(db, gym_id, "stripe", "elements", plan, request_key)

    # A provider result is recovered using the same durable operation identity
    # after a network retry or a database failure following provider success.
    if intent.provider_reference_id:
        subscription = stripe.Subscription.retrieve(intent.provider_reference_id,
                                                     expand=["latest_invoice.payment_intent"])
        invoice = subscription.get("latest_invoice") or {}
        pi = invoice.get("payment_intent") or {}
        return {"subscription_id": subscription.id, "client_secret": pi.get("client_secret", ""),
                "status": subscription.status, "purchase_intent_id": intent.id}

    sub = db.query(Subscription).filter(
        Subscription.gym_id == gym_id
    ).first()

    if sub and sub.status in {"active", "trialing", "past_due"}:
        raise ValueError("Ya existe una suscripción. Usa el portal para gestionarla.")
    customer_id = intent.provider_customer_id or (sub.stripe_customer_id if sub else None)

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
            metadata={"gym_id": gym_id},
            idempotency_key=f"purchase_{intent.id}_customer",
        )
        customer_id = customer.id
        intent.provider_customer_id = customer_id

        # Persist StripeCustomer record in DB
        stripe_cust = StripeCustomer(
            gym_id=gym_id,
            stripe_customer_id=customer_id,
            email=email,
            default_payment_method=payment_method_id,
        )
        db.add(stripe_cust)
        db.flush()
        db.commit()
        logger.info("StripeCustomer created: gym=%s customer=%s", gym_id, customer_id)
    else:
        method = stripe.PaymentMethod.retrieve(payment_method_id)
        if method.get("customer") and method.get("customer") != customer_id:
            raise ValueError("El método de pago pertenece a otra cuenta")
        if not method.get("customer"):
            stripe.PaymentMethod.attach(payment_method_id, customer=customer_id,
                                        idempotency_key=f"purchase_{intent.id}_attach")
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
            idempotency_key=f"purchase_{intent.id}_default_method",
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

    idempotency_key = f"purchase_{intent.id}_subscription"

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=items,
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
        metadata={"plan": plan, "gym_id": gym_id, "purchase_intent_id": intent.id},
        idempotency_key=idempotency_key,
    )

    payment_intent = subscription.latest_invoice.payment_intent
    client_secret = payment_intent.client_secret if payment_intent else ""
    intent.provider_reference_id = subscription.id
    intent.provider_customer_id = customer_id
    intent.status = "provider_created"
    db.commit()

    return {
        "subscription_id": subscription.id,
        "client_secret": client_secret,
        "status": subscription.status,
        "purchase_intent_id": intent.id,
    }


# ── Confirm Subscription (client-side fallback) ─────────────────────────────

def _stripe_period(snapshot: dict, key: str):
    """Resolve old and current Stripe API period shapes to aware UTC."""
    value = snapshot.get(key)
    if not value:
        items = (snapshot.get("items") or {}).get("data") or []
        value = items[0].get(key) if items else None
    return datetime.fromtimestamp(value, tz=timezone.utc) if value else None


def _verified_invoice_charge(invoice: dict, customer_id: str, expected_amount: int, *, fetch_charge=None) -> bool:
    """Require captured current funding; an approved partial keeps its period."""
    charge = invoice.get("charge")
    if isinstance(charge, str):
        charge = (fetch_charge or stripe.Charge.retrieve)(charge)
    if not isinstance(charge, dict) or not isinstance(charge.get("id"), str):
        return False
    amount, returned = charge.get("amount"), charge.get("amount_refunded")
    return (charge.get("paid") is True and charge.get("captured") is True and
            type(amount) is int and amount >= expected_amount and type(returned) is int and
            0 <= returned < amount and charge.get("refunded") is False and
            ("amount_captured" not in charge or type(charge["amount_captured"]) is int and charge["amount_captured"] == amount) and
            charge.get("currency") == "mxn" and
            charge.get("customer") == customer_id)


def _validate_refund_progress(payment: Payment, charge: dict) -> tuple[str, int]:
    """Bind an aggregate provider observation; inconsistent reads stay retryable."""
    amount, returned, charge_id = charge.get("amount"), charge.get("amount_refunded"), charge.get("id")
    if (not isinstance(charge_id, str) or not charge_id.startswith("ch_") or len(charge_id) > 255
            or type(amount) is not int or amount <= 0 or amount != payment.amount_cents
            or type(returned) is not int or not 0 <= returned <= amount
            or type(charge.get("refunded")) is not bool or charge["refunded"] != (returned == amount)
            or payment.currency != charge.get("currency")
            or charge.get("payment_intent") and payment.stripe_payment_intent_id
                and charge["payment_intent"] != payment.stripe_payment_intent_id
            or ("amount_captured" in charge and (type(charge["amount_captured"]) is not int or charge["amount_captured"] != amount))
            or payment.stripe_charge_id is not None and payment.stripe_charge_id != charge_id
            or payment.refund_amount_cents is not None and returned < payment.refund_amount_cents
            or payment.status == "refunded" and returned != amount):
        raise ValueError("Refund observation contradicts the persisted payment")
    return charge_id, returned


def _observe_payment_refund(payment: Payment, charge: dict) -> None:
    """Observe current cumulative refunds, never manufacture individual refunds."""
    charge_id, returned = _validate_refund_progress(payment, charge)
    if payment.refund_amount_cents != returned:
        payment.refund_observed_at = datetime.now(timezone.utc)
    payment.stripe_charge_id = charge_id
    payment.refund_amount_cents = returned
    payment.status = ("refunded" if returned == payment.amount_cents else
                      "partially_refunded" if returned else "succeeded")


def reconcile_subscription(db: Session, subscription_id: str, subject_id: str | None = None,
                           *, fetch_subscription=None, fetch_charge=None, fetch_invoice=None) -> dict:
    """Fetch current provider truth and reconcile B2B/B2C in one transaction.

    Ownership comes from a persisted purchase or existing provider mapping.
    Active paid access requires expected MXN/month price, paid invoice and an
    captured charge with remaining funds. Partial refunds retain the actual paid
    period; they never add time. Fetching current state prevents old events overwriting a
    newer provider state. Caller commits; provider errors remain retryable.
    Optional keyword-only callbacks are synchronous read capabilities for the
    bounded administrative job; defaults preserve the existing SDK calls.
    """
    retrieve = fetch_subscription or stripe.Subscription.retrieve
    snapshot = retrieve(subscription_id, expand=[
        "latest_invoice.payment_intent", "latest_invoice.charge", "items.data.price"])
    if snapshot.get("id") != subscription_id:
        raise ValueError("Subscription resource mismatch")
    metadata = snapshot.get("metadata") or {}
    intent_id = metadata.get("purchase_intent_id")
    intent = db.query(PurchaseIntent).filter_by(id=intent_id, provider="stripe").first() if intent_id else None
    owner = intent.subject_id if intent else provider_subject(db, "stripe", "subscription", subscription_id)
    # An authenticated confirmation can check its own pre-existing mapping;
    # public callbacks require the persisted minimal association instead.
    if owner is None and subject_id is not None:
        owner = str(subject_id)
    if not owner or (subject_id is not None and owner != str(subject_id)):
        raise ValueError("Payment account mismatch")
    if metadata.get("gym_id") and str(metadata["gym_id"]) != str(owner):
        raise ValueError("Subscription identity mismatch")
    bind_verified_subject(db, str(owner))
    mapped = db.query(Subscription).filter_by(stripe_subscription_id=subscription_id).first()
    if not intent and (mapped is None or mapped.gym_id != str(owner)):
        raise ValueError("Legacy purchase requires explicit reconciliation")
    db.query(Usuario).filter_by(id=owner).update({Usuario.id: Usuario.id})
    # The account may have renewed through a different subscription while this
    # request waited for its lock. Re-read the mapping, bypassing the identity
    # map, before touching the current canonical row.
    mapped = db.query(Subscription).filter_by(stripe_subscription_id=subscription_id).populate_existing().first()
    current = db.query(Subscription).filter_by(gym_id=owner).populate_existing().first()
    if current and current.provider not in (None, "stripe") and (
            current.status in {"active", "trialing", "past_due"} or intent is None or intent.status == "confirmed"):
        # A notification from a previous Stripe subscription must never modify
        # the current MP-funded entitlement, even if the Stripe object is live.
        return {"status": "superseded", "plan": current.plan, "activated": False}
    if current and current.stripe_subscription_id and current.stripe_subscription_id != subscription_id:
        newer_intent = db.query(PurchaseIntent).filter_by(provider="stripe", provider_reference_id=current.stripe_subscription_id).first()
        incoming_time = (intent.created_at.replace(tzinfo=timezone.utc) if intent.created_at.tzinfo is None else intent.created_at) if intent else None
        newer_time = (newer_intent.created_at.replace(tzinfo=timezone.utc) if newer_intent.created_at.tzinfo is None else newer_intent.created_at) if newer_intent else None
        if intent is None or (newer_time and incoming_time < newer_time):
            return {"status": "superseded", "plan": current.plan, "activated": False}
    # Resolve the account first, then fetch again under its transaction lock.
    # A request that waited for a refund/cancellation must observe fresh state.
    snapshot = retrieve(subscription_id, expand=[
        "latest_invoice.payment_intent", "latest_invoice.charge", "items.data.price"])
    metadata = snapshot.get("metadata") or {}
    if snapshot.get("id") != subscription_id:
        raise ValueError("Subscription resource mismatch")
    if intent and metadata.get("purchase_intent_id") != intent.id:
        raise ValueError("Purchase identity mismatch")
    if metadata.get("gym_id") and str(metadata["gym_id"]) != str(owner):
        raise ValueError("Subscription identity mismatch")
    customer_id = snapshot.get("customer")
    if intent and intent.provider_customer_id and intent.provider_customer_id != customer_id:
        raise ValueError("Payment customer mismatch")
    if mapped and mapped.stripe_customer_id and mapped.stripe_customer_id != customer_id:
        raise ValueError("Payment customer mismatch")
    plan = intent.plan if intent else mapped.plan
    if metadata.get("plan") and metadata["plan"] != plan:
        raise ValueError("Subscription plan mismatch")
    if intent:
        record_provider_subject(db, "stripe", "subscription", subscription_id, owner, intent.id)
        if isinstance(customer_id, str) and customer_id:
            record_provider_subject(db, "stripe", "customer", customer_id, owner, intent.id)
    status = snapshot.get("status", "incomplete")
    period_start = _stripe_period(snapshot, "current_period_start")
    period_end = _stripe_period(snapshot, "current_period_end")
    if status == "active":
        items = (snapshot.get("items") or {}).get("data") or []
        if len(items) != 1 or items[0].get("quantity", 1) != 1:
            raise ValueError("Invalid subscription item")
        price = items[0].get("price") or {}
        configured_price = PLANES_LICENCIA[plan].get("stripe_price_id")
        if configured_price and price.get("id") != configured_price:
            raise ValueError("Subscription price mismatch")
        if (str(price.get("currency", "")).lower() != "mxn" or
                price.get("unit_amount") != price_in_cents(plan) or
                (price.get("recurring") or {}).get("interval") != "month" or
                (price.get("recurring") or {}).get("interval_count", 1) != 1):
            raise ValueError("Subscription amount or period mismatch")
        invoice = snapshot.get("latest_invoice") or {}
        if fetch_invoice is not None:
            invoice_id = invoice.get("id") if isinstance(invoice, dict) else invoice
            if not isinstance(invoice_id, str) or not invoice_id.startswith("in_"):
                raise ValueError("Subscription invoice identity missing")
            invoice = fetch_invoice(invoice_id)
            if snapshot.get("livemode") is not invoice.get("livemode"):
                raise ValueError("Subscription invoice mode mismatch")
        # Resolve a string capability once and use that same resource for both
        # funding and progression. Two reads can straddle a full refund.
        if isinstance(invoice, dict) and isinstance(invoice.get("charge"), str):
            invoice = dict(invoice, charge=(fetch_charge or stripe.Charge.retrieve)(invoice["charge"]))
        if not isinstance(invoice, dict) or not (invoice.get("paid") is True or invoice.get("status") == "paid"):
            status = "incomplete"
        elif (str(invoice.get("currency", "")).lower() != "mxn" or
              invoice.get("amount_paid", 0) < price_in_cents(plan)):
            status = "incomplete"
        elif (invoice.get("paid_out_of_band") is True or
              not _verified_invoice_charge(invoice, customer_id, price_in_cents(plan), fetch_charge=fetch_charge)):
            status = "unpaid"
        if status == "active":
            charge = invoice.get("charge")
            if isinstance(charge, str):
                charge = (fetch_charge or stripe.Charge.retrieve)(charge)
            payment = db.query(Payment).filter_by(gym_id=owner, stripe_invoice_id=invoice.get("id")).one_or_none()
            if payment:
                _validate_refund_progress(payment, charge)
            if charge.get("amount_refunded", 0) > 0:
                if period_start is None or period_end is None or period_end <= period_start:
                    raise ValueError("Partial refund requires the actual bounded paid period")
                # A refund observation is not a new purchase. For an already
                # observed invoice it cannot extend the entitlement's end.
                old_start = mapped.current_period_start if mapped else None
                old_start = old_start.replace(tzinfo=timezone.utc) if old_start and old_start.tzinfo is None else old_start
                already_paid = payment and payment.status in {"succeeded", "partially_refunded", "refunded"}
                if payment and mapped and mapped.current_period_end and (already_paid or old_start == period_start):
                    old_end = mapped.current_period_end
                    old_end = old_end.replace(tzinfo=timezone.utc) if old_end.tzinfo is None else old_end
                    period_end = min(period_end, old_end)
                if period_end <= datetime.now(timezone.utc):
                    status = "unpaid"
    if status == "active":
        mapped = activate_subscription(db, owner, plan, stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id, current_period_start=period_start,
            current_period_end=period_end, provider="stripe")
        if intent:
            intent.status = "confirmed"
            intent.provider_reference_id = subscription_id
            intent.provider_customer_id = customer_id
    elif mapped:
        update_subscription_status(db, mapped, status)
    if mapped:
        mapped.cancel_at_period_end = bool(snapshot.get("cancel_at_period_end", False))
        mapped.current_period_start = period_start
        mapped.current_period_end = period_end
    db.flush()
    return {"status": status, "plan": plan, "activated": status == "active"}


def confirm_subscription(db: Session, gym_id: str, subscription_id: str) -> dict:
    """Confirm provider evidence; browser success alone never grants paid access."""
    if not _init_stripe():
        raise RuntimeError("Stripe not configured")
    return reconcile_subscription(db, subscription_id, gym_id)


def verify_webhook(payload: bytes, sig_header: str) -> dict:
    """Verifica firma del webhook y retorna el evento."""
    settings = get_settings()
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET not set")
        raise RuntimeError("Stripe webhooks no configurados")

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
    if not event_id:
        raise ValueError("Webhook event identity missing")
    event_type = event["type"]
    
    # ── Idempotencia: verificar si ya fue procesado ──
    if _is_event_processed(db, event_id):
        logger.info("Webhook duplicado ignorado: event_id=%s type=%s", event_id, event_type)
        return f"duplicate:{event_type}"
    
    data = event["data"]["object"]
    if event_type in {"invoice.paid", "invoice.payment_succeeded", "invoice.payment_failed"}:
        if type(event.get("livemode")) is not bool or data.get("livemode") is not event["livemode"]:
            raise ValueError("Invoice event mode mismatch")
    if event_type == "charge.refunded" and "livemode" in data:
        if type(event.get("livemode")) is not bool or data["livemode"] is not event["livemode"]:
            raise ValueError("Refund event mode mismatch")
    _init_stripe()

    handlers = {
        "checkout.session.completed": _on_checkout_completed,
        "checkout.session.async_payment_succeeded": _on_checkout_completed,
        "checkout.session.async_payment_failed": _on_checkout_completed,
        "customer.subscription.created": _on_subscription_updated,
        "charge.refunded": _on_charge_refunded,
        "customer.subscription.updated": _on_subscription_updated,
        "customer.subscription.deleted": _on_subscription_deleted,
        # This event also covers invoices marked paid outside Stripe. The
        # handler independently reads the invoice and captured charge; the
        # event name or its snapshot can never grant access or prove payment.
        "invoice.paid": _on_invoice_paid,
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
        logger.warning("Plan lookup failed subscription=%s class=%s", subscription_id, type(e).__name__)
    return ""


def _on_checkout_completed(db: Session, session: dict) -> str:
    """A completed checkout can still be unpaid; reconcile only paid evidence."""
    if session.get("payment_status") != "paid":
        return "pending:payment_not_paid"
    subscription_id = session.get("subscription")
    if not subscription_id:
        raise ValueError("Checkout has no subscription")
    result = reconcile_subscription(db, subscription_id)
    return ("activated:" if result["activated"] else "pending:") + result["plan"]


def _on_subscription_updated(db: Session, subscription: dict) -> str:
    """Read the current provider state instead of applying a stale event body."""
    result = reconcile_subscription(db, subscription["id"])
    return "updated:" + result["status"]


def _on_subscription_deleted(db: Session, subscription: dict) -> str:
    """Reconcile cancellation for canonical subscription and individual quota."""
    result = reconcile_subscription(db, subscription["id"])
    return "canceled" if result["status"] == "canceled" else "updated:" + result["status"]


def _invoice_subscription_id(db: Session, invoice: dict) -> str:
    reference = invoice.get("subscription") or ((invoice.get("parent") or {}).get("subscription_details") or {}).get("subscription")
    if reference:
        return reference
    _bind_customer_purchase(db, invoice.get("customer"))
    mapped = db.query(Subscription).filter_by(stripe_customer_id=invoice.get("customer")).first()
    return mapped.stripe_subscription_id if mapped else ""


def _record_invoice(db: Session, invoice: dict, status: str) -> str:
    """Observe the current invoice, never an event's historical payment state.

    Webhook payloads can use a newer API version than our explicitly pinned
    reads. Fetching by invoice identity handles both shapes and rejects stale,
    out-of-band or refunded success assertions. Read failures propagate so the
    route rolls back both business state and the event inbox for a retry.
    """
    invoice_id = invoice.get("id")
    if not isinstance(invoice_id, str) or not invoice_id.startswith("in_"):
        raise ValueError("Invoice identity missing")

    observations = {}

    def funding_frame(actual):
        # Compare consumed facts, retaining bool/int distinctions. Unrelated
        # descriptions or provider metadata do not participate in funding.
        def fields(resource, names):
            return tuple((name, name in resource, type(resource.get(name)), resource.get(name)) for name in names)
        charge = actual.get("charge")
        charge_frame = fields(charge, ("id", "object", "invoice", "customer", "livemode",
            "currency", "payment_intent", "paid", "captured", "amount", "amount_captured",
            "amount_refunded", "refunded")) if isinstance(charge, dict) else (type(charge), charge)
        subscription = actual.get("subscription") or ((actual.get("parent") or {}).get(
            "subscription_details") or {}).get("subscription")
        return (subscription, fields(actual, ("id", "object", "customer", "livemode", "currency",
            "paid", "status", "paid_out_of_band", "amount_paid", "amount_due", "payment_intent")),
            "charge" in actual, charge_frame)

    def read_invoice(reference=invoice_id):
        current = stripe.Invoice.retrieve(reference, expand=["charge"])
        if (not isinstance(current, dict) or current.get("id") != reference
                or current.get("object") != "invoice"
                or type(current.get("livemode")) is not bool):
            raise ValueError("Invoice resource mismatch")
        if isinstance(current.get("charge"), str):
            current = dict(current, charge=stripe.Charge.retrieve(current["charge"]))
        frame = funding_frame(current)
        if reference in observations and observations[reference] != frame:
            # Reconciliation may already have changed entitlement in this
            # transaction. Never acknowledge a later contradictory observation
            # as pending: let the route roll back access, money and inbox.
            raise RuntimeError("Invoice funding changed during reconciliation")
        observations[reference] = frame
        return current

    current = read_invoice()
    subscription_id = current.get("subscription") or ((current.get("parent") or {}).get(
        "subscription_details") or {}).get("subscription")
    customer_id = current.get("customer")
    mode = current["livemode"]
    if (not isinstance(subscription_id, str) or not subscription_id.startswith("sub_")
            or not isinstance(customer_id, str) or not customer_id.startswith("cus_")):
        raise ValueError("Invoice subscription or customer identity missing")
    if "livemode" in invoice and invoice["livemode"] is not mode:
        raise ValueError("Invoice mode mismatch")

    def read_subscription_invoice(reference):
        actual = read_invoice(reference)
        actual_subscription = actual.get("subscription") or ((actual.get("parent") or {}).get(
            "subscription_details") or {}).get("subscription")
        if (actual_subscription != subscription_id or actual.get("customer") != customer_id
                or actual["livemode"] is not mode):
            raise ValueError("Invoice subscription identity mismatch")
        if type(actual.get("paid")) is not bool or (actual.get("status") == "paid") != actual["paid"]:
            raise ValueError("Invoice payment state mismatch")
        charge = actual.get("charge")
        if isinstance(charge, str):
            charge = stripe.Charge.retrieve(charge)
            actual = dict(actual, charge=charge)
        if isinstance(charge, dict) and (charge.get("invoice") != reference or charge.get("livemode") is not mode):
            raise ValueError("Invoice charge identity mismatch")
        return actual

    result = reconcile_subscription(db, subscription_id, fetch_invoice=read_subscription_invoice)
    # Reconciliation holds the account transaction lock. Observe the invoice
    # again after waiting for it, just as the subscription reconciler does.
    current = read_invoice()
    current_subscription = current.get("subscription") or ((current.get("parent") or {}).get(
        "subscription_details") or {}).get("subscription")
    if (current_subscription != subscription_id or current.get("customer") != customer_id
            or current["livemode"] is not mode):
        raise ValueError("Invoice identity changed")
    if result["status"] == "superseded":
        return "ignored:superseded_invoice"
    sub = db.query(Subscription).filter_by(stripe_subscription_id=subscription_id).first()
    if sub is None:
        return "pending:subscription_not_confirmed"
    if sub.stripe_customer_id != customer_id:
        raise ValueError("Invoice customer mismatch")
    if current.get("currency") != "mxn":
        raise ValueError("Invoice currency mismatch")
    paid = current.get("paid") is True and current.get("status") == "paid"
    if paid:
        amount = current.get("amount_paid")
        charge = current.get("charge")
        if isinstance(charge, str):
            charge = stripe.Charge.retrieve(charge)
            current = dict(current, charge=charge)
        if (type(amount) is not int or amount < price_in_cents(sub.plan)
                or current.get("paid_out_of_band") is True
                or not _verified_invoice_charge(current, customer_id, amount)):
            return "pending:invoice_payment_not_verified"
        if charge.get("invoice") != invoice_id or charge.get("livemode") is not mode:
            raise ValueError("Invoice charge identity mismatch")
        status = "succeeded"
    elif status == "succeeded":
        return "pending:invoice_not_paid"
    else:
        amount = current.get("amount_due")
        if type(amount) is not int or amount < 0:
            raise ValueError("Invoice amount invalid")
    payment = db.query(Payment).filter_by(stripe_invoice_id=invoice_id).first()
    if payment:
        if payment.gym_id != sub.gym_id or payment.currency != current["currency"]:
            raise ValueError("Invoice payment owner mismatch")
        # An older invoice event cannot erase a succeeded or refunded fact.
        if payment.status not in {"succeeded", "partially_refunded", "refunded"}:
            payment.status = status
            payment.amount_cents = amount
    else:
        payment_intent = current.get("payment_intent")
        if payment_intent is not None and not isinstance(payment_intent, str):
            raise ValueError("Invoice payment identity invalid")
        payment = record_payment(db, sub.gym_id, amount_cents=amount, currency=current["currency"],
                       status=status, plan=sub.plan, stripe_payment_intent_id=payment_intent,
                       stripe_invoice_id=invoice_id)
    if paid:
        _observe_payment_refund(payment, charge)
    db.flush()
    return ("paid:" if status == "succeeded" else "failed:") + str(amount)


def _on_invoice_paid(db: Session, invoice: dict) -> str:
    return _record_invoice(db, invoice, "succeeded")


def _on_invoice_failed(db: Session, invoice: dict) -> str:
    return _record_invoice(db, invoice, "failed")


def _on_charge_refunded(db: Session, charge: dict) -> str:
    """Observe partial/full refunds without revoking a newer paid renewal."""
    customer_id = charge.get("customer")
    _bind_customer_purchase(db, customer_id)
    mapped = db.query(Subscription).filter_by(stripe_customer_id=customer_id).first()
    if not mapped:
        raise ValueError("Refund subscription mapping unavailable")
    # Lock first, then re-read the mapping and current refund evidence. A stale
    # expanded subscription must not be evaluated before the known Charge.
    db.query(Usuario).filter_by(id=mapped.gym_id).update({Usuario.id: Usuario.id})
    mapped = db.query(Subscription).filter_by(stripe_customer_id=customer_id).populate_existing().first()
    if not mapped:
        raise ValueError("Refund subscription mapping changed")
    # There is no historical ledger to repair before its first observation.
    # Keep that absence explicit instead of inventing a past charge or row.
    if not db.query(Payment.id).filter(Payment.gym_id == mapped.gym_id,
            Payment.stripe_invoice_id.is_not(None)).first():
        reconcile_subscription(db, mapped.stripe_subscription_id)
        return "refund:reconciled"
    charge_id = charge.get("id")
    if not isinstance(charge_id, str) or not charge_id.startswith("ch_"):
        raise ValueError("Refund charge identity missing")
    current = stripe.Charge.retrieve(charge_id)
    if (not isinstance(current, dict) or current.get("id") != charge_id
            or current.get("object") != "charge" or current.get("customer") != customer_id
            or type(current.get("livemode")) is not bool
            or current.get("livemode") is not charge.get("livemode")
            or current.get("paid") is not True or current.get("captured") is not True
            or current.get("currency") != "mxn"):
        raise ValueError("Refund charge resource mismatch")
    invoice_id = current.get("invoice")
    if not isinstance(invoice_id, str) or not invoice_id.startswith("in_"):
        raise ValueError("Refund invoice identity missing")
    invoice = stripe.Invoice.retrieve(invoice_id, expand=["charge"])
    subscription_id = invoice.get("subscription") or ((invoice.get("parent") or {}).get(
        "subscription_details") or {}).get("subscription")
    invoice_charge = invoice.get("charge")
    invoice_charge_id = invoice_charge.get("id") if isinstance(invoice_charge, dict) else invoice_charge
    owner = provider_subject(db, "stripe", "subscription", subscription_id)
    if (invoice.get("id") != invoice_id or invoice.get("object") != "invoice"
            or invoice.get("customer") != customer_id or invoice.get("livemode") is not current["livemode"]
            or invoice.get("currency") != "mxn" or invoice_charge_id != charge_id
            or (subscription_id != mapped.stripe_subscription_id and owner != mapped.gym_id)):
        raise ValueError("Refund invoice resource mismatch")
    amount, returned = current.get("amount"), current.get("amount_refunded")
    if (type(amount) is not int or amount <= 0 or type(returned) is not int
            or not 0 <= returned <= amount
            or type(current.get("refunded")) is not bool
            or current["refunded"] != (returned == amount)):
        raise ValueError("Refund amount or currency mismatch")
    payment = db.query(Payment).filter_by(gym_id=mapped.gym_id, stripe_invoice_id=invoice_id).one_or_none()
    if payment is not None:
        if (current.get("payment_intent") and payment.stripe_payment_intent_id
                and current["payment_intent"] != payment.stripe_payment_intent_id):
            raise ValueError("Refund payment identity mismatch")
        _validate_refund_progress(payment, current)
    def refund_funding_invoice(reference):
        actual = invoice if reference == invoice_id else stripe.Invoice.retrieve(reference, expand=["charge"])
        actual_subscription = actual.get("subscription") or ((actual.get("parent") or {}).get(
            "subscription_details") or {}).get("subscription")
        if (actual.get("id") != reference or actual.get("object") != "invoice"
                or actual.get("customer") != customer_id or actual.get("livemode") is not current["livemode"]
                or actual_subscription != mapped.stripe_subscription_id):
            raise ValueError("Refund funding invoice identity mismatch")
        # The independently read Charge is authoritative for its own invoice.
        # A stale embedded snapshot cannot keep a fully refunded period active;
        # an unrelated new renewal keeps its own current funding evidence.
        return dict(actual, charge=current) if reference == invoice_id else actual
    reconcile_subscription(db, mapped.stripe_subscription_id, fetch_invoice=refund_funding_invoice)
    if payment is not None:
        _observe_payment_refund(payment, current)
    db.flush()
    return "refund:reconciled"


def _bind_customer_purchase(db: Session, customer_id: str) -> None:
    """Resolve signed provider callbacks through the minimal purchase plane.

    Customer alone never grants rights: exactly one persisted subject must own
    that provider customer; the reconciler subsequently validates subscription,
    customer, paid invoice and current unrefunded charge. Legacy unbound data
    remains pending reconciliation rather than using an unscoped table scan.
    """
    if not isinstance(customer_id, str) or not customer_id:
        raise ValueError("Provider customer identity missing")
    linked = provider_subject(db, "stripe", "customer", customer_id)
    if linked is not None:
        bind_verified_subject(db, linked)
        return
    owners = db.query(PurchaseIntent.subject_id).filter_by(provider="stripe", provider_customer_id=customer_id).distinct().all()
    if len(owners) != 1:
        raise ValueError("Provider customer requires purchase reconciliation")
    bind_verified_subject(db, owners[0][0])


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
        "provider": sub.provider,
        "currency": "MXN",
        "precio_centavos": price_in_cents(sub.plan) if sub.plan in PLANES_LICENCIA and PLANES_LICENCIA[sub.plan].get("precio_mxn") else 0,
        "period": "month",
        "max_clientes": sub.max_clientes,
        "current_period_start": int((sub.current_period_start.replace(tzinfo=timezone.utc) if sub.current_period_start.tzinfo is None else sub.current_period_start).timestamp()) if sub.current_period_start else None,
        "current_period_end": period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "stripe_customer_id": sub.stripe_customer_id,
    }


def _history_utc(value):
    if value is None:
        return None
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return aware.astimezone(timezone.utc).isoformat()


def get_payment_history(db: Session, gym_id: str, limit: int = 20) -> list[dict]:
    """Historial de pagos del gym."""
    rows = db.query(Payment).filter(
        Payment.gym_id == gym_id
    ).order_by(Payment.created_at.desc()).limit(limit).all()
    return [
        {
            "id": p.id,
            "amount_cents": p.amount_cents,
            "refund_amount_cents": p.refund_amount_cents,
            "net_amount_cents": p.amount_cents - p.refund_amount_cents if p.refund_amount_cents is not None else None,
            "refund_observed_at": _history_utc(p.refund_observed_at),
            "currency": p.currency,
            "status": p.status,
            "plan": p.plan,
            "created_at": _history_utc(p.created_at),
            "stripe_invoice_id": p.stripe_invoice_id,
        }
        for p in rows
    ]
