"""
tests/test_alimentos_seed.py
=============================
Tests para la integridad del seed de alimentos.

Valida:
- Que todos los alimentos en ALIMENTOS_BASE_SEED tengan la estructura correcta.
- Que los valores nutricionales estén dentro de rangos fisiológicos.
- Que CATEGORIAS_SEED no tenga alimentos sin datos nutricionales.
- Que los alimentos extras (ALIMENTOS_BASE_EXTRA) sean coherentes con el seed base.
- Normalización: sin aliases en las categorías (usando el mapa de alias).

Ejecutar con:
    python -m pytest tests/test_alimentos_seed.py -v
"""
from __future__ import annotations

import pytest

from src.alimentos_seed import (
    ALIMENTOS_BASE_SEED,
    CATEGORIAS_SEED,
    LIMITES_ALIMENTOS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED,
)
from src.alimentos_seed_runtime import (
    ALIMENTOS_BASE_EXTRA,
    LIMITES_ALIMENTOS_EXTRA,
    ALIMENTOS_BASE_SEED as RUNTIME_SEED,
    CATEGORIAS_SEED as RUNTIME_CATEGORIAS,
)
from core.services.alimentos_alias import ALIAS_MAPA


# ---------------------------------------------------------------------------
# Constantes de validación nutricional
# ---------------------------------------------------------------------------

# Rangos fisiológicos por macronutriente (por 100g de alimento)
RANGOS_PROTEIN  = (0.0, 100.0)
RANGOS_CARBS    = (0.0, 100.0)
RANGOS_GRASA    = (0.0, 100.0)
RANGOS_KCAL     = (0.0, 1000.0)

CAMPOS_REQUERIDOS = {"proteina", "carbs", "grasa", "kcal", "meal_idx"}
MEAL_IDX_VALIDOS = {0, 1, 2, 3}


# ---------------------------------------------------------------------------
# 1. Estructura del seed base
# ---------------------------------------------------------------------------

class TestEstructuraSeedBase:
    """Verifica la estructura de ALIMENTOS_BASE_SEED."""

    def test_seed_no_vacio(self):
        assert len(ALIMENTOS_BASE_SEED) > 0

    @pytest.mark.parametrize("alimento", list(ALIMENTOS_BASE_SEED.keys()))
    def test_alimento_tiene_campos_requeridos(self, alimento):
        datos = ALIMENTOS_BASE_SEED[alimento]
        faltantes = CAMPOS_REQUERIDOS - set(datos.keys())
        assert not faltantes, (
            f"Alimento '{alimento}' le faltan campos: {faltantes}"
        )

    @pytest.mark.parametrize("alimento", list(ALIMENTOS_BASE_SEED.keys()))
    def test_proteina_en_rango(self, alimento):
        val = ALIMENTOS_BASE_SEED[alimento]["proteina"]
        assert RANGOS_PROTEIN[0] <= val <= RANGOS_PROTEIN[1], (
            f"{alimento}: proteina={val} fuera de [{RANGOS_PROTEIN}]"
        )

    @pytest.mark.parametrize("alimento", list(ALIMENTOS_BASE_SEED.keys()))
    def test_carbs_en_rango(self, alimento):
        val = ALIMENTOS_BASE_SEED[alimento]["carbs"]
        assert RANGOS_CARBS[0] <= val <= RANGOS_CARBS[1], (
            f"{alimento}: carbs={val} fuera de [{RANGOS_CARBS}]"
        )

    @pytest.mark.parametrize("alimento", list(ALIMENTOS_BASE_SEED.keys()))
    def test_grasa_en_rango(self, alimento):
        val = ALIMENTOS_BASE_SEED[alimento]["grasa"]
        assert RANGOS_GRASA[0] <= val <= RANGOS_GRASA[1], (
            f"{alimento}: grasa={val} fuera de [{RANGOS_GRASA}]"
        )

    @pytest.mark.parametrize("alimento", list(ALIMENTOS_BASE_SEED.keys()))
    def test_kcal_en_rango(self, alimento):
        val = ALIMENTOS_BASE_SEED[alimento]["kcal"]
        assert RANGOS_KCAL[0] <= val <= RANGOS_KCAL[1], (
            f"{alimento}: kcal={val} fuera de [0, 1000]"
        )

    @pytest.mark.parametrize("alimento", list(ALIMENTOS_BASE_SEED.keys()))
    def test_meal_idx_es_lista_valida(self, alimento):
        meal_idx = ALIMENTOS_BASE_SEED[alimento]["meal_idx"]
        assert isinstance(meal_idx, list), (
            f"{alimento}: meal_idx debe ser lista"
        )
        assert len(meal_idx) > 0, (
            f"{alimento}: meal_idx no puede estar vacío"
        )
        for idx in meal_idx:
            assert idx in MEAL_IDX_VALIDOS, (
                f"{alimento}: meal_idx={idx} no es válido (debe ser 0,1,2,3)"
            )


# ---------------------------------------------------------------------------
# 2. CATEGORIAS_SEED
# ---------------------------------------------------------------------------

class TestCategoriasSeed:
    """Verifica que las categorías tengan alimentos con datos en el seed."""

    CATEGORIAS_ESPERADAS = {"proteina", "carbs", "grasa", "verdura", "fruta"}

    def test_categorias_esperadas_presentes(self):
        assert self.CATEGORIAS_ESPERADAS.issubset(set(CATEGORIAS_SEED.keys()))

    def test_cada_categoria_no_vacia(self):
        for cat, alimentos in CATEGORIAS_SEED.items():
            assert len(alimentos) > 0, f"Categoría '{cat}' está vacía"

    def test_proteinas_en_seed_tienen_datos(self):
        """Cada proteína en CATEGORIAS_SEED debe tener datos en ALIMENTOS_BASE_SEED."""
        # Unión de seeds base y runtime para la verificación
        todos = {**ALIMENTOS_BASE_SEED, **ALIMENTOS_BASE_EXTRA}
        for alimento in CATEGORIAS_SEED.get("proteina", []):
            assert alimento in todos, (
                f"Proteína '{alimento}' en CATEGORIAS_SEED no tiene datos nutricionales"
            )

    def test_no_duplicados_en_categoria(self):
        """Cada categoría no debe tener alimentos duplicados."""
        for cat, alimentos in CATEGORIAS_SEED.items():
            assert len(alimentos) == len(set(alimentos)), (
                f"Categoría '{cat}' tiene duplicados: "
                f"{[a for a in alimentos if alimentos.count(a) > 1]}"
            )


# ---------------------------------------------------------------------------
# 3. LIMITES_ALIMENTOS_SEED
# ---------------------------------------------------------------------------

class TestLimitesAlimentosSeed:
    """Verifica que los límites sean valores positivos."""

    def test_limites_positivos(self):
        for alimento, limite in LIMITES_ALIMENTOS_SEED.items():
            assert limite > 0, f"{alimento}: límite={limite} debe ser positivo"

    def test_limites_son_numericos(self):
        for alimento, limite in LIMITES_ALIMENTOS_SEED.items():
            assert isinstance(limite, (int, float)), (
                f"{alimento}: límite debe ser numérico"
            )


# ---------------------------------------------------------------------------
# 4. ALIMENTOS_BASE_EXTRA (seed_runtime)
# ---------------------------------------------------------------------------

class TestSeedRuntime:
    """Verifica que los alimentos extra del runtime sean coherentes."""

    def test_extra_no_sobreescribe_base(self):
        """Los alimentos extra no deben estar en el seed base."""
        solapados = set(ALIMENTOS_BASE_EXTRA.keys()) & set(ALIMENTOS_BASE_SEED.keys())
        assert not solapados, (
            f"Alimentos en EXTRA que también están en BASE: {solapados}"
        )

    def test_runtime_incluye_base_y_extra(self):
        """El seed runtime debe incluir todos los alimentos del seed base."""
        for nombre in ALIMENTOS_BASE_SEED:
            assert nombre in RUNTIME_SEED, (
                f"'{nombre}' está en ALIMENTOS_BASE_SEED pero no en RUNTIME_SEED"
            )

    def test_extra_tiene_campos_requeridos(self):
        for alimento, datos in ALIMENTOS_BASE_EXTRA.items():
            faltantes = CAMPOS_REQUERIDOS - set(datos.keys())
            assert not faltantes, (
                f"EXTRA alimento '{alimento}' le faltan campos: {faltantes}"
            )

    def test_extra_kcal_positivas(self):
        for alimento, datos in ALIMENTOS_BASE_EXTRA.items():
            assert datos["kcal"] > 0, (
                f"EXTRA '{alimento}': kcal debe ser positivo"
            )


# ---------------------------------------------------------------------------
# 5. Consistencia de nombres (alias)
# ---------------------------------------------------------------------------

class TestConsistenciaNombres:
    """Detecta que no haya aliases en las categorías del seed."""

    def test_categorias_seed_no_tienen_aliases(self):
        """Las categorías del seed deben usar nombres canónicos, no aliases."""
        aliases_encontrados = {}
        for cat, alimentos in CATEGORIAS_SEED.items():
            aliases_en_cat = [a for a in alimentos if a in ALIAS_MAPA]
            if aliases_en_cat:
                aliases_encontrados[cat] = aliases_en_cat

        assert not aliases_encontrados, (
            f"CATEGORIAS_SEED usa aliases en lugar de nombres canónicos: "
            f"{aliases_encontrados}. "
            f"Corregir usando los canónicos del mapa de alias."
        )

    def test_alimentos_base_seed_claves_no_tienen_aliases(self):
        """Las claves del seed de alimentos deben ser canónicas."""
        aliases_en_claves = [k for k in ALIMENTOS_BASE_SEED if k in ALIAS_MAPA]
        assert not aliases_en_claves, (
            f"ALIMENTOS_BASE_SEED tiene claves que son aliases: {aliases_en_claves}"
        )
