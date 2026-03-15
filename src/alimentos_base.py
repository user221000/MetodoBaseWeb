"""
Base de alimentos.

Ahora los datos se cargan desde SQLite para permitir edición y persistencia,
manteniendo la misma interfaz pública de dicts.
"""
from __future__ import annotations

from core.branding import branding
from utils.logger import logger
from src.alimentos_seed_runtime import (
    ALIMENTOS_BASE_SEED,
    LIMITES_ALIMENTOS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED,
    CATEGORIAS_SEED,
)
from src.alimentos_sqlite import inicializar_db_si_es_necesario, cargar_datos


def _obtener_excluidos_gym() -> set[str]:
    raw = branding.get("alimentos.excluidos", [])
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def _aplicar_exclusiones_gym() -> None:
    excluidos = _obtener_excluidos_gym()
    if not excluidos:
        return
    for _, items in CATEGORIAS.items():
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
    ALIMENTOS_BASE = _datos["alimentos_base"]
    LIMITES_ALIMENTOS = _datos["limites_alimentos"]
    EQUIVALENCIAS_PRACTICAS = _datos["equivalencias_practicas"]
    CATEGORIAS = _datos["categorias"]
    _aplicar_exclusiones_gym()
except Exception as exc:
    logger.warning("[ALIMENTOS] Error cargando SQLite: %s. Usando seeds en memoria.", exc)
    ALIMENTOS_BASE = ALIMENTOS_BASE_SEED
    LIMITES_ALIMENTOS = LIMITES_ALIMENTOS_SEED
    EQUIVALENCIAS_PRACTICAS = EQUIVALENCIAS_PRACTICAS_SEED
    CATEGORIAS = CATEGORIAS_SEED
    _aplicar_exclusiones_gym()


def _reemplazar_dict(destino: dict, fuente: dict) -> None:
    """Reemplaza contenido sin romper referencias externas."""
    destino.clear()
    destino.update(fuente)


def recargar_desde_db() -> bool:
    """Recarga datos desde SQLite y actualiza dicts en memoria."""
    try:
        datos = cargar_datos()
    except Exception as exc:
        logger.warning("[ALIMENTOS] Error recargando SQLite: %s", exc)
        return False

    _reemplazar_dict(ALIMENTOS_BASE, datos["alimentos_base"])
    _reemplazar_dict(LIMITES_ALIMENTOS, datos["limites_alimentos"])
    _reemplazar_dict(EQUIVALENCIAS_PRACTICAS, datos["equivalencias_practicas"])
    _reemplazar_dict(CATEGORIAS, datos["categorias"])
    _aplicar_exclusiones_gym()
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
