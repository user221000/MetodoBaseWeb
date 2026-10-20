"""Independent technical probes of the frozen pure nutrition boundary."""
from copy import deepcopy

import pytest

from core.food_catalog import FoodCatalog, FoodRestrictionError
from core.modelos import ClienteEvaluacion
from core.nutrition_restrictions import (
    AllergyDeclaration,
    NutritionRestrictionInputError,
    NutritionRestrictions,
    NutritionRestrictionsChanged,
    ProfessionalNutritionReviewRequired,
    generation_catalog,
)
from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS


@pytest.mark.parametrize("level", ["profile", "allergy"])
@pytest.mark.parametrize("version", [True, 1.0, 0, 2])
def test_version_is_closed_at_each_independent_boundary(level, version):
    payload = NutritionRestrictions.from_profile(ALIMENTOS_BASE).declaration_payload()
    if level == "profile":
        payload["version"] = version
    else:
        payload["allergies"]["version"] = version
    with pytest.raises(NutritionRestrictionInputError):
        NutritionRestrictions.from_declaration(payload, ALIMENTOS_BASE)


@pytest.mark.parametrize("field", ["approved", "professional_approval", "diagnosis"])
@pytest.mark.parametrize("level", ["profile", "allergy"])
def test_client_approval_cannot_become_clinical_clearance(field, level):
    payload = NutritionRestrictions.from_profile(ALIMENTOS_BASE).declaration_payload()
    selected = payload if level == "profile" else payload["allergies"]
    selected[field] = "SYNTHETIC_HEALTH_MARKER"
    with pytest.raises(NutritionRestrictionInputError) as result:
        NutritionRestrictions.from_declaration(payload, ALIMENTOS_BASE)
    assert "SYNTHETIC_HEALTH_MARKER" not in str(result.value)


def test_unknown_is_preserved_through_roundtrip_and_is_not_a_none_reported_claim():
    unknown = NutritionRestrictions.from_declaration(None, ALIMENTOS_BASE)
    explicit_none = NutritionRestrictions.from_profile(ALIMENTOS_BASE, allergies={
        "version": 1, "status": "none_reported", "foods": [], "other_reported": False,
    })
    payload = unknown.declaration_payload()
    restored = NutritionRestrictions.from_declaration(payload, ALIMENTOS_BASE)
    assert restored.allergies.status == "not_reported"
    assert restored.snapshot_digest() == unknown.snapshot_digest()
    assert restored.snapshot_digest() != explicit_none.snapshot_digest()
    payload["allergies"]["foods"].append("huevo")
    assert restored.allergies.foods == ()


@pytest.mark.parametrize("other", [False, True])
@pytest.mark.parametrize("kind", ["fixed", "options"])
def test_supplied_stricter_catalog_does_not_clear_any_reported_allergy(other, kind, monkeypatch, tmp_path):
    from core import generador_opciones, generador_planes

    def forbidden_work(*args, **kwargs):
        raise AssertionError("Automated work reached after declared allergy")

    monkeypatch.setattr(generador_planes, "generar_seed_bloques", forbidden_work)
    monkeypatch.setattr(generador_planes.AjusteCaloricoMensual, "aplicar_ajuste", forbidden_work)
    client = ClienteEvaluacion(nutrition_restrictions=NutritionRestrictions.from_profile(
        ALIMENTOS_BASE, allergies={"version": 1, "status": "reported",
            "foods": [] if other else ["huevo"], "other_reported": other},
    ))
    supplied = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["huevo", "avena"])
    build = (generador_planes.ConstructorPlanNuevo.construir if kind == "fixed"
        else generador_opciones.ConstructorPlanConOpciones.construir)
    with pytest.raises(ProfessionalNutritionReviewRequired):
        build(client, catalogo=supplied, directorio_planes=str(tmp_path))
    assert not list(tmp_path.iterdir())


def test_equal_reported_snapshot_still_cannot_be_finalized():
    restriction = NutritionRestrictions(AllergyDeclaration(status="reported", other_reported=True), ())
    same = NutritionRestrictions.from_declaration(restriction.declaration_payload(), ALIMENTOS_BASE)
    assert same.snapshot_digest() == restriction.snapshot_digest()
    with pytest.raises(ProfessionalNutritionReviewRequired):
        restriction.require_current(same)


def test_supplied_catalog_is_never_broadened_or_mutated_when_profile_excludes_more():
    source_foods = deepcopy(ALIMENTOS_BASE)
    source_categories = deepcopy(CATEGORIAS)
    supplied = FoodCatalog.from_data(source_foods, source_categories, ["avena"])
    restriction = NutritionRestrictions.from_profile(ALIMENTOS_BASE, excluded_foods=["huevo"])
    selected = generation_catalog(restriction, source_foods, source_categories, supplied)
    assert selected.excluidos == frozenset({"avena", "huevo"})
    assert "avena" not in selected.alimentos and "huevo" not in selected.alimentos
    assert "huevo" in supplied.alimentos and "avena" not in supplied.alimentos
    assert source_foods == ALIMENTOS_BASE and source_categories == CATEGORIAS
    with pytest.raises(FoodRestrictionError):
        selected.validate_plan({"nested": [{"alimento": "huevo"}]})


@pytest.mark.parametrize("kind", ["fixed", "options"])
def test_final_catalog_validation_rejects_corruption_after_food_selection(kind, monkeypatch, tmp_path):
    from core import generador_opciones, generador_planes
    from core.motor_nutricional import MotorNutricional

    client = MotorNutricional.calcular_motor(ClienteEvaluacion(
        nombre="Synthetic boundary", id_cliente="SEC35_" + kind, edad=30,
        peso_kg=80, estatura_cm=175, grasa_corporal_pct=20,
        nivel_actividad="moderada", objetivo="mantenimiento",
        nutrition_restrictions=NutritionRestrictions.from_profile(ALIMENTOS_BASE, excluded_foods=["huevo"]),
    ))
    observed = []
    if kind == "fixed":
        original = generador_planes._validar_limites_estrictos_por_plan
        def corrupt(plan, *args, **kwargs):
            result = original(plan, *args, **kwargs)
            result["desayuno"]["alimentos"]["huevo"] = 25
            observed.append(True)
            return result
        monkeypatch.setattr(generador_planes, "_validar_limites_estrictos_por_plan", corrupt)
        # Simulate a separate nutrient validator accepting corrupted food selection.
        monkeypatch.setattr(generador_planes.MealStructureContract, "validar_plan_completo", lambda plan: (True, []))
        build = generador_planes.ConstructorPlanNuevo.construir
    else:
        original = generador_opciones.GeneradorOpcionesEquivalentes.generar_opciones_proteina
        def corrupt(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            result.append({"alimento": "huevo", "gramos": 25})
            observed.append(True)
            return result
        monkeypatch.setattr(generador_opciones.GeneradorOpcionesEquivalentes, "generar_opciones_proteina", corrupt)
        build = generador_opciones.ConstructorPlanConOpciones.construir
    with pytest.raises(FoodRestrictionError):
        build(client, directorio_planes=str(tmp_path))
    assert observed


def test_sensitive_new_declaration_is_absent_from_client_repr_and_error_messages():
    facts = NutritionRestrictions.from_profile(ALIMENTOS_BASE, allergies={
        "version": 1, "status": "reported", "foods": ["huevo"], "other_reported": True,
    })
    client = ClienteEvaluacion(nutrition_restrictions=facts)
    assert "nutrition_restrictions" not in repr(client)
    assert "huevo" not in repr(client) and "other_reported" not in repr(client)
    with pytest.raises(ProfessionalNutritionReviewRequired) as result:
        facts.require_automated_generation()
    assert "huevo" not in str(result.value)
    with pytest.raises(NutritionRestrictionsChanged) as changed:
        facts.require_current(NutritionRestrictions.from_profile(ALIMENTOS_BASE))
    assert "huevo" not in str(changed.value)
