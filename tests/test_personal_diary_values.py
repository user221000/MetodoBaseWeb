"""R14 preparation only: DTO/date/snapshot values, no persistence claim."""
from datetime import date, datetime, timezone
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError


@pytest.mark.parametrize('instant,expected', [
    ('2026-10-19T01:30:00+00:00', '2026-10-18'),
    ('2026-10-19T05:59:59+00:00', '2026-10-18'),
    ('2026-10-19T06:00:00+00:00', '2026-10-19'),
    ('2026-01-01T03:00:00+00:00', '2025-12-31'),
])
def test_diary_day_uses_explicit_mexico_city_midnight(instant, expected):
    from web.services.personal_diary_service import local_today
    assert local_today(datetime.fromisoformat(instant)).isoformat() == expected


def test_diary_clock_rejects_ambiguous_naive_timestamp():
    from web.services.personal_diary_service import local_today
    with pytest.raises(ValueError):
        local_today(datetime(2026, 10, 19, 1, 30))


@pytest.mark.parametrize('patch', [
    {'operation':'water','expected_version':0,'water_ml':-1},
    {'operation':'water','expected_version':0,'water_ml':20001},
    {'operation':'water','expected_version':0,'water_ml':True},
    {'operation':'water','expected_version':'0','water_ml':1500},
    {'operation':'water','expected_version':0,'water_ml':1500,'user_id':'other-account'},
    {'operation':'water','expected_version':0,'water_ml':1500,'gym_id':'other-gym'},
    {'operation':'water','expected_version':0,'water_ml':1500,'timezone':'UTC'},
    {'operation':'meal','expected_version':1,'source_plan_id':1,'meal':'desayuno','selections':{'proteinas':0},'kcal':9999},
    {'operation':'meal','expected_version':1,'source_plan_id':1,'meal':'desayuno','selections':{'proteinas':-1}},
    {'operation':'completion','expected_version':1,'meal':'desayuno','completed':'true'},
])
def test_diary_patch_rejects_invalid_units_authority_and_nutritional_totals(patch):
    from web.personal_diary_schemas import DiaryPatch
    with pytest.raises(ValidationError):
        TypeAdapter(DiaryPatch).validate_python(patch)


def test_operation_dto_keeps_changed_field_independent():
    from web.personal_diary_schemas import DiaryPatch
    patch = TypeAdapter(DiaryPatch).validate_python({'operation':'water','expected_version':2,'water_ml':1500})
    assert patch.model_dump() == {'operation':'water','expected_version':2,'water_ml':1500}


def source_plan(owner='personal-owner'):
    return SimpleNamespace(id=7, gym_id=owner, deleted_at=None, plan_json=json.dumps({
        'desayuno': {'proteinas':{'opciones':[{'alimento':'huevo','gramos':100,'equivalencia':'2 piezas','macros':{'kcal':140,'proteina':12,'carbs':1,'grasa':10}}]},
                     'vegetales':[{'alimento':'tomate','gramos':50,'macros':{'kcal':10,'proteina':0.5,'carbs':2,'grasa':0}}]}
    }))


def test_consumed_food_snapshot_comes_from_own_plan_and_records_actual_source():
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    snapshot = resolve_consumed_meal(source_plan(), 'personal-owner', 'desayuno', MealSelection(proteinas=0,include_vegetables=True), now=datetime(2026,10,19,1,30,tzinfo=timezone.utc))
    assert snapshot['source_plan_id'] == 7
    assert [food['food_id'] for food in snapshot['foods']] == ['huevo','tomate']
    assert snapshot['foods'][0]['grams'] == 100
    assert snapshot['totals'] == {'kcal':150.0,'protein_g':12.5,'carbs_g':3.0,'fat_g':10.0}
    assert snapshot['recorded_at'] == '2026-10-19T01:30:00+00:00'


def test_other_owner_plan_does_not_resolve_any_food():
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    with pytest.raises(HTTPException) as rejected:
        resolve_consumed_meal(source_plan('other-owner'), 'personal-owner', 'desayuno', MealSelection(proteinas=0))
    assert rejected.value.status_code == 404


def test_invalid_plan_option_never_becomes_a_zero_or_fake_consumption():
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    with pytest.raises(HTTPException) as rejected:
        resolve_consumed_meal(source_plan(), 'personal-owner', 'desayuno', MealSelection(proteinas=9))
    assert rejected.value.status_code == 422


def test_empty_selections_clear_meal_without_counting_vegetables_from_menu():
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    snapshot = resolve_consumed_meal(source_plan(), 'personal-owner', 'desayuno', MealSelection())
    assert snapshot['foods'] == [] and snapshot['totals']['kcal'] == 0


def test_vegetables_are_only_consumed_when_explicitly_selected():
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    snapshot = resolve_consumed_meal(source_plan(), 'personal-owner', 'desayuno', MealSelection(proteinas=0))
    assert [food['food_id'] for food in snapshot['foods']] == ['huevo']
    assert snapshot['totals']['kcal'] == 140


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, True, 10**1000], ids=['nan','infinity','negative','boolean','overflow'])
def test_corrupt_saved_plan_macros_fail_closed(bad):
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    source = source_plan()
    data = json.loads(source.plan_json)
    data['desayuno']['proteinas']['opciones'][0]['macros']['kcal'] = bad
    source.plan_json = json.dumps(data)
    with pytest.raises(HTTPException) as rejected:
        resolve_consumed_meal(source, 'personal-owner', 'desayuno', MealSelection(proteinas=0))
    assert rejected.value.status_code == 409


def test_future_write_is_rejected_and_calendar_range_is_bounded():
    from web.services.personal_diary_service import require_writable_day, require_calendar_range
    now = datetime(2026,10,19,1,30,tzinfo=timezone.utc)
    assert require_writable_day(date(2026,10,18), now=now) == date(2026,10,18)
    with pytest.raises(HTTPException) as rejected:
        require_writable_day(date(2026,10,19), now=now)
    assert rejected.value.status_code == 422
    with pytest.raises(HTTPException):
        require_calendar_range(date(2026,1,1),date(2026,10,1))
