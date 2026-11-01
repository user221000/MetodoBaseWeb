"""Exact hardware constraints; broad machine/cable flags cannot substitute."""
from copy import deepcopy

import pytest

from core.gym_equipment_catalog import (
    annotate_inventory, get_effective_equipment, get_machine_catalog, get_machine_requirements,
)
from core.routine_catalog import get_exercise_catalog
from core.routine_generator import RoutineGenerationError, build_routine


def test_all_exercises_have_reviewed_hardware_and_inputs_remain_independent():
    pool = get_exercise_catalog()
    before = deepcopy(pool)
    machines = get_machine_catalog()
    identifiers = {row["id"] for row in machines}
    assert len(pool) == 91 and len(identifiers) == len(machines) == 33
    for row in pool:
        assert row["machine_options"] == get_machine_requirements(row["id"])
        assert all(set(option) <= identifiers for option in row["machine_options"])
    available = annotate_inventory(pool, list(identifiers))
    assert all(row["available_in_inventory"] for row in available)
    assert pool == before
    available[0]["machine_options"][0].append("untrusted")
    assert pool == before and get_exercise_catalog() == before
    machines[0]["label"] = "Untrusted"
    assert get_machine_catalog()[0]["label"] != "Untrusted"
    with pytest.raises(ValueError):
        get_machine_requirements("future-exercise-without-reviewed-hardware")


@pytest.mark.parametrize("selected,available,unavailable", [
    ([], ["goblet-squat", "biceps-curl", "forearm-plank"], ["chest-press", "lat-pulldown", "smith-squat"]),
    (["high-pulley"], ["triceps-extension", "rope-face-pull"], ["lat-pulldown", "cable-biceps-curl", "cable-reverse-fly"]),
    (["low-pulley"], ["cable-biceps-curl", "seated-cable-row"], ["triceps-extension", "lat-pulldown", "standing-cable-hip-abduction"]),
    (["dual-adjustable-pulley"], ["standing-cable-chest-fly", "rope-face-pull", "cable-pallof-press"], ["lat-pulldown", "standing-cable-hip-abduction"]),
    (["low-pulley", "ankle-cuff"], ["standing-cable-hip-abduction"], ["standing-cable-chest-fly", "cable-pallof-press"]),
    (["smith"], ["smith-squat", "smith-flat-bench-press"], ["machine-hack-squat", "barbell-flat-bench-press"]),
    (["rack-safeties"], ["barbell-flat-bench-press", "seated-barbell-shoulder-press"], ["smith-squat", "chest-press"]),
    (["leg-curl-seated"], ["seated-leg-curl"], ["lying-machine-leg-curl", "standing-machine-leg-curl"]),
    (["leg-curl-lying"], ["lying-machine-leg-curl"], ["seated-leg-curl", "standing-machine-leg-curl"]),
    (["leg-press-horizontal"], ["horizontal-leg-press", "leg-press-calf-raise"], ["leg-press", "machine-hack-squat"]),
    (["leg-press-45"], ["leg-press", "leg-press-calf-raise"], ["horizontal-leg-press", "machine-hack-squat"]),
])
def test_specific_hardware_never_enables_a_different_machine(selected, available, unavailable):
    result = {row["id"]: row for row in annotate_inventory(get_exercise_catalog(), selected)}
    assert all(result[key]["available_in_inventory"] is True for key in available)
    assert all(result[key]["available_in_inventory"] is False for key in unavailable)
    assert all(set(result[key]["required_machine_ids"]) <= set(selected) for key in available)


@pytest.mark.parametrize("level", ["inicial", "intermedio", "avanzado"])
@pytest.mark.parametrize("count", [6, 7, 8])
def test_primary_and_alternative_exercises_only_use_the_supplied_inventory(level, count):
    machines = [row["id"] for row in get_machine_catalog()]
    requirements = {"experience": level, "exercises_per_session": count, "session_minutes": 90,
                    "equipment": get_effective_equipment(machines)}
    result = build_routine(requirements, available_machine_ids=machines)
    assert [len(row["exercises"]) for row in result["sessions"]] == [count] * 3
    for session in result["sessions"]:
        selected_ids = {row["id"] for row in session["exercises"]}
        for row in session["exercises"]:
            assert set(row["required_machine_ids"]) <= set(machines)
            assert set(row["alternative"]["required_machine_ids"]) <= set(machines)
            assert row["alternative"]["id"] == row["id"] or row["alternative"]["id"] not in selected_ids


def test_restricted_inventory_and_basic_equipment_are_server_enforceable():
    machines = ["pec-deck", "high-pulley", "lat-pulldown", "leg-curl-seated", "supported-row", "reverse-fly"]
    requirements = {"equipment": get_effective_equipment(machines), "session_minutes": 90}
    result = build_routine(requirements, available_machine_ids=machines)
    for session in result["sessions"]:
        for row in session["exercises"]:
            assert set(row["required_machine_ids"]) <= set(machines)
            assert set(row["alternative"]["required_machine_ids"]) <= set(machines)
    assert get_effective_equipment([]) == ["dumbbell", "barbell", "bench", "bodyweight"]
    with pytest.raises(RoutineGenerationError):
        build_routine({"equipment": ["machine", "cable", "dumbbell", "barbell", "bench", "bodyweight"]},
                      available_machine_ids=[])
