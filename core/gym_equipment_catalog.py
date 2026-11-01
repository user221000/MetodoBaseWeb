"""Reviewed hardware requirements, independent of accounts and persistence."""
from copy import deepcopy

BASE_EQUIPMENT_KEYS = ("barbell", "bench", "dumbbell", "bodyweight")
_KEY_ORDER = ("machine", "cable", "dumbbell", "barbell", "bench", "bodyweight")
_MACHINES = (
    ("chest-press", "Press de pecho horizontal en máquina", "Pecho y hombros", "machine"),
    ("incline-chest-press", "Press inclinado de pecho en máquina", "Pecho y hombros", "machine"),
    ("pec-deck", "Pec deck para aperturas de pecho", "Pecho y hombros", "machine"),
    ("shoulder-press", "Press de hombros en máquina", "Pecho y hombros", "machine"),
    ("lateral-raise", "Elevación lateral en máquina", "Pecho y hombros", "machine"),
    ("triceps-extension", "Extensión de tríceps en máquina", "Brazos", "machine"),
    ("preacher-curl", "Curl de bíceps en máquina predicador", "Brazos", "machine"),
    ("high-pulley", "Polea alta con barra, cuerda y agarres", "Poleas y espalda", "cable"),
    ("low-pulley", "Polea baja con agarres, cuerda y asiento para remo", "Poleas y espalda", "cable"),
    ("dual-adjustable-pulley", "Dos poleas regulables con manerales", "Poleas y espalda", "cable"),
    ("lat-pulldown", "Jalón alto con asiento y apoyo de muslos", "Poleas y espalda", "cable"),
    ("converging-pulldown", "Jalón en máquina convergente", "Poleas y espalda", "machine"),
    ("assisted-pullup", "Dominadas asistidas en máquina", "Poleas y espalda", "machine"),
    ("supported-row", "Remo en máquina con apoyo de pecho", "Poleas y espalda", "machine"),
    ("plate-loaded-row", "Remo con apoyo de pecho y carga de discos", "Poleas y espalda", "machine"),
    ("reverse-fly", "Apertura posterior en máquina o pec deck reversible", "Poleas y espalda", "machine"),
    ("shrug-machine", "Encogimiento de hombros en máquina", "Poleas y espalda", "machine"),
    ("leg-press-45", "Prensa de piernas a 45°", "Piernas y glúteos", "machine"),
    ("leg-press-horizontal", "Prensa horizontal de piernas", "Piernas y glúteos", "machine"),
    ("hack-squat", "Sentadilla hack en máquina", "Piernas y glúteos", "machine"),
    ("leg-extension", "Extensión de rodillas en máquina", "Piernas y glúteos", "machine"),
    ("leg-curl-seated", "Curl femoral sentado en máquina", "Piernas y glúteos", "machine"),
    ("leg-curl-lying", "Curl femoral tumbado en máquina", "Piernas y glúteos", "machine"),
    ("leg-curl-standing", "Curl femoral unilateral de pie en máquina", "Piernas y glúteos", "machine"),
    ("hip-thrust", "Hip thrust en máquina", "Piernas y glúteos", "machine"),
    ("hip-abduction", "Abducción de cadera en máquina", "Piernas y glúteos", "machine"),
    ("hip-adduction", "Aducción de cadera en máquina", "Piernas y glúteos", "machine"),
    ("calf-standing", "Elevación de talones de pie en máquina", "Piernas y glúteos", "machine"),
    ("calf-seated", "Elevación de talones sentado en máquina", "Piernas y glúteos", "machine"),
    ("abdominal-crunch", "Crunch abdominal en máquina", "Zona media", "machine"),
    ("smith", "Máquina Smith con seguros", "Soportes y accesorios", "machine"),
    ("rack-safeties", "Rack o jaula con soportes y seguros para barra", "Soportes y accesorios", None),
    ("ankle-cuff", "Tobillera compatible con la polea", "Soportes y accesorios", None),
)

# An exercise can have alternative hardware configurations: outer OR, inner AND.
# A dual cable station does not imply a pulldown seat/thigh restraint, Smith or
# an arbitrary leg machine. A pec deck counts as reversible only if marked so.
_OPTIONS = {
    "chest-press": (("chest-press",),),
    "triceps-extension": (("high-pulley",), ("dual-adjustable-pulley",)),
    "lat-pulldown": (("lat-pulldown",),),
    "supported-row": (("supported-row",),),
    "reverse-fly": (("reverse-fly",),),
    "leg-press": (("leg-press-45",),),
    "seated-leg-curl": (("leg-curl-seated",),),
    "standing-machine-calf-raise": (("calf-standing",),),
    "incline-machine-chest-press": (("incline-chest-press",),),
    "smith-flat-bench-press": (("smith",),),
    "smith-incline-bench-press": (("smith",),),
    "barbell-flat-bench-press": (("rack-safeties",),),
    "barbell-incline-bench-press": (("rack-safeties",),),
    "standing-cable-chest-fly": (("dual-adjustable-pulley",),),
    "low-to-high-cable-fly": (("dual-adjustable-pulley",),),
    "pec-deck-fly": (("pec-deck",),),
    "machine-shoulder-press": (("shoulder-press",),),
    "seated-barbell-shoulder-press": (("rack-safeties",),),
    "single-arm-cable-lateral-raise": (("low-pulley",), ("dual-adjustable-pulley",)),
    "machine-lateral-raise": (("lateral-raise",),),
    "overhead-cable-triceps-extension": (("high-pulley",), ("dual-adjustable-pulley",)),
    "straight-bar-triceps-pushdown": (("high-pulley",), ("dual-adjustable-pulley",)),
    "machine-triceps-extension": (("triceps-extension",),),
    "cross-body-cable-triceps-extension": (("high-pulley",), ("dual-adjustable-pulley",)),
    "neutral-grip-lat-pulldown": (("lat-pulldown",),),
    "supinated-lat-pulldown": (("lat-pulldown",),),
    "single-arm-lat-pulldown": (("lat-pulldown",),),
    "converging-machine-pulldown": (("converging-pulldown",),),
    "assisted-machine-pull-up": (("assisted-pullup",),),
    "assisted-machine-chin-up": (("assisted-pullup",),),
    "seated-cable-row": (("low-pulley",),),
    "wide-grip-cable-row": (("low-pulley",),),
    "single-arm-cable-row": (("low-pulley",),),
    "plate-loaded-machine-row": (("plate-loaded-row",),),
    "cable-reverse-fly": (("dual-adjustable-pulley",),),
    "rope-face-pull": (("high-pulley",), ("dual-adjustable-pulley",)),
    "cable-biceps-curl": (("low-pulley",), ("dual-adjustable-pulley",)),
    "machine-preacher-curl": (("preacher-curl",),),
    "rope-cable-hammer-curl": (("low-pulley",), ("dual-adjustable-pulley",)),
    "machine-shrug": (("shrug-machine",),),
    "horizontal-leg-press": (("leg-press-horizontal",),),
    "machine-hack-squat": (("hack-squat",),),
    "smith-squat": (("smith",),),
    "machine-leg-extension": (("leg-extension",),),
    "cable-pull-through": (("low-pulley",), ("dual-adjustable-pulley",)),
    "lying-machine-leg-curl": (("leg-curl-lying",),),
    "standing-machine-leg-curl": (("leg-curl-standing",),),
    "machine-hip-thrust": (("hip-thrust",),),
    "machine-hip-abduction": (("hip-abduction",),),
    "standing-cable-hip-abduction": (("low-pulley", "ankle-cuff"), ("dual-adjustable-pulley", "ankle-cuff")),
    "machine-hip-adduction": (("hip-adduction",),),
    "seated-machine-calf-raise": (("calf-seated",),),
    "leg-press-calf-raise": (("leg-press-45",), ("leg-press-horizontal",)),
    "cable-pallof-press": (("dual-adjustable-pulley",),),
    "machine-abdominal-crunch": (("abdominal-crunch",),),
}
_BASIC_EXERCISES = frozenset({
    "shoulder-press", "lateral-raise", "biceps-curl", "dumbbell-romanian-deadlift", "forearm-plank",
    "dumbbell-flat-bench-press", "incline-dumbbell-press", "dumbbell-floor-press", "incline-push-up",
    "floor-push-up", "flat-dumbbell-chest-fly", "arnold-dumbbell-press", "seated-dumbbell-lateral-raise",
    "seated-dumbbell-triceps-extension", "lying-dumbbell-triceps-extension", "one-arm-dumbbell-row",
    "incline-bench-dumbbell-row", "bent-over-barbell-row", "supinated-barbell-row",
    "incline-dumbbell-reverse-fly", "seated-dumbbell-biceps-curl", "dumbbell-hammer-curl",
    "incline-dumbbell-curl", "barbell-biceps-curl", "dumbbell-shrug", "goblet-squat",
    "dumbbell-box-squat", "dumbbell-reverse-lunge", "dumbbell-split-squat", "barbell-romanian-deadlift",
    "dumbbell-kickstand-romanian-deadlift", "barbell-hip-thrust", "dumbbell-glute-bridge",
    "standing-dumbbell-calf-raise", "dead-bug", "side-plank",
})


def get_machine_catalog():
    return [{"id": key, "label": label, "group": group} for key, label, group, _ in _MACHINES]


def normalize_machine_ids(machine_ids):
    if not isinstance(machine_ids, (list, tuple, set, frozenset)):
        raise ValueError("Invalid machine inventory")
    known = {row[0] for row in _MACHINES}
    if any(type(key) is not str or key not in known for key in machine_ids):
        raise ValueError("Unknown machine inventory entry")
    return sorted(set(machine_ids))


def get_effective_equipment(machine_ids):
    selected = set(normalize_machine_ids(machine_ids))
    keys = set(BASE_EQUIPMENT_KEYS)
    keys.update(kind for key, _, _, kind in _MACHINES if key in selected and kind is not None)
    return [key for key in _KEY_ORDER if key in keys]


def get_machine_requirements(exercise_id):
    if exercise_id in _BASIC_EXERCISES:
        return [[]]
    if exercise_id not in _OPTIONS:
        raise ValueError("Exercise has no reviewed hardware mapping")
    return [list(option) for option in _OPTIONS[exercise_id]]


def annotate_inventory(exercises, machine_ids):
    selected = set(normalize_machine_ids(machine_ids))
    result = []
    for source in exercises:
        row = deepcopy(source)
        options = get_machine_requirements(row["id"])
        admitted = next((option for option in options if set(option).issubset(selected)), None)
        row.update(machine_options=options, required_machine_ids=list(admitted if admitted is not None else options[0]),
                   available_in_inventory=admitted is not None)
        result.append(row)
    return result
