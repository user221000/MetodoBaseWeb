"""Bounded profile declarations and the final nutrition publication barrier.

Callers establish the authenticated principal and authorized gym. Queries repeat
client/tenant eligibility. These functions never commit, reserve quota, publish
objects or log declared facts; the caller owns its transaction and compensation.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, NoReturn

from core.nutrition_restrictions import (
    NutritionRestrictionInputError,
    NutritionRestrictions,
    NutritionRestrictionsChanged,
    ProfessionalNutritionReviewRequired,
)
from src.alimentos_base import ALIMENTOS_BASE

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from web.database.models import Cliente

MAX_DECLARATION_BYTES = 16 * 1024
NUTRITION_ERRORS = (NutritionRestrictionInputError, NutritionRestrictionsChanged, ProfessionalNutritionReviewRequired)


def _invalid() -> NoReturn:
    raise NutritionRestrictionInputError("Revisa la declaración de restricciones alimentarias.") from None


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _decode(raw: str) -> object:
    if type(raw) is not str:
        _invalid()
    try:
        if len(raw.encode("utf-8")) > MAX_DECLARATION_BYTES:
            _invalid()
        return json.loads(raw, object_pairs_hook=_closed_object)
    except (ValueError, TypeError, RecursionError, UnicodeError):
        _invalid()


def encode_declaration(value: object) -> str:
    """Validate and canonically encode a full declaration, without exclusions.

    Partial updates must call this only for a non-null submitted object. Null or
    omission never erases an existing declaration. Explicit reset uses a valid
    full object and remains a person's declaration, without clinical clearance.
    """
    if value is None:
        _invalid()
    canonical = NutritionRestrictions.from_declaration(value, ALIMENTOS_BASE).declaration_payload()
    result = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(result.encode("utf-8")) > MAX_DECLARATION_BYTES:
        _invalid()
    return result


def capture_profile(client: Cliente) -> NutritionRestrictions:
    """Read strict persisted facts; corrupt records never become unrestricted."""
    declaration = _decode(client.nutrition_restrictions_json) if client.nutrition_restrictions_json is not None else None
    if client.nutrition_restrictions_json is not None and declaration is None:
        _invalid()
    exclusions = _decode(client.alimentos_excluidos) if client.alimentos_excluidos is not None else []
    return NutritionRestrictions.from_declaration(declaration, ALIMENTOS_BASE, excluded_foods=exclusions)


def require_client_automation(db: Session, gym_id: str, client_id: str) -> NutritionRestrictions:
    """Recheck a live owned client before new quota consumption or worker work."""
    from web.database.models import Cliente

    client = db.query(Cliente).filter(
        Cliente.gym_id == gym_id, Cliente.id_cliente == client_id,
        Cliente.activo.is_(True), Cliente.deleted_at.is_(None),
    ).populate_existing().one_or_none()
    if client is None:
        raise NutritionRestrictionsChanged("El perfil ya no está disponible para esta generación.")
    captured = capture_profile(client)
    captured.require_automated_generation()
    return captured


def lock_current_restrictions(db: Session, gym_id: str, client_id: str, expected: NutritionRestrictions) -> None:
    """Hold a row write lock and compare facts before ready object/plan commit.

    Account locks required by the quota protocol must be obtained first. Any
    concurrent profile update either precedes this comparison or waits for its
    publication transaction. Unknown/missing/corrupt facts cannot be adopted.
    SQLite relies on its writer transaction; real concurrency is verified in PG.
    """
    from web.database.models import Cliente

    connection = db.connection()
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        # SQLite's legacy driver does not begin a transaction for SELECT.
        # Own the writer before the comparison so a profile cannot change
        # between that SELECT and the first ready-object/plan UPDATE.
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    client = db.query(Cliente).filter(
        Cliente.gym_id == gym_id, Cliente.id_cliente == client_id,
        Cliente.activo.is_(True), Cliente.deleted_at.is_(None),
    ).populate_existing().with_for_update().one_or_none()
    if client is None:
        raise NutritionRestrictionsChanged("El perfil cambió. Revisa los datos antes de generar otro plan.")
    expected.require_current(capture_profile(client))


def public_error(error: NutritionRestrictionInputError | NutritionRestrictionsChanged | ProfessionalNutritionReviewRequired) -> tuple[int, dict[str, str]]:
    """Translate only these closed domain failures; never expose health values."""
    code = error.code
    status = 409 if isinstance(error, NutritionRestrictionsChanged) else 422
    message = ("Este perfil requiere revisión profesional. La generación automática no está disponible."
               if code == "nutrition_professional_review_required"
               else "Revisa las restricciones del perfil antes de generar otro plan.")
    return status, {"code": code, "message": message}
