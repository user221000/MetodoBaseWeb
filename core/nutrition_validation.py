"""Pure profile normalization shared by HTTP consumers.

Ranges retain the existing product contract; they are input constraints and
do not establish clinical suitability. No persistence or external effects.
"""
from __future__ import annotations

import math

from utils.validadores import RANGO_EDAD, RANGO_ESTATURA, RANGO_GRASA, RANGO_PESO

PROFILE_RANGES = {"edad": RANGO_EDAD, "peso_kg": RANGO_PESO,
    "estatura_cm": RANGO_ESTATURA, "grasa_corporal_pct": RANGO_GRASA}


def validate_measurement(name: str, value: int | float | None) -> int | float | None:
    """Validate years, kg, cm or body-fat percent; reject nonfinite values."""
    if value is None:
        return None
    lower, upper = PROFILE_RANGES[name]
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name} debe estar entre {lower} y {upper}")
    return value


def normalize_activity(value: str | None) -> str | None:
    """Map the legacy personal-portal sedentario label to canonical nula."""
    if value is None:
        return None
    value = value.strip().lower()
    value = {"sedentario": "nula"}.get(value, value)
    if value not in {"nula", "leve", "moderada", "intensa"}:
        raise ValueError("Nivel de actividad inválido")
    return value


def normalize_objective(value: str | None) -> str | None:
    """Normalize the three supported nonclinical energy objectives."""
    if value is None:
        return None
    value = value.strip().lower()
    if value not in {"deficit", "mantenimiento", "superavit"}:
        raise ValueError("Objetivo inválido")
    return value


def normalize_sex(value: str | None) -> str | None:
    """Accept historical labels without deriving medical classifications."""
    if value is None or not value.strip():
        return None
    normalized = {"m": "M", "masculino": "M", "f": "F", "femenino": "F", "otro": "Otro"}.get(value.strip().lower())
    if normalized is None:
        raise ValueError("Sexo debe ser M, F u Otro")
    return normalized
