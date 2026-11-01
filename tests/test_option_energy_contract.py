"""Independent option choices must describe real, bounded combinations."""

from copy import deepcopy
from itertools import product

import pytest

from core import generador_opciones as engine
from core.food_catalog import FoodCatalog, FoodRestrictionError
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS

GROUPS = ("proteinas", "carbohidratos", "grasas")
MEALS = ("desayuno", "almuerzo", "comida", "cena")


def client(**values):
    return MotorNutricional.calcular_motor(
        ClienteEvaluacion(
            **{
                "nombre": "Synthetic energy contract",
                "id_cliente": "OPTION_ENERGY_001",
                "edad": 30,
                "peso_kg": 68,
                "estatura_cm": 175,
                "grasa_corporal_pct": 25,
                "nivel_actividad": "moderada",
                "objetivo": "deficit",
                **values,
                "factor_actividad": 1.55,
            }
        )
    )


def raw_nutrients(catalog, rows):
    return {
        macro: sum(
            catalog.alimentos[row["alimento"]][macro] * row["gramos"] / 100
            for row in rows
        )
        for macro in ("proteina", "carbs", "grasa", "kcal")
    }


def assert_energy_contract(plan, catalog):
    actual_day = 0
    minimum_day = 0
    maximum_day = 0
    for name in MEALS:
        meal = plan[name]
        choices = [meal[group]["opciones"] for group in GROUPS]
        # Do not use stored option macros or the engine's range calculation as
        # the oracle: recompute every combination from the request food data.
        combinations = [
            raw_nutrients(catalog, [*choice, *meal["vegetales"]])
            for choice in product(*choices)
        ]
        energies = [row["kcal"] for row in combinations]
        assert all(
            abs(energy / meal["kcal_objetivo"] - 1) <= 0.05 + 1e-10
            for energy in energies
        )
        assert meal["energia_min"] == pytest.approx(min(energies))
        assert meal["energia_max"] == pytest.approx(max(energies))
        assert meal["desviacion_pct"] == pytest.approx(
            max(abs(energy / meal["kcal_objetivo"] - 1) for energy in energies) * 100
        )
        base = [
            meal[group]["opciones"][meal["base_selection"][group]] for group in GROUPS
        ]
        actual = raw_nutrients(catalog, [*base, *meal["vegetales"]])
        assert meal["kcal_real"] == pytest.approx(actual["kcal"])
        assert meal["macros_reales"] == pytest.approx(actual)
        for group, macro in zip(GROUPS, ("proteina", "carbs", "grasa")):
            assert meal[group]["num_opciones"] == len(meal[group]["opciones"])
            assert meal[group]["aporte_referencia"] == pytest.approx(
                raw_nutrients(catalog, [base[GROUPS.index(group)]])[macro]
            )
            for option in meal[group]["opciones"]:
                assert option["macros"] == pytest.approx(
                    raw_nutrients(catalog, [option])
                )
        for row in [
            *meal["vegetales"],
            *(option for choices_in_group in choices for option in choices_in_group),
        ]:
            assert MEALS.index(name) in catalog.alimentos[row["alimento"]]["meal_idx"]
            assert type(row["gramos"]) is int and row["gramos"] > 0
            assert (
                engine._portion_bounds(row["alimento"])[0]
                <= row["gramos"]
                <= engine._portion_bounds(row["alimento"])[1]
            )
        assert sum(row["gramos"] for row in meal["vegetales"]) == 125
        actual_day += actual["kcal"]
        minimum_day += min(energies)
        maximum_day += max(energies)
    metadata = plan["metadata"]
    assert metadata["kcal_totales"] == pytest.approx(actual_day)
    assert metadata["energia_min"] == pytest.approx(minimum_day)
    assert metadata["energia_max"] == pytest.approx(maximum_day)
    assert metadata["opciones_por_comida"] == {
        name: {group: len(plan[name][group]["opciones"]) for group in GROUPS}
        for name in MEALS
    }


@pytest.mark.parametrize("plan_number", [1, 4])
@pytest.mark.parametrize(
    "values",
    [{}, {"peso_kg": 80, "grasa_corporal_pct": 18, "objetivo": "mantenimiento"}],
)
def test_real_catalog_every_independent_choice_has_valid_energy(
    tmp_path, plan_number, values
):
    catalog = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS)
    plan = engine.ConstructorPlanConOpciones.construir(
        client(**values),
        plan_numero=plan_number,
        directorio_planes=str(tmp_path),
        catalogo=catalog,
    )
    assert_energy_contract(plan, catalog)
    assert plan["metadata"]["kcal_objetivo"] == pytest.approx(
        client(**values).kcal_objetivo
    )
    assert plan["metadata"]["kcal_totales"] != plan["metadata"]["kcal_objetivo"]


def synthetic_catalog(
    *, excluded=(), vegetables=3, alternatives=True, invalid_meals=False
):
    foods = {}
    categories = {key: [] for key in ("proteina", "carbs", "grasa", "verdura", "fruta")}
    # Data with an exact, feasible joint solution and deliberately mixed
    # alternatives; swapping one group must account for its other nutrients.
    values = {
        "proteina": [(25, 0, 0), (25, 20, 15)],
        "carbs": [(0, 50, 0), (10, 50, 20)],
        "grasa": [(0, 0, 75), (20, 20, 75)],
        "verdura": [(1, 4, 0)] * vegetables,
    }
    for category, entries in values.items():
        for index, (protein, carbs, fat) in enumerate(entries):
            if not alternatives and category != "verdura" and index:
                continue
            food = f"synthetic_{category}_{index}"
            foods[food] = {
                "proteina": protein,
                "carbs": carbs,
                "grasa": fat,
                "kcal": 4 * protein + 4 * carbs + 9 * fat,
                "meal_idx": [2]
                if invalid_meals and category == "grasa"
                else [0, 1, 2, 3],
            }
            categories[category].append(food)
    return FoodCatalog.from_data(foods, categories, excluded)


def test_joint_solution_counts_all_nutrients_and_prunes_unsafe_alternatives(
    monkeypatch, tmp_path
):
    catalog = synthetic_catalog()
    monkeypatch.setattr(
        engine.SelectorAlimentos,
        "seleccionar_lista",
        lambda macro, **kwargs: list(catalog.categorias[macro]),
    )
    plan = engine.ConstructorPlanConOpciones.construir(
        client(), directorio_planes=str(tmp_path), catalogo=catalog
    )
    assert_energy_contract(plan, catalog)
    assert all(
        len(plan[name][group]["opciones"]) == 1 for name in MEALS for group in GROUPS
    )
    assert plan["metadata"]["num_opciones_solicitadas"] == 3


@pytest.mark.parametrize("vegetable_count", [1, 2, 3])
def test_vegetable_125g_total_is_not_truncated_for_small_pools(
    vegetable_count, tmp_path
):
    catalog = synthetic_catalog(vegetables=vegetable_count, alternatives=False)
    plan = engine.ConstructorPlanConOpciones.construir(
        client(), directorio_planes=str(tmp_path), catalogo=catalog
    )
    assert_energy_contract(plan, catalog)


def test_vegetable_limits_are_respected_by_redistributing_existing_total(
    monkeypatch, tmp_path
):
    catalog = synthetic_catalog(vegetables=4, alternatives=False)
    monkeypatch.setattr(
        engine,
        "LIMITES_ALIMENTOS",
        {food: 40 for food in catalog.categorias["verdura"]},
    )
    plan = engine.ConstructorPlanConOpciones.construir(
        client(), directorio_planes=str(tmp_path), catalogo=catalog
    )
    assert_energy_contract(plan, catalog)
    assert all(len(plan[name]["vegetales"]) == 4 for name in MEALS)


@pytest.mark.parametrize(
    "failure",
    ["unavailable_meal", "infeasible_caps", "infeasible_vegetables", "negative_carbs"],
)
def test_infeasible_constraints_fail_closed(failure, monkeypatch, tmp_path):
    catalog = synthetic_catalog(
        alternatives=False, invalid_meals=failure == "unavailable_meal"
    )
    actor = client()
    if failure == "infeasible_caps":
        monkeypatch.setattr(
            engine,
            "LIMITES_ALIMENTOS",
            {food: 1 for food in catalog.categorias["carbs"]},
        )
    elif failure == "infeasible_vegetables":
        monkeypatch.setattr(
            engine,
            "LIMITES_ALIMENTOS",
            {food: 1 for food in catalog.categorias["verdura"]},
        )
    elif failure == "negative_carbs":
        actor.carbs_g = -20
    with pytest.raises(FoodRestrictionError):
        engine.ConstructorPlanConOpciones.construir(
            actor, directorio_planes=str(tmp_path), catalogo=catalog
        )


def test_excluding_all_breakfast_vegetables_never_restores_another_meals_foods(
    tmp_path,
):
    original = synthetic_catalog(alternatives=False)
    foods = {key: dict(value) for key, value in original.alimentos.items()}
    for food in original.categorias["verdura"]:
        foods[food]["meal_idx"] = [1, 2, 3]
    first = original.categorias["verdura"][0]
    foods[first]["meal_idx"] = [0, 1, 2, 3]
    catalog = FoodCatalog.from_data(foods, original.categorias, [first])
    assert catalog.categorias["verdura"]
    with pytest.raises(FoodRestrictionError):
        engine.ConstructorPlanConOpciones.construir(
            client(), directorio_planes=str(tmp_path), catalogo=catalog
        )


def test_request_snapshot_exclusions_autogeneration_meals_and_repeatability(tmp_path):
    foods = deepcopy(ALIMENTOS_BASE)
    categories = deepcopy(CATEGORIAS)
    excluded = ("huevo", "avena", "aceite_de_oliva")
    foods["audit_manual_only"] = {
        "proteina": 50,
        "carbs": 0,
        "grasa": 0,
        "kcal": 200,
        "meal_idx": [0, 1, 2, 3],
        "auto_generation": False,
    }
    categories["proteina"].append("audit_manual_only")
    catalog = FoodCatalog.from_data(foods, categories, excluded)
    plans = [
        engine.ConstructorPlanConOpciones.construir(
            client(), directorio_planes=str(tmp_path), catalogo=catalog
        )
        for _ in range(2)
    ]
    assert {name: plans[0][name] for name in MEALS} == {
        name: plans[1][name] for name in MEALS
    }
    for plan in plans:
        assert_energy_contract(plan, catalog)
        catalog.validate_plan(plan)
        assert not any(
            food in repr({name: plan[name] for name in MEALS})
            for food in ("audit_manual_only", *excluded)
        )
    assert "huevo" in ALIMENTOS_BASE and "audit_manual_only" not in ALIMENTOS_BASE


def test_final_validation_still_rejects_a_corrupted_selected_option(
    monkeypatch, tmp_path
):
    catalog = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["huevo"])
    original = engine._build_meal
    observed = []

    def corrupt(*args, **kwargs):
        meal = original(*args, **kwargs)
        meal["proteinas"]["opciones"].append({"alimento": "huevo", "gramos": 25})
        observed.append(True)
        return meal

    monkeypatch.setattr(engine, "_build_meal", corrupt)
    with pytest.raises(FoodRestrictionError):
        engine.ConstructorPlanConOpciones.construir(
            client(), directorio_planes=str(tmp_path), catalogo=catalog
        )
    assert observed
