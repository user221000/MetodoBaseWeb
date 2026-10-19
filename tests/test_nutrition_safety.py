"""Behavior regressions for the published nutrition/profile pathways."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize("field,value", [("edad", -5), ("peso_kg", -80), ("estatura_cm", 0),
    ("grasa_corporal_pct", 150), ("peso_kg", float("nan")), ("peso_kg", float("inf"))])
def test_personal_profile_rejects_invalid_measurements(field, value):
    from web.routes.usuario import PerfilUpdate
    with pytest.raises(ValidationError):
        PerfilUpdate(**{field: value})


def test_partial_client_update_uses_create_contact_contract():
    from api.schemas import ClienteUpdate
    for data in ({"email": "broken"}, {"telefono": "123"}, {"nombre": "   "}):
        with pytest.raises(ValidationError):
            ClienteUpdate(**data)


def _catalog(excluded=()):
    from core.food_catalog import FoodCatalog
    from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS
    return FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, excluded)


def test_total_category_exclusion_fails_and_never_restores_original():
    from core.food_catalog import FoodRestrictionError
    from src.alimentos_base import CATEGORIAS
    proteins = tuple(CATEGORIAS["proteina"])
    with pytest.raises(FoodRestrictionError):
        _catalog(proteins)
    assert tuple(CATEGORIAS["proteina"]) == proteins


def test_catalog_is_deeply_immutable_and_validates_final_output():
    from core.food_catalog import FoodRestrictionError
    catalog = _catalog(["huevo"])
    with pytest.raises(TypeError):
        catalog.alimentos["pechuga_de_pollo"]["kcal"] = 0
    with pytest.raises(TypeError):
        catalog.categorias["proteina"] = ()
    with pytest.raises(FoodRestrictionError):
        catalog.validate_plan({"desayuno": {"alimentos": {"huevo": 120}}})
    with pytest.raises(FoodRestrictionError):
        catalog.validate_plan({"cena": {"proteinas": {"opciones": [{"alimento": "huevo", "gramos": 80}]}}})


def test_concurrent_selectors_and_emergency_adjustments_use_request_catalog():
    from core.generador_comidas import ReajustadorPlan
    from core.selector_alimentos import SelectorAlimentos
    from src.alimentos_base import CATEGORIAS
    original = {key: tuple(value) for key, value in CATEGORIAS.items()}

    def generate(excluded):
        catalog = _catalog(excluded)
        for meal in range(4):
            proteins = SelectorAlimentos.seleccionar_lista("proteina", meal, seed=42, catalogo=catalog)
            assert proteins
            assert not set(proteins).intersection(excluded)
            menu = {"alimentos": {"pechuga_de_pollo": 100}, "kcal_objetivo": 650}
            ReajustadorPlan._agregar_alimento_emergencia(menu, 300, meal, "carbs", catalogo=catalog)
            catalog.validate_plan({"comida": menu})

    groups = [["huevo", "avena", "papa"], ["arroz_blanco", "granola", "nueces"]] * 8
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(generate, groups))
    assert {key: tuple(value) for key, value in CATEGORIAS.items()} == original


def test_option_generation_rejects_excluded_foods_in_final_menu():
    from core.generador_opciones import ConstructorPlanConOpciones
    from core.modelos import ClienteEvaluacion
    from core.motor_nutricional import MotorNutricional
    from tempfile import TemporaryDirectory
    excluded = ["huevo", "avena", "brocoli", "espinaca", "aguacate", "papa"]
    catalog = _catalog(excluded)
    client = ClienteEvaluacion(nombre="Synthetic", id_cliente="NUTRITION_TEST", edad=30,
        peso_kg=80, estatura_cm=175, grasa_corporal_pct=20, nivel_actividad="moderada", objetivo="mantenimiento")
    client = MotorNutricional.calcular_motor(client)
    with TemporaryDirectory() as output:
        plan = ConstructorPlanConOpciones.construir(client, directorio_planes=output, catalogo=catalog)
    catalog.validate_plan(plan)
    for name in ("desayuno", "almuerzo", "comida", "cena"):
        assert plan[name]["proteinas"]["opciones"]
        assert plan[name]["carbohidratos"]["opciones"]
        assert plan[name]["grasas"]["opciones"]


def test_fixed_generation_is_repeatable_and_checks_restrictions_after_adjustments(tmp_path):
    from core.generador_planes import ConstructorPlanNuevo
    from core.modelos import ClienteEvaluacion
    from core.motor_nutricional import MotorNutricional
    catalog = _catalog(["huevo", "avena", "papa", "nueces"])

    def generate():
        client = MotorNutricional.calcular_motor(ClienteEvaluacion(nombre="Synthetic", id_cliente="FIXED_SAFE",
            edad=30, peso_kg=80, estatura_cm=175, grasa_corporal_pct=20,
            nivel_actividad="moderada", objetivo="mantenimiento"))
        plan = ConstructorPlanNuevo.construir(client, directorio_planes=str(tmp_path), catalogo=catalog)
        catalog.validate_plan(plan)
        return {name: data["alimentos"] for name, data in plan.items() if "alimentos" in data}

    assert generate() == generate()
