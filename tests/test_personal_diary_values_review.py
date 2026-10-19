"""Independent pure R14 review; no route, persistence or diary completion claim."""
from datetime import date, datetime, timezone
import json
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from web.personal_diary_schemas import MealSelection
from web.services.personal_diary_service import (
    require_calendar_range, require_writable_day, resolve_consumed_meal,
)


def source(raw):
    return SimpleNamespace(id=7, gym_id="personal-review", deleted_at=None, plan_json=raw)


@pytest.mark.parametrize("raw", [pytest.param("[" * 5000 + "0" + "]" * 5000, id="deep-json"), "not-json", "[]", "null"])
def test_corrupt_legacy_source_is_a_structured_domain_error(raw):
    with pytest.raises(HTTPException) as failure:
        resolve_consumed_meal(source(raw), "personal-review", "desayuno", MealSelection(proteinas=0))
    assert failure.value.status_code == 409
    assert failure.value.detail["code"] == "diary_source_unavailable"


def test_legacy_food_without_macros_resolves_catalog_and_snapshot_is_independent():
    from src.alimentos_base import ALIMENTOS_BASE
    food = dict(ALIMENTOS_BASE["huevo"])
    raw = json.dumps({"desayuno": {"proteinas": {"opciones": [{"alimento": "huevo", "gramos": 125}]}}})
    record = source(raw)
    snapshot = resolve_consumed_meal(record, "personal-review", "desayuno", MealSelection(proteinas=0))
    assert snapshot["totals"] == {
        name: round(food[key] * 1.25, 1)
        for name, key in {"kcal": "kcal", "protein_g": "proteina", "carbs_g": "carbs", "fat_g": "grasa"}.items()
    }
    record.plan_json = "null"
    assert snapshot["foods"][0]["grams"] == 125
    snapshot["foods"][0]["macros"]["kcal"] = -1
    assert dict(ALIMENTOS_BASE["huevo"]) == food


def test_unknown_legacy_food_without_verified_macros_does_not_become_zero_consumption():
    raw = json.dumps({"desayuno": {"proteinas": {"opciones": [{"alimento": "unknown-synthetic-food", "gramos": 100}]}}})
    with pytest.raises(HTTPException) as failure:
        resolve_consumed_meal(source(raw), "personal-review", "desayuno", MealSelection(proteinas=0))
    assert failure.value.status_code == 409


def test_deleted_own_plan_cannot_resolve_new_consumption():
    record = source("{}")
    record.deleted_at = datetime(2026, 10, 18, tzinfo=timezone.utc)
    with pytest.raises(HTTPException) as failure:
        resolve_consumed_meal(record, "personal-review", "desayuno", MealSelection())
    assert failure.value.status_code == 404


def test_calendar_exact_inclusive_limit_and_datetime_rejection():
    assert require_calendar_range(date(2026, 1, 1), date(2026, 3, 3)) == (date(2026, 1, 1), date(2026, 3, 3))
    for end in (date(2026, 3, 4), date(2025, 12, 31)):
        with pytest.raises(HTTPException) as failure:
            require_calendar_range(date(2026, 1, 1), end)
        assert failure.value.status_code == 422
    with pytest.raises(HTTPException):
        require_writable_day(datetime(2026, 1, 1), now=datetime(2026, 10, 18, tzinfo=timezone.utc))
