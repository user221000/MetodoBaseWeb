"""
core/services/alimentos_alias.py
=================================
Mapa centralizado de alias y nombres canónicos de alimentos.

REGLAS DE NOMENCLATURA
----------------------
1. **Fuente de verdad**: Las claves en ``src/alimentos_seed.py``
   (``ALIMENTOS_BASE_SEED`` y ``CATEGORIAS_SEED``) son los nombres canónicos.
2. **Formato**: snake_case, minúsculas, sin acentos en claves de código
   (excepción: ``requesón`` / ``champiñones`` que preservan la ñ/ó por
   compatibilidad histórica con la BD existente).
3. **Aliases**: nombres cortos, variantes o errores tipográficos que circulan
   en ``config/constantes.py`` y ``core/selector_alimentos.py``.

INCONSISTENCIAS DETECTADAS
---------------------------
| Alias / nombre incorrecto | Nombre canónico (BD / seed) | Origen del alias          |
|---------------------------|------------------------------|---------------------------|
| atun                      | atun_en_agua                 | config/constantes.py      |
| carne_molida              | carne_molida_res             | config/constantes.py      |
| pavo                      | pavo_pechuga                 | config/constantes.py      |
| sardina                   | sardinas                     | config/constantes.py      |
| cerdo_lomo                | lomo_cerdo                   | config/constantes.py      |
| tofu                      | tofu_firme                   | config/constantes.py (implícito) |

USO
---
::

    from core.services.alimentos_alias import resolver, es_canonico, ALIAS_MAPA

    nombre_real = resolver("atun")        # → "atun_en_agua"
    nombre_real = resolver("atun_en_agua")# → "atun_en_agua" (ya es canónico)
    ok = es_canonico("sardina")           # → False
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# MAPA ALIAS → NOMBRE CANÓNICO
# ---------------------------------------------------------------------------

ALIAS_MAPA: dict[str, str] = {
    # Alias de proteínas
    "atun":          "atun_en_agua",
    "carne_molida":  "carne_molida_res",
    "pavo":          "pavo_pechuga",
    "sardina":       "sardinas",
    "cerdo_lomo":    "lomo_cerdo",
    "tofu":          "tofu_firme",

    # Variantes de grasas
    # (ninguna detectada aún)
}

# Conjunto de nombres canónicos (los que SÍ están en la BD)
NOMBRES_CANONICOS: frozenset[str] = frozenset({
    # Fuente: ALIMENTOS_BASE_SEED + ALIMENTOS_BASE_EXTRA (alimentos_seed_runtime)
    "pechuga_de_pollo", "carne_magra_res", "pescado_blanco", "salmon",
    "huevo", "claras_huevo", "queso_panela", "yogurt_griego_light",
    "proteina_suero", "atun_en_agua", "pollo_muslo", "carne_molida_res",
    "pavo_pechuga", "tofu_firme", "requesón", "jamon_pavo", "camarones",
    "sardinas", "leche_descremada", "yogurt_natural",
    "pavo_molido_93", "lomo_cerdo", "queso_cottage_bajo_grasa",
    "edamame_cocido",
    # Carbohidratos
    "arroz_blanco", "arroz_integral", "papa", "camote", "avena",
    "pan_integral", "tortilla_maiz", "frijoles", "lentejas", "garbanzos",
    "pasta_integral", "quinoa", "elote", "platano_macho", "tortilla_harina",
    "pan_blanco", "cereal_integral", "granola",
    "yuca", "bulgur", "cebada_perlada", "cuscus",
    # Grasas
    "aceite_de_oliva", "aguacate", "nueces", "almendras", "mantequilla_mani",
    "aceite_de_aguacate", "semillas_chia", "aceite_coco", "crema_cacahuate",
    "pistaches", "semillas_calabaza", "linaza", "aceitunas_verdes",
    "semillas_girasol", "cacahuates",
    # Verduras
    "brocoli", "espinaca", "calabacita", "champiñones", "coliflor",
    "zanahoria", "apio", "pepino", "tomate", "lechuga", "cebolla",
    "pimiento", "ejotes", "esparragos", "berenjena", "coles_bruselas",
    "alcachofa",
    # Frutas
    "manzana", "platano", "banana", "papaya", "naranja", "mango",
    "melon", "piña",
    # Aceites
    "aceite_de_oliva", "aceite_de_aguacate", "aceite_coco",
})


# ---------------------------------------------------------------------------
# API PÚBLICA
# ---------------------------------------------------------------------------

def resolver(nombre: str) -> str:
    """Devuelve el nombre canónico del alimento, resolviendo alias si existen.

    Args:
        nombre: Nombre del alimento tal como aparece en el código fuente
                (puede ser alias o canónico).

    Returns:
        Nombre canónico registrado en ``ALIMENTOS_BASE_SEED``.

    Examples:
        >>> resolver("atun")
        'atun_en_agua'
        >>> resolver("pavo_pechuga")
        'pavo_pechuga'
    """
    return ALIAS_MAPA.get(nombre, nombre)


def es_canonico(nombre: str) -> bool:
    """Devuelve ``True`` si el nombre es un nombre canónico (está en la BD).

    Args:
        nombre: Nombre a verificar.

    Returns:
        ``True`` si el nombre existe en ``NOMBRES_CANONICOS``.
    """
    return nombre in NOMBRES_CANONICOS


def es_alias(nombre: str) -> bool:
    """Devuelve ``True`` si el nombre es un alias (no canónico).

    Args:
        nombre: Nombre a verificar.

    Returns:
        ``True`` si el nombre existe en ``ALIAS_MAPA``.
    """
    return nombre in ALIAS_MAPA


def resolver_lista(nombres: list[str]) -> list[str]:
    """Aplica :func:`resolver` a cada elemento de una lista.

    Args:
        nombres: Lista de nombres de alimentos (pueden ser alias o canónicos).

    Returns:
        Nueva lista con los nombres canónicos correspondientes.
        Se eliminan duplicados manteniendo el orden original.

    Examples:
        >>> resolver_lista(["atun", "pavo", "pechuga_de_pollo"])
        ['atun_en_agua', 'pavo_pechuga', 'pechuga_de_pollo']
    """
    vistos: set[str] = set()
    resultado: list[str] = []
    for nombre in nombres:
        canonico = resolver(nombre)
        if canonico not in vistos:
            vistos.add(canonico)
            resultado.append(canonico)
    return resultado


def detectar_alias_en_set(nombres: set[str]) -> dict[str, str]:
    """Detecta qué nombres de un conjunto son alias y sugiere el canónico.

    Útil para auditar constantes del proyecto.

    Args:
        nombres: Conjunto de nombres a auditar.

    Returns:
        Diccionario ``{alias: canónico}`` para los nombres que son alias.

    Examples:
        >>> detectar_alias_en_set({"atun", "pechuga_de_pollo", "sardina"})
        {'atun': 'atun_en_agua', 'sardina': 'sardinas'}
    """
    return {n: ALIAS_MAPA[n] for n in nombres if n in ALIAS_MAPA}
