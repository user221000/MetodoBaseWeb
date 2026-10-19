"""
web/routes/usuario.py — Routes for individual users (tipo='usuario').

Individual users are their own "gym" — they have a single Cliente record
where gym_id = user.id, and they generate plans for themselves.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from web.auth_deps import get_usuario_actual
from web.database.engine import get_db
from web.database.models import Cliente, PlanGenerado, UserSubscription, Subscription
from web.profile_schemas import NutritionProfileUpdate

try:
    from src.alimentos_base import ALIMENTOS_BASE as _ALIMENTOS_BASE
except Exception:
    _ALIMENTOS_BASE = {}

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Usuario Individual"])


# ── Schemas ───────────────────────────────────────────────────────────────

class PerfilUpdate(NutritionProfileUpdate):
    """Shared, bounded nutrition fields; no identity or billing mass assignment."""


# ── Helpers ───────────────────────────────────────────────────────────────

def _require_usuario(user: dict):
    """Preserve a member's personal space, including legacy gym-type members."""
    if user.get("tipo") != "usuario" and not user.get("team_gym_id"):
        raise HTTPException(403, "Esta ruta es solo para usuarios individuales.")
    return user


def _get_or_create_self_cliente(db: Session, user: dict) -> Cliente:
    """
    Get or create the user's own Cliente record.
    For individual users, gym_id = user.id (they are their own gym).
    """
    user_id = user["id"]
    cliente = db.query(Cliente).filter(
        Cliente.gym_id == user_id,
    ).first()

    if not cliente:
        cliente = Cliente(
            gym_id=user_id,
            nombre=f"{user.get('nombre', '')} {user.get('apellido', '')}".strip() or "Mi Perfil",
            email=user.get("email"),
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    return cliente


# ── GET /usuario/perfil ──────────────────────────────────────────────────

@router.get("/usuario/perfil")
async def get_perfil(
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Returns the individual user's profile (body data)."""
    _require_usuario(usuario)
    cliente = _get_or_create_self_cliente(db, usuario)

    excluidos_raw = cliente.alimentos_excluidos
    try:
        excluidos = json.loads(excluidos_raw) if excluidos_raw else []
    except (json.JSONDecodeError, TypeError):
        excluidos = []

    return {
        "nombre": usuario.get("nombre", ""),
        "apellido": usuario.get("apellido", ""),
        "email": usuario.get("email", ""),
        "edad": cliente.edad,
        "peso_kg": cliente.peso_kg,
        "estatura_cm": cliente.estatura_cm,
        "sexo": cliente.sexo,
        "grasa_corporal_pct": cliente.grasa_corporal_pct,
        "objetivo": cliente.objetivo,
        "nivel_actividad": cliente.nivel_actividad,
        "notas": cliente.notas,
        "alimentos_excluidos": excluidos,
    }


# ── PUT /usuario/perfil ─────────────────────────────────────────────────

@router.put("/usuario/perfil")
async def update_perfil(
    data: PerfilUpdate,
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Updates the individual user's body data."""
    _require_usuario(usuario)
    cliente = _get_or_create_self_cliente(db, usuario)

    if data.edad is not None:
        cliente.edad = data.edad
    if data.peso_kg is not None:
        cliente.peso_kg = data.peso_kg
    if data.estatura_cm is not None:
        cliente.estatura_cm = data.estatura_cm
    if data.sexo is not None:
        cliente.sexo = data.sexo
    if data.grasa_corporal_pct is not None:
        cliente.grasa_corporal_pct = data.grasa_corporal_pct
    if data.objetivo is not None:
        cliente.objetivo = data.objetivo
    if data.nivel_actividad is not None:
        cliente.nivel_actividad = data.nivel_actividad
    if data.notas is not None:
        cliente.notas = data.notas
    if data.alimentos_excluidos is not None:
        cliente.alimentos_excluidos = json.dumps(data.alimentos_excluidos)

    db.commit()
    return {"message": "Perfil actualizado correctamente"}


# ── GET /usuario/catalogo-alimentos ──────────────────────────────────────

@router.get("/usuario/catalogo-alimentos")
async def get_catalogo_alimentos(
    usuario=Depends(get_usuario_actual),
):
    """Returns all available foods grouped by category for exclusion UI."""
    _require_usuario(usuario)
    from config.catalogo_alimentos import CATALOGO_POR_TIPO
    return {
        cat: sorted(items)
        for cat, items in CATALOGO_POR_TIPO.items()
    }


# ── GET /usuario/mi-plan ─────────────────────────────────────────────────

@router.get("/usuario/mi-plan")
async def get_mi_plan(
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Returns the user's latest generated plan."""
    _require_usuario(usuario)
    user_id = usuario["id"]

    cliente = db.query(Cliente).filter(Cliente.gym_id == user_id).first()
    if not cliente:
        return {"plan": None, "meta": {}, "tiene_pdf": False, "plan_id": None, "pdf_url": None}

    from web.services.generation_quota import individual_plan_results_query
    plan_record = (
        individual_plan_results_query(db, user_id)
        .filter(PlanGenerado.id_cliente == cliente.id_cliente)
        .order_by(PlanGenerado.fecha_generacion.desc(), PlanGenerado.id.desc())
        .first()
    )

    if not plan_record:
        return {"plan": None, "meta": {}, "tiene_pdf": False, "plan_id": None, "pdf_url": None}
    return _individual_plan_response(plan_record)


def _load_plan_json(plan_record: "PlanGenerado") -> dict:
    """Load plan JSON: DB column first, then companion file fallback."""
    # 1. Try DB column (persists across container restarts)
    try:
        col_value = plan_record.plan_json
        if col_value:
            return json.loads(col_value)
    except Exception:
        pass
    # 2. Fall back to companion file next to PDF
    if not plan_record.ruta_pdf:
        return {}
    json_path = plan_record.ruta_pdf.rsplit(".", 1)[0] + ".json"
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _enrich_plan_macros(plan_data: dict) -> dict:
    """Back-fill 'macros' on plan options that were saved before the macros fix.

    Plans saved before commit a27d285 only contain alimento/gramos/equivalencia.
    This function calculates macros on-the-fly from ALIMENTOS_BASE so the
    frontend calorie tracker works for all plans, not just newly generated ones.
    """
    if not isinstance(plan_data, dict):
        return plan_data

    ALIMENTOS_BASE = _ALIMENTOS_BASE
    if not ALIMENTOS_BASE:
        return plan_data

    _macro_groups = ("proteinas", "carbohidratos", "grasas")
    _meals = ("desayuno", "almuerzo", "comida", "cena")

    for meal_key in _meals:
        meal = plan_data.get(meal_key)
        if not isinstance(meal, dict):
            continue
        for group_key in _macro_groups:
            group = meal.get(group_key)
            if not isinstance(group, dict):
                continue
            for op in group.get("opciones", []):
                if op.get("macros"):
                    continue
                alimento = op.get("alimento", "")
                gramos = float(op.get("gramos", 0))
                if alimento in ALIMENTOS_BASE and gramos > 0:
                    datos = ALIMENTOS_BASE[alimento]
                    f = gramos / 100.0
                    op["macros"] = {
                        "proteina": round(datos.get("proteina", 0) * f, 1),
                        "carbs":    round(datos.get("carbs", 0) * f, 1),
                        "grasa":    round(datos.get("grasa", 0) * f, 1),
                        "kcal":     round(datos.get("kcal", 0) * f),
                    }
        # Also enrich vegetales
        for veg in meal.get("vegetales", []):
            if veg.get("macros"):
                continue
            alimento = veg.get("alimento", "")
            gramos = float(veg.get("gramos", 0))
            if alimento in ALIMENTOS_BASE and gramos > 0:
                datos = ALIMENTOS_BASE[alimento]
                f = gramos / 100.0
                veg["macros"] = {
                    "proteina": round(datos.get("proteina", 0) * f, 1),
                    "carbs":    round(datos.get("carbs", 0) * f, 1),
                    "grasa":    round(datos.get("grasa", 0) * f, 1),
                    "kcal":     round(datos.get("kcal", 0) * f),
                }
    return plan_data


# ── POST /usuario/generar-plan ───────────────────────────────────────────

@router.post("/usuario/generar-plan")
async def generar_plan_usuario(
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Reserve quota, persist one generated plan and return its exact result.

    Idempotency-Key is scoped to the authenticated individual. Completed retries
    return the same plan; failed generation refunds its credit once. A process
    interruption retains a reservation for explicit reconciliation.
    """
    _require_usuario(usuario)
    user_id = usuario["id"]

    cliente = _get_or_create_self_cliente(db, usuario)

    # Validate required fields
    if not all([cliente.edad, cliente.peso_kg, cliente.estatura_cm, cliente.objetivo]):
        raise HTTPException(
            400,
            "Completa tu perfil antes de generar un plan. "
            "Necesitas: edad, peso, estatura y objetivo."
        )

    if not cliente.nivel_actividad:
        cliente.nivel_actividad = "moderada"
        db.commit()

    from web.services.generation_quota import (
        reserve_generation, finish_generation, compensate_individual_generation_failure, reconciliation_required,
        read_individual_plan_result,
    )
    reservation = reserve_generation(db, user_id, idempotency_key)
    reservation_id = reservation.id
    if reservation.status == "completed":
        record = read_individual_plan_result(db, user_id, reservation.plan_id)
        if record is None:
            raise HTTPException(409, {"code": "generation_result_unavailable", "message": "El resultado requiere revisión. No se consumió otro crédito."})
        return _individual_plan_response(record)

    # Count existing plans for plan_numero
    total_planes = (
        db.query(PlanGenerado)
        .filter(PlanGenerado.id_cliente == cliente.id_cliente, PlanGenerado.gym_id == user_id)
        .count()
    )

    # Generate plan in thread pool (CPU-bound)
    from web.routes.planes import _generar_plan_sync

    try:
        result = await asyncio.to_thread(
            _generar_plan_sync,
            cliente.id_cliente,
            total_planes + 1,
            user_id,
            "opciones",
            individual_reservation_id=reservation_id,
        )
    except ValueError as e:
        compensate_individual_generation_failure(db, reservation_id, user_id)
        raise HTTPException(400, {"code": "generation_unavailable", "message": "No fue posible generar un plan con estos datos y exclusiones. Revisa tu perfil."}) from e
    except Exception as e:
        compensate_individual_generation_failure(db, reservation_id, user_id)
        logger.error("Generation failed class=%s", type(e).__name__)
        raise HTTPException(500, "Error interno al generar el plan. Intenta de nuevo.")
    # Worker commits Plan, object readiness and completed consumption together.
    # Failure to verify that result is never evidence that its credit is free.
    try:
        finish_generation(db, reservation_id, user_id, result.get("plan_id"), success=True)
    except Exception as error:
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.error("Generation verification rollback failed class=%s", type(rollback_error).__name__)
        logger.error("Generation verification failed class=%s", type(error).__name__)
        raise reconciliation_required() from None
    plan_record = read_individual_plan_result(db, user_id, result["plan_id"])
    if plan_record is None:
        raise HTTPException(409, {"code": "generation_result_unavailable", "message": "El resultado requiere revisión. No se consumió otro crédito."})
    return _individual_plan_response(plan_record)


def _individual_plan_response(plan_record: PlanGenerado) -> dict:
    """Build the existing API response from a persisted, authorized result."""
    return {
        "plan_id": plan_record.id,
        "pdf_url": "/api/usuario/descargar-pdf?plan_id=" + str(plan_record.id),
        "plan": _enrich_plan_macros(_load_plan_json(plan_record)),
        "meta": {
            "kcal_objetivo": plan_record.kcal_objetivo if plan_record else 0,
            "kcal_real": plan_record.kcal_real if plan_record else 0,
            "proteina_g": plan_record.proteina_g if plan_record else 0,
            "carbs_g": plan_record.carbs_g if plan_record else 0,
            "grasa_g": plan_record.grasa_g if plan_record else 0,
            "tmb": plan_record.tmb if plan_record else 0,
            "objetivo": plan_record.objetivo if plan_record else "",
            "fecha": plan_record.fecha_generacion.isoformat() if plan_record and plan_record.fecha_generacion else None,
        },
        "tiene_pdf": bool(plan_record.pdf_object_id or (plan_record.ruta_pdf and os.path.isfile(plan_record.ruta_pdf))),
    }


# ── GET /usuario/descargar-pdf ───────────────────────────────────────────

@router.get("/usuario/descargar-pdf")
async def descargar_pdf_usuario(
    plan_id: Optional[int] = Query(default=None, gt=0, le=2147483647),
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Downloads the user's most recent (or specific) plan PDF."""
    _require_usuario(usuario)
    user_id = usuario["id"]

    cliente = db.query(Cliente).filter(Cliente.gym_id == user_id).first()
    if not cliente:
        raise HTTPException(404, "No tienes planes generados.")

    query = db.query(PlanGenerado).filter(
        PlanGenerado.id_cliente == cliente.id_cliente,
        PlanGenerado.gym_id == user_id,
    )

    if plan_id is not None:
        plan_record = query.filter(PlanGenerado.id == plan_id).first()
    else:
        plan_record = query.order_by(PlanGenerado.fecha_generacion.desc()).first()

    if not plan_record:
        raise HTTPException(404, "No hay PDF disponible.")
    from web.services.plan_documents import read_plan_pdf
    return Response(read_plan_pdf(db, user_id, plan_record.id), media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="mi_plan_nutricional.pdf"',
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
    })


# ── GET /usuario/historial ──────────────────────────────────────────────

@router.get("/usuario/historial")
async def historial_planes(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Bounded, live keyset pages for the same authorized personal profile."""
    from sqlalchemy import and_, or_
    from web.services.generation_quota import individual_plan_results_query
    from web.services.personal_history_cursor import decode_position, encode_position
    from web.settings import get_settings

    _require_usuario(usuario)
    user_id = usuario["id"]
    response.headers.update({"Cache-Control":"no-store", "Referrer-Policy":"no-referrer"})

    cliente = db.query(Cliente).filter(Cliente.gym_id == user_id).first()
    position = None
    if cursor is not None:
        try:
            if cliente is None:
                raise ValueError('Missing personal profile')
            position = decode_position(cursor, secret=get_settings().SECRET_KEY,
                subject=user_id, profile=cliente.id_cliente)
        except ValueError:
            raise HTTPException(422, {"code":"history_cursor_invalid",
                "message":"No se pudo continuar el historial. Vuelve a consultar desde el inicio."},
                headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer"}) from None
    if not cliente:
        return {"planes": [], "next_cursor": None}

    query = individual_plan_results_query(db, user_id).filter(PlanGenerado.id_cliente == cliente.id_cliente)
    if position is not None:
        stamp, identity = position
        query = query.filter(and_(PlanGenerado.fecha_generacion.is_(None), PlanGenerado.id < identity)
            if stamp is None else or_(PlanGenerado.fecha_generacion < stamp,
                and_(PlanGenerado.fecha_generacion == stamp, PlanGenerado.id < identity),
                PlanGenerado.fecha_generacion.is_(None)))
    # Fetch summary columns only; private plan JSON and paths are never loaded for every row.
    rows = query.with_entities(PlanGenerado.id, PlanGenerado.fecha_generacion,
        PlanGenerado.kcal_objetivo, PlanGenerado.proteina_g, PlanGenerado.carbs_g,
        PlanGenerado.grasa_g, PlanGenerado.tipo_plan, PlanGenerado.pdf_object_id, PlanGenerado.ruta_pdf
    ).order_by(PlanGenerado.fecha_generacion.desc().nulls_last(), PlanGenerado.id.desc()).limit(limit + 1).all()
    planes = rows[:limit]
    next_cursor = encode_position(planes[-1].fecha_generacion, planes[-1].id,
        secret=get_settings().SECRET_KEY, subject=user_id, profile=cliente.id_cliente) if len(rows) > limit else None

    return {
        "next_cursor": next_cursor,
        "planes": [
            {
                "id": p.id,
                "fecha": p.fecha_generacion.isoformat() if p.fecha_generacion else None,
                "kcal_objetivo": p.kcal_objetivo,
                "proteina_g": p.proteina_g,
                "carbs_g": p.carbs_g,
                "grasa_g": p.grasa_g,
                "tipo_plan": p.tipo_plan,
                "tiene_pdf": bool(p.pdf_object_id or (p.ruta_pdf and os.path.isfile(p.ruta_pdf))),
            }
            for p in planes
        ]
    }


# ── Subscription helpers ─────────────────────────────────────────────────

from core.plan_catalog import get_individual_plan_catalog

PLANES_USUARIO = {
    name: {"max_planes_mes": info["max_planes_mes"], "precio_mxn": info["precio_centavos"] / 100}
    for name, info in get_individual_plan_catalog().items()
}


def _get_or_create_subscription(db: Session, user_id: str) -> UserSubscription:
    """Resolve canonical B2C rights and Mexico City quota; caller owns commit."""
    from web.services.billing_integrity import get_individual_subscription
    sub = get_individual_subscription(db, user_id)
    return sub


# ── GET /api/usuario/suscripcion ─────────────────────────────────────────

@router.get("/usuario/suscripcion")
async def get_suscripcion(
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Returns the current subscription status for the individual user."""
    _require_usuario(usuario)
    sub = _get_or_create_subscription(db, usuario["id"])
    canonical = db.query(Subscription).filter_by(gym_id=usuario["id"], plan="pro_usuario").first()
    return {
        "plan": sub.plan,
        "planes_usados": sub.planes_usados_mes,
        "max_planes": sub.max_planes_mes,
        "renovacion": sub.mes_actual,
        "status": canonical.status if canonical else sub.status,
        "provider": canonical.provider if canonical else None,
        "currency": "MXN",
        "precio_mxn": PLANES_USUARIO[sub.plan]["precio_mxn"],
        "planes_restantes": max(0, sub.max_planes_mes - sub.planes_usados_mes),
        "period_start": canonical.current_period_start.isoformat() if canonical and canonical.current_period_start else None,
        "period_end": canonical.current_period_end.isoformat() if canonical and canonical.current_period_end else None,
        "cancel_at_period_end": bool(canonical.cancel_at_period_end) if canonical else False,
    }


# ── POST /api/usuario/suscripcion ────────────────────────────────────────

class CambioPlan(BaseModel):
    plan: str

@router.post("/usuario/suscripcion")
async def cambiar_suscripcion(
    body: CambioPlan,
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Reject preference-based upgrades; payment providers own paid rights.

    Cancellation of a paid subscription must also reach the provider's portal,
    so this compatibility endpoint never creates or cancels a recurring charge.
    """
    _require_usuario(usuario)

    if body.plan not in PLANES_USUARIO:
        raise HTTPException(400, f"Plan inválido: {body.plan}")

    raise HTTPException(409, {"code": "payment_required" if body.plan == "pro" else "provider_management_required",
                              "message": "Gestiona tu suscripción mediante el proveedor de pago. El regreso a esta página no confirma un pago."})


# ── User Billing Endpoints ───────────────────────────────────────────────

_ALLOWED_REDIRECT_PREFIXES_U = ("/mi-suscripcion",)


def _validate_redirect_url_u(url: str, field_name: str = "url") -> str:
    url = url.strip()
    if not url.startswith("/"):
        raise HTTPException(400, f"{field_name} must be a relative path starting with /")
    if url.startswith("//") or "://" in url:
        raise HTTPException(400, f"{field_name} contains an invalid URL scheme")
    if not any(url.startswith(p) for p in _ALLOWED_REDIRECT_PREFIXES_U):
        raise HTTPException(400, f"{field_name} must redirect to an allowed path")
    return url


@router.get("/usuario/billing-config")
async def usuario_billing_config(
    usuario=Depends(get_usuario_actual),
):
    """Returns payment configuration for the user subscription page."""
    _require_usuario(usuario)
    from web.settings import get_settings
    settings = get_settings()
    stripe_ready = bool(settings.STRIPE_SECRET_KEY)
    mp_ready = bool(settings.MERCADOPAGO_ACCESS_TOKEN)
    # Validate payment link URL before exposing
    payment_link = settings.STRIPE_PAYMENT_LINK_PRO_USUARIO
    if payment_link and not payment_link.startswith("https://buy.stripe.com/"):
        payment_link = ""  # only allow valid Stripe buy links
    return {
        "stripe_configured": stripe_ready,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY if stripe_ready else "",
        "mercadopago_configured": mp_ready,
        # Static Payment Links cannot bind a durable purchase to this account.
        # Keep the compatibility key empty and initiate the supported checkout.
        "payment_link_pro": "",
        "checkout_supported": stripe_ready,
    }


class UsuarioCheckoutRequest(BaseModel):
    success_url: str = Field("/mi-suscripcion?result=success", max_length=500)
    cancel_url: str = Field("/mi-suscripcion?result=canceled", max_length=500)


@router.post("/usuario/checkout")
async def usuario_checkout(data: UsuarioCheckoutRequest, usuario=Depends(get_usuario_actual),
                           db: Session = Depends(get_db),
                           idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    """Start an account-bound Pro checkout; returning to the page grants no access."""
    _require_usuario(usuario)
    _validate_redirect_url_u(data.success_url, "success_url")
    _validate_redirect_url_u(data.cancel_url, "cancel_url")
    from web.services.stripe_service import create_checkout_session
    try:
        return create_checkout_session(db, usuario["id"], "pro_usuario", usuario["email"],
                                       data.success_url, data.cancel_url, idempotency_key)
    except Exception as error:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("individual_checkout", error, "No fue posible iniciar el pago")) from None


class UsuarioPortalRequest(BaseModel):
    return_url: str = Field("/mi-suscripcion", max_length=500)


@router.post("/usuario/billing-portal")
async def usuario_billing_portal(data: UsuarioPortalRequest, usuario=Depends(get_usuario_actual),
                                 db: Session = Depends(get_db)):
    """Open the provider portal for this individual's own mapped subscription."""
    _require_usuario(usuario)
    _validate_redirect_url_u(data.return_url, "return_url")
    from web.services.stripe_service import create_portal_session
    try:
        return create_portal_session(db, usuario["id"], data.return_url)
    except Exception as error:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("individual_portal", error, "No fue posible abrir la gestión de tu suscripción")) from None


class UsuarioStripeSubscribeRequest(BaseModel):
    plan: str = Field(..., description="pro")
    payment_method_id: str = Field(..., min_length=5, max_length=255, pattern=r"^pm_")


@router.post("/usuario/stripe-subscribe")
async def usuario_stripe_subscribe(
    data: UsuarioStripeSubscribeRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Create Stripe subscription for individual user (Pro plan)."""
    _require_usuario(usuario)
    if data.plan not in PLANES_USUARIO or data.plan == "starter":
        raise HTTPException(400, "Solo puedes suscribirte al plan Pro.")

    from web.services import stripe_service
    try:
        result = stripe_service.create_subscription_with_payment_method(
            db=db,
            gym_id=usuario["id"],
            plan="pro_usuario",
            email=usuario["email"],
            payment_method_id=data.payment_method_id,
            request_key=idempotency_key,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(503, "El servicio de pago no está disponible") from e
    except ValueError as e:
        raise HTTPException(400, "No fue posible iniciar la suscripción con los datos indicados") from e
    except Exception as e:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("individual_subscribe", e, "Error al crear suscripción")) from None


class UsuarioConfirmSubscriptionRequest(BaseModel):
    subscription_id: str = Field(..., min_length=5, max_length=255, pattern=r"^sub_")


@router.post("/usuario/confirm-subscription")
async def usuario_confirm_subscription(
    data: UsuarioConfirmSubscriptionRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    """Confirm Stripe subscription after card payment."""
    _require_usuario(usuario)
    from web.services import stripe_service
    try:
        result = stripe_service.confirm_subscription(db, usuario["id"], data.subscription_id)
        return result
    except RuntimeError as e:
        raise HTTPException(503, "El servicio de pago no está disponible") from e
    except ValueError as e:
        raise HTTPException(400, "No fue posible confirmar la suscripción indicada") from e
    except Exception as e:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("individual_confirm", e, "Error al confirmar suscripción")) from None


class UsuarioMPPreferenceRequest(BaseModel):
    plan: str = Field(..., description="pro")
    success_url: str = Field("/mi-suscripcion?result=success", max_length=500)
    cancel_url: str = Field("/mi-suscripcion?result=canceled", max_length=500)


@router.post("/usuario/mp-preference")
async def usuario_mp_preference(
    data: UsuarioMPPreferenceRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Create MercadoPago preference for individual user Pro plan."""
    _require_usuario(usuario)
    if data.plan not in PLANES_USUARIO or data.plan == "starter":
        raise HTTPException(400, "Solo puedes pagar el plan Pro.")
    _validate_redirect_url_u(data.success_url, "success_url")
    _validate_redirect_url_u(data.cancel_url, "cancel_url")

    from web.settings import get_settings
    settings = get_settings()
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(503, "MercadoPago no configurado")

    from web.services.mercadopago_service import create_preference
    try:
        return create_preference(db, usuario["id"], "pro_usuario", usuario.get("email", ""),
                                 data.success_url, data.cancel_url, idempotency_key)
    except Exception as error:
        from web.services.billing_integrity import public_failure
        raise HTTPException(502, public_failure("individual_mp_preference", error, "Error al crear preferencia de pago")) from None
