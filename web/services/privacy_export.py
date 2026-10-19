"""Read-only, bounded export of the authenticated account's personal space.

This is an application export contract, not a legal retention or erasure policy.
Professional portfolios never become personal data merely through gym_id=self.
"""
import json
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException
from sqlalchemy import Text, case, func, select
from sqlalchemy.orm import Session

from web.database.models import (
    Cliente, ClientProgress, GenerationReservation, PlanGenerado, PurchaseIntent,
    Subscription, Usuario, UserRole, UserSubscription,
)
from web.database.tenant_context import bind_verified_subject

MAX_PAGE_SIZE = 200
MAX_PLAN_JSON_CHARS = 250_000
MAX_TEXT_CHARS = 131_072
MAX_SECTION_BYTES = 131_072
MAX_EXPORT_BYTES = 5 * MAX_SECTION_BYTES + 16_384
_MEALS = ("desayuno", "almuerzo", "comida", "cena")
_ACCOUNT = ("id", "email", "nombre", "apellido", "tipo", "role", "fecha_registro")
_PROFILE = ("id", "id_cliente", "nombre", "telefono", "email", "edad", "sexo",
    "peso_kg", "estatura_cm", "grasa_corporal_pct", "masa_magra_kg", "nivel_actividad",
    "objetivo", "fecha_registro", "ultimo_plan", "total_planes_generados", "activo",
    "deleted_at", "notas", "plantilla_tipo", "alimentos_excluidos", "fecha_suscripcion",
    "fecha_fin_suscripcion")
_PLAN = ("id", "id_cliente", "fecha_generacion", "tmb", "get_total", "kcal_objetivo",
    "kcal_real", "proteina_g", "carbs_g", "grasa_g", "objetivo", "nivel_actividad",
    "deleted_at", "peso_en_momento", "grasa_en_momento", "desviacion_maxima_pct",
    "plantilla_tipo", "tipo_plan")
_PROGRESS = ("id", "id_cliente", "fecha", "peso_kg", "grasa_corporal_pct", "masa_magra_kg", "notas")
_PURCHASE = ("id", "provider", "operation", "plan", "amount_cents", "currency", "status",
    "created_at", "updated_at")
_GENERATION = ("id", "period", "status", "plan_id", "created_at", "updated_at")
_PERSONAL_SUB = ("plan", "max_planes_mes", "planes_usados_mes", "mes_actual", "status",
    "created_at", "updated_at")
_CANONICAL_SUB = ("plan", "status", "provider", "current_period_start", "current_period_end",
    "trial_start", "trial_end", "canceled_at", "ended_at", "cancel_at_period_end",
    "created_at", "updated_at")


def _value(value):
    if isinstance(value, datetime):
        # Existing models store UTC instants in timestamp-without-timezone.
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _record(row, fields):
    return {name: _value(row[name] if isinstance(row, Mapping) else getattr(row, name)) for name in fields}


def _encoded_size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _finish(result):
    if _encoded_size(result) > MAX_EXPORT_BYTES:
        raise HTTPException(413, {"code": "privacy_export_requires_review",
            "message": "La descarga supera el volumen disponible. Solicita una revisión autorizada."})
    return result


def _food(value):
    if not isinstance(value, dict):
        return None
    output = {key: _value(value[key]) for key in ("alimento", "gramos", "equivalencia")
              if key in value and isinstance(value[key], (str, int, float)) and not isinstance(value[key], bool)}
    macros = value.get("macros")
    if isinstance(macros, dict):
        output["macros"] = {key: _value(macros[key]) for key in ("proteina", "carbs", "grasa", "kcal")
                            if isinstance(macros.get(key), (int, float)) and not isinstance(macros[key], bool)}
    return output


def _plan_content(raw, stored_length=None):
    if stored_length is not None and stored_length > MAX_PLAN_JSON_CHARS:
        return None, "oversized_legacy_content"
    if not raw:
        return None, "unavailable_legacy_content"
    if len(raw) > MAX_PLAN_JSON_CHARS:
        return None, "oversized_legacy_content"
    try:
        content = json.loads(raw)
    except (ValueError, TypeError, RecursionError):
        return None, "unavailable_legacy_content"
    if not isinstance(content, dict):
        return None, "unavailable_legacy_content"
    output = {}
    for name in _MEALS:
        meal = content.get(name)
        if not isinstance(meal, dict):
            continue
        result = {key: _value(meal[key]) for key in ("kcal_objetivo", "kcal_real")
                  if isinstance(meal.get(key), (int, float)) and not isinstance(meal[key], bool)}
        if isinstance(meal.get("tipo_plan"), str) and meal["tipo_plan"] in {"opciones", "menu_fijo"}:
            result["tipo_plan"] = meal["tipo_plan"]
        if isinstance(meal.get("alimentos"), dict):
            result["alimentos"] = {food: _value(amount) for food, amount in meal["alimentos"].items()
                if isinstance(food, str) and isinstance(amount, (int, float)) and not isinstance(amount, bool)}
        for group in ("proteinas", "carbohidratos", "grasas"):
            source = meal.get(group)
            if not isinstance(source, dict):
                continue
            result[group] = {}
            target = source.get("cantidad_objetivo")
            if isinstance(target, (int, float)) and not isinstance(target, bool):
                result[group]["cantidad_objetivo"] = _value(target)
            options = source.get("opciones")
            if isinstance(options, list):
                result[group]["opciones"] = [item for value in options if (item := _food(value)) is not None]
        if isinstance(meal.get("vegetales"), list):
            result["vegetales"] = [item for value in meal["vegetales"] if (item := _food(value)) is not None]
        if result:
            output[name] = result
    return (output, "structured_copy") if output else (None, "unavailable_legacy_content")


def _page(db, query, model, fields, limit, after=None, *, plans=False):
    columns = []
    oversized_fields = []
    for name in fields:
        column = getattr(model, name)
        if isinstance(column.type, Text):
            columns.append(case((func.length(column) <= MAX_TEXT_CHARS, column), else_=None).label(name))
            flag = "_oversized_" + name
            columns.append((func.length(column) > MAX_TEXT_CHARS).label(flag))
            oversized_fields.append(flag)
        else:
            columns.append(column)
    if plans:
        columns.extend([
            case((func.length(model.plan_json) <= MAX_PLAN_JSON_CHARS, model.plan_json), else_=None).label("_plan_json"),
            func.length(model.plan_json).label("_plan_length"),
        ])
    query = query.with_only_columns(*columns, maintain_column_froms=True)
    if after is not None:
        query = query.where(model.id > after)
    records = []
    used = 256
    has_more = False
    rows = db.execute(query.order_by(model.id).limit(limit + 1).execution_options(yield_per=1)).mappings()
    try:
        for row in rows:
            if len(records) == limit:
                has_more = True
                break
            if any(row[flag] for flag in oversized_fields):
                raise HTTPException(413, {"code": "privacy_record_requires_review",
                    "message": "Un registro supera el volumen de descarga. Solicita una revisión autorizada para obtenerlo completo."})
            item = _record(row, fields)
            if plans:
                item["structured_plan"], item["content_status"] = _plan_content(row["_plan_json"], row["_plan_length"])
            size = _encoded_size(item) + 1
            if size + used > MAX_SECTION_BYTES:
                if records:
                    has_more = True
                    break
                if plans:
                    item["structured_plan"], item["content_status"] = None, "content_requires_authorized_review"
                    size = _encoded_size(item) + 1
                if size + used > MAX_SECTION_BYTES:
                    raise HTTPException(413, {"code": "privacy_record_requires_review",
                        "message": "Un registro supera el volumen de descarga. Solicita una revisión autorizada para obtenerlo completo."})
            records.append(item)
            used += size
    finally:
        rows.close()
    return {"records": records, "next_after": records[-1]["id"] if has_more else None}


def export_personal_data(db: Session, subject_id: str, *, limit: int = 100, cursors=None):
    """Export one persisted authenticated subject; callers cannot select a gym.

    The caller supplies subject_id exclusively from get_usuario_actual. Each
    collection has a stable keyset cursor and explicit next_after. Pages are
    live reads, not an immutable multi-request snapshot. No writes or file/network
    access occur, and incomplete legacy plan bodies are explicitly marked.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError("Invalid export page size")
    user = db.execute(select(Usuario).where(Usuario.id == subject_id, Usuario.activo.is_(True),
        Usuario.deleted_at.is_(None)).execution_options(populate_existing=True)).scalar_one_or_none()
    if user is None:
        raise HTTPException(401, {"code": "privacy_identity_unavailable", "message": "Inicia sesión nuevamente."})
    try:
        bind_verified_subject(db, user.id)
    except ValueError:
        raise HTTPException(403, {"code": "privacy_context_mismatch", "message": "Abre tu espacio personal para exportar tus datos."}) from None
    personal = user.role != UserRole.OWNER and (user.tipo == "usuario" or bool(user.team_gym_id))
    cursors = cursors or {}
    result = {
        "format_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": _record(user, _ACCOUNT),
        "scope": {
            "personal_space": personal,
            "professional_membership": bool(user.team_gym_id),
            "consistency": "live_keyset_pages",
            "page_size": limit,
            "max_response_bytes": MAX_EXPORT_BYTES,
            "max_collection_bytes": MAX_SECTION_BYTES,
            "coverage": "account_and_persisted_personal_space",
            "excluded_categories": ["professional_portfolio", "credentials_and_tokens", "provider_resource_identifiers",
                "security_logs_and_metadata", "binary_objects", "browser_local_diary", "unverified_gym_member_links"],
            "legacy_plan_content": "Known nutrition fields only; unavailable or oversized bodies require authorized review.",
            "numeric_encoding": "Historical non-finite numbers are preserved as strings.",
        },
        "profiles": {"records": [], "next_after": None},
        "plans": {"records": [], "next_after": None},
        "measurements": {"records": [], "next_after": None},
        "purchases": {"records": [], "next_after": None},
        "generation_requests": {"records": [], "next_after": None},
        "personal_subscription": None,
        "canonical_subscription": None,
    }
    if not personal:
        return _finish(result)
    own_profiles = select(Cliente.id_cliente).where(Cliente.gym_id == user.id)
    result["profiles"] = _page(db, select(Cliente).where(Cliente.gym_id == user.id), Cliente,
        _PROFILE, limit, cursors.get("profile"))
    result["plans"] = _page(db, select(PlanGenerado).where(PlanGenerado.gym_id == user.id,
        PlanGenerado.id_cliente.in_(own_profiles)), PlanGenerado, _PLAN, limit, cursors.get("plan"), plans=True)
    result["measurements"] = _page(db, select(ClientProgress).where(ClientProgress.gym_id == user.id,
        ClientProgress.id_cliente.in_(own_profiles)), ClientProgress, _PROGRESS, limit, cursors.get("measurement"))
    result["purchases"] = _page(db, select(PurchaseIntent).where(PurchaseIntent.subject_id == user.id,
        PurchaseIntent.plan == "pro_usuario"), PurchaseIntent, _PURCHASE, limit, cursors.get("purchase"))
    result["generation_requests"] = _page(db, select(GenerationReservation).where(GenerationReservation.user_id == user.id),
        GenerationReservation, _GENERATION, limit, cursors.get("generation"))
    linked_ids = [item["plan_id"] for item in result["generation_requests"]["records"] if item["plan_id"] is not None]
    allowed_ids = set(db.execute(select(PlanGenerado.id).where(PlanGenerado.id.in_(linked_ids),
        PlanGenerado.gym_id == user.id, PlanGenerado.id_cliente.in_(own_profiles))).scalars()) if linked_ids else set()
    for item in result["generation_requests"]["records"]:
        if item["plan_id"] is not None and item["plan_id"] not in allowed_ids:
            item["plan_id"] = None
            item["result_reference_status"] = "requires_authorized_review"
    subscription = db.execute(select(UserSubscription).where(UserSubscription.user_id == user.id)).scalar_one_or_none()
    canonical = db.execute(select(Subscription).where(Subscription.gym_id == user.id,
        Subscription.plan == "pro_usuario")).scalar_one_or_none()
    result["personal_subscription"] = _record(subscription, _PERSONAL_SUB) if subscription else None
    result["canonical_subscription"] = _record(canonical, _CANONICAL_SUB) if canonical else None
    return _finish(result)
