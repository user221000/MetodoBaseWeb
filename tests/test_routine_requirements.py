"""Request bounds reject fabricated capability, identity and malformed inputs."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from web.schemas_routines import RoutineRequirements


def requirements():
    return {"activity_level": "leve", "experience": "inicial", "goal": "fuerza_general",
            "equipment": ["machine", "cable", "dumbbell", "bench", "bodyweight"],
            "exercises_per_session": 6, "days_per_week": 3, "variant": 0,
            "excluded_exercises": [], "session_minutes": 60}


@pytest.mark.parametrize("field,value", [
    ("activity_level", "elite"), ("activity_level", 2), ("experience", "moderada"),
    ("goal", "curar_lesion"), ("equipment", []), ("equipment", ["unknown"]),
    ("equipment", ["machine", "machine"]),
    ("equipment", ["machine", "cable", "dumbbell", "barbell", "bench", "bodyweight", "machine"]),
    ("exercises_per_session", 5), ("exercises_per_session", 9),
    ("exercises_per_session", "6"), ("exercises_per_session", 6.0),
    ("days_per_week", 2), ("days_per_week", 7), ("days_per_week", True),
    ("variant", -1), ("variant", 10), ("variant", True), ("variant", "0"),
    ("session_minutes", 30), ("session_minutes", 120), ("session_minutes", 60.0),
    ("session_minutes", "60"), ("session_minutes", True),
    ("excluded_exercises", ["leg-press", "leg-press"]),
    ("excluded_exercises", ["<script>"]), ("excluded_exercises", ["a" * 81]),
    ("excluded_exercises", ["exercise-" + str(index) for index in range(121)]),
    ("client_id", "another-client"), ("gym_id", "another-tenant"),
    ("load_kg", 200), ("role", "OWNER"),
])
def test_request_rejects_invalid_or_unrelated_fields(field, value):
    payload = requirements()
    payload[field] = value
    with pytest.raises(ValidationError):
        RoutineRequirements.model_validate(payload)


@pytest.mark.parametrize("activity", ["nula", "leve", "normal", "moderada", "intensa"])
def test_activity_is_separate_from_experience_and_does_not_mutate_input(activity):
    payload = requirements()
    payload["activity_level"] = activity
    before = deepcopy(payload)
    actual = RoutineRequirements.model_validate(payload).model_dump()
    assert payload == before
    assert actual["activity_level"] == activity
    assert actual["experience"] == "inicial"
    assert actual["exercises_per_session"] == 6
    assert not ({"client_id", "gym_id", "load_kg", "nombre"} & actual.keys())


def test_optional_preview_defaults_are_bounded_and_independent():
    payload = {key: value for key, value in requirements().items()
               if key in {"activity_level", "experience", "goal", "equipment"}}
    first, second = RoutineRequirements(**payload), RoutineRequirements(**payload)
    assert first.session_minutes == 60 and first.variant == 0
    assert first.days_per_week == 3 and first.exercises_per_session == 6
    first.excluded_exercises.append("leg-press")
    assert second.excluded_exercises == []
