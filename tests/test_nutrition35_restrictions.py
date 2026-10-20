"""Structured declarations guard automation without inferring clinical rules."""
from dataclasses import FrozenInstanceError

import pytest

from core.food_catalog import FoodRestrictionError
from core.nutrition_restrictions import (
    AllergyDeclaration,
    NutritionRestrictionInputError,
    NutritionRestrictions,
    NutritionRestrictionsChanged,
    ProfessionalNutritionReviewRequired,
)

FOODS = {name: {"kcal": 100} for name in ("huevo", "pollo", "arroz", "aceite", "zanahoria")}
CATEGORIES = {"proteina": ["huevo", "pollo"], "carbs": ["arroz"], "grasa": ["aceite"], "verdura": ["zanahoria"]}


def declaration(**changes):
    return {"version": 1, "status": "reported", "foods": ["huevo"], "other_reported": False, **changes}


def test_unknown_and_none_reported_remain_distinct_without_guarantees():
    unknown = NutritionRestrictions.from_profile(FOODS)
    none = NutritionRestrictions.from_profile(FOODS, allergies=declaration(status="none_reported", foods=[]))
    assert unknown.allergies.status == "not_reported"
    assert none.allergies.status == "none_reported"
    assert unknown.snapshot_digest() != none.snapshot_digest()
    assert set(unknown.catalog(FOODS, CATEGORIES).alimentos) == set(FOODS)
    assert set(none.catalog(FOODS, CATEGORIES).alimentos) == set(FOODS)


@pytest.mark.parametrize("payload", [
    declaration(), declaration(foods=[], other_reported=True),
    declaration(foods=["huevo", "pollo"], other_reported=True),
])
def test_every_reported_allergy_requires_review_without_ingredient_inference(payload):
    restrictions = NutritionRestrictions.from_profile(FOODS, allergies=payload)
    with pytest.raises(ProfessionalNutritionReviewRequired) as result:
        restrictions.catalog(FOODS, CATEGORIES)
    assert result.value.code == "nutrition_professional_review_required"
    assert "huevo" not in str(result.value)
    assert FOODS["huevo"] == {"kcal": 100}


@pytest.mark.parametrize("status", ["not_reported", "none_reported", "reported"])
def test_explicit_review_request_always_guards_generation(status):
    payload = declaration(status=status, foods=["huevo"] if status == "reported" else [])
    restrictions = NutritionRestrictions.from_profile(FOODS, allergies=payload, professional_review_requested=True)
    with pytest.raises(ProfessionalNutritionReviewRequired):
        restrictions.require_automated_generation()


@pytest.mark.parametrize("payload", [
    {}, [], "none", True,
    declaration(version=True), declaration(version=1.0), declaration(version=2),
    declaration(status="approved"), declaration(status=1), declaration(status=None),
    declaration(foods=[]), declaration(status="none_reported"),
    declaration(status="not_reported", foods=[], other_reported=True),
    declaration(foods="huevo"), declaration(foods=["unknown"]), declaration(foods=[True]),
    declaration(foods=[None]), declaration(foods=["huevo"] * 251),
    declaration(other_reported=1), declaration(other_reported="false"),
    {**declaration(), "approved_by_professional": True},
    {**declaration(), "notes": "synthetic free text is not interpreted"},
])
def test_invalid_or_self_approved_declarations_never_become_an_empty_default(payload):
    with pytest.raises(NutritionRestrictionInputError) as result:
        NutritionRestrictions.from_profile(FOODS, allergies=payload)
    assert result.value.code == "nutrition_restrictions_invalid"
    assert "synthetic" not in str(result.value) and "unknown" not in str(result.value)


@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_review_flag_does_not_coerce(value):
    with pytest.raises(NutritionRestrictionInputError):
        NutritionRestrictions.from_profile(FOODS, professional_review_requested=value)


def test_restrictions_and_returned_json_never_share_mutable_input():
    payload = declaration(foods=["pollo", "huevo", "huevo"])
    restrictions = NutritionRestrictions.from_profile(FOODS, allergies=payload)
    digest = restrictions.snapshot_digest()
    payload["foods"].clear()
    exported = restrictions.allergies.as_dict()
    exported["foods"].clear()
    assert restrictions.allergies.foods == ("huevo", "pollo")
    assert restrictions.snapshot_digest() == digest
    with pytest.raises(FrozenInstanceError):
        restrictions.allergies.status = "none_reported"


def test_exclusions_preserve_existing_failure_and_final_plan_validation():
    restrictions = NutritionRestrictions.from_profile(FOODS, excluded_foods=["huevo"])
    catalog = restrictions.catalog(FOODS, CATEGORIES)
    assert catalog.categorias["proteina"] == ("pollo",)
    catalog.validate_plan({"cena": {"alimentos": {"pollo": 100}}})
    with pytest.raises(FoodRestrictionError):
        catalog.validate_plan({"cena": {"alimentos": {"huevo": 100}}})
    assert CATEGORIES["proteina"] == ["huevo", "pollo"]
    with pytest.raises(FoodRestrictionError):
        NutritionRestrictions.from_profile(FOODS, excluded_foods=["huevo", "pollo"]).catalog(FOODS, CATEGORIES)


@pytest.mark.parametrize("changes", [
    {"excluded_foods": ["huevo"]},
    {"allergies": declaration(status="none_reported", foods=[])},
    {"allergies": declaration()},
    {"professional_review_requested": True},
])
def test_changed_declarations_cannot_adopt_an_old_generation(changes):
    original = NutritionRestrictions.from_profile(FOODS)
    current = NutritionRestrictions.from_profile(FOODS, **changes)
    with pytest.raises(NutritionRestrictionsChanged) as result:
        original.require_current(current)
    assert result.value.code == "nutrition_restrictions_changed"
    original.require_current(NutritionRestrictions.from_profile(FOODS))


def test_canonical_exclusion_order_and_duplicates_do_not_invent_a_profile_change():
    first = NutritionRestrictions.from_profile(FOODS, excluded_foods=["huevo", "pollo", "huevo"])
    same = NutritionRestrictions.from_profile(FOODS, excluded_foods=["pollo", "huevo"])
    assert first.snapshot_digest() == same.snapshot_digest()
    first.require_current(same)


@pytest.mark.parametrize("args", [
    {"status": "none_reported", "foods": ("huevo",)},
    {"status": "reported", "foods": ["huevo"]},
    {"status": "reported", "foods": ("huevo", "huevo")},
    {"status": "reported", "foods": (False,)},
])
def test_direct_domain_constructor_also_rejects_inconsistent_records(args):
    with pytest.raises(NutritionRestrictionInputError):
        AllergyDeclaration(**args)
