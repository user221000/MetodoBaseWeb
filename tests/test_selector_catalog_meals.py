"""The request catalog controls eligible meals, including newly added foods."""

from copy import deepcopy

import pytest

from core.food_catalog import FoodCatalog, FoodRestrictionError
from core.selector_alimentos import SelectorAlimentos
from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS

EXTRAS = {
    "audit_breakfast_protein": (
        "proteina",
        {"proteina": 20.0, "carbs": 1.0, "grasa": 1.0, "kcal": 93.0, "meal_idx": [0]},
    ),
    "audit_breakfast_carb": (
        "carbs",
        {"proteina": 1.0, "carbs": 50.0, "grasa": 1.0, "kcal": 213.0, "meal_idx": [0]},
    ),
    "audit_breakfast_fat": (
        "grasa",
        {"proteina": 1.0, "carbs": 1.0, "grasa": 50.0, "kcal": 458.0, "meal_idx": [0]},
    ),
    "audit_lunch_protein": (
        "proteina",
        {"proteina": 20.0, "carbs": 1.0, "grasa": 1.0, "kcal": 93.0, "meal_idx": [2]},
    ),
    "audit_lunch_carb": (
        "carbs",
        {"proteina": 1.0, "carbs": 50.0, "grasa": 1.0, "kcal": 213.0, "meal_idx": [2]},
    ),
    "audit_lunch_fat": (
        "grasa",
        {"proteina": 1.0, "carbs": 1.0, "grasa": 50.0, "kcal": 458.0, "meal_idx": [2]},
    ),
}


def catalog(excluded=()):
    foods = deepcopy(dict(ALIMENTOS_BASE))
    categories = {k: list(v) for k, v in CATEGORIAS.items()}
    for key, (category, nutrients) in EXTRAS.items():
        foods[key] = deepcopy(nutrients)
        categories[category].append(key)
    return FoodCatalog.from_data(foods, categories, excluded)


@pytest.mark.parametrize("category", ["proteina", "carbs", "grasa", "fruta"])
@pytest.mark.parametrize("meal", [0, 1, 2, 3])
def test_every_candidate_obeys_its_declared_meal(category, meal):
    allowed = catalog()
    selected = SelectorAlimentos.seleccionar_lista(
        category, meal_idx=meal, seed=981, plan_numero=1, catalogo=allowed
    )
    assert all(
        meal in allowed.alimentos[name].get("meal_idx", (0, 1, 2, 3))
        for name in selected
    )


@pytest.mark.parametrize(
    "category,food,meal",
    [
        ("carbs", "audit_breakfast_carb", 0),
        ("grasa", "audit_breakfast_fat", 0),
        ("carbs", "audit_lunch_carb", 2),
        ("grasa", "audit_lunch_fat", 2),
    ],
)
def test_new_permitted_foods_remain_reachable_beyond_hardcoded_priorities(
    category, food, meal
):
    assert food in SelectorAlimentos.seleccionar_lista(
        category, meal_idx=meal, seed=0, catalogo=catalog()
    )


@pytest.mark.parametrize("category", ["proteina", "carbs", "grasa"])
def test_no_meal_candidate_fails_closed_instead_of_restoring_forbidden_foods(category):
    foods = {key: deepcopy(value) for key, (_, value) in EXTRAS.items()}
    categories = {key: [] for key in ("proteina", "carbs", "grasa", "verdura", "fruta")}
    for key, (kind, value) in EXTRAS.items():
        categories[kind].append(key)
    foods["audit_vegetable"] = {
        "proteina": 1.0,
        "carbs": 4.0,
        "grasa": 0.1,
        "kcal": 21.0,
        "meal_idx": [0, 1, 2, 3],
    }
    categories["verdura"].append("audit_vegetable")
    for key in categories[category]:
        foods[key]["meal_idx"] = [2]
    allowed = FoodCatalog.from_data(foods, categories)
    with pytest.raises(FoodRestrictionError):
        SelectorAlimentos.seleccionar_lista(category, meal_idx=0, catalogo=allowed)


@pytest.mark.parametrize(
    "category,excluded",
    [
        ("carbs", "audit_breakfast_carb"),
        ("grasa", "audit_breakfast_fat"),
        ("proteina", "audit_breakfast_protein"),
    ],
)
def test_exclusions_determinism_and_input_catalog_immutability(category, excluded):
    allowed = catalog([excluded])
    before = repr(allowed)
    first = SelectorAlimentos.seleccionar_lista(
        category, meal_idx=0, seed=12345, catalogo=allowed
    )
    second = SelectorAlimentos.seleccionar_lista(
        category, meal_idx=0, seed=12345, catalogo=allowed
    )
    assert first == second and excluded not in first and repr(allowed) == before


@pytest.mark.parametrize("category", ["proteina", "carbs", "grasa"])
def test_direct_catalog_also_skips_manual_only_foods(category):
    allowed = catalog()
    foods = {key: dict(value) for key, value in allowed.alimentos.items()}
    food = next(
        name for name in allowed.categorias[category] if name.startswith("audit_")
    )
    foods[food]["auto_generation"] = False
    direct = FoodCatalog(foods, allowed.categorias)
    assert food not in SelectorAlimentos.seleccionar_lista(
        category, meal_idx=0, catalogo=direct
    )
