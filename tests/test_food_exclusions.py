"""
tests/test_food_exclusions.py
=============================
Verifica que las exclusiones de alimentos funcionan para TODOS los planes
de suscripción — tanto socio comercial como usuario regular.

Ejecutar con:
    python -m pytest tests/test_food_exclusions.py -v
"""
import copy
import json
import pytest


class TestFoodPreferencesAllPlans:
    """check_food_preferences_allowed debe retornar True para todos los planes."""

    def test_all_plans_allow_food_preferences(self):
        from web.constants import PLANES_LICENCIA
        for plan_name, plan_cfg in PLANES_LICENCIA.items():
            assert plan_cfg.get("preferencias_alimentos") is True, (
                f"Plan '{plan_name}' debe tener preferencias_alimentos=True"
            )

    def test_check_food_preferences_allowed_free(self):
        from web.subscription_guard import check_food_preferences_allowed
        assert check_food_preferences_allowed("free") is True

    def test_check_food_preferences_allowed_standard(self):
        from web.subscription_guard import check_food_preferences_allowed
        assert check_food_preferences_allowed("standard") is True

    def test_check_food_preferences_allowed_gym_comercial(self):
        from web.subscription_guard import check_food_preferences_allowed
        assert check_food_preferences_allowed("gym_comercial") is True

    def test_check_food_preferences_allowed_clinica(self):
        from web.subscription_guard import check_food_preferences_allowed
        assert check_food_preferences_allowed("clinica") is True

    def test_check_food_preferences_allowed_pro_usuario(self):
        from web.subscription_guard import check_food_preferences_allowed
        assert check_food_preferences_allowed("pro_usuario") is True


class TestExclusionFiltering:
    """Verifica que la lógica de filtrado de CATEGORIAS excluye alimentos correctamente."""

    def test_exclusion_removes_food_from_categories(self):
        """Simula el filtrado que hace _do_generar_plan con excluidos_cliente."""
        from src.alimentos_base import CATEGORIAS

        excluidos_cliente = set()
        # Pick a real food from the catalog to exclude
        for cat, items in CATEGORIAS.items():
            if items:
                excluidos_cliente.add(items[0])
                break

        assert len(excluidos_cliente) == 1, "Necesitamos al menos 1 alimento para excluir"
        excluded_food = next(iter(excluidos_cliente))

        # Simulate filtering (same logic as planes.py _do_generar_plan)
        categorias_local = copy.deepcopy(CATEGORIAS)
        for cat, items in categorias_local.items():
            filtrados = [a for a in items if a not in excluidos_cliente]
            if filtrados:
                items.clear()
                items.extend(filtrados)

        # Verify the excluded food is NOT in any category
        all_foods = []
        for items in categorias_local.values():
            all_foods.extend(items)

        assert excluded_food not in all_foods, (
            f"'{excluded_food}' debería haber sido excluido pero sigue en las categorías"
        )

    def test_exclusion_does_not_modify_original(self):
        """Verifica que deepcopy protege las categorías originales."""
        from src.alimentos_base import CATEGORIAS

        original_counts = {cat: len(items) for cat, items in CATEGORIAS.items()}

        excluidos = set()
        for cat, items in CATEGORIAS.items():
            if items:
                excluidos.add(items[0])
                break

        categorias_local = copy.deepcopy(CATEGORIAS)
        for cat, items in categorias_local.items():
            filtrados = [a for a in items if a not in excluidos]
            if filtrados:
                items.clear()
                items.extend(filtrados)

        # Original must be untouched
        for cat, items in CATEGORIAS.items():
            assert len(items) == original_counts[cat], (
                f"Categoría '{cat}' fue modificada en el original"
            )

    def test_multiple_exclusions(self):
        """Excluir múltiples alimentos de distintas categorías."""
        from src.alimentos_base import CATEGORIAS

        excluidos = set()
        for cat, items in CATEGORIAS.items():
            if len(items) >= 2:
                excluidos.add(items[0])
                excluidos.add(items[1])
            elif items:
                excluidos.add(items[0])

        categorias_local = copy.deepcopy(CATEGORIAS)
        for cat, items in categorias_local.items():
            filtrados = [a for a in items if a not in excluidos]
            if filtrados:
                items.clear()
                items.extend(filtrados)

        all_foods = []
        for items in categorias_local.values():
            all_foods.extend(items)

        for food in excluidos:
            assert food not in all_foods, (
                f"'{food}' debería estar excluido"
            )

    def test_empty_exclusion_set_leaves_all_foods(self):
        """Sin exclusiones, todas las categorías permanecen intactas."""
        from src.alimentos_base import CATEGORIAS

        excluidos = set()
        categorias_local = copy.deepcopy(CATEGORIAS)
        for cat, items in categorias_local.items():
            filtrados = [a for a in items if a not in excluidos]
            if filtrados:
                items.clear()
                items.extend(filtrados)

        for cat in CATEGORIAS:
            assert len(categorias_local[cat]) == len(CATEGORIAS[cat])
