"""
Validaciones de negocio para alimentos del catálogo.

Reglas:
- Rangos realistas por macro (proteína, carbs, grasa, kcal)
- Coherencia macro → kcal (fórmula Atwater: P*4 + C*4 + G*9)
- Límites máximos razonables
- meal_idx válidos (0-3)
"""
from __future__ import annotations

from typing import List, Tuple

# Tolerancia de coherencia kcal (±15 %)
_TOLERANCIA_KCAL_PCT = 0.15

# Rangos realistas por 100 g de alimento
_RANGOS = {
    "proteina": (0.0, 90.0),
    "carbs":    (0.0, 100.0),
    "grasa":    (0.0, 100.0),
    "kcal":     (0.0, 900.0),
    "limite":   (1.0, 2000.0),
}

_MEAL_IDX_VALIDOS = {0, 1, 2, 3}


def validar_alimento(detalle: dict) -> Tuple[bool, List[str]]:
    """
    Valida un dict de alimento con reglas de negocio.

    Returns:
        (es_valido, lista_de_errores)
    """
    errores: List[str] = []

    nombre = (detalle.get("nombre") or "").strip()
    if not nombre:
        errores.append("El nombre del alimento es obligatorio.")
    elif len(nombre) < 2:
        errores.append("El nombre debe tener al menos 2 caracteres.")
    elif len(nombre) > 100:
        errores.append("El nombre no puede superar 100 caracteres.")

    # --- Macros obligatorios ---
    for campo in ("proteina", "carbs", "grasa", "kcal"):
        valor = detalle.get(campo)
        if valor is None:
            errores.append(f"{campo.title()} es obligatorio.")
            continue
        try:
            v = float(valor)
        except (ValueError, TypeError):
            errores.append(f"{campo.title()} debe ser numérico.")
            continue
        lo, hi = _RANGOS[campo]
        if v < lo or v > hi:
            errores.append(f"{campo.title()} fuera de rango realista ({lo}–{hi} por 100 g).")

    # --- Coherencia macro → kcal (Atwater) ---
    try:
        p = float(detalle.get("proteina", 0))
        c = float(detalle.get("carbs", 0))
        g = float(detalle.get("grasa", 0))
        k = float(detalle.get("kcal", 0))
        kcal_calculada = p * 4 + c * 4 + g * 9
        if k > 0 and kcal_calculada > 0:
            desviacion = abs(k - kcal_calculada) / max(k, kcal_calculada)
            if desviacion > _TOLERANCIA_KCAL_PCT:
                errores.append(
                    f"Kcal ({k:.0f}) no coincide con macros "
                    f"(calculado ≈ {kcal_calculada:.0f}). "
                    f"Desviación {desviacion:.0%} > {_TOLERANCIA_KCAL_PCT:.0%} permitido."
                )
    except (ValueError, TypeError):
        pass  # ya reportado arriba

    # --- Límite opcional ---
    limite = detalle.get("limite")
    if limite is not None:
        try:
            lim_val = float(limite)
            lo, hi = _RANGOS["limite"]
            if lim_val < lo or lim_val > hi:
                errores.append(f"Límite fuera de rango ({lo}–{hi} g).")
        except (ValueError, TypeError):
            errores.append("El límite debe ser numérico o vacío.")

    # --- meal_idx ---
    meal_idx = detalle.get("meal_idx", [])
    if isinstance(meal_idx, list):
        for idx in meal_idx:
            if idx not in _MEAL_IDX_VALIDOS:
                errores.append(
                    f"Meal IDX inválido: {idx}. Valores permitidos: {sorted(_MEAL_IDX_VALIDOS)}."
                )
                break

    # --- Categoría ---
    categoria = (detalle.get("categoria") or "").strip()
    if not categoria:
        errores.append("La categoría es obligatoria.")

    return (len(errores) == 0, errores)
