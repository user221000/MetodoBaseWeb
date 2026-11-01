"""Reviewed, generic resistance-training examples; no profile or generated data.

This catalogue is educational organisation, not an individual prescription or
a claim that a PPL split meets every public-health recommendation.
Each call creates an independent inert value; no user state lives here.
"""


def _exercise(identifier, name, equipment, cues, alternative, *, rest=90,
              repetitions="8–12", repetition_unit="repetitions"):
    return {
        "id": identifier, "name": name, "sets": {"minimum": 2, "maximum": 2},
        "repetitions": repetitions, "repetition_unit": repetition_unit,
        "rest_seconds": rest, "equipment": equipment, "cues": cues,
        "alternative": alternative,
    }


def get_routine_program():
    """Return the same bounded, unpersonalised programme for every account."""
    return {
        "id": "ppl-basico-v1", "title": "Organiza tu entrenamiento de fuerza",
        "audience": "Guía de gimnasio para adultos sanos con técnica básica",
        "summary": "Elige de 3 a 6 días. Alterna empuje, tirón y piernas, también en días seguidos.",
        "schedule": {
            "sessions_per_week": 3, "available_sessions": [3, 4, 5, 6],
            "nonconsecutive": False, "cycle": ["push", "pull", "legs"],
            "rotation": "continuous", "minimum_rest_days": 1,
            "default_days": [0, 2, 4],
            "days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            "note": "Mantén al menos un día libre por semana. Con 4 o 5 días, el ciclo continúa la semana siguiente para repartir las sesiones.",
        },
        "warmup": [
            "Camina o muévete suavemente durante 5–10 minutos.",
            "Ensaya los movimientos sin carga o con una carga ligera antes de las series.",
        ],
        "starting_point": "Haz 2 series por ejercicio con una carga que controles, sin llegar al fallo. Si completas el rango con buena técnica, aumenta la carga poco a poco. Elige 5–6 días sólo si ya toleras esa frecuencia; no aumentes también las series.",
        "cautions": [
            "Muévete con control y respira sin contener el aire. Una alternativa sustituye al ejercicio; no se suma como trabajo extra.",
            "Si aparece dolor, detente. Si tienes lesiones, síntomas o una condición de salud, consulta con un profesional antes de usar este ejemplo.",
        ],
        "guideline_note": "CDC y ACSM recomiendan trabajar los grandes grupos musculares al menos dos días por semana. Un PPL de 3 días no asegura esa frecuencia por grupo. Esta guía no sustituye una rutina individual ni la actividad aeróbica.",
        "sessions": [
            {"id": "push", "name": "Push", "label": "Empuje", "focus": "Pecho · hombros · tríceps", "description": "Empuja con control, con apoyo estable y una carga fácil de manejar.", "exercises": [
                _exercise("chest-press", "Press de pecho sentado en máquina", ["Máquina de press de pecho"],
                    ["Ajusta el asiento para que las asas queden a la altura del pecho.", "Apoya la espalda; empuja y vuelve despacio sin bloquear los codos."],
                    {"name": "Press de pecho con mancuernas en banco plano", "equipment": ["Mancuernas", "Banco plano"], "cue": "Apoya pies y espalda, baja las mancuernas con control y empuja sin rebotar."}, rest=120),
                _exercise("shoulder-press", "Press de hombros sentado con mancuernas", ["Mancuernas", "Banco con respaldo"],
                    ["Siéntate con la espalda apoyada y los pies firmes.", "Eleva las mancuernas sin arquear la espalda; baja hasta una posición cómoda."],
                    {"name": "Press de hombros en máquina", "equipment": ["Máquina de hombros"], "cue": "Ajusta asiento y recorrido; mantén la espalda apoyada."}),
                _exercise("lateral-raise", "Elevación lateral con mancuernas", ["Mancuernas"],
                    ["Mantén los codos ligeramente flexionados y los hombros relajados.", "Eleva con control hasta una altura cómoda, como máximo a la altura de los hombros; evita balancearte."],
                    {"name": "Elevación lateral en máquina", "equipment": ["Máquina de elevación lateral"], "cue": "Ajusta los apoyos y eleva sin encoger los hombros ni impulsar el tronco."}, rest=60, repetitions="10–15"),
                _exercise("triceps-extension", "Extensión de tríceps en polea", ["Polea alta", "Cuerda o barra"],
                    ["Mantén los codos cerca del cuerpo y el tronco estable.", "Extiende sin bloquear el codo y vuelve lentamente, sin mover el hombro."],
                    {"name": "Extensión de tríceps en máquina", "equipment": ["Máquina de tríceps"], "cue": "Ajusta asiento y apoyos; mueve el antebrazo sin despegar los codos."}, rest=60, repetitions="10–15"),
            ]},
            {"id": "pull", "name": "Pull", "label": "Tirón", "focus": "Espalda · parte posterior del hombro · bíceps", "description": "Tira sin impulsos y deja que los brazos vuelvan despacio.", "exercises": [
                _exercise("lat-pulldown", "Jalón al pecho en polea alta", ["Polea alta con asiento", "Barra de jalón"],
                    ["Ajusta el apoyo de las piernas y sujeta con un agarre cómodo.", "Lleva la barra hacia la parte alta del pecho, nunca detrás del cuello; evita balancearte."],
                    {"name": "Jalón al pecho en máquina convergente", "equipment": ["Máquina de jalón"], "cue": "Ajusta el asiento, fija los muslos y lleva los codos hacia abajo sin inclinarte hacia atrás."}, rest=120),
                _exercise("supported-row", "Remo con apoyo de pecho", ["Máquina de remo con apoyo"],
                    ["Ajusta el asiento y apoya el pecho sin forzar la postura.", "Lleva los codos hacia atrás sin encoger los hombros y vuelve con control."],
                    {"name": "Remo sentado en polea baja", "equipment": ["Polea baja", "Agarre de remo"], "cue": "Mantén pies apoyados y tronco estable; acerca el agarre al abdomen sin balancearte."}, rest=120),
                _exercise("reverse-fly", "Apertura posterior en máquina", ["Máquina de apertura posterior"],
                    ["Ajusta las asas a una altura cómoda y apoya el pecho.", "Abre los brazos suavemente con los codos algo flexionados; no eleves los hombros."],
                    {"name": "Apertura posterior con mancuernas y pecho apoyado", "equipment": ["Mancuernas", "Banco inclinado"], "cue": "Apoya el pecho y abre los brazos con carga ligera, sin extender la espalda."}, rest=60, repetitions="10–15"),
                _exercise("biceps-curl", "Curl de bíceps de pie con mancuernas", ["Mancuernas"],
                    ["Mantén los codos junto al cuerpo y las muñecas alineadas.", "Flexiona y baja despacio sin balancear la espalda."],
                    {"name": "Curl de bíceps en polea baja", "equipment": ["Polea baja", "Barra de curl"], "cue": "Mantén los codos junto al cuerpo y baja con control, sin echar el tronco hacia atrás."}, rest=60, repetitions="10–15"),
            ]},
            {"id": "legs", "name": "Legs", "label": "Piernas", "focus": "Cuádriceps · isquiotibiales · glúteos · gemelos · abdomen", "description": "Combina empuje de piernas, bisagra de cadera y trabajo específico con control.", "exercises": [
                _exercise("leg-press", "Prensa de piernas a 45°", ["Máquina de prensa a 45°"],
                    ["Ajusta respaldo y seguros; apoya toda la planta del pie y mantén la pelvis contra el respaldo.", "Baja sólo hasta donde controles la pelvis y las rodillas sigan la dirección de los pies; empuja sin bloquearlas."],
                    {"name": "Prensa horizontal de piernas", "equipment": ["Máquina de prensa horizontal"], "cue": "Ajusta la distancia del asiento, apoya la espalda y empuja con ambos pies sin despegar la pelvis."}, rest=120),
                _exercise("dumbbell-romanian-deadlift", "Peso muerto rumano con mancuernas", ["Mancuernas"],
                    ["Parte de pie, con las rodillas ligeramente flexionadas y las mancuernas cerca de los muslos.", "Lleva la cadera atrás manteniendo el tronco estable; baja hasta sentir tensión controlada detrás del muslo y vuelve sin arquearte. No necesitas tocar el suelo."],
                    {"name": "Bisagra de cadera sin carga · práctica técnica", "equipment": ["Sin equipo"], "cue": "Ensaya el movimiento de cadera hacia atrás con recorrido corto. Usa esta práctica para aprender el gesto antes de cargarlo."}, rest=120),
                _exercise("seated-leg-curl", "Curl femoral sentado en máquina", ["Máquina de curl femoral sentado"],
                    ["Alinea las rodillas con el eje de la máquina y ajusta los apoyos del muslo y del tobillo.", "Flexiona las rodillas sin levantar la cadera; vuelve con control y evita soltar la carga."],
                    {"name": "Curl femoral tumbado en máquina", "equipment": ["Máquina de curl femoral tumbado"], "cue": "Ajusta el rodillo sobre la parte baja de las piernas y flexiona las rodillas sin levantar la pelvis."}, repetitions="10–15"),
                _exercise("standing-machine-calf-raise", "Elevación de talones de pie en máquina", ["Máquina de gemelos de pie"],
                    ["Ajusta los apoyos y coloca la parte delantera de ambos pies sobre la plataforma.", "Sube y baja los talones con un recorrido que controles, sin rebotes ni flexionar las rodillas para impulsarte."],
                    {"name": "Elevación de talones sentado en máquina", "equipment": ["Máquina de gemelos sentado"], "cue": "Ajusta el apoyo sobre los muslos y mueve ambos talones despacio, sin dejar caer la carga."}, rest=60, repetitions="10–15"),
                _exercise("forearm-plank", "Plancha frontal sobre antebrazos", ["Colchoneta"],
                    ["Coloca los codos bajo los hombros y apóyate en antebrazos y puntas de los pies.", "Mantén el tronco estable y respira; termina la serie si pierdes la posición, aunque falten segundos."],
                    {"name": "Plancha frontal con rodillas apoyadas", "equipment": ["Colchoneta"], "cue": "Apoya las rodillas y conserva el tronco alineado con la cadera, respirando con normalidad."}, rest=60, repetitions="20–30", repetition_unit="seconds"),
            ]},
        ],
        "sources": [
            {"label": "ACSM · Guías de fuerza 2026", "url": "https://acsm.org/resistance-training-guidelines-update-2026/"},
            {"label": "CDC · Actividad física para adultos", "url": "https://www.cdc.gov/physical-activity-basics/guidelines/adults.html"},
            {"label": "NSCA · Frecuencia y rutinas divididas", "url": "https://www.nsca.com/education/articles/kinetic-select/determination-of-resistance-training-frequency/"},
            {"label": "NASM · Biblioteca de ejercicios", "url": "https://www.nasm.org/resource-center/exercise-library"},
        ],
    }
