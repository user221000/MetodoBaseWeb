"""Emergency/rebalancing paths must keep the same request food boundaries."""

from copy import deepcopy

import pytest

from core import generador_comidas as helper
from core.food_catalog import FoodCatalog, FoodRestrictionError


@pytest.fixture
def catalog(monkeypatch):
    foods = {
        "audit_protein": {"proteina": 25, "carbs": 0, "grasa": 0, "kcal": 100},
        "audit_carb": {"proteina": 0, "carbs": 50, "grasa": 0, "kcal": 200},
        "audit_fat": {"proteina": 0, "carbs": 0, "grasa": 100, "kcal": 900},
        "audit_vegetable": {"proteina": 1, "carbs": 4, "grasa": 0, "kcal": 20},
        "avena": {"proteina": 0, "carbs": 50, "grasa": 0, "kcal": 200},
        "aguacate": {"proteina": 0, "carbs": 0, "grasa": 100, "kcal": 900},
        "pechuga_de_pollo": {"proteina": 25, "carbs": 0, "grasa": 0, "kcal": 100},
        "espinaca": {"proteina": 1, "carbs": 4, "grasa": 0, "kcal": 20},
    }
    categories = {
        "proteina": ["audit_protein", "pechuga_de_pollo"],
        "carbs": ["audit_carb", "avena"],
        "grasa": ["audit_fat", "aguacate"],
        "verdura": ["audit_vegetable", "espinaca"],
        "fruta": [],
    }
    for food, row in foods.items():
        row["meal_idx"] = [0, 1, 2, 3] if food.startswith("audit_") else [2]
    monkeypatch.setattr(
        helper,
        "LIMITES_ALIMENTOS",
        {
            "audit_protein": 120,
            "audit_carb": 100,
            "audit_fat": 20,
            "audit_vegetable": 50,
        },
    )
    monkeypatch.setattr(
        helper,
        "LIMITES_DUROS_ALIMENTOS",
        {
            "audit_protein": 100,
            "audit_carb": 150,
            "audit_fat": 25,
            "audit_vegetable": 100,
        },
    )
    return FoodCatalog.from_data(foods, categories)


@pytest.mark.parametrize(
    "kind,expected", [("carbs", "audit_carb"), ("grasa", "audit_fat")]
)
def test_emergency_uses_eligible_new_foods_instead_of_wrong_meal_fallbacks(
    catalog, kind, expected
):
    meal = {"alimentos": {}, "kcal_objetivo": 150}
    helper.ReajustadorPlan._agregar_alimento_emergencia(
        meal, 150, 0, kind, catalogo=catalog
    )
    assert expected in meal["alimentos"]
    assert set(meal["alimentos"]) == {expected}
    assert meal["alimentos"][expected] <= {"audit_carb": 100, "audit_fat": 20}[expected]


def test_protein_fallback_never_restores_wrong_meal_chicken(catalog):
    result, _, _ = helper.CalculadorGramosNuevo.asignar_proteina_estructural(
        25, ["audit_protein"], 0, catalogo=catalog
    )
    assert set(result) == {"audit_protein"} and result["audit_protein"] <= 100


def test_vegetable_base_uses_request_eligibility_and_catalog_cap(catalog):
    assert helper.CalculadorGramosNuevo.insertar_vegetal_base(0, catalogo=catalog) == {
        "audit_vegetable": 50
    }


@pytest.mark.parametrize(
    "food,expected",
    [
        ("audit_protein", 100),
        ("audit_carb", 100),
        ("audit_fat", 20),
        ("audit_vegetable", 50),
        ("avena", 300),
    ],
)
def test_maximum_portion_is_the_stricter_existing_limit_without_grace(
    catalog, food, expected
):
    assert (
        helper.ValidadorEnergia._obtener_limite_maximo(food, catalogo=catalog)
        == expected
    )


def test_enforcement_recomputes_energy_after_strict_clipping(catalog):
    meal = {
        "alimentos": {"audit_carb": 150},
        "kcal_objetivo": 300,
        "kcal_real": 300,
        "desviacion_pct": 0,
    }
    result = helper.ReajustadorPlan._enforce_limites_duros(meal, catalogo=catalog)
    assert result["alimentos"]["audit_carb"] == 100
    assert result["kcal_real"] == 200
    assert result["desviacion_pct"] == pytest.approx(100 / 3)


def test_strict_clip_can_still_finish_on_target_and_recomputes_both_fields(catalog):
    meal = {
        "alimentos": {"audit_carb": 105},
        "kcal_objetivo": 200,
        "kcal_real": 210,
        "desviacion_pct": 5,
    }
    result = helper.ReajustadorPlan._enforce_limites_duros(meal, catalogo=catalog)
    assert result["alimentos"] == {"audit_carb": 100}
    assert result["kcal_real"] == 200 and result["desviacion_pct"] == 0


@pytest.mark.parametrize("version", [1, 2])
def test_redistribution_cannot_expand_past_catalog_or_hard_limit(catalog, version):
    meal = {"alimentos": {"audit_carb": 95}}
    method = (
        helper.ValidadorEnergia._redistribuir_kcals_respetando_limites
        if version == 1
        else helper.ValidadorEnergia._redistribuir_kcals_respetando_limites_v2
    )
    method(meal, 100, catalogo=catalog)
    assert meal["alimentos"]["audit_carb"] <= 100


def test_energy_validator_does_not_accept_an_overlimit_but_on_target_meal(catalog):
    meal = {"alimentos": {"audit_carb": 200}}
    result = helper.ValidadorEnergia.validar_y_ajustar(
        meal, 400, meal_idx=0, catalogo=catalog
    )
    assert result["alimentos"]["audit_carb"] <= 100
    assert result["kcal_real"] <= 200
    assert result["desviacion_pct"] >= 50


@pytest.mark.parametrize("method", ["adjust", "rebalance"])
def test_wrong_meal_existing_food_is_rejected_instead_of_counted_or_expanded(
    catalog, method
):
    meal = {"alimentos": {"avena": 60}, "kcal_objetivo": 300}
    with pytest.raises(FoodRestrictionError):
        if method == "adjust":
            helper.ValidadorEnergia.validar_y_ajustar(
                meal, 300, meal_idx=0, catalogo=catalog
            )
        else:
            helper.ReajustadorPlan._reajustar_comida_agresivo(
                meal, 0, 5, catalogo=catalog
            )


@pytest.mark.parametrize(
    "method", ["new_protein", "iterative", "emergency", "vegetable"]
)
def test_direct_request_catalog_manual_only_food_is_never_selected(catalog, method):
    foods = {food: dict(row) for food, row in catalog.alimentos.items()}
    for food in ("pechuga_de_pollo", "avena", "aguacate", "espinaca"):
        foods[food]["meal_idx"] = [0, 1, 2, 3]
        foods[food]["auto_generation"] = False
    direct = FoodCatalog(foods, catalog.categorias)
    if method == "new_protein":
        result, _, _ = helper.CalculadorGramosNuevo.asignar_proteina_estructural(
            25, ["pechuga_de_pollo", "audit_protein"], 0, catalogo=direct
        )
    elif method == "iterative":
        result = helper.CalculadorGramos.calcular_iterativo(
            40, "carbs", ["avena", "audit_carb"], 0, catalogo=direct
        )
    elif method == "vegetable":
        result = helper.CalculadorGramosNuevo.insertar_vegetal_base(0, catalogo=direct)
    else:
        meal = {"alimentos": {}}
        helper.ReajustadorPlan._agregar_alimento_emergencia(
            meal, 150, 0, "carbs", catalogo=direct
        )
        result = meal["alimentos"]
    assert result and all(food.startswith("audit_") for food in result)


def test_iterative_and_simple_portions_do_not_bypass_caps(catalog):
    result = helper.CalculadorGramos.calcular_iterativo(
        500, "carbs", ["audit_carb"], 0, catalogo=catalog
    )
    assert result["audit_carb"] <= 100
    assert (
        helper.CalculadorGramos.calcular(500, "audit_carb", "carbs", catalogo=catalog)
        <= 100
    )


def test_no_eligible_emergency_candidate_does_not_restore_forbidden_category(catalog):
    foods = {food: dict(row) for food, row in catalog.alimentos.items()}
    foods["audit_carb"]["meal_idx"] = [2]
    direct = FoodCatalog.from_data(foods, catalog.categorias)
    meal = {"alimentos": {"audit_protein": 80}}
    before = deepcopy(meal)
    helper.ReajustadorPlan._agregar_alimento_emergencia(
        meal, 500, 0, "carbs", catalogo=direct
    )
    assert meal == before


@pytest.mark.parametrize(
    "weight,fat,goal", [(80, 18, "mantenimiento"), (68, 25, "deficit")]
)
def test_fixed_constructor_final_output_respects_caps_and_energy(
    weight, fat, goal, tmp_path
):
    from config.constantes import FACTORES_ACTIVIDAD, LIMITES_DUROS_ALIMENTOS
    from core.generador_planes import ConstructorPlanNuevo
    from core.modelos import ClienteEvaluacion
    from core.motor_nutricional import MotorNutricional
    from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS, LIMITES_ALIMENTOS

    snapshot = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS)
    client = MotorNutricional.calcular_motor(
        ClienteEvaluacion(
            nombre="Synthetic strict portions",
            id_cliente="HELPER_STRICT_001",
            edad=30,
            peso_kg=weight,
            estatura_cm=175,
            grasa_corporal_pct=fat,
            nivel_actividad="moderada",
            factor_actividad=FACTORES_ACTIVIDAD["moderada"],
            objetivo=goal,
        )
    )
    plan = ConstructorPlanNuevo.construir(
        client, directorio_planes=str(tmp_path), catalogo=snapshot
    )
    for index, name in enumerate(("desayuno", "almuerzo", "comida", "cena")):
        meal = plan[name]
        actual = 0
        for food, grams in meal["alimentos"].items():
            assert (
                grams
                <= min(
                    LIMITES_ALIMENTOS.get(food, 300),
                    LIMITES_DUROS_ALIMENTOS.get(food, 300),
                )
                + 1e-8
            )
            assert index in snapshot.alimentos[food]["meal_idx"]
            assert snapshot.alimentos[food].get("auto_generation", True)
            actual += snapshot.alimentos[food]["kcal"] * grams / 100
        assert meal["kcal_real"] == pytest.approx(actual)
        assert abs(actual / meal["kcal_objetivo"] - 1) <= 0.05 + 1e-10


def test_impossible_strict_caps_never_publish_an_invalid_fixed_plan(
    catalog, monkeypatch, tmp_path
):
    from core.generador_planes import ConstructorPlanNuevo, PlanInvalidoError
    from core.modelos import ClienteEvaluacion
    from core.motor_nutricional import MotorNutricional

    monkeypatch.setattr(
        helper, "LIMITES_ALIMENTOS", {food: 1 for food in catalog.alimentos}
    )
    client = MotorNutricional.calcular_motor(
        ClienteEvaluacion(
            nombre="Synthetic impossible caps",
            id_cliente="HELPER_IMPOSSIBLE",
            edad=30,
            peso_kg=68,
            estatura_cm=175,
            grasa_corporal_pct=25,
            nivel_actividad="moderada",
            factor_actividad=1.55,
            objetivo="deficit",
        )
    )
    with pytest.raises((FoodRestrictionError, PlanInvalidoError)):
        ConstructorPlanNuevo.construir(
            client, directorio_planes=str(tmp_path), catalogo=catalog
        )
