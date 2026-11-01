"""Bounded editorial PPL selection from declared requirements; pure, no I/O.

Daily activity is context, not an assessment of lifting ability. It may reorder
supported equipment preferences but never infers experience or an absolute load.
The supplied constraints are not a clinical assessment or a training history.
"""
from collections.abc import Mapping
from copy import deepcopy
from math import ceil
import re

from core.routine_catalog import _base_program, get_exercise_catalog


EQUIPMENT_KEYS = ("machine", "cable", "dumbbell", "barbell", "bench", "bodyweight")
ACTIVITY_LEVELS = ("nula", "leve", "normal", "moderada", "intensa")
EXPERIENCE_LEVELS = ("inicial", "intermedio", "avanzado")
GOALS = ("fuerza_general", "hipertrofia")
SESSION_MINUTES = (45, 60, 75, 90)
_DEFAULT_DAYS = {3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 3, 4], 6: [0, 1, 2, 3, 4, 5]}
_FIELDS = {"activity_level", "experience", "equipment", "goal", "exercises_per_session",
           "days_per_week", "variant", "excluded_exercises", "session_minutes"}
_DEFAULTS = {"activity_level": "leve", "experience": "inicial", "equipment": list(EQUIPMENT_KEYS),
             "goal": "fuerza_general", "exercises_per_session": 6, "days_per_week": 3,
             "variant": 0, "excluded_exercises": [], "session_minutes": 60}
_COMPOUND = {"chest_press", "shoulder_press", "vertical_pull", "horizontal_pull",
             "knee_dominant", "hip_hinge", "hip_extension"}
_REQUIRED = {
    "push": ["chest_press", "chest_fly", "shoulder_press", "lateral_raise", "triceps"],
    "pull": ["vertical_pull", "horizontal_pull", "rear_delt", "biceps"],
    "legs": ["knee_dominant", "posterior_chain", "knee_flexion", "calf", "core"],
}
_EXTRA_ORDER = {
    "push": ["triceps", "chest_press", "lateral_raise", "chest_fly"],
    "pull": ["horizontal_pull", "biceps", "scapula", "vertical_pull", "rear_delt"],
    "legs": ["hip_accessory", "knee_extension", "hip_extension", "knee_dominant", "knee_flexion"],
}
_CAPS = {"chest_press": 2, "chest_fly": 1, "shoulder_press": 1, "lateral_raise": 2,
         "triceps": 2, "vertical_pull": 2, "horizontal_pull": 2, "rear_delt": 2,
         "biceps": 2, "scapula": 1, "knee_dominant": 2, "knee_extension": 1,
         "hip_hinge": 1, "knee_flexion": 2, "hip_extension": 1,
         "hip_accessory": 2, "calf": 1, "core": 1}
_ORDER = {"push": ["chest_press", "shoulder_press", "chest_fly", "lateral_raise", "triceps"],
          "pull": ["vertical_pull", "horizontal_pull", "rear_delt", "scapula", "biceps"],
          "legs": ["knee_dominant", "hip_hinge", "hip_extension", "knee_flexion",
                   "knee_extension", "hip_accessory", "calf", "core"]}


class RoutineGenerationError(ValueError):
    """A bounded user-facing generation rejection, without supplied free text."""
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


def _invalid(message="Revisa los requisitos de la rutina."):
    raise RoutineGenerationError("invalid_requirements", message)


def normalize_requirements(requirements):
    """Validate without coercing booleans, strings or missing clinical facts."""
    if not isinstance(requirements, Mapping) or set(requirements) - _FIELDS:
        _invalid()
    result = deepcopy(_DEFAULTS)
    result.update(deepcopy(dict(requirements)))
    for key, allowed in (("activity_level", ACTIVITY_LEVELS), ("experience", EXPERIENCE_LEVELS), ("goal", GOALS)):
        if type(result[key]) is not str or result[key] not in allowed:
            _invalid()
    if result["activity_level"] == "normal":
        result["activity_level"] = "moderada"
    for key, allowed in (("exercises_per_session", (6, 7, 8)), ("days_per_week", (3, 4, 5, 6)),
                         ("session_minutes", SESSION_MINUTES), ("variant", tuple(range(10)))):
        if type(result[key]) is not int or result[key] not in allowed:
            _invalid()
    equipment = result["equipment"]
    if (not isinstance(equipment, list) or not 1 <= len(equipment) <= len(EQUIPMENT_KEYS)
            or any(type(key) is not str or key not in EQUIPMENT_KEYS for key in equipment)
            or len(set(equipment)) != len(equipment)):
        _invalid("Elige los tipos de equipo disponibles, sin duplicados.")
    result["equipment"] = [key for key in EQUIPMENT_KEYS if key in equipment]
    excluded = result["excluded_exercises"]
    known = {row["id"] for row in get_exercise_catalog()}
    if (not isinstance(excluded, list) or len(excluded) > 120
            or any(type(identifier) is not str or identifier not in known for identifier in excluded)
            or len(set(excluded)) != len(excluded)):
        _invalid("Revisa la lista de ejercicios excluidos.")
    result["excluded_exercises"] = sorted(excluded)
    return result


def _eligible(catalog, requirements):
    level = EXPERIENCE_LEVELS.index(requirements["experience"])
    return [row for row in catalog if row["id"] not in requirements["excluded_exercises"]
            and row.get("available_in_inventory", True)
            and EXPERIENCE_LEVELS.index(row["experience_min"]) <= level
            and set(row["equipment_keys"]).issubset(requirements["equipment"])]


def _choose_session(pool, group, requirements):
    candidates = [row for row in pool if row["session"] == group]
    selected, counts = [], {}
    variant = requirements["variant"]

    def choose(slot):
        slots = ("hip_hinge", "hip_extension") if slot == "posterior_chain" else (slot,)
        options = [row for row in candidates if row["slot"] in slots
                   and row["id"] not in {item["id"] for item in selected}
                   and counts.get(row["slot"], 0) < _CAPS[row["slot"]]]
        if not options:
            return False
        def preference(row):
            # A conservative equipment preference, not a change in dose or a
            # claim about individual suitability. Experience remains explicit.
            supported = "machine" in row["equipment_keys"]
            preferred = (not supported) if requirements["activity_level"] in ("nula", "leve") else False
            return (preferred, row["id"])
        options.sort(key=preference)
        first_preference = preference(options[0])[0]
        preferred = [row for row in options if preference(row)[0] == first_preference]
        chosen = deepcopy(preferred[variant % len(preferred)])
        selected.append(chosen)
        counts[chosen["slot"]] = counts.get(chosen["slot"], 0) + 1
        return True

    for slot in _REQUIRED[group]:
        if not choose(slot):
            raise RoutineGenerationError("insufficient_equipment",
                "El equipo, la experiencia y las exclusiones no permiten cubrir todos los movimientos. Revisa esos requisitos.")
    extra_slots = _EXTRA_ORDER[group]
    while len(selected) < requirements["exercises_per_session"]:
        added = False
        for slot in extra_slots:
            if choose(slot):
                added = True
                if len(selected) == requirements["exercises_per_session"]:
                    break
        if not added:
            raise RoutineGenerationError("insufficient_exercises",
                "No hay suficientes ejercicios distintos para esa combinación. Elige más equipo, menos exclusiones o 6 ejercicios.")
    selected.sort(key=lambda row: _ORDER[group].index(row["slot"]))
    for row in selected:
        _prescribe(row, requirements)
        selected_ids = {item["id"] for item in selected}
        alternatives = [item for item in candidates if item["slot"] == row["slot"]
                        and item["id"] not in selected_ids
                        and item["repetition_unit"] == row["repetition_unit"]
                        and ("por lado" in item["repetitions"]) == ("por lado" in row["repetitions"])]
        if alternatives:
            replacement = sorted(alternatives, key=lambda item: item["id"])[variant % len(alternatives)]
            row["alternative"] = {"id": replacement["id"], "name": replacement["name"],
                                  "equipment": list(replacement["equipment"]),
                                  "required_machine_ids": list(replacement["required_machine_ids"]),
                                  "machine_options": deepcopy(replacement["machine_options"]),
                                  "cue": " ".join(replacement["cues"])}
        else:
            row["alternative"] = {"id": row["id"], "name": row["name"] + " · práctica técnica",
                                  "equipment": list(row["equipment"]),
                                  "required_machine_ids": list(row["required_machine_ids"]),
                                  "machine_options": deepcopy(row["machine_options"]),
                                  "cue": "Practica este mismo movimiento con menos resistencia y un recorrido cómodo; no añadas una serie extra."}
    return selected


def _prescribe(row, requirements):
    # Session counts and daily activity do not establish a lifting history.
    sets = 1 if requirements["experience"] == "inicial" else 2
    row["sets"] = {"minimum": sets, "maximum": sets}
    if row["repetition_unit"] == "seconds":
        row["repetitions"] = "20–30 por lado" if row["id"] == "side-plank" else "20–30"
        row["rest_seconds"] = 60
        return
    per_side = " por lado" if "por lado" in row["repetitions"] else ""
    if requirements["goal"] == "hipertrofia":
        row["repetitions"] = ("8–12" if row["slot"] in _COMPOUND else "12–15") + per_side
    else:
        row["repetitions"] = ("8–12" if row["slot"] in _COMPOUND else "10–15") + per_side
    if row["slot"] in _COMPOUND:
        row["rest_seconds"] = 180 if requirements["goal"] == "fuerza_general" and sets == 2 else 120
    else:
        row["rest_seconds"] = 90 if requirements["goal"] == "hipertrofia" and sets == 2 else 60


def estimate_session_minutes(exercises):
    """Editorial planning estimate, not a measured or promised duration."""
    seconds = 8 * 60
    for row in exercises:
        maximum = max(int(value) for value in re.findall(r"\d+", row["repetitions"]))
        work = maximum if row["repetition_unit"] == "seconds" else maximum * 4
        if "por lado" in row["repetitions"]:
            work *= 2
        sets = row["sets"]["maximum"]
        seconds += 90 + work * sets + row["rest_seconds"] * (sets - 1)
    return ceil(seconds / 60)


def build_routine(requirements, *, available_machine_ids=None):
    """Return three PPL sessions with six to eight compatible exercises each."""
    requirements = normalize_requirements(requirements)
    catalog = get_exercise_catalog()
    if available_machine_ids is not None:
        from core.gym_equipment_catalog import annotate_inventory
        catalog = annotate_inventory(catalog, available_machine_ids)
    pool = _eligible(catalog, requirements)
    program = _base_program()
    for session in program["sessions"]:
        session["exercises"] = _choose_session(pool, session["id"], requirements)
        session["estimated_minutes"] = estimate_session_minutes(session["exercises"])
        if session["estimated_minutes"] > requirements["session_minutes"]:
            raise RoutineGenerationError("insufficient_time",
                "El tiempo disponible no alcanza para esta combinación estimada. Elige más tiempo o 6 ejercicios.")
    count = requirements["days_per_week"]
    program["schedule"]["sessions_per_week"] = count
    program["schedule"]["default_days"] = list(_DEFAULT_DAYS[count])
    program["title"] = "Tu propuesta Push / Pull / Legs"
    program["audience"] = "Selección orientativa según tus requisitos declarados"
    program["summary"] = str(requirements["exercises_per_session"]) + " ejercicios por sesión. Revisa equipo y técnica antes de empezar."
    sets = 1 if requirements["experience"] == "inicial" else 2
    program["starting_point"] = ("Haz " + str(sets) + (" serie" if sets == 1 else " series")
        + " por ejercicio con una carga que controles, sin llegar al fallo. La actividad diaria no determina tu experiencia ni una carga en kilos. Elige 5–6 días sólo si ya toleras esa frecuencia.")
    program["requirements"] = deepcopy(requirements)
    program["generated"] = True
    program["catalog_count"] = len(catalog)
    program["duration_basis"] = "Estimación: 8 min de calentamiento + 90 s de preparación por ejercicio + 4 s por repetición (o segundos de posición mantenida) + descansos entre series. Los movimientos por lado cuentan ambos lados. No es tiempo medido."
    return program
