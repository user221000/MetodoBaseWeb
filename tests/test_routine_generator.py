"""Independent invariants for the editorial PPL constraint selector."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
from math import ceil
import re

import pytest

from core.routine_catalog import get_exercise_catalog, get_routine_program
from core.routine_generator import (
    EQUIPMENT_KEYS, RoutineGenerationError, build_routine, normalize_requirements,
)


def test_library_is_large_unique_fresh_and_concrete():
    first = get_exercise_catalog()
    second = get_exercise_catalog()
    assert first == second
    assert len(first) == len({row["id"] for row in first}) >= 90
    assert len({row["name"] for row in first}) == len(first)
    assert Counter(row["session"] for row in first) == {"push": 30, "pull": 30, "legs": 31}
    assert len(json.dumps(first, ensure_ascii=False).encode()) < 131072
    original = {"chest-press", "shoulder-press", "lateral-raise", "triceps-extension",
                "lat-pulldown", "supported-row", "reverse-fly", "biceps-curl", "leg-press",
                "dumbbell-romanian-deadlift", "seated-leg-curl", "standing-machine-calf-raise", "forearm-plank"}
    assert original <= {row["id"] for row in first}
    for row in first:
        assert re.fullmatch(r"[a-z]+(?:-[a-z]+)*", row["id"])
        assert row["equipment"] and set(row["equipment_keys"]) <= set(EQUIPMENT_KEYS)
        assert row["experience_min"] in {"inicial", "intermedio", "avanzado"}
        assert len(row["cues"]) == 2 and all(len(cue) > 20 for cue in row["cues"])
        assert row["muscles"] and row["source_url"].startswith("https://www.nasm.org/")
        assert row["source_scope"].startswith("Referencia de familia")
        assert row["repetition_unit"] in {"seconds", "repetitions"}
    first[0]["cues"].clear()
    first[0]["equipment_keys"].clear()
    assert get_exercise_catalog() == second


def _duration(exercises):
    seconds = 480
    for row in exercises:
        maximum = max(map(int, re.findall(r"\d+", row["repetitions"])))
        per_set = maximum * (1 if row["repetition_unit"] == "seconds" else 4)
        if "por lado" in row["repetitions"]:
            per_set *= 2
        sets = row["sets"]["maximum"]
        seconds += 90 + sets * per_set + (sets - 1) * row["rest_seconds"]
    return ceil(seconds / 60)


@pytest.mark.parametrize("experience", ["inicial", "intermedio", "avanzado"])
@pytest.mark.parametrize("count", [6, 7, 8])
@pytest.mark.parametrize("days", [3, 4, 5, 6])
def test_generation_matrix_respects_every_declared_constraint(experience, count, days):
    library = {row["id"]: row for row in get_exercise_catalog()}
    ranks = {"inicial": 0, "intermedio": 1, "avanzado": 2}
    for activity in ("nula", "leve", "normal", "moderada", "intensa"):
        requirements = {"experience": experience, "exercises_per_session": count,
                        "days_per_week": days, "activity_level": activity, "session_minutes": 90}
        before = deepcopy(requirements)
        program = build_routine(requirements)
        assert requirements == before
        assert build_routine(requirements) == program
        assert program["generated"] is True
        assert program["requirements"]["activity_level"] == ("moderada" if activity == "normal" else activity)
        assert len(program["schedule"]["default_days"]) == days
        assert program["schedule"]["sessions_per_week"] == days
        assert [row["id"] for row in program["sessions"]] == ["push", "pull", "legs"]
        for session in program["sessions"]:
            ids = {row["id"] for row in session["exercises"]}
            assert len(ids) == len(session["exercises"]) == count
            assert _duration(session["exercises"]) == session["estimated_minutes"] <= 90
            slots = {row["slot"] for row in session["exercises"]}
            if session["id"] == "push":
                assert {"chest_press", "chest_fly", "shoulder_press", "lateral_raise", "triceps"} <= slots
            elif session["id"] == "pull":
                assert {"vertical_pull", "horizontal_pull", "rear_delt", "biceps"} <= slots
                assert not slots & {"chest_press", "triceps", "shoulder_press"}
            else:
                assert {"knee_dominant", "knee_flexion", "calf", "core"} <= slots
                assert slots & {"hip_hinge", "hip_extension"}
            for row in session["exercises"]:
                canonical = library[row["id"]]
                assert canonical["session"] == session["id"]
                assert ranks[canonical["experience_min"]] <= ranks[experience]
                assert set(canonical["equipment_keys"]) <= set(program["requirements"]["equipment"])
                assert row["sets"] == {"minimum": 1 if experience == "inicial" else 2,
                                       "maximum": 1 if experience == "inicial" else 2}
                assert row["rest_seconds"] in {60, 90, 120, 180}
                alternative = row["alternative"]["id"]
                assert alternative == row["id"] or alternative not in ids
                assert library[alternative]["slot"] == row["slot"]
                assert library[alternative]["repetition_unit"] == row["repetition_unit"]
                assert ("por lado" in library[alternative]["repetitions"]) == ("por lado" in row["repetitions"])


def test_normal_is_an_exact_alias_and_activity_never_establishes_experience():
    assert build_routine({"activity_level": "normal"}) == build_routine({"activity_level": "moderada"})
    for activity in ["nula", "leve", "moderada", "intensa"]:
        assert normalize_requirements({"activity_level": activity})["experience"] == "inicial"
        for days in [3, 6]:
            program = build_routine({"activity_level": activity, "days_per_week": days})
            assert all(ex["sets"] == {"minimum": 1, "maximum": 1}
                       for session in program["sessions"] for ex in session["exercises"])


def test_variants_change_selection_without_accumulating_or_mutating():
    base = build_routine({})
    other = build_routine({"variant": 1})
    base_ids = [row["id"] for session in base["sessions"] for row in session["exercises"]]
    other_ids = [row["id"] for session in other["sessions"] for row in session["exercises"]]
    assert base_ids != other_ids
    assert len(base_ids) == len(other_ids) == 18
    base["sessions"][0]["exercises"][0]["cues"].append("Untrusted edit")
    assert build_routine({}) != base
    assert get_routine_program()["generated"] is False


def test_exclusions_apply_to_primaries_and_alternatives_without_fallback():
    first = build_routine({})
    excluded = [row["id"] for session in first["sessions"] for row in session["exercises"]]
    second = build_routine({"excluded_exercises": excluded})
    for session in second["sessions"]:
        for row in session["exercises"]:
            assert row["id"] not in excluded
            assert row["alternative"]["id"] not in excluded
    all_push = [row["id"] for row in get_exercise_catalog() if row["session"] == "push"]
    with pytest.raises(RoutineGenerationError, match="requisitos") as error:
        build_routine({"excluded_exercises": all_push})
    assert error.value.code == "insufficient_equipment"


def test_equipment_subsets_never_fabricate_equipment_or_ignore_rejection():
    successes, rejections = 0, 0
    library = {row["id"]: row for row in get_exercise_catalog()}
    for size in range(1, len(EQUIPMENT_KEYS) + 1):
        for keys in combinations(EQUIPMENT_KEYS, size):
            try:
                program = build_routine({"equipment": list(keys), "session_minutes": 90})
            except RoutineGenerationError as error:
                assert error.code in {"insufficient_equipment", "insufficient_exercises"}
                rejections += 1
                continue
            successes += 1
            for session in program["sessions"]:
                for row in session["exercises"]:
                    assert set(row["equipment_keys"]) <= set(keys)
                    assert set(library[row["alternative"]["id"]]["equipment_keys"]) <= set(keys)
    assert successes > 0 and rejections > 0
    assert successes + rejections == 63


def test_time_limit_is_explicit_and_never_removes_exercises():
    requirements = {"experience": "intermedio", "exercises_per_session": 8, "session_minutes": 45}
    with pytest.raises(RoutineGenerationError) as error:
        build_routine(requirements)
    assert error.value.code == "insufficient_time"
    adequate = build_routine({**requirements, "session_minutes": 60})
    assert all(len(row["exercises"]) == 8 for row in adequate["sessions"])
    assert max(row["estimated_minutes"] for row in adequate["sessions"]) <= 60


def test_goal_changes_prescription_without_inventing_external_load():
    general = build_routine({"experience": "intermedio"})
    hypertrophy = build_routine({"experience": "intermedio", "goal": "hipertrofia"})
    assert general["sessions"] != hypertrophy["sessions"]
    for program in (general, hypertrophy):
        for session in program["sessions"]:
            for row in session["exercises"]:
                assert not {"weight_kg", "load_kg", "one_rep_max"} & row.keys()


@pytest.mark.parametrize("requirements", [
    None, [], {"client_name": "private"}, {"activity_level": "sedentary"}, {"activity_level": None},
    {"experience": "intensa"}, {"goal": "medical"}, {"equipment": []}, {"equipment": ["machine", "machine"]},
    {"equipment": ["machine", "invisible"]}, {"equipment": "machine"}, {"excluded_exercises": ["unknown"]},
    {"excluded_exercises": [True]}, {"excluded_exercises": "chest-press"}, {"exercises_per_session": 5},
    {"exercises_per_session": 9}, {"exercises_per_session": True}, {"exercises_per_session": 6.0},
    {"days_per_week": 7}, {"days_per_week": "3"}, {"session_minutes": 30}, {"session_minutes": True},
    {"variant": -1}, {"variant": 10}, {"variant": "1"},
])
def test_invalid_requirements_reject_instead_of_coercing(requirements):
    with pytest.raises(RoutineGenerationError) as error:
        build_routine(requirements)
    assert error.value.code == "invalid_requirements"
