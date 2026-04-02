"""
web/routes/billing.py — Rutas de facturación y suscripción.

Endpoints Stripe:
  POST /billing/checkout        → Crea sesión Stripe Checkout
  POST /billing/portal          → Abre portal de gestión Stripe
  GET  /billing/subscription    → Estado de suscripción actual
  GET  /billing/payments        → Historial de pagos
  POST /billing/webhook         → Webhook de Stripe (sin auth)

Endpoints MercadoPago:
  POST /billing/mp/preference   → Crea preferencia de pago MP
  POST /billing/mp/webhook      → Webhook de MercadoPago (sin auth)
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from web.constants import PLANES_LICENCIA
from web.settings import get_settings
from web.auth_deps import get_usuario_actual
from web.database.engine import get_db
from web.services import stripe_service
from web.services.permissions import verify_permission
from web.services.subscription_service import (
    activate_subscription,
    complete_checkout,
    is_payment_processed,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Billing"])
_STRIPE_PAYMENT_LINK_PREFIXES = (
    "https://buy.stripe.com/",
    "https://checkout.stripe.com/",
)


# ── URL validation (prevent open redirect) ────────────────────────────────────

_ALLOWED_REDIRECT_PREFIXES = ("/dashboard", "/suscripciones", "/configuracion")


def _validate_redirect_url(url: str, field_name: str = "url") -> str:
    """Ensure redirect URL is a safe relative path (no protocol, no //host)."""
    url = url.strip()
    if not url.startswith("/"):
        raise HTTPException(400, f"{field_name} must be a relative path starting with /")
    if url.startswith("//") or "://" in url:
        raise HTTPException(400, f"{field_name} contains an invalid URL scheme")
    if not any(url.startswith(p) for p in _ALLOWED_REDIRECT_PREFIXES):
        raise HTTPException(400, f"{field_name} must redirect to an allowed application path")
    return url


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str = Field(..., description="standard | gym_comercial | clinica")
    success_url: str = Field("/dashboard?subscription=success", max_length=500)
    cancel_url: str = Field("/dashboard?subscription=canceled", max_length=500)


class StripeSubscribeRequest(BaseModel):
    plan: str = Field(..., description="standard | gym_comercial | clinica")
    payment_method_id: str = Field(..., min_length=5, max_length=255, pattern=r"^pm_")


class ConfirmSubscriptionRequest(BaseModel):
    subscription_id: str = Field(..., min_length=5, max_length=255, pattern=r"^sub_")


class PortalRequest(BaseModel):
    return_url: str = Field("/dashboard", max_length=500)


# ── Endpoints con autenticación ───────────────────────────────────────────────

@router.get("/billing/config", summary="Estado de configuración de pagos")
def billing_config(
    usuario: dict = Depends(get_usuario_actual),
):
    """Retorna qué métodos de pago están configurados."""
    verify_permission(usuario, "read", "billing")
    settings = get_settings()
    stripe_ready = bool(settings.STRIPE_SECRET_KEY)
    mp_ready = bool(settings.MERCADOPAGO_ACCESS_TOKEN)
    plans = {}
    for key, info in PLANES_LICENCIA.items():
        if key == "free":
            continue
        plans[key] = {
            "precio_mxn": info["precio_mxn"],
            "max_clientes": info["max_clientes"] or None,
            "max_sesiones": info.get("max_sesiones", 1) or None,
            "max_planes_diarios": info.get("max_planes_diarios", 1) or None,
            "multi_usuario": info.get("multi_usuario", False),
            "preferencias_alimentos": info.get("preferencias_alimentos", False),
            "gestion_suscripciones": info.get("gestion_suscripciones", False),
            "progresion_clientes": info.get("progresion_clientes", False),
            "descripcion": info.get("descripcion", ""),
            "features": info.get("features", []),
        }
    def _clean_link(url: str) -> str:
        clean = (url or "").strip().strip('"').strip("'").strip()
        return clean if any(clean.startswith(p) for p in _STRIPE_PAYMENT_LINK_PREFIXES) else ""

    # Lee directamente de os.getenv para evitar stale lru_cache de Settings
    link_standard     = _clean_link(os.getenv("STRIPE_PAYMENT_LINK_STANDARD", ""))
    link_gym_comercial = _clean_link(os.getenv("STRIPE_PAYMENT_LINK_GYM_COMERCIAL", ""))
    link_clinica      = _clean_link(os.getenv("STRIPE_PAYMENT_LINK_CLINICA", ""))
    logger.info(
        "[billing/config] payment_links resolved — standard=%s gym_comercial=%s clinica=%s",
        bool(link_standard), bool(link_gym_comercial), bool(link_clinica),
    )

    return {
        "stripe_configured": stripe_ready,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "mercadopago_configured": mp_ready,
        "plans": plans,
        "payment_links": {
            "standard":      link_standard,
            "gym_comercial": link_gym_comercial,
            "clinica":       link_clinica,
        },
    }


@router.post("/billing/checkout", summary="Crear sesión de Stripe Checkout")
def crear_checkout(
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "subscription")
    _require_paid_plan(data.plan)
    _validate_redirect_url(data.success_url, "success_url")
    _validate_redirect_url(data.cancel_url, "cancel_url")
    email = (usuario.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(400, "Email de usuario no configurado. Actualiza tu perfil.")
    try:
        result = stripe_service.create_checkout_session(
            db=db,
            gym_id=usuario["id"],
            plan=data.plan,
            email=email,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        from web.settings import get_settings as _gs
        logger.error(
            "Error checkout: %s", e,
            exc_info=not _gs().is_production
        )
        raise HTTPException(502, "Error al crear sesión de pago")


@router.post("/billing/stripe/subscribe", summary="Crear suscripción con tarjeta (Stripe Elements)")
def stripe_subscribe(
    data: StripeSubscribeRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "subscription")
    _require_paid_plan(data.plan)
    try:
        result = stripe_service.create_subscription_with_payment_method(
            db=db,
            gym_id=usuario["id"],
            plan=data.plan,
            email=usuario["email"],
            payment_method_id=data.payment_method_id,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        from web.settings import get_settings as _gs
        logger.error(
            "Stripe subscribe error: %s", e,
            exc_info=not _gs().is_production
        )
        raise HTTPException(502, "Error al crear suscripción")


@router.post("/billing/confirm-subscription", summary="Confirmar suscripción tras pago")
def confirm_subscription(
    data: ConfirmSubscriptionRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    """Verifica con Stripe que el pago se completó y activa la suscripción.
    Llamado por el frontend tras confirmCardPayment exitoso."""
    verify_permission(usuario, "update", "subscription")
    try:
        result = stripe_service.confirm_subscription(db, usuario["id"], data.subscription_id)
        db.commit()
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        db.rollback()
        from web.settings import get_settings as _gs
        logger.error("Confirm subscription error: %s", e, exc_info=not _gs().is_production)
        raise HTTPException(502, "Error al confirmar suscripción")


@router.post("/billing/portal", summary="Abrir portal Stripe")
def abrir_portal(
    data: PortalRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "subscription")
    try:
        result = stripe_service.create_portal_session(
            db=db,
            gym_id=usuario["id"],
            return_url=data.return_url,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/billing/subscription", summary="Estado de suscripción")
def obtener_suscripcion(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "billing")
    sub = stripe_service.get_subscription(db, usuario["id"])
    if not sub:
        return {"status": "none", "plan": None, "message": "Sin suscripción activa"}
    return sub


@router.get("/billing/payments", summary="Historial de pagos")
def historial_pagos(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "invoices")
    return {"payments": stripe_service.get_payment_history(db, usuario["id"])}


# ── Webhook (sin auth — vía firma Stripe) ─────────────────────────────────────

@router.post("/billing/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """Recibe webhooks de Stripe. Verificación por firma, sin JWT."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_service.verify_webhook(payload, sig_header)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception:
        raise HTTPException(400, "Firma de webhook inválida")

    if event is None:
        return {"status": "ignored", "reason": "webhook_secret_not_configured"}

    # Procesar evento con sesión de BD vía pool de conexiones
    from web.database.engine import get_engine, SessionLocal

    db = SessionLocal()
    try:
        result = stripe_service.handle_webhook_event(db, event)
        db.commit()
        logger.info("Webhook processed: type=%s result=%s", event["type"], result)
    except Exception as exc:
        db.rollback()
        from web.settings import get_settings as _gs
        logger.error(
            "Webhook error: %s", exc,
            exc_info=not _gs().is_production
        )
        raise HTTPException(500, "Error procesando webhook")
    finally:
        db.close()

    return {"status": "ok", "result": result}


# ── MercadoPago endpoints ─────────────────────────────────────────────────────

_PAID_PLANS = {"standard", "gym_comercial", "clinica"}


def _require_paid_plan(plan: str) -> None:
    if plan not in _PAID_PLANS:
        raise HTTPException(400, f"Plan inválido: {plan}")


class MPPreferenceRequest(BaseModel):
    plan: str = Field(..., description="standard | gym_comercial | clinica")
    email: Optional[str] = Field(None, min_length=5, max_length=120)
    success_url: str = Field("/dashboard?subscription=success", max_length=500)
    cancel_url: str = Field("/dashboard?subscription=canceled", max_length=500)

    model_config = {"extra": "forbid"}


def _get_mp_sdk():
    """Obtiene SDK de MercadoPago con timeout configurado."""
    import mercadopago
    settings = get_settings()
    access_token = settings.MERCADOPAGO_ACCESS_TOKEN
    sdk = mercadopago.SDK(access_token)
    sdk.request_options.request_timeout = settings.MERCADOPAGO_TIMEOUT
    sdk.request_options.connection_timeout = settings.HTTP_CONNECT_TIMEOUT
    return sdk


@router.post("/billing/mp/preference", summary="Crear preferencia de pago MercadoPago")
def crear_preferencia_mp(
    data: MPPreferenceRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    """Crea una preferencia de pago en MercadoPago. Requiere RBAC."""
    verify_permission(usuario, "update", "subscription")
    _require_paid_plan(data.plan)
    _validate_redirect_url(data.success_url, "success_url")
    _validate_redirect_url(data.cancel_url, "cancel_url")
    gym_id = usuario["id"]
    settings = get_settings()

    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(503, "MercadoPago no configurado")

    email = (data.email or usuario.get("email") or "").strip()
    if len(email) < 5:
        raise HTTPException(400, "Email inválido")

    info = PLANES_LICENCIA[data.plan]

    try:
        from web.services.resilience import retry_with_backoff, mercadopago_circuit

        @retry_with_backoff(max_retries=2, circuit=mercadopago_circuit)
        def _create_pref(sdk, pref_data):
            return sdk.preference().create(pref_data)

        sdk = _get_mp_sdk()
        preference = _create_pref(sdk, {
            "items": [{
                "title": f"Método Base — {data.plan.title()}",
                "quantity": 1,
                "unit_price": info["precio_mxn"],
                "currency_id": "MXN",
            }],
            "payer": {"email": email},
            "back_urls": {
                "success": data.success_url,
                "failure": data.cancel_url,
                "pending": data.cancel_url,
            },
            "auto_return": "approved",
            "metadata": {
                "plan": data.plan,
                "gym_id": gym_id,
            },
        })

        resp = preference["response"]
        pref_id = resp["id"]

        # Persist checkout session
        from web.database.models import CheckoutSession
        checkout = CheckoutSession(
            id=secrets.token_urlsafe(32),
            gym_id=gym_id,
            stripe_session_id=pref_id,
            plan=data.plan,
            email=email,
            status="pending",
        )
        db.add(checkout)
        db.commit()

        return {"session_id": pref_id, "redirect_url": resp["init_point"]}

    except ImportError:
        raise HTTPException(503, "Módulo mercadopago no instalado")
    except Exception as e:
        logger.error("MercadoPago error: %s", e, exc_info=settings.DEBUG)
        raise HTTPException(502, "Error al crear preferencia de pago")


@router.post("/billing/mp/webhook", include_in_schema=False)
async def mp_webhook(request: Request):
    """Webhook de MercadoPago. Verificación por firma, sin JWT.

    Seguridad: verifica firma x-signature HMAC-SHA256 en producción.
    Idempotencia: payment_id duplicado se ignora sin error.
    """
    settings = get_settings()
    raw_body = await request.body()

    # ── Verificar firma ───────────────────────────────────────────────
    if not settings.MERCADOPAGO_WEBHOOK_SECRET:
        logger.warning("MP webhook received but MERCADOPAGO_WEBHOOK_SECRET not set")
        raise HTTPException(503, "MercadoPago webhooks not configured")

    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    parts = dict(
        p.split("=", 1) for p in x_signature.split(",") if "=" in p
    )
    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")

    if ts and v1:
        data_id = request.query_params.get(
            "data.id", request.query_params.get("id", "")
        )
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        expected = hmac.new(
            settings.MERCADOPAGO_WEBHOOK_SECRET.encode(),
            manifest.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(v1, expected):
            logger.warning("MP webhook firma inválida")
            raise HTTPException(401, "Firma inválida")
    else:
        logger.warning("MP webhook sin firma")
        raise HTTPException(401, "Firma requerida")

    body = json.loads(raw_body)
    topic = body.get("type", "")

    if topic != "payment":
        return {"status": "ignored"}

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        return {"status": "no_payment_id"}

    logger.info("MercadoPago notificación payment_id=%s", payment_id)

    try:
        sdk = _get_mp_sdk()
        payment_response = sdk.payment().get(payment_id)

        if payment_response["status"] != 200:
            logger.error("MP: No se pudo obtener pago %s", payment_id)
            return {"status": "error"}

        payment_data = payment_response["response"]
        status = payment_data.get("status")

        if status != "approved":
            logger.info("MP pago %s no aprobado: status=%s", payment_id, status)
            return {"status": "not_approved"}

        metadata = payment_data.get("metadata", {})
        plan = metadata.get("plan", "standard")
        gym_id = metadata.get("gym_id", "")
        email = payment_data.get("payer", {}).get("email", "")

        if not gym_id:
            logger.error("MP pago %s sin gym_id en metadata", payment_id)
            return {"status": "missing_gym_id"}

        # Procesar con sesión de BD vía pool de conexiones
        from web.database.engine import SessionLocal

        db = SessionLocal()
        try:
            # Idempotencia
            if is_payment_processed(db, str(payment_id)):
                logger.info("MP webhook duplicado payment_id=%s", payment_id)
                return {"status": "already_processed"}

            # Completar checkout
            complete_checkout(db, gym_id, plan, email, str(payment_id))

            # Activar suscripción
            activate_subscription(db, gym_id, plan, provider="mercadopago")

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        logger.info("MP pago aprobado: payment_id=%s plan=%s gym=%s", payment_id, plan, gym_id)
        return {"status": "ok"}

    except ImportError:
        logger.error("SDK de MercadoPago no instalado")
        return {"status": "sdk_missing"}
    except Exception as e:
        logger.error("Error procesando webhook MP: %s", e)
        return {"status": "error"}
