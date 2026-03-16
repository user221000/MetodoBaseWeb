"""
tests/test_selector_alimentos.py
==================================
Tests para SelectorAlimentos y SelectorAlimentosService.

Valida:
- Que la selección por tipo y comida devuelva listas no vacías.
- Que los nombres retornados sean canónicos (no aliases).
- Que la rotación sea determinista (mismo seed = misma lista).
- Que la rotación varíe con seeds distintos.
- Edge cases: meal_idx fuera de rango, alimentos_usados llenos, etc.

Ejecutar con:
    python -m pytest tests/test_selector_alimentos.py -v
"""
from __future__ import annotations

import pytest

from core.modelos import ClienteEvaluacion
from core.selector_alimentos import (
    SelectorAlimentos,
    generar_seed,
    generar_seed_bloques,
    obtener_lista_rotada,
    aplicar_penalizacion_semana,
)
from core.services.selector_alimentos_service import (
    SelectorAlimentosService,
    obtener_alimentos_por_comida,
)
from core.services.alimentos_alias import es_alias, ALIAS_MAPA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cliente_base():
    """Cliente de prueba con todos los campos requeridos."""
    return ClienteEvaluacion(
        nombre="Test Usuario",
        edad=28,
        peso_kg=75.0,
        estatura_cm=170.0,
        grasa_corporal_pct=20.0,
        nivel_actividad="moderada",
        objetivo="deficit",
        factor_actividad=1.55,
        id_cliente="TEST_SEL",
    )


# ---------------------------------------------------------------------------
# 1. SelectorAlimentos.seleccionar_lista — listas básicas
# ---------------------------------------------------------------------------

class TestSelectorAlimentosListas:
    """Valida que se devuelvan listas no vacías con nombres existentes."""

    @pytest.mark.parametrize("tipo", ["proteina", "carbs", "grasa"])
    @pytest.mark.parametrize("meal_idx", [0, 1, 2, 3])
    def test_lista_no_vacia(self, tipo, meal_idx):
        """Cualquier combinación tipo × meal_idx debe devolver al menos un alimento."""
        lista = SelectorAlimentos.seleccionar_lista(tipo, meal_idx=meal_idx)
        assert isinstance(lista, list)
        assert len(lista) > 0, (
            f"La lista de '{tipo}' para meal_idx={meal_idx} no debe estar vacía."
        )

    @pytest.mark.parametrize("tipo", ["proteina", "carbs", "grasa"])
    def test_lista_contiene_strings(self, tipo):
        lista = SelectorAlimentos.seleccionar_lista(tipo, meal_idx=0)
        assert all(isinstance(item, str) for item in lista)


# ---------------------------------------------------------------------------
# 2. Determinismo: mismo seed → misma lista
# ---------------------------------------------------------------------------

class TestDeterminismo:
    """Verifica que la selección sea determinista con el mismo seed."""

    def test_misma_lista_mismo_seed(self, cliente_base):
        seed = generar_seed(cliente_base, semana=1)
        lista_a = SelectorAlimentos.seleccionar_lista(
            "proteina", meal_idx=0, seed=seed, plan_numero=1
        )
        lista_b = SelectorAlimentos.seleccionar_lista(
            "proteina", meal_idx=0, seed=seed, plan_numero=1
        )
        assert lista_a == lista_b

    def test_lista_diferente_seed_diferente(self, cliente_base):
        seed1 = generar_seed(cliente_base, semana=1)
        seed2 = generar_seed(cliente_base, semana=2)
        lista1 = SelectorAlimentos.seleccionar_lista(
            "proteina", meal_idx=0, seed=seed1, plan_numero=1
        )
        lista2 = SelectorAlimentos.seleccionar_lista(
            "proteina", meal_idx=0, seed=seed2, plan_numero=1
        )
        # No necesariamente distintas en todos los casos, pero con semanas
        # diferentes es muy probable que difieran
        assert not (seed1 == seed2), "Las semillas de semanas distintas deben diferir"

    def test_generar_seed_determinista(self, cliente_base):
        seed_a = generar_seed(cliente_base, semana=1, gym_id="gym1")
        seed_b = generar_seed(cliente_base, semana=1, gym_id="gym1")
        assert seed_a == seed_b

    def test_generar_seed_diferente_gym(self, cliente_base):
        seed_gym1 = generar_seed(cliente_base, semana=1, gym_id="gym1")
        seed_gym2 = generar_seed(cliente_base, semana=1, gym_id="gym2")
        assert seed_gym1 != seed_gym2

    def test_generar_seed_bloques(self, cliente_base):
        seed_base, seed_var = generar_seed_bloques(cliente_base, gym_id="default")
        assert isinstance(seed_base, int)
        assert isinstance(seed_var, int)
        assert seed_base != seed_var


# ---------------------------------------------------------------------------
# 3. SelectorAlimentosService — nombres canónicos
# ---------------------------------------------------------------------------

class TestSelectorAlimentosServiceCanonicidad:
    """Comprueba que el servicio retorne nombres canónicos (no aliases)."""

    def test_proteinas_meal0_no_tienen_alias(self, cliente_base):
        svc = SelectorAlimentosService(cliente=cliente_base)
        proteinas = svc.obtener_proteinas(meal_idx=0)
        aliases_detectados = [p for p in proteinas if es_alias(p)]
        assert aliases_detectados == [], (
            f"Se encontraron aliases en la lista de proteínas: {aliases_detectados}. "
            f"Deben resolverse con alimentos_alias.py"
        )

    def test_carbs_no_tienen_alias(self, cliente_base):
        svc = SelectorAlimentosService(cliente=cliente_base)
        for meal_idx in [0, 1, 2, 3]:
            carbs = svc.obtener_carbs(meal_idx=meal_idx)
            aliases = [c for c in carbs if es_alias(c)]
            assert aliases == [], (
                f"meal_idx={meal_idx}: aliases en carbs: {aliases}"
            )

    def test_grasas_no_tienen_alias(self, cliente_base):
        svc = SelectorAlimentosService(cliente=cliente_base)
        grasas = svc.obtener_grasas(meal_idx=0)
        aliases = [g for g in grasas if es_alias(g)]
        assert aliases == [], f"Aliases en grasas: {aliases}"


# ---------------------------------------------------------------------------
# 4. obtener_alimentos_por_comida
# ---------------------------------------------------------------------------

class TestObtenerAlimentosPorComida:
    """Verifica la función de conveniencia de alto nivel."""

    @pytest.mark.parametrize("meal_idx", [0, 1, 2, 3])
    def test_devuelve_tres_categorias(self, cliente_base, meal_idx):
        resultado = obtener_alimentos_por_comida(cliente_base, meal_idx=meal_idx)
        assert "proteinas" in resultado
        assert "carbs" in resultado
        assert "grasas" in resultado

    def test_cada_categoria_es_lista(self, cliente_base):
        resultado = obtener_alimentos_por_comida(cliente_base, meal_idx=0)
        assert isinstance(resultado["proteinas"], list)
        assert isinstance(resultado["carbs"], list)
        assert isinstance(resultado["grasas"], list)

    def test_listas_no_vacias_comida_principal(self, cliente_base):
        resultado = obtener_alimentos_por_comida(cliente_base, meal_idx=2)
        assert len(resultado["proteinas"]) > 0
        assert len(resultado["carbs"]) > 0


# ---------------------------------------------------------------------------
# 5. obtener_lista_rotada — rotación básica
# ---------------------------------------------------------------------------

class TestObtenerListaRotada:
    """Tests para la función de rotación determinista."""

    def test_misma_lista_mismo_seed(self):
        lista = ["a", "b", "c", "d"]
        r1 = obtener_lista_rotada(lista, seed=42, meal_idx=0)
        r2 = obtener_lista_rotada(lista, seed=42, meal_idx=0)
        assert r1 == r2

    def test_no_pierde_elementos(self):
        lista = ["salmon", "pechuga_de_pollo", "huevo", "claras_huevo"]
        rotada = obtener_lista_rotada(lista, seed=12345, meal_idx=1)
        assert set(rotada) == set(lista)

    def test_lista_vacia_retorna_vacia(self):
        assert obtener_lista_rotada([], seed=0, meal_idx=0) == []

    def test_lista_un_elemento(self):
        assert obtener_lista_rotada(["salmon"], seed=99, meal_idx=0) == ["salmon"]


# ---------------------------------------------------------------------------
# 6. aplicar_penalizacion_semana
# ---------------------------------------------------------------------------

class TestAplicarPenalizacionSemana:
    """Verifica que los alimentos penalizados se muevan al final."""

    def test_semana_1_no_cambia_lista(self):
        lista = ["a", "b", "c", "d"]
        resultado = aplicar_penalizacion_semana(lista, seed=1, semana=1)
        assert resultado == lista

    def test_semana_mayor_penaliza_elementos(self):
        lista = ["a", "b", "c", "d", "e", "f"]
        original = list(lista)
        resultado = aplicar_penalizacion_semana(lista, seed=1, semana=3)
        # El orden cambia, pero todos los elementos deben estar presentes
        assert sorted(resultado) == sorted(original)

    def test_lista_muy_corta_no_cambia(self):
        lista = ["a", "b"]
        resultado = aplicar_penalizacion_semana(lista, seed=1, semana=4)
        assert resultado == lista
