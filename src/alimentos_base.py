"""
Base de alimentos.

Ahora los datos se cargan desde SQLite para permitir edición y persistencia,
manteniendo la misma interfaz pública de dicts.
"""
from __future__ import annotations

import sys
from copy import deepcopy

from core.branding import branding
from src.alimentos_seed_runtime import (
    ALIMENTOS_BASE_SEED,
    CATEGORIAS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED,
    LIMITES_ALIMENTOS_SEED,
)
from src.alimentos_sqlite import cargar_datos, inicializar_db_si_es_necesario
from utils.logger import logger


def _enriquecer_alimentos(foods: dict) -> dict:
    """Attach current-row provenance without replacing stored nutrient amounts."""
    from src.alimentos_catalogo_usda import metadata_by_id

    metadata = metadata_by_id(foods)
    protected = ("proteina", "carbs", "grasa", "kcal", "meal_idx")
    legacy_profile = {"proteina": 25, "carbs": 8, "grasa": 6, "kcal": 400}
    result = {}
    for food_id, current in foods.items():
        # SQLite's persisted contract is these five fields. Rebuild from them
        # so a previously enriched snapshot cannot retain stale attribution.
        row = {key: deepcopy(current[key]) for key in protected if key in current}
        if food_id in metadata:
            row.update({key: value for key, value in metadata[food_id].items() if key not in protected})
        if food_id == "proteina_suero" and all(
                type(row.get(key)) in (int, float) and row[key] == value for key, value in legacy_profile.items()):
            row.update({"auto_generation": False, "provenance_status": "legacy_review_required",
                        "review_reason": "energy_inconsistency", "source": None})
        result[food_id] = row
    return result


def _obtener_excluidos_gym() -> set[str]:
    raw = branding.get("alimentos.excluidos", [])
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def _aplicar_exclusiones_gym() -> None:
    excluidos = _obtener_excluidos_gym()
    if not excluidos:
        return
    for items in CATEGORIAS.values():
        if isinstance(items, list):
            filtrados = [a for a in items if a not in excluidos]
            items.clear()
            items.extend(filtrados)


try:
    inicializar_db_si_es_necesario(
        ALIMENTOS_BASE_SEED,
        CATEGORIAS_SEED,
        LIMITES_ALIMENTOS_SEED,
        EQUIVALENCIAS_PRACTICAS_SEED,
    )
    _datos = cargar_datos()
    ALIMENTOS_BASE = _enriquecer_alimentos(_datos["alimentos_base"])
    LIMITES_ALIMENTOS = _datos["limites_alimentos"]
    EQUIVALENCIAS_PRACTICAS = _datos["equivalencias_practicas"]
    CATEGORIAS = _datos["categorias"]
    _aplicar_exclusiones_gym()
except Exception as exc:  # noqa: BLE001 - retain the bundled-seed fallback for unavailable local storage.
    logger.warning("[ALIMENTOS] Error cargando SQLite: %s. Usando seeds en memoria.", exc)
    ALIMENTOS_BASE = _enriquecer_alimentos(ALIMENTOS_BASE_SEED)
    LIMITES_ALIMENTOS = dict(LIMITES_ALIMENTOS_SEED)
    EQUIVALENCIAS_PRACTICAS = dict(EQUIVALENCIAS_PRACTICAS_SEED)
    CATEGORIAS = deepcopy(CATEGORIAS_SEED)
    _aplicar_exclusiones_gym()


def _reemplazar_dict(destino: dict, fuente: dict) -> None:
    """Reemplaza contenido sin romper referencias externas."""
    destino.clear()
    destino.update(fuente)


def recargar_desde_db() -> bool:
    """Recarga datos desde SQLite y actualiza dicts en memoria."""
    try:
        datos = cargar_datos()
        foods = _enriquecer_alimentos(datos["alimentos_base"])
    except Exception as exc:  # noqa: BLE001 - failed reload must preserve the prior in-memory catalog.
        logger.warning("[ALIMENTOS] Error recargando SQLite: %s", exc)
        return False

    _reemplazar_dict(ALIMENTOS_BASE, foods)
    _reemplazar_dict(LIMITES_ALIMENTOS, datos["limites_alimentos"])
    _reemplazar_dict(EQUIVALENCIAS_PRACTICAS, datos["equivalencias_practicas"])
    _reemplazar_dict(CATEGORIAS, datos["categorias"])
    _aplicar_exclusiones_gym()
    catalog_module = sys.modules.get("config.catalogo_alimentos")
    refresh = getattr(catalog_module, "refrescar_catalogo", None)
    if callable(refresh):
        refresh()
    return True


# ==========================================================================
# REGLAS DE PENALIZACIÓN (Qué NO se puede repetir en el mismo día)
# ==========================================================================

REGLAS_PENALIZACION = {
    'huevo': 1,                    # Max 1x día (huevo + claras = grupo)
    'claras_huevo': 1,             # Max 1x día
    'salmon': 1,                   # Max 1x día (muy graso)
    'carne_magra_res': 1,          # Max 1x día (rojo)
    'pechuga_de_pollo': 2,         # Max 2x día (pollo es versátil)
    'pescado_blanco': 1,           # Max 1x día
    'aceite_de_oliva': 1,          # Max 1x día (grasa concentrada)
}

# ==========================================================================
# ROTACIONES POR COMIDA (Orden de preferencia)
# ==========================================================================

ROTACIONES = {
    'desayuno': {
        'proteina': ['proteina_suero', 'yogurt_griego_light', 'huevo', 'claras_huevo', 'queso_panela'],
        'carbs': ['avena', 'pan_integral', 'tortilla_maiz'],
        'grasa': ['aceite_de_oliva', 'nueces', 'almendras'],
        'verdura': ['brocoli', 'espinaca'],
        'fruta': ['platano', 'manzana', 'papaya', 'naranja', 'mango', 'melon', 'piña'],
    },
    'comida': {
        'proteina': ['pechuga_de_pollo', 'carne_magra_res', 'pescado_blanco', 'salmon'],
        'carbs': ['arroz_blanco', 'arroz_integral', 'papa', 'camote', 'tortilla_maiz'],
        'grasa': ['aguacate', 'nueces', 'mantequilla_mani'],
        'verdura': ['espinaca', 'calabacita', 'champiñones'],
    },
    'cena': {
        'proteina': ['pechuga_de_pollo', 'pescado_blanco', 'claras_huevo', 'queso_panela'],
        'carbs': ['papa', 'camote', 'pan_integral'],
        'grasa': ['nueces', 'almendras'],
        'verdura': ['calabacita', 'coliflor', 'brocoli'],
        'fruta': ['manzana', 'papaya', 'naranja', 'melon', 'piña', 'platano', 'mango'],
    },
}
