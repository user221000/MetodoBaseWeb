"""Shared HTTP profile contract, with no privileged or tenant fields.

Optional fields permit progressive onboarding. A partial update only applies
submitted fields; complete generation still requires the full engine profile.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from core.nutrition_validation import (
    normalize_activity, normalize_objective, normalize_sex, validate_measurement,
)


class NutritionValidationMixin(BaseModel):
    """Apply the same finite/range and enum rules to create/update/profile DTOs."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    restricciones_nutricionales: dict | None = None

    @field_validator("restricciones_nutricionales", mode="before")
    @classmethod
    def validate_declared_restrictions(cls, value):
        """Validate explicit user declarations, without a clinical approval flag."""
        if value is None:
            return None
        from core.nutrition_restrictions import NutritionRestrictions
        from src.alimentos_base import ALIMENTOS_BASE

        return NutritionRestrictions.from_declaration(value, ALIMENTOS_BASE).declaration_payload()

    @field_validator("edad", "peso_kg", "estatura_cm", "grasa_corporal_pct", check_fields=False)
    @classmethod
    def validate_measurements(cls, value, info: ValidationInfo):
        return validate_measurement(info.field_name, value)

    @field_validator("nivel_actividad", mode="before", check_fields=False)
    @classmethod
    def validate_activity(cls, value):
        return normalize_activity(value)

    @field_validator("objetivo", mode="before", check_fields=False)
    @classmethod
    def validate_objective(cls, value):
        return normalize_objective(value)

    @field_validator("sexo", mode="before", check_fields=False)
    @classmethod
    def validate_sex(cls, value):
        return normalize_sex(value)

    @field_validator("alimentos_excluidos", check_fields=False)
    @classmethod
    def validate_exclusions(cls, value):
        """Reject unknown food IDs, keeping safety rules independent of billing."""
        if value is None:
            return None
        from src.alimentos_base import ALIMENTOS_BASE
        if len(value) > 250 or any(food not in ALIMENTOS_BASE for food in value):
            raise ValueError("Selecciona alimentos del catálogo disponible")
        return list(dict.fromkeys(value))


class NutritionProfileUpdate(NutritionValidationMixin):
    """Partial personal profile, in years/kg/cm/percent; no clinical promises."""

    edad: int | None = None
    peso_kg: float | None = None
    estatura_cm: float | None = None
    sexo: str | None = None
    grasa_corporal_pct: float | None = None
    objetivo: str | None = None
    nivel_actividad: str | None = None
    notas: str | None = Field(None, max_length=500)
    alimentos_excluidos: list[str] | None = None
