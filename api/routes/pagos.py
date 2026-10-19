"""Rutas de pago — integración Stripe y MercadoPago.

Las claves de API se leen de variables de entorno:
  STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
  MERCADOPAGO_ACCESS_TOKEN

Ambos proveedores siguen el mismo flujo:
  1. Frontend solicita sesión/preferencia (requiere autenticación).
  2. Backend crea la sesión con redirect URLs.
  3. El webhook confirma el pago y activa la licencia.

Seguridad: Todos los endpoints de creación de sesión requieren
autenticación para asociar el pago al gym correcto.
"""
import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from config.constantes import PLANES_LICENCIA, ERR_PAGOS_NO_CONFIGURADOS
from config.settings import get_settings
from web.auth_deps import get_usuario_gym
from web.services.resilience import retry_with_backoff, mercadopago_circuit, stripe_circuit
from web.services.subscription_service import activate_subscription, complete_checkout, is_payment_processed

logger = logging.getLogger(__name__)


def _get_mp_sdk():
    """Obtiene SDK de MercadoPago con timeout configurado."""
    import mercadopago
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    sdk = mercadopago.SDK(access_token)

    # Configurar timeouts (MercadoPago SDK usa requests)
    settings = get_settings()
    sdk.request_options.request_timeout = settings.MERCADOPAGO_TIMEOUT
    sdk.request_options.connection_timeout = settings.HTTP_CONNECT_TIMEOUT

    return sdk

router = APIRouter(tags=["Pagos"])

# ── Schemas ───────────────────────────────────────────────────────────────────

_PLANES_VALIDOS = set(PLANES_LICENCIA.keys())


class CrearSesionRequest(BaseModel):
    plan: str = Field(..., description="standard | gym_comercial | clinica")
    email: str = Field(..., min_length=5, max_length=120)
    success_url: str = Field("/checkout/success", max_length=500)
    cancel_url: str = Field("/checkout/cancel", max_length=500)


def _validate_payment_request(req: CrearSesionRequest) -> None:
    """Keep supported paid plans and relative application redirects explicit."""
    if req.plan not in {"standard", "gym_comercial", "clinica"}:
        raise HTTPException(400, "Plan de pago invalido")
    for value in (req.success_url, req.cancel_url):
        if (not value.startswith(("/checkout/", "/dashboard", "/suscripciones", "/configuracion")) or
                value.startswith("//") or "://" in value):
            raise HTTPException(400, "Direccion de regreso invalida")


class SesionResponse(BaseModel):
    session_id: str
    redirect_url: str


# ── Almacén de sesiones persistente en DB ─────────────────────────────────────
# Las sesiones de checkout se persisten en CheckoutSession (web.database.models)
# para sobrevivir reinicios de pods.


# ── Stripe endpoints ─────────────────────────────────────────────────────────

@retry_with_backoff(max_retries=3, circuit=stripe_circuit)
def _stripe_create_session(stripe_key: str, **kwargs) -> dict:
    """Crea sesión de Stripe Checkout (protegida con retry + circuit breaker)."""
    import stripe
    
    settings = get_settings()
    stripe.api_key = stripe_key
    stripe.max_network_retries = 0  # Usamos nuestro circuit breaker
    stripe.default_http_client = stripe.http_client.RequestsClient(
        timeout=settings.STRIPE_TIMEOUT
    )
    
    session = stripe.checkout.Session.create(**kwargs)
    return {"id": session.id, "url": session.url}


@router.post("/pagos/stripe/session", response_model=SesionResponse)
async def crear_sesion_stripe(
    req: CrearSesionRequest,
    usuario: dict = Depends(get_usuario_gym),
):
    """Keep the legacy response while using durable canonical billing."""
    from web.services.permissions import verify_permission
    from web.services.stripe_service import create_checkout_session
    from web.database.engine import SessionLocal
    verify_permission(usuario, "update", "subscription")
    _validate_payment_request(req)
    try:
        with SessionLocal() as db:
            result = create_checkout_session(db, usuario["id"], req.plan, usuario["email"],
                                             req.success_url, req.cancel_url)
            return SesionResponse(session_id=result["session_id"], redirect_url=result["url"])
    except ValueError:
        raise HTTPException(400, "Solicitud de pago invalida") from None
    except Exception:
        raise HTTPException(502, "No fue posible iniciar el pago") from None


@router.post("/pagos/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """
    Recibe webhooks de Stripe para confirmar pagos.
    
    Delega a stripe_service.handle_webhook_event para:
    - Verificación de firma
    - Idempotencia (evita procesar eventos duplicados)
    - Handlers completos de todos los eventos
    """
    from sqlalchemy.orm import Session as SQLASession
    from web.database.engine import get_engine
    from web.services.stripe_service import verify_webhook, handle_webhook_event
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    # Verificar firma y construir evento
    event = verify_webhook(payload, sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Firma de webhook inválida.")
    
    # Procesar con idempotencia
    engine = get_engine()
    with SQLASession(engine) as db:
        result = handle_webhook_event(db, event)
        db.commit()
        logger.info("Webhook procesado: event_type=%s, result=%s", event["type"], result)
    
    return {"status": "ok", "result": result}


# ── MercadoPago endpoints ────────────────────────────────────────────────────

@retry_with_backoff(max_retries=2, circuit=mercadopago_circuit)
def _mp_create_preference(sdk, preference_data: dict) -> dict:
    """Crea preferencia de pago en MercadoPago (protegida con retry + circuit breaker)."""
    return sdk.preference().create(preference_data)


@router.post("/pagos/mp/preference", response_model=SesionResponse)
async def crear_preferencia_mp(
    req: CrearSesionRequest,
    usuario: dict = Depends(get_usuario_gym),
):
    """Legacy API adapter to the same purchase intent and MP verification."""
    from web.services.permissions import verify_permission
    from web.services.mercadopago_service import create_preference
    from web.database.engine import SessionLocal
    verify_permission(usuario, "update", "subscription")
    _validate_payment_request(req)
    try:
        with SessionLocal() as db:
            result = create_preference(db, usuario["id"], req.plan, usuario["email"],
                                       req.success_url, req.cancel_url)
            return SesionResponse(session_id=result["session_id"], redirect_url=result["redirect_url"])
    except ValueError:
        raise HTTPException(400, "Solicitud de pago invalida") from None
    except Exception:
        raise HTTPException(502, "No fue posible iniciar el pago") from None


@router.post("/pagos/mp/webhook", include_in_schema=False)
async def mp_webhook(request: Request):
    """Use the same authenticated, retryable MP webhook as the SaaS runtime."""
    from web.services.mercadopago_service import handle_webhook
    return await handle_webhook(request)
