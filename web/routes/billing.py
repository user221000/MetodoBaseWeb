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

from fastapi import APIRouter, HTTPException, Depends, Request, Header
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
    return {
        "stripe_configured": stripe_ready,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "mercadopago_configured": mp_ready,
        "plans": plans,
        "payment_links": {
            "standard": "",
            "gym_comercial": "",
            "clinica": "",
        },
    }


@router.post("/billing/checkout", summary="Crear sesión de Stripe Checkout")
def crear_checkout(
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
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
            request_key=idempotency_key,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(503, "El servicio de pago no esta disponible") from e
    except ValueError as e:
        raise HTTPException(400, "No fue posible completar la solicitud de pago") from e
    except Exception as e:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("checkout", e, "Error al crear sesión de pago")) from None


@router.post("/billing/stripe/subscribe", summary="Crear suscripción con tarjeta (Stripe Elements)")
def stripe_subscribe(
    data: StripeSubscribeRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
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
            request_key=idempotency_key,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(503, "El servicio de pago no esta disponible") from e
    except ValueError as e:
        raise HTTPException(400, "No fue posible completar la solicitud de pago") from e
    except Exception as e:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("subscribe", e, "Error al crear suscripción")) from None


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
        raise HTTPException(503, "El servicio de pago no esta disponible") from e
    except ValueError as e:
        raise HTTPException(400, "No fue posible completar la solicitud de pago") from e
    except Exception as e:
        db.rollback()
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("confirm", e, "Error al confirmar suscripción")) from None


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
        raise HTTPException(503, "El servicio de pago no esta disponible") from e
    except ValueError as e:
        raise HTTPException(400, "No fue posible completar la solicitud de pago") from e


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
        raise HTTPException(503, "El servicio de pago no esta disponible") from e
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
        from web.services.billing_integrity import public_failure
        raise HTTPException(503, public_failure("stripe_webhook", exc, "Error procesando webhook")) from None
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
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

    from web.services.mercadopago_service import create_preference
    try:
        return create_preference(db, gym_id, data.plan, email, data.success_url, data.cancel_url, idempotency_key)
    except Exception as error:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("mp_preference", error, "Error al crear preferencia de pago")) from None


@router.post("/billing/mp/webhook", include_in_schema=False)
async def mp_webhook(request: Request):
    """Delegate signature, replay, current-state reconciliation and retry status."""
    from web.services.mercadopago_service import handle_webhook
    return await handle_webhook(request)
