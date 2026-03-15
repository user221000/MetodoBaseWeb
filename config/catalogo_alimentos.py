"""
Catálogo centralizado de alimentos — Fuente Única de Verdad (Single Source of Truth).

Todos los módulos que necesiten listas de alimentos por categoría DEBEN importar
desde aquí. Las listas se derivan dinámicamente de src.alimentos_base.CATEGORIAS
para garantizar coherencia.
"""

from src.alimentos_base import CATEGORIAS, ALIMENTOS_BASE


# ---------------------------------------------------------------------------
# Listas canónicas por categoría (derivadas de CATEGORIAS)
# ---------------------------------------------------------------------------

PROTEINAS: list[str] = list(CATEGORIAS.get('proteina', []))
CARBS: list[str] = list(CATEGORIAS.get('carbs', []))
GRASAS: list[str] = list(CATEGORIAS.get('grasa', []))
VERDURAS: list[str] = list(CATEGORIAS.get('verdura', []))
FRUTAS: list[str] = list(CATEGORIAS.get('fruta', []))

# Sets equivalentes (para búsquedas O(1))
PROTEINAS_SET: set[str] = set(PROTEINAS)
CARBS_SET: set[str] = set(CARBS)
GRASAS_SET: set[str] = set(GRASAS)
VERDURAS_SET: set[str] = set(VERDURAS)
FRUTAS_SET: set[str] = set(FRUTAS)

# Mapa tipo -> lista (útil para iteración genérica)
CATALOGO_POR_TIPO: dict[str, list[str]] = {
    'proteina': PROTEINAS,
    'carbs': CARBS,
    'grasa': GRASAS,
    'verdura': VERDURAS,
    'fruta': FRUTAS,
}

# Mapa tipo -> set
CATALOGO_SETS: dict[str, set[str]] = {
    'proteina': PROTEINAS_SET,
    'carbs': CARBS_SET,
    'grasa': GRASAS_SET,
    'verdura': VERDURAS_SET,
    'fruta': FRUTAS_SET,
}


def categoria_de(alimento: str) -> str | None:
    """Devuelve la categoría ('proteina', 'carbs', 'grasa', …) de un alimento, o None."""
    for tipo, items in CATALOGO_SETS.items():
        if alimento in items:
            return tipo
    return None


def _refrescar_lista(nombre: str, nuevos: list[str]) -> None:
    actual = globals().get(nombre)
    if isinstance(actual, list):
        actual.clear()
        actual.extend(nuevos)
    else:
        globals()[nombre] = list(nuevos)


def _refrescar_set(nombre: str, nuevos: set[str]) -> None:
    actual = globals().get(nombre)
    if isinstance(actual, set):
        actual.clear()
        actual.update(nuevos)
    else:
        globals()[nombre] = set(nuevos)


def _refrescar_dict(nombre: str, nuevos: dict) -> None:
    actual = globals().get(nombre)
    if isinstance(actual, dict):
        actual.clear()
        actual.update(nuevos)
    else:
        globals()[nombre] = dict(nuevos)


def refrescar_catalogo() -> None:
    """Refresca listas/sets/dicts desde CATEGORIAS (sin romper referencias)."""
    nuevas_proteinas = list(CATEGORIAS.get('proteina', []))
    nuevas_carbs = list(CATEGORIAS.get('carbs', []))
    nuevas_grasas = list(CATEGORIAS.get('grasa', []))
    nuevas_verduras = list(CATEGORIAS.get('verdura', []))
    nuevas_frutas = list(CATEGORIAS.get('fruta', []))

    _refrescar_lista("PROTEINAS", nuevas_proteinas)
    _refrescar_lista("CARBS", nuevas_carbs)
    _refrescar_lista("GRASAS", nuevas_grasas)
    _refrescar_lista("VERDURAS", nuevas_verduras)
    _refrescar_lista("FRUTAS", nuevas_frutas)

    _refrescar_set("PROTEINAS_SET", set(nuevas_proteinas))
    _refrescar_set("CARBS_SET", set(nuevas_carbs))
    _refrescar_set("GRASAS_SET", set(nuevas_grasas))
    _refrescar_set("VERDURAS_SET", set(nuevas_verduras))
    _refrescar_set("FRUTAS_SET", set(nuevas_frutas))

    _refrescar_dict(
        "CATALOGO_POR_TIPO",
        {
            'proteina': PROTEINAS,
            'carbs': CARBS,
            'grasa': GRASAS,
            'verdura': VERDURAS,
            'fruta': FRUTAS,
        },
    )
    _refrescar_dict(
        "CATALOGO_SETS",
        {
            'proteina': PROTEINAS_SET,
            'carbs': CARBS_SET,
            'grasa': GRASAS_SET,
            'verdura': VERDURAS_SET,
            'fruta': FRUTAS_SET,
        },
    )
