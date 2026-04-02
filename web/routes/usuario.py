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

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from web.auth_deps import get_usuario_actual
from web.database.engine import get_db
from web.database.models import Cliente, PlanGenerado, UserSubscription

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Usuario Individual"])


# ── Schemas ───────────────────────────────────────────────────────────────

class PerfilUpdate(BaseModel):
    edad: Optional[int] = None
    peso_kg: Optional[float] = None
    estatura_cm: Optional[float] = None
    sexo: Optional[str] = None
    grasa_corporal_pct: Optional[float] = None
    objetivo: Optional[str] = None
    nivel_actividad: Optional[str] = None
    notas: Optional[str] = None
    alimentos_excluidos: Optional[List[str]] = None


# ── Helpers ───────────────────────────────────────────────────────────────

def _require_usuario(user: dict):
    """Ensure the authenticated user is tipo='usuario'."""
    if user.get("tipo") != "usuario":
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

    VALID_OBJETIVOS = {"deficit", "mantenimiento", "superavit"}
    VALID_ACTIVIDADES = {"sedentario", "leve", "moderada", "intensa"}
    VALID_SEXOS = {"M", "F", "Otro"}
    SEXO_MAP = {"masculino": "M", "femenino": "F", "otro": "Otro"}

    # Normalize empty strings to None
    if data.sexo is not None and not data.sexo.strip():
        data.sexo = None
    if data.sexo:
        data.sexo = SEXO_MAP.get(data.sexo.lower(), data.sexo)
    if data.objetivo and data.objetivo not in VALID_OBJETIVOS:
        raise HTTPException(400, f"Objetivo inválido. Opciones: {', '.join(VALID_OBJETIVOS)}")
    if data.nivel_actividad and data.nivel_actividad not in VALID_ACTIVIDADES:
        raise HTTPException(400, f"Nivel de actividad inválido. Opciones: {', '.join(VALID_ACTIVIDADES)}")
    if data.sexo and data.sexo not in VALID_SEXOS:
        raise HTTPException(400, f"Sexo inválido. Opciones: {', '.join(VALID_SEXOS)}")

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
        return {"plan": None, "meta": {}, "tiene_pdf": False}

    plan_record = (
        db.query(PlanGenerado)
        .filter(
            PlanGenerado.id_cliente == cliente.id_cliente,
            PlanGenerado.gym_id == user_id,
        )
        .order_by(PlanGenerado.fecha_generacion.desc())
        .first()
    )

    if not plan_record:
        return {"plan": None, "meta": {}, "tiene_pdf": False}

    # Load serialized plan from PDF directory companion JSON
    plan_data = _load_plan_json(plan_record)
    plan_data = _enrich_plan_macros(plan_data)  # back-fill macros for pre-fix plans

    tiene_pdf = bool(plan_record.ruta_pdf and os.path.isfile(plan_record.ruta_pdf))

    return {
        "plan": plan_data,
        "meta": {
            "kcal_objetivo": plan_record.kcal_objetivo,
            "kcal_real": plan_record.kcal_real,
            "proteina_g": plan_record.proteina_g,
            "carbs_g": plan_record.carbs_g,
            "grasa_g": plan_record.grasa_g,
            "tmb": plan_record.tmb,
            "objetivo": plan_record.objetivo,
            "fecha": plan_record.fecha_generacion.isoformat() if plan_record.fecha_generacion else None,
        },
        "tiene_pdf": tiene_pdf,
    }


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
    try:
        from src.alimentos_base import ALIMENTOS_BASE
    except Exception:
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
):
    """Generates a nutrition plan for the individual user."""
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
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("Error generando plan para usuario %s: %s", user_id, e)
        raise HTTPException(500, "Error interno al generar el plan. Intenta de nuevo.")

    # Save plan JSON companion file AND persist to DB column
    plan_serializado = _enrich_plan_macros(result.get("plan", {}))
    ruta_pdf = result.get("ruta_pdf", "")
    if ruta_pdf:
        json_path = ruta_pdf.rsplit(".", 1)[0] + ".json"
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(plan_serializado, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Could not save plan JSON file: %s", e)

    # Load the just-created plan record
    plan_record = (
        db.query(PlanGenerado)
        .filter(PlanGenerado.id_cliente == cliente.id_cliente, PlanGenerado.gym_id == user_id)
        .order_by(PlanGenerado.fecha_generacion.desc())
        .first()
    )

    # Persist plan JSON to DB so it survives container restarts
    if plan_record and plan_serializado:
        try:
            plan_record.plan_json = json.dumps(plan_serializado, ensure_ascii=False)
            db.commit()
        except Exception as e:
            logger.warning("Could not save plan_json to DB: %s", e)

    tiene_pdf = bool(ruta_pdf and os.path.isfile(ruta_pdf))

    return {
        "plan": plan_serializado,
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
        "tiene_pdf": tiene_pdf,
    }


# ── GET /usuario/descargar-pdf ───────────────────────────────────────────

@router.get("/usuario/descargar-pdf")
async def descargar_pdf_usuario(
    plan_id: Optional[int] = None,
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

    if plan_id:
        plan_record = query.filter(PlanGenerado.id == plan_id).first()
    else:
        plan_record = query.order_by(PlanGenerado.fecha_generacion.desc()).first()

    if not plan_record or not plan_record.ruta_pdf:
        raise HTTPException(404, "No hay PDF disponible.")

    if not os.path.isfile(plan_record.ruta_pdf):
        raise HTTPException(404, "El archivo PDF no se encontró.")

    # Validate path is within expected output directory
    from web.constants import CARPETA_SALIDA
    real_path = os.path.realpath(plan_record.ruta_pdf)
    allowed_dir = os.path.realpath(CARPETA_SALIDA)
    if not real_path.startswith(allowed_dir + os.sep):
        raise HTTPException(403, "Acceso denegado.")

    return FileResponse(
        plan_record.ruta_pdf,
        media_type="application/pdf",
        filename="mi_plan_nutricional.pdf",
    )


# ── GET /usuario/historial ──────────────────────────────────────────────

@router.get("/usuario/historial")
async def historial_planes(
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Returns all generated plans for the individual user."""
    _require_usuario(usuario)
    user_id = usuario["id"]

    cliente = db.query(Cliente).filter(Cliente.gym_id == user_id).first()
    if not cliente:
        return {"planes": []}

    planes = (
        db.query(PlanGenerado)
        .filter(
            PlanGenerado.id_cliente == cliente.id_cliente,
            PlanGenerado.gym_id == user_id,
        )
        .order_by(PlanGenerado.fecha_generacion.desc())
        .all()
    )

    return {
        "planes": [
            {
                "id": p.id,
                "fecha": p.fecha_generacion.isoformat() if p.fecha_generacion else None,
                "kcal_objetivo": p.kcal_objetivo,
                "proteina_g": p.proteina_g,
                "carbs_g": p.carbs_g,
                "grasa_g": p.grasa_g,
                "tipo_plan": p.tipo_plan,
                "tiene_pdf": bool(p.ruta_pdf and os.path.isfile(p.ruta_pdf)),
            }
            for p in planes
        ]
    }


# ── Subscription helpers ─────────────────────────────────────────────────

PLANES_USUARIO = {
    "starter": {"max_planes_mes": 1, "precio_mxn": 0},
    "pro":     {"max_planes_mes": 5, "precio_mxn": 79},
}


def _get_or_create_subscription(db: Session, user_id: str) -> UserSubscription:
    """Get or create user subscription, resetting monthly counter if needed."""
    mes_actual = datetime.now(timezone.utc).strftime("%Y-%m")
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub:
        sub = UserSubscription(
            user_id=user_id,
            plan="starter",
            max_planes_mes=1,
            planes_usados_mes=0,
            mes_actual=mes_actual,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    elif sub.mes_actual != mes_actual:
        sub.planes_usados_mes = 0
        sub.mes_actual = mes_actual
        db.commit()
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
    return {
        "plan": sub.plan,
        "planes_usados": sub.planes_usados_mes,
        "max_planes": sub.max_planes_mes,
        "renovacion": sub.mes_actual,
        "status": sub.status,
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
    """Change the user's subscription plan."""
    _require_usuario(usuario)

    if body.plan not in PLANES_USUARIO:
        raise HTTPException(400, f"Plan inválido: {body.plan}")

    sub = _get_or_create_subscription(db, usuario["id"])
    plan_info = PLANES_USUARIO[body.plan]
    sub.plan = body.plan
    sub.max_planes_mes = plan_info["max_planes_mes"]
    sub.status = "active"
    db.commit()

    logger.info(
        "[SUSCRIPCION] user=%s cambió a plan=%s",
        usuario["id"], body.plan,
    )

    return {
        "ok": True,
        "plan": sub.plan,
        "max_planes": sub.max_planes_mes,
        "planes_usados": sub.planes_usados_mes,
    }


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
    return {
        "stripe_configured": stripe_ready,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY if stripe_ready else "",
        "mercadopago_configured": mp_ready,
    }


class UsuarioStripeSubscribeRequest(BaseModel):
    plan: str = Field(..., description="pro")
    payment_method_id: str = Field(..., min_length=5, max_length=255, pattern=r"^pm_")


@router.post("/usuario/stripe-subscribe")
async def usuario_stripe_subscribe(
    data: UsuarioStripeSubscribeRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
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
        )
        # Also activate the user subscription record
        sub = _get_or_create_subscription(db, usuario["id"])
        sub.plan = "pro"
        sub.max_planes_mes = PLANES_USUARIO["pro"]["max_planes_mes"]
        sub.status = "active"
        db.commit()
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("Stripe subscribe error (usuario): %s", e, exc_info=True)
        raise HTTPException(502, "Error al crear suscripción")


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
        # Activate user subscription
        sub = _get_or_create_subscription(db, usuario["id"])
        sub.plan = "pro"
        sub.max_planes_mes = PLANES_USUARIO["pro"]["max_planes_mes"]
        sub.status = "active"
        db.commit()
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("Confirm subscription error (usuario): %s", e, exc_info=True)
        raise HTTPException(502, "Error al confirmar suscripción")


class UsuarioMPPreferenceRequest(BaseModel):
    plan: str = Field(..., description="pro")
    success_url: str = Field("/mi-suscripcion?result=success", max_length=500)
    cancel_url: str = Field("/mi-suscripcion?result=canceled", max_length=500)


@router.post("/usuario/mp-preference")
async def usuario_mp_preference(
    data: UsuarioMPPreferenceRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
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

    try:
        import mercadopago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        base_url = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost:8000')}"
        preference_data = {
            "items": [{
                "title": "Método Base — Plan Pro",
                "quantity": 1,
                "unit_price": PLANES_USUARIO["pro"]["precio_mxn"],
                "currency_id": "MXN",
            }],
            "back_urls": {
                "success": base_url + data.success_url,
                "failure": base_url + data.cancel_url,
                "pending": base_url + data.cancel_url,
            },
            "auto_return": "approved",
            "external_reference": f"usuario_{usuario['id']}_pro",
            "payer": {"email": usuario.get("email", "")},
        }
        result = sdk.preference().create(preference_data)
        if result["status"] == 201:
            return {"redirect_url": result["response"]["init_point"]}
        raise HTTPException(502, "No se pudo crear la preferencia de pago")
    except ImportError:
        raise HTTPException(503, "SDK de MercadoPago no instalado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("MP preference error (usuario): %s", e, exc_info=True)
        raise HTTPException(502, "Error al crear preferencia de pago")
