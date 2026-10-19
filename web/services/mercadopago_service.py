"""MercadoPago purchase and webhook adapter, shared by web and legacy API.

Official signature components are query data.id, x-request-id and timestamp.
The original body is parsed only after binding its resource id to those signed
components. A five-minute acceptance window is a local replay policy; payment
state is fetched from the provider and applied under an account-row lock.
"""
import calendar
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from web.database.models import PurchaseIntent, Subscription, StripeWebhookEvent, Usuario
from web.services.billing_integrity import prepare_purchase
from web.services.subscription_service import activate_subscription, update_subscription_status, record_payment
from web.database.tenant_context import bind_verified_subject
from web.services.provider_subjects import record_provider_subject
from web.settings import get_settings


def get_sdk():
    """Create the configured provider adapter; ordinary test suites replace it."""
    import mercadopago
    token = get_settings().MERCADOPAGO_ACCESS_TOKEN
    if not token:
        raise RuntimeError("MercadoPago no configurado")
    return mercadopago.SDK(token)


def create_preference(db: Session, subject_id: str, plan: str, email: str,
                      success_url: str, cancel_url: str, request_key: str | None = None) -> dict:
    """Persist purchase identity before creating a recoverable checkout preference.

    Caller authorizes subject and validates relative return paths. Preference
    creation has no entitlement effect. Metadata/reference bind later payment
    evidence to this exact purchase; amounts come from the existing catalog.
    """
    from mercadopago.config import RequestOptions
    sdk = get_sdk()
    intent = prepare_purchase(db, subject_id, "mercadopago", "preference", plan, request_key)
    if intent.provider_reference_id:
        result = sdk.preference().get(intent.provider_reference_id)
    else:
        base = get_settings().BASE_URL.rstrip("/")
        result = sdk.preference().create({
            "items": [{"title": "MetodoBase - " + plan, "quantity": 1,
                       "unit_price": float(Decimal(intent.amount_cents) / 100), "currency_id": "MXN"}],
            "back_urls": {"success": base + success_url, "failure": base + cancel_url, "pending": base + cancel_url},
            "auto_return": "approved", "external_reference": intent.id,
            "payer": {"email": email},
            "metadata": {"purchase_intent_id": intent.id, "gym_id": subject_id, "plan": plan},
        }, RequestOptions(custom_headers={"x-idempotency-key": "purchase_" + intent.id}))
    if result.get("status") not in (200, 201):
        raise RuntimeError("MercadoPago preference unavailable")
    preference = result["response"]
    intent.provider_reference_id = str(preference["id"])
    intent.status = "provider_created"
    db.commit()
    return {"session_id": str(preference["id"]), "redirect_url": preference["init_point"],
            "purchase_intent_id": intent.id}


def verify_notification(request: Request, raw: bytes, *, now: float | None = None) -> tuple[dict, str]:
    """Validate HMAC, resource binding and freshness before any provider/database use."""
    secret = get_settings().MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(503, "MercadoPago webhooks no configurados")
    try:
        parts = {}
        for part in request.headers.get("x-signature", "").split(","):
            key, value = part.strip().split("=", 1)
            if key in parts:
                raise ValueError("duplicate signature component")
            parts[key] = value
        stamp, signature = parts["ts"], parts["v1"]
        timestamp = int(stamp)
        # Providers/SDKs may express their timestamps in seconds or milliseconds.
        epoch = timestamp / 1000 if timestamp > 10**11 else timestamp
        if abs((time.time() if now is None else now) - epoch) > 300:
            raise ValueError("expired signature")
        signed_id = request.query_params.get("data.id", "")
        request_id = request.headers.get("x-request-id", "")
        if not signed_id or not request_id:
            raise ValueError("missing signed components")
        manifest = f"id:{signed_id.lower()};request-id:{request_id};ts:{stamp};"
        expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature mismatch")
        body = json.loads(raw)
        if not isinstance(body, dict) or str((body.get("data") or {}).get("id", "")).lower() != signed_id.lower():
            raise ValueError("signed and processed resource differ")
    except (KeyError, ValueError, TypeError, AttributeError):
        raise HTTPException(401, "Notificación de pago inválida") from None
    # Provider event ids identify retries; the digest keeps untrusted ids bounded.
    event_identity = str(body.get("id") or request_id) + ":" + signed_id + ":" + str(body.get("action", ""))
    return body, "mp:" + hashlib.sha256(event_identity.encode()).hexdigest()


def _next_month(start: datetime) -> datetime:
    year, month = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
    return start.replace(year=year, month=month, day=min(start.day, calendar.monthrange(year, month)[1]))


def reconcile_payment(db: Session, payment_id: str, sdk=None) -> str:
    """Read current MP truth and apply one verified purchase or its reversal.

    Caller commits. Every notification uses provider state, including refunds;
    only the payment currently funding a subscription may revoke that access.
    Legacy payments without an intent remain pending manual reconciliation.
    """
    sdk = sdk or get_sdk()
    response = sdk.payment().get(payment_id)
    if response.get("status") != 200:
        raise RuntimeError("MercadoPago payment unavailable")
    payment = response["response"]
    if str(payment.get("id")) != str(payment_id):
        raise ValueError("Payment resource mismatch")
    metadata = payment.get("metadata") or {}
    reference = metadata.get("purchase_intent_id") or payment.get("external_reference")
    intent = db.query(PurchaseIntent).filter_by(id=reference, provider="mercadopago").first()
    if not intent:
        raise ValueError("Payment requires purchase reconciliation")
    if (payment.get("external_reference") != intent.id or
            str(payment.get("currency_id", "")).lower() != intent.currency or
            Decimal(str(payment.get("transaction_amount", 0))) * 100 != intent.amount_cents):
        raise ValueError("Payment identity or amount mismatch")
    bind_verified_subject(db, intent.subject_id)
    db.query(Usuario).filter_by(id=intent.subject_id).update({Usuario.id: Usuario.id})
    # Fetch again after serializing the subject to prevent a stale fetch waiting
    # behind a newer refund from restoring the old approved state.
    response = sdk.payment().get(payment_id)
    if response.get("status") != 200:
        raise RuntimeError("MercadoPago payment unavailable")
    payment = response["response"]
    if (str(payment.get("id")) != str(payment_id) or
            payment.get("external_reference") != intent.id or
            str(payment.get("currency_id", "")).lower() != intent.currency or
            Decimal(str(payment.get("transaction_amount", 0))) * 100 != intent.amount_cents):
        raise ValueError("Payment identity or amount mismatch")
    record_provider_subject(db, "mercadopago", "payment", str(payment_id), intent.subject_id, intent.id)
    sub = db.query(Subscription).filter_by(gym_id=intent.subject_id).first()
    status = payment.get("status")
    if status == "approved":
        if intent.status == "superseded":
            return "already_processed"
        if intent.status == "confirmed":
            if not sub or sub.provider_payment_id != str(payment_id):
                raise ValueError("Purchase already funded by another payment; reconciliation required")
            return "already_processed"
        approved_at = payment.get("date_approved")
        if not approved_at:
            raise ValueError("Approved payment has no billing date")
        start = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
        if start.tzinfo is None:
            raise ValueError("Payment date has no timezone")
        current_start = sub.current_period_start if sub else None
        if current_start is not None:
            current_start = current_start.replace(tzinfo=timezone.utc) if current_start.tzinfo is None else current_start
        if current_start is not None and start < current_start:
            # Preserve newer funding when an older independently paid purchase
            # is first notified after renewal. Record its money for reconciliation.
            intent.status = "superseded"
            record_payment(db, intent.subject_id, amount_cents=intent.amount_cents, currency=intent.currency,
                           plan=intent.plan, stripe_payment_intent_id="mp_" + str(payment_id), status="succeeded")
            return "superseded"
        sub = activate_subscription(db, intent.subject_id, intent.plan, current_period_start=start,
                                    current_period_end=_next_month(start), provider="mercadopago")
        sub.provider_payment_id = str(payment_id)
        intent.status = "confirmed"
        record_payment(db, intent.subject_id, amount_cents=intent.amount_cents, currency=intent.currency,
                       plan=intent.plan, stripe_payment_intent_id="mp_" + str(payment_id), status="succeeded")
        return "activated"
    if status in {"refunded", "charged_back", "cancelled", "rejected"}:
        if sub and sub.provider == "mercadopago" and sub.provider_payment_id == str(payment_id):
            update_subscription_status(db, sub, "unpaid" if status in {"refunded", "charged_back"} else "canceled")
            intent.status = "reversed"
        return "reversed"
    return "pending"


async def handle_webhook(request: Request) -> dict:
    """Use a durable replay inbox; temporary provider/DB failures return HTTP 503."""
    raw = await request.body()
    body, event_id = verify_notification(request, raw)
    if body.get("type") != "payment":
        return {"status": "ignored"}
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        if db.query(StripeWebhookEvent).filter_by(event_id=event_id).first():
            return {"status": "already_processed"}
        try:
            result = reconcile_payment(db, str(body["data"]["id"]))
            db.add(StripeWebhookEvent(event_id=event_id, event_type="mp.payment", result=result))
            db.commit()
            return {"status": result}
        except ValueError:
            db.rollback()
            raise HTTPException(409, "El pago requiere conciliación antes de activar acceso") from None
        except Exception:
            db.rollback()
            raise HTTPException(503, "No fue posible procesar el pago. Se reintentará.") from None
