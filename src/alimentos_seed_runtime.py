"""
Semillas extendidas de alimentos para poblar SQLite sin perder compatibilidad.
"""
from __future__ import annotations

from src.alimentos_seed import (
    ALIMENTOS_BASE_SEED as BASE_ALIMENTOS_BASE_SEED,
    CATEGORIAS_SEED as BASE_CATEGORIAS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED as BASE_EQUIVALENCIAS_PRACTICAS_SEED,
    LIMITES_ALIMENTOS_SEED as BASE_LIMITES_ALIMENTOS_SEED,
)


ALIMENTOS_BASE_EXTRA = {
    "pavo_molido_93": {
        "proteina": 18.7,
        "carbs": 0,
        "grasa": 8.34,
        "kcal": 150,
        "meal_idx": [1, 2, 3],
    },
    "lomo_cerdo": {
        "proteina": 21.0,
        "carbs": 0,
        "grasa": 4.5,
        "kcal": 143,
        "meal_idx": [1, 2, 3],
    },
    "queso_cottage_bajo_grasa": {
        "proteina": 11.0,
        "carbs": 4.31,
        "grasa": 2.3,
        "kcal": 84,
        "meal_idx": [0, 3],
    },
    "edamame_cocido": {
        "proteina": 11.54,
        "carbs": 8.63,
        "grasa": 7.58,
        "kcal": 140,
        "meal_idx": [1, 2, 3],
    },
    "yuca": {
        "proteina": 1.4,
        "carbs": 38.1,
        "grasa": 0.3,
        "kcal": 160,
        "meal_idx": [1, 2, 3],
    },
    "bulgur": {
        "proteina": 3.1,
        "carbs": 18.6,
        "grasa": 0.2,
        "kcal": 83,
        "meal_idx": [1, 2, 3],
    },
    "cebada_perlada": {
        "proteina": 2.3,
        "carbs": 28.2,
        "grasa": 0.4,
        "kcal": 123,
        "meal_idx": [1, 2, 3],
    },
    "cuscus": {
        "proteina": 3.8,
        "carbs": 23.2,
        "grasa": 0.2,
        "kcal": 112,
        "meal_idx": [1, 2, 3],
    },
    "pistaches": {
        "proteina": 20.2,
        "carbs": 27.2,
        "grasa": 45.4,
        "kcal": 562,
        "meal_idx": [0, 3],
    },
    "semillas_calabaza": {
        "proteina": 30.2,
        "carbs": 10.7,
        "grasa": 49.1,
        "kcal": 559,
        "meal_idx": [0, 3],
    },
    "linaza": {
        "proteina": 18.3,
        "carbs": 28.9,
        "grasa": 42.2,
        "kcal": 534,
        "meal_idx": [0],
    },
    "aceitunas_verdes": {
        "proteina": 1.0,
        "carbs": 3.8,
        "grasa": 15.3,
        "kcal": 145,
        "meal_idx": [1, 2, 3],
    },
    "esparragos": {
        "proteina": 2.2,
        "carbs": 3.9,
        "grasa": 0.1,
        "kcal": 20,
        "meal_idx": [1, 2, 3],
    },
    "berenjena": {
        "proteina": 1.0,
        "carbs": 5.9,
        "grasa": 0.2,
        "kcal": 25,
        "meal_idx": [1, 2, 3],
    },
    "coles_bruselas": {
        "proteina": 3.4,
        "carbs": 8.9,
        "grasa": 0.3,
        "kcal": 43,
        "meal_idx": [1, 2, 3],
    },
    "alcachofa": {
        "proteina": 3.3,
        "carbs": 10.5,
        "grasa": 0.2,
        "kcal": 47,
        "meal_idx": [1, 2, 3],
    },
}

LIMITES_ALIMENTOS_EXTRA = {
    "pavo_molido_93": 220,
    "lomo_cerdo": 220,
    "queso_cottage_bajo_grasa": 220,
    "edamame_cocido": 180,
    "yuca": 250,
    "bulgur": 220,
    "cebada_perlada": 220,
    "cuscus": 220,
    "pistaches": 40,
    "semillas_calabaza": 35,
    "linaza": 20,
    "aceitunas_verdes": 80,
    "esparragos": 200,
    "berenjena": 200,
    "coles_bruselas": 180,
    "alcachofa": 180,
}

EQUIVALENCIAS_PRACTICAS_EXTRA = {
    "pavo_molido_93": "≈ 1 porcion mediana de pavo molido",
    "lomo_cerdo": "≈ 1 filete mediano",
    "queso_cottage_bajo_grasa": "≈ 3/4 taza",
    "edamame_cocido": "≈ 1 taza",
    "yuca": "≈ 1 taza cocida",
    "bulgur": "≈ 3/4 taza cocida",
    "cebada_perlada": "≈ 3/4 taza cocida",
    "cuscus": "≈ 3/4 taza cocida",
    "pistaches": "≈ 1 punado pequeno",
    "semillas_calabaza": "≈ 2 cucharadas",
    "linaza": "≈ 1 cucharada y media",
    "aceitunas_verdes": "≈ 10-12 aceitunas",
    "esparragos": "≈ 8-10 tallos",
    "berenjena": "≈ 1 taza picada",
    "coles_bruselas": "≈ 1 taza",
    "alcachofa": "≈ 1 pieza mediana",
}

CATEGORIAS_EXTRA = {
    "proteina": [
        "pavo_molido_93",
        "lomo_cerdo",
        "queso_cottage_bajo_grasa",
        "edamame_cocido",
    ],
    "carbs": [
        "yuca",
        "bulgur",
        "cebada_perlada",
        "cuscus",
    ],
    "grasa": [
        "pistaches",
        "semillas_calabaza",
        "linaza",
        "aceitunas_verdes",
    ],
    "verdura": [
        "esparragos",
        "berenjena",
        "coles_bruselas",
        "alcachofa",
    ],
}


def _merge_categorias() -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    claves = set(BASE_CATEGORIAS_SEED) | set(CATEGORIAS_EXTRA)
    for clave in claves:
        base = list(BASE_CATEGORIAS_SEED.get(clave, []))
        extra = [item for item in CATEGORIAS_EXTRA.get(clave, []) if item not in base]
        merged[clave] = base + extra
    return merged


ALIMENTOS_BASE_SEED = {
    **BASE_ALIMENTOS_BASE_SEED,
    **ALIMENTOS_BASE_EXTRA,
}

LIMITES_ALIMENTOS_SEED = {
    **BASE_LIMITES_ALIMENTOS_SEED,
    **LIMITES_ALIMENTOS_EXTRA,
}

EQUIVALENCIAS_PRACTICAS_SEED = {
    **BASE_EQUIVALENCIAS_PRACTICAS_SEED,
    **EQUIVALENCIAS_PRACTICAS_EXTRA,
}

CATEGORIAS_SEED = _merge_categorias()
