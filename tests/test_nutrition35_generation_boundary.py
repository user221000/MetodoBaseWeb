"""Every supported plan constructor must honor a captured declaration first."""
import pytest

from core.food_catalog import FoodCatalog
from core.modelos import ClienteEvaluacion
from core.nutrition_restrictions import (
    NutritionRestrictionInputError,
    NutritionRestrictions,
    ProfessionalNutritionReviewRequired,
)
from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS


class AutomatedWorkReached(AssertionError):
    """The generation reached seeds/adjustments before the declaration guard."""


def _stop_automated_work(*args, **kwargs):
    raise AutomatedWorkReached("The declared profile reached automated work")


@pytest.fixture(params=["fixed", "options"])
def constructor(request, monkeypatch):
    from core import generador_opciones, generador_planes

    monkeypatch.setattr(generador_planes, "generar_seed_bloques", _stop_automated_work)
    monkeypatch.setattr(generador_planes.AjusteCaloricoMensual, "aplicar_ajuste", _stop_automated_work)
    if request.param == "fixed":
        return generador_planes.ConstructorPlanNuevo.construir
    return generador_opciones.ConstructorPlanConOpciones.construir


@pytest.mark.parametrize("supplied_catalog", [False, True])
@pytest.mark.parametrize("declared", ["allergy", "review"])
def test_declared_review_stops_before_automated_work(constructor, supplied_catalog, declared, tmp_path):
    client = ClienteEvaluacion(nombre="Synthetic declaration", id_cliente="BOUNDARY35")
    allergies = {"version": 1, "status": "reported", "foods": [], "other_reported": True}
    client.nutrition_restrictions = NutritionRestrictions.from_profile(
        ALIMENTOS_BASE, allergies=allergies if declared == "allergy" else None,
        professional_review_requested=declared == "review",
    )
    options = {"catalogo": FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS)} if supplied_catalog else {}
    with pytest.raises(ProfessionalNutritionReviewRequired) as result:
        constructor(client, directorio_planes=str(tmp_path), **options)
    assert result.value.code == "nutrition_professional_review_required"
    assert list(tmp_path.iterdir()) == []


def test_invalid_attached_declaration_cannot_be_silently_ignored(constructor, tmp_path):
    client = ClienteEvaluacion(nombre="Synthetic declaration", id_cliente="INVALID35")
    client.nutrition_restrictions = {"professional_review_requested": True}
    with pytest.raises(NutritionRestrictionInputError):
        constructor(client, directorio_planes=str(tmp_path))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["fixed", "options"])
def test_real_constructor_preserves_both_profile_and_supplied_catalog_exclusions(kind, tmp_path):
    from core.generador_opciones import ConstructorPlanConOpciones
    from core.generador_planes import ConstructorPlanNuevo
    from core.motor_nutricional import MotorNutricional

    client = MotorNutricional.calcular_motor(ClienteEvaluacion(
        nombre="Synthetic exclusions", id_cliente="PROFILE35_"+kind, edad=30,
        peso_kg=80, estatura_cm=175, grasa_corporal_pct=20,
        nivel_actividad="moderada", objetivo="mantenimiento",
        nutrition_restrictions=NutritionRestrictions.from_profile(ALIMENTOS_BASE, excluded_foods=["huevo"]),
    ))
    supplied = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["avena"])
    build = ConstructorPlanNuevo.construir if kind == "fixed" else ConstructorPlanConOpciones.construir
    plan = build(client, directorio_planes=str(tmp_path), catalogo=supplied)
    FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["huevo", "avena"]).validate_plan(plan)
    assert "huevo" in supplied.alimentos and "avena" not in supplied.alimentos
    assert supplied.excluidos == frozenset({"avena"})
    assert "huevo" in ALIMENTOS_BASE and "avena" in ALIMENTOS_BASE


def test_closed_declaration_roundtrip_preserves_unknown_and_exclusions_separately():
    original = NutritionRestrictions.from_profile(ALIMENTOS_BASE, excluded_foods=["huevo"])
    payload = original.declaration_payload()
    assert set(payload) == {"version", "allergies", "professional_review_requested"}
    assert payload["allergies"]["status"] == "not_reported"
    restored = NutritionRestrictions.from_declaration(payload, ALIMENTOS_BASE, excluded_foods=["huevo"])
    original.require_current(restored)
    payload["allergies"]["status"] = "none_reported"
    assert original.allergies.status == "not_reported"
    assert "nutrition_restrictions=" not in repr(ClienteEvaluacion(nutrition_restrictions=original))


@pytest.mark.parametrize("change", [
    {"version": True}, {"version": 2}, {"allergies": None},
    {"professional_review_requested": 1}, {"professional_review_requested": "false"},
    {"approved_by_professional": True}, {"excluded_foods": []}, {"notes": "synthetic"},
])
def test_closed_profile_declaration_rejects_coercion_approval_and_duplicate_exclusion_fields(change):
    payload = NutritionRestrictions.from_profile(ALIMENTOS_BASE).declaration_payload()
    with pytest.raises(NutritionRestrictionInputError):
        NutritionRestrictions.from_declaration({**payload, **change}, ALIMENTOS_BASE)
