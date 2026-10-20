"""Closed DTO and corrupt-persistence boundaries for structured declarations."""
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from api.schemas import ClienteCreate, ClienteUpdate
from core.nutrition_restrictions import (
    NutritionRestrictionInputError,
    NutritionRestrictions,
)
from src.alimentos_base import ALIMENTOS_BASE
from web.profile_schemas import NutritionProfileUpdate
from web.services.nutrition_profiles import (
    MAX_DECLARATION_BYTES,
    capture_profile,
    encode_declaration,
)


def declaration(*, reported=False, review=False):
    payload = NutritionRestrictions.from_profile(ALIMENTOS_BASE).declaration_payload()
    payload["professional_review_requested"] = review
    if reported:
        payload["allergies"] = {"version": 1, "status": "reported", "foods": ["huevo"], "other_reported": False}
    return payload


@pytest.mark.parametrize("schema", [ClienteUpdate, NutritionProfileUpdate])
def test_partial_profile_declares_facts_and_never_adds_approval_or_duplicates_exclusions(schema):
    original = declaration(reported=True)
    dto = schema(restricciones_nutricionales=original)
    encoded = encode_declaration(dto.restricciones_nutricionales)
    original["allergies"]["foods"].clear()
    captured = capture_profile(SimpleNamespace(nutrition_restrictions_json=encoded, alimentos_excluidos='["avena"]'))
    assert captured.allergies.foods == ("huevo",)
    assert captured.excluded_foods == ("avena",)
    assert "alimentos_excluidos" not in json.loads(encoded)
    assert schema().model_dump(exclude_unset=True) == {}
    assert schema(restricciones_nutricionales=None).restricciones_nutricionales is None


@pytest.mark.parametrize("change", [
    {"version": True}, {"version": 2}, {"professional_review_requested": 1},
    {"professional_review_requested": "false"}, {"allergies": None},
    {"approved_by_professional": True}, {"excluded_foods": ["huevo"]},
])
@pytest.mark.parametrize("schema", [ClienteCreate, ClienteUpdate, NutritionProfileUpdate])
def test_all_profile_adapters_share_strict_declared_facts(schema, change):
    fields = {"nombre": "Synthetic", "edad": 30, "peso_kg": 75, "estatura_cm": 175,
              "nivel_actividad": "moderada", "objetivo": "mantenimiento"} if schema is ClienteCreate else {}
    with pytest.raises(ValidationError):
        schema(**fields, restricciones_nutricionales={**declaration(), **change})


@pytest.mark.parametrize("raw", [
    "null", "[]", "{}", "true", "1", "broken-json",
    '{"version":1,"version":1,"allergies":{},"professional_review_requested":false}',
    " "*(MAX_DECLARATION_BYTES+1),
])
def test_corrupt_stored_declarations_fail_instead_of_becoming_unknown(raw):
    with pytest.raises(NutritionRestrictionInputError) as error:
        capture_profile(SimpleNamespace(nutrition_restrictions_json=raw, alimentos_excluidos=None))
    assert str(error.value) == "Revisa la declaración de restricciones alimentarias."


def test_only_SQL_null_preserves_the_legacy_unknown_declaration():
    value = capture_profile(SimpleNamespace(nutrition_restrictions_json=None, alimentos_excluidos=None))
    assert value.allergies.status == "not_reported" and not value.professional_review_requested
    with pytest.raises(NutritionRestrictionInputError):
        encode_declaration(None)


@pytest.mark.parametrize("raw", ["null", "{}", '["unknown"]', '["huevo",1]'])
def test_corrupt_existing_exclusions_are_not_discarded(raw):
    with pytest.raises(NutritionRestrictionInputError):
        capture_profile(SimpleNamespace(nutrition_restrictions_json=None, alimentos_excluidos=raw))
