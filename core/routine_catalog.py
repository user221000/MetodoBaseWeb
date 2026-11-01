"""Editorial exercise catalogue and a generic preview; no profile I/O.

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


def _base_program():
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


_EQUIPMENT = {
    "machine": "Máquina indicada en el ejercicio", "cable": "Polea y agarre indicado",
    "dumbbell": "Mancuernas", "barbell": "Barra, discos y soportes con seguros",
    "bench": "Banco estable y ajustable", "bodyweight": "Suelo firme y colchoneta",
}
_SLOTS = {
    "chest_press": ("Pecho · tríceps", "Ajusta el apoyo, planta los pies y sitúa el agarre frente al pecho.", "Empuja con control y vuelve sin rebotar ni perder el apoyo de la espalda."),
    "chest_fly": ("Pecho", "Ajusta banco, asiento o poleas y deja los codos ligeramente flexionados.", "Acerca los brazos frente al pecho y abre sólo hasta el recorrido que controles, sin forzar el hombro."),
    "shoulder_press": ("Hombros · tríceps", "Coloca el agarre cerca de los hombros y mantén pies y tronco estables.", "Empuja hacia arriba sin arquear la zona lumbar; vuelve despacio hasta un recorrido cómodo."),
    "lateral_raise": ("Deltoides lateral", "Mantén una ligera flexión de codo y ajusta el agarre o apoyo antes de elevar.", "Separa el brazo hasta una altura cómoda, como máximo la del hombro, sin encogerlo ni balancearte."),
    "triceps": ("Tríceps", "Ajusta el agarre y mantén el brazo estable en la posición indicada, sin forzar el hombro.", "Extiende el codo con control y vuelve despacio, sin impulsarte con el tronco."),
    "vertical_pull": ("Dorsales · bíceps", "Ajusta el apoyo de muslos y toma el agarre por encima del cuerpo con los pies firmes.", "Lleva los codos hacia abajo y el agarre al frente del pecho; evita tirar detrás de la cabeza o balancearte."),
    "horizontal_pull": ("Espalda media · dorsales", "Ajusta asiento, apoyo de pecho o posición de cadera y comienza con el tronco estable.", "Acerca los codos al tronco o llévalos hacia atrás según el agarre, sin encoger los hombros; vuelve con control."),
    "rear_delt": ("Deltoides posterior · espalda alta", "Ajusta el apoyo o la polea para mantener los brazos delante del pecho y el tronco estable.", "Abre o tira de los brazos sin arquear la espalda ni elevar los hombros; usa una resistencia que controles."),
    "biceps": ("Bíceps · flexores del codo", "Sujeta el agarre con las muñecas alineadas y coloca los codos estables junto al cuerpo o sobre el apoyo.", "Flexiona el codo y baja despacio; evita desplazar el hombro o impulsar la espalda."),
    "scapula": ("Trapecio · estabilizadores escapulares", "Mantén los brazos extendidos, el cuello relajado y el tronco estable.", "Mueve los hombros y las escápulas de forma controlada, sin girar el cuello ni dar tirones."),
    "knee_dominant": ("Cuádriceps · glúteos", "Ajusta el apoyo o la carga, apoya toda la planta del pie y mantén el tronco estable.", "Flexiona cadera y rodillas sólo hasta donde controles la pelvis; empuja siguiendo la dirección de los pies, sin rebotes."),
    "knee_extension": ("Cuádriceps", "Alinea las rodillas con el eje de la máquina y ajusta el rodillo sobre la parte baja de la pierna.", "Extiende las rodillas sin golpear el tope ni levantar la cadera; regresa despacio."),
    "hip_hinge": ("Isquiotibiales · glúteos", "Parte con las rodillas ligeramente flexionadas y la carga cerca del cuerpo.", "Lleva la cadera atrás sin perder estabilidad del tronco; vuelve con la cadera sin arquearte. No necesitas tocar el suelo."),
    "knee_flexion": ("Isquiotibiales", "Ajusta el apoyo para que la rodilla coincida con el eje y el rodillo quede sobre la parte baja de la pierna.", "Flexiona las rodillas sin despegar la pelvis ni soltar la carga; vuelve con control."),
    "hip_extension": ("Glúteos", "Ajusta el apoyo y coloca los pies estables; protege el contacto de la carga con la cadera.", "Extiende la cadera sin arquear la espalda ni levantar las costillas; vuelve despacio."),
    "hip_accessory": ("Glúteos · musculatura de cadera", "Ajusta los apoyos o la polea para mantener pelvis y tronco estables.", "Mueve la pierna en el recorrido indicado con control, sin girar la pelvis ni impulsarte."),
    "calf": ("Gemelos · sóleo", "Coloca la parte delantera del pie sobre el apoyo y ajusta la carga sin perder el equilibrio.", "Sube y baja los talones sin rebotes ni impulsos de rodilla, en un recorrido que controles."),
    "core": ("Abdomen · estabilidad del tronco", "Adopta la posición indicada con un apoyo firme y respira con normalidad.", "Mantén el tronco estable y termina la serie si pierdes la postura; evita aguantar la respiración o forzar la zona lumbar."),
}

# Distinct named variants. The categories describe equipment types, not an
# assertion that every gym owns every machine. Exact equipment is shown in each
# entry; unavailable individual variants can be excluded before generating.
_ADDITIONS = [
    ("dumbbell-flat-bench-press", "Press de pecho con mancuernas en banco plano", "push", "chest_press", ["dumbbell", "bench"], "inicial"),
    ("incline-dumbbell-press", "Press inclinado con mancuernas", "push", "chest_press", ["dumbbell", "bench"], "inicial"),
    ("incline-machine-chest-press", "Press inclinado de pecho en máquina", "push", "chest_press", ["machine"], "inicial"),
    ("smith-flat-bench-press", "Press de pecho en banco plano en Smith", "push", "chest_press", ["machine", "bench"], "intermedio"),
    ("smith-incline-bench-press", "Press inclinado de pecho en Smith", "push", "chest_press", ["machine", "bench"], "intermedio"),
    ("barbell-flat-bench-press", "Press de banca con barra y seguros", "push", "chest_press", ["barbell", "bench"], "intermedio"),
    ("barbell-incline-bench-press", "Press de banca inclinado con barra", "push", "chest_press", ["barbell", "bench"], "intermedio"),
    ("dumbbell-floor-press", "Press de pecho con mancuernas en el suelo", "push", "chest_press", ["dumbbell"], "inicial"),
    ("incline-push-up", "Flexión de brazos con manos en banco", "push", "chest_press", ["bodyweight", "bench"], "inicial"),
    ("floor-push-up", "Flexión de brazos en el suelo", "push", "chest_press", ["bodyweight"], "intermedio"),
    ("standing-cable-chest-fly", "Apertura de pecho de pie en poleas", "push", "chest_fly", ["cable"], "inicial"),
    ("low-to-high-cable-fly", "Apertura de pecho en poleas de abajo hacia arriba", "push", "chest_fly", ["cable"], "intermedio"),
    ("pec-deck-fly", "Apertura de pecho en máquina pec deck", "push", "chest_fly", ["machine"], "inicial"),
    ("flat-dumbbell-chest-fly", "Apertura de pecho con mancuernas en banco plano", "push", "chest_fly", ["dumbbell", "bench"], "intermedio"),
    ("machine-shoulder-press", "Press de hombros sentado en máquina", "push", "shoulder_press", ["machine"], "inicial"),
    ("seated-barbell-shoulder-press", "Press de hombros sentado con barra y seguros", "push", "shoulder_press", ["barbell", "bench"], "intermedio"),
    ("arnold-dumbbell-press", "Press Arnold sentado con mancuernas", "push", "shoulder_press", ["dumbbell", "bench"], "intermedio"),
    ("single-arm-cable-lateral-raise", "Elevación lateral unilateral en polea baja", "push", "lateral_raise", ["cable"], "inicial"),
    ("machine-lateral-raise", "Elevación lateral sentado en máquina", "push", "lateral_raise", ["machine"], "inicial"),
    ("seated-dumbbell-lateral-raise", "Elevación lateral sentado con mancuernas", "push", "lateral_raise", ["dumbbell", "bench"], "inicial"),
    ("overhead-cable-triceps-extension", "Extensión de tríceps sobre la cabeza en polea", "push", "triceps", ["cable"], "intermedio"),
    ("straight-bar-triceps-pushdown", "Extensión de tríceps en polea con barra recta", "push", "triceps", ["cable"], "inicial"),
    ("seated-dumbbell-triceps-extension", "Extensión de tríceps sentado con mancuerna sobre la cabeza", "push", "triceps", ["dumbbell", "bench"], "intermedio"),
    ("lying-dumbbell-triceps-extension", "Extensión de tríceps tumbado con mancuernas", "push", "triceps", ["dumbbell", "bench"], "intermedio"),
    ("machine-triceps-extension", "Extensión de tríceps sentado en máquina", "push", "triceps", ["machine"], "inicial"),
    ("cross-body-cable-triceps-extension", "Extensión cruzada de tríceps unilateral en polea", "push", "triceps", ["cable"], "inicial"),
    ("neutral-grip-lat-pulldown", "Jalón al pecho con agarre neutro", "pull", "vertical_pull", ["cable"], "inicial"),
    ("supinated-lat-pulldown", "Jalón al pecho con agarre supino", "pull", "vertical_pull", ["cable"], "inicial"),
    ("single-arm-lat-pulldown", "Jalón unilateral sentado en polea alta", "pull", "vertical_pull", ["cable"], "inicial"),
    ("converging-machine-pulldown", "Jalón al pecho en máquina convergente", "pull", "vertical_pull", ["machine"], "inicial"),
    ("assisted-machine-pull-up", "Dominada asistida en máquina con agarre prono", "pull", "vertical_pull", ["machine"], "intermedio"),
    ("assisted-machine-chin-up", "Dominada asistida en máquina con agarre supino", "pull", "vertical_pull", ["machine"], "intermedio"),
    ("seated-cable-row", "Remo sentado en polea baja con agarre neutro", "pull", "horizontal_pull", ["cable"], "inicial"),
    ("wide-grip-cable-row", "Remo sentado en polea con agarre prono ancho", "pull", "horizontal_pull", ["cable"], "inicial"),
    ("single-arm-cable-row", "Remo unilateral sentado en polea", "pull", "horizontal_pull", ["cable"], "inicial"),
    ("one-arm-dumbbell-row", "Remo unilateral con mancuerna y apoyo en banco", "pull", "horizontal_pull", ["dumbbell", "bench"], "inicial"),
    ("incline-bench-dumbbell-row", "Remo con mancuernas y pecho apoyado en banco inclinado", "pull", "horizontal_pull", ["dumbbell", "bench"], "inicial"),
    ("bent-over-barbell-row", "Remo inclinado con barra", "pull", "horizontal_pull", ["barbell"], "intermedio"),
    ("supinated-barbell-row", "Remo inclinado con barra y agarre supino", "pull", "horizontal_pull", ["barbell"], "intermedio"),
    ("plate-loaded-machine-row", "Remo sentado en máquina de discos con apoyo de pecho", "pull", "horizontal_pull", ["machine"], "inicial"),
    ("incline-dumbbell-reverse-fly", "Apertura posterior con mancuernas y pecho apoyado", "pull", "rear_delt", ["dumbbell", "bench"], "inicial"),
    ("cable-reverse-fly", "Apertura posterior cruzada de pie en poleas", "pull", "rear_delt", ["cable"], "intermedio"),
    ("rope-face-pull", "Face pull con cuerda en polea alta", "pull", "rear_delt", ["cable"], "inicial"),
    ("seated-dumbbell-biceps-curl", "Curl de bíceps sentado con mancuernas", "pull", "biceps", ["dumbbell", "bench"], "inicial"),
    ("dumbbell-hammer-curl", "Curl martillo de pie con mancuernas", "pull", "biceps", ["dumbbell"], "inicial"),
    ("incline-dumbbell-curl", "Curl de bíceps con mancuernas en banco inclinado", "pull", "biceps", ["dumbbell", "bench"], "intermedio"),
    ("barbell-biceps-curl", "Curl de bíceps de pie con barra", "pull", "biceps", ["barbell"], "intermedio"),
    ("cable-biceps-curl", "Curl de bíceps de pie en polea baja", "pull", "biceps", ["cable"], "inicial"),
    ("machine-preacher-curl", "Curl de bíceps en máquina con apoyo predicador", "pull", "biceps", ["machine"], "inicial"),
    ("rope-cable-hammer-curl", "Curl martillo con cuerda en polea baja", "pull", "biceps", ["cable"], "inicial"),
    ("dumbbell-shrug", "Encogimiento de hombros con mancuernas", "pull", "scapula", ["dumbbell"], "inicial"),
    ("machine-shrug", "Encogimiento de hombros en máquina", "pull", "scapula", ["machine"], "inicial"),
    ("horizontal-leg-press", "Prensa horizontal de piernas", "legs", "knee_dominant", ["machine"], "inicial"),
    ("goblet-squat", "Sentadilla goblet con mancuerna", "legs", "knee_dominant", ["dumbbell"], "inicial"),
    ("dumbbell-box-squat", "Sentadilla a banco con mancuerna en goblet", "legs", "knee_dominant", ["dumbbell", "bench"], "inicial"),
    ("machine-hack-squat", "Sentadilla en máquina hack", "legs", "knee_dominant", ["machine"], "intermedio"),
    ("smith-squat", "Sentadilla en máquina Smith con seguros", "legs", "knee_dominant", ["machine"], "intermedio"),
    ("dumbbell-reverse-lunge", "Zancada hacia atrás con mancuernas", "legs", "knee_dominant", ["dumbbell"], "intermedio"),
    ("dumbbell-split-squat", "Sentadilla dividida con mancuernas", "legs", "knee_dominant", ["dumbbell"], "intermedio"),
    ("machine-leg-extension", "Extensión de rodillas sentado en máquina", "legs", "knee_extension", ["machine"], "inicial"),
    ("barbell-romanian-deadlift", "Peso muerto rumano con barra", "legs", "hip_hinge", ["barbell"], "intermedio"),
    ("cable-pull-through", "Pull through de cadera con cuerda en polea baja", "legs", "hip_hinge", ["cable"], "intermedio"),
    ("dumbbell-kickstand-romanian-deadlift", "Peso muerto rumano con mancuernas y apoyo escalonado", "legs", "hip_hinge", ["dumbbell"], "intermedio"),
    ("lying-machine-leg-curl", "Curl femoral tumbado en máquina", "legs", "knee_flexion", ["machine"], "inicial"),
    ("standing-machine-leg-curl", "Curl femoral de pie unilateral en máquina", "legs", "knee_flexion", ["machine"], "inicial"),
    ("barbell-hip-thrust", "Hip thrust con barra y espalda apoyada en banco", "legs", "hip_extension", ["barbell", "bench"], "intermedio"),
    ("machine-hip-thrust", "Hip thrust en máquina", "legs", "hip_extension", ["machine"], "inicial"),
    ("dumbbell-glute-bridge", "Puente de glúteos con mancuerna sobre la cadera", "legs", "hip_extension", ["dumbbell"], "inicial"),
    ("machine-hip-abduction", "Abducción de cadera sentado en máquina", "legs", "hip_accessory", ["machine"], "inicial"),
    ("standing-cable-hip-abduction", "Abducción de cadera de pie en polea baja", "legs", "hip_accessory", ["cable"], "inicial"),
    ("machine-hip-adduction", "Aducción de cadera sentado en máquina", "legs", "hip_accessory", ["machine"], "inicial"),
    ("seated-machine-calf-raise", "Elevación de talones sentado en máquina", "legs", "calf", ["machine"], "inicial"),
    ("leg-press-calf-raise", "Elevación de talones en prensa de piernas", "legs", "calf", ["machine"], "intermedio"),
    ("standing-dumbbell-calf-raise", "Elevación de talones de pie con mancuernas", "legs", "calf", ["dumbbell"], "inicial"),
    ("dead-bug", "Dead bug alternado en colchoneta", "legs", "core", ["bodyweight"], "inicial"),
    ("side-plank", "Plancha lateral sobre antebrazo", "legs", "core", ["bodyweight"], "intermedio"),
    ("cable-pallof-press", "Press Pallof de pie en polea", "legs", "core", ["cable"], "inicial"),
    ("machine-abdominal-crunch", "Crunch abdominal sentado en máquina", "legs", "core", ["machine"], "inicial"),
]

_EXISTING = {
    "chest-press": ("push", "chest_press", ["machine"]),
    "shoulder-press": ("push", "shoulder_press", ["dumbbell", "bench"]),
    "lateral-raise": ("push", "lateral_raise", ["dumbbell"]),
    "triceps-extension": ("push", "triceps", ["cable"]),
    "lat-pulldown": ("pull", "vertical_pull", ["cable"]),
    "supported-row": ("pull", "horizontal_pull", ["machine"]),
    "reverse-fly": ("pull", "rear_delt", ["machine"]),
    "biceps-curl": ("pull", "biceps", ["dumbbell"]),
    "leg-press": ("legs", "knee_dominant", ["machine"]),
    "dumbbell-romanian-deadlift": ("legs", "hip_hinge", ["dumbbell"]),
    "seated-leg-curl": ("legs", "knee_flexion", ["machine"]),
    "standing-machine-calf-raise": ("legs", "calf", ["machine"]),
    "forearm-plank": ("legs", "core", ["bodyweight"]),
}

_SPECIAL_CUES = {
    "dumbbell-floor-press": ["Túmbate boca arriba con las rodillas flexionadas; coloca las mancuernas a los lados del pecho.", "Empuja sin despegar la espalda y baja despacio hasta que los brazos contacten suavemente el suelo, sin golpearlos."],
    "incline-push-up": ["Apoya las manos en un banco firme, un poco más abiertas que los hombros, y alinea cabeza, tronco y piernas.", "Acerca el pecho al banco doblando los codos y empuja conservando el cuerpo en bloque; evita hundir la cadera."],
    "floor-push-up": ["Apoya manos y puntas de los pies en el suelo; mantén cabeza, tronco y piernas alineados.", "Baja el pecho con los codos en un ángulo cómodo y empuja sin hundir la cadera ni adelantar la cabeza."],
    "arnold-dumbbell-press": ["Siéntate con respaldo, mancuernas frente a los hombros y palmas hacia ti; usa una carga ligera.", "Eleva mientras giras suavemente las palmas al frente y regresa sin forzar el hombro ni arquear la espalda."],
    "overhead-cable-triceps-extension": ["Toma la cuerda con la polea detrás de ti y coloca los brazos por encima de la cabeza en una posición cómoda.", "Extiende los codos sin mover el brazo ni arquear la espalda; baja la resistencia si pierdes la posición."],
    "seated-dumbbell-triceps-extension": ["Siéntate con respaldo y sujeta una mancuerna con ambas manos por encima de la cabeza, sin forzar el hombro.", "Flexiona y extiende los codos manteniendo los brazos estables; usa una carga que puedas colocar y retirar con control."],
    "lying-dumbbell-triceps-extension": ["Túmbate en banco plano con las mancuernas sobre los hombros y las palmas enfrentadas.", "Flexiona los codos llevando las mancuernas a los lados de la cabeza y vuelve sin desplazar el brazo ni perder control de la carga."],
    "assisted-machine-pull-up": ["Ajusta la asistencia y coloca rodillas o pies en el apoyo de la máquina según sus instrucciones; sujeta las asas con palmas al frente.", "Eleva el cuerpo sin balancearte ni estirar el cuello; baja con control y conserva apoyo al subir o bajar de la máquina."],
    "assisted-machine-chin-up": ["Ajusta la asistencia y apoya rodillas o pies según la máquina; usa las asas de agarre supino con palmas hacia ti.", "Acerca el cuerpo a las asas sin impulsos y desciende despacio; conserva el apoyo al entrar o salir de la máquina."],
    "rope-face-pull": ["Coloca la polea a la altura de la cara y sujeta los extremos de la cuerda con una carga ligera.", "Tira hacia los lados de la cara sin echar la cabeza hacia delante ni arquear la espalda; vuelve con control."],
    "machine-leg-extension": ["Alinea las rodillas con el eje de la máquina y coloca el rodillo sobre la parte baja de las piernas, por encima del tobillo.", "Extiende las rodillas sin golpear el tope ni levantar la cadera; regresa despacio sin soltar la carga."],
    "dumbbell-reverse-lunge": ["Sujeta las mancuernas a los lados y da un paso hacia atrás, conservando el pie delantero completo sobre el suelo.", "Baja ambas rodillas en un recorrido que controles y empuja con la pierna delantera para volver, sin rebotes; completa ambos lados."],
    "dumbbell-split-squat": ["Adopta una postura dividida con ambos pies en el suelo y las mancuernas a los lados; busca una base estable.", "Baja doblando ambas rodillas sin desplazar la pelvis de lado y vuelve con control; realiza el mismo trabajo en ambos lados."],
    "cable-pull-through": ["De espaldas a la polea baja, sujeta la cuerda entre las piernas y aléjate lo suficiente para mantener tensión.", "Lleva la cadera atrás con las rodillas algo flexionadas y extiéndela sin tirar con los brazos ni arquear la espalda."],
    "machine-hip-abduction": ["Siéntate con espalda apoyada y ajusta los apoyos por fuera de las rodillas en una posición inicial cómoda.", "Separa las piernas moviendo la cadera sin impulsar el tronco; vuelve despacio sin golpear los apoyos."],
    "machine-hip-adduction": ["Siéntate con espalda apoyada y coloca los apoyos por dentro de las rodillas, sin forzar la apertura inicial.", "Acerca las piernas con control y vuelve despacio, sin mover el tronco ni dejar caer la carga."],
    "standing-cable-hip-abduction": ["Coloca la tobillera en la pierna alejada de la polea y sujétate a un apoyo firme con la otra mano.", "Separa la pierna de lado sin girar la pelvis ni inclinar el tronco; vuelve con control y cambia de lado."],
    "dead-bug": ["Túmbate boca arriba con brazos hacia el techo y caderas y rodillas flexionadas; respira con normalidad.", "Extiende un brazo y la pierna contraria sólo hasta donde puedas mantener el tronco estable; vuelve y alterna sin arquearte."],
    "side-plank": ["Coloca el antebrazo bajo el hombro y apoya los pies de lado; eleva la cadera sin girar el tronco.", "Respira mientras mantienes la posición y termina si pierdes la alineación; realiza el mismo tiempo en ambos lados."],
    "cable-pallof-press": ["Colócate de lado a la polea a la altura del pecho, sujeta el agarre con ambas manos y separa los pies para estar estable.", "Extiende los brazos al frente resistiendo el giro del tronco y vuelve al pecho; completa ambos lados con la misma resistencia."],
    "machine-abdominal-crunch": ["Ajusta asiento y apoyos para que el movimiento parta del tronco y no de tirar con brazos o cuello.", "Acerca suavemente costillas y pelvis mientras expulsas el aire y vuelve con control, sin impulsos ni un recorrido doloroso."],
}

_SETUP_CUES = {
    "dumbbell-flat-bench-press": "Túmbate en un banco plano con pies firmes y mancuernas a los lados del pecho, con muñecas alineadas sobre los codos.",
    "incline-dumbbell-press": "Túmbate en un banco inclinado con pies firmes y mancuernas a los lados de la parte alta del pecho; no aumentes la inclinación si pierdes el apoyo.",
    "incline-machine-chest-press": "Ajusta el asiento y respaldo de la máquina inclinada para que las asas queden frente a la parte alta del pecho y los pies estén apoyados.",
    "smith-flat-bench-press": "Coloca un banco plano bajo la Smith, ajusta los seguros y alinea la barra con el pecho antes de liberar el gancho; pide ayuda para el ajuste si lo necesitas.",
    "smith-incline-bench-press": "Coloca el banco inclinado bajo la Smith y fija los seguros para que la barra llegue al frente de la parte alta del pecho sin forzar el hombro.",
    "barbell-flat-bench-press": "Túmbate en banco plano, planta los pies y ajusta soportes y seguros para retirar y devolver la barra con control; utiliza ayuda si no dominas el montaje.",
    "barbell-incline-bench-press": "Túmbate en banco inclinado, ajusta soportes y seguros y sujeta la barra por encima de la parte alta del pecho, con muñecas alineadas.",
    "standing-cable-chest-fly": "Coloca ambas poleas cerca de la altura del pecho, toma los agarres y adopta una postura dividida estable con los brazos abiertos y los codos algo flexionados.",
    "low-to-high-cable-fly": "Coloca ambas poleas abajo, toma los agarres y adopta una postura estable; acerca los brazos de abajo hacia el frente de la parte alta del pecho, sin elevar los hombros.",
    "pec-deck-fly": "Ajusta el asiento de la pec deck para que los apoyos o agarres queden a la altura del pecho y mantén la espalda apoyada.",
    "flat-dumbbell-chest-fly": "Túmbate en banco plano con las mancuernas sobre el pecho y los codos ligeramente flexionados; conserva ese ángulo mientras abres los brazos.",
    "machine-shoulder-press": "Ajusta asiento y respaldo de la máquina de hombros para comenzar con los agarres cerca de los hombros y los pies completamente apoyados.",
    "seated-barbell-shoulder-press": "Siéntate en banco con respaldo dentro de soportes con seguros y toma la barra delante de los hombros; no la lleves detrás del cuello.",
    "single-arm-cable-lateral-raise": "Colócate de lado a la polea baja y toma el agarre con el brazo alejado; mantén el tronco erguido y el codo ligeramente flexionado.",
    "machine-lateral-raise": "Ajusta el asiento de la máquina de elevación lateral para alinear los codos con los apoyos y conserva los pies firmes.",
    "seated-dumbbell-lateral-raise": "Siéntate en banco con pies firmes y mancuernas a los lados, con codos algo flexionados y hombros relajados.",
    "straight-bar-triceps-pushdown": "Coloca una barra recta en la polea alta, sujétala con palmas hacia abajo y mantén los codos junto al tronco.",
    "machine-triceps-extension": "Ajusta el asiento y apoyo de brazos de la máquina de tríceps para que los codos coincidan con el eje de movimiento.",
    "cross-body-cable-triceps-extension": "Colócate de lado a una polea alta y sujeta el agarre con la mano contraria; fija el brazo cerca del cuerpo antes de extender en diagonal.",
    "neutral-grip-lat-pulldown": "Siéntate en la polea alta, fija los muslos bajo el apoyo y toma un agarre neutro con las palmas enfrentadas.",
    "supinated-lat-pulldown": "Siéntate en la polea alta con muslos sujetos y toma la barra con palmas hacia ti, sin forzar muñecas ni hombros.",
    "single-arm-lat-pulldown": "Siéntate bajo la polea alta, fija la posición del cuerpo y toma el agarre con una mano; mantén el hombro alejado de la oreja.",
    "converging-machine-pulldown": "Ajusta asiento y apoyo de muslos de la máquina de jalón y toma las asas con un agarre cómodo, sin despegar los pies.",
    "seated-cable-row": "Siéntate frente a la polea baja con pies apoyados, rodillas algo flexionadas y un agarre neutro frente al abdomen.",
    "wide-grip-cable-row": "Siéntate frente a la polea baja con los pies apoyados y sujeta la barra con un agarre prono algo más abierto que los hombros.",
    "single-arm-cable-row": "Siéntate frente a una polea baja con pies firmes y toma un agarre con una mano; conserva los hombros y la pelvis orientados al frente.",
    "one-arm-dumbbell-row": "Apoya una mano y una rodilla en un banco firme y la otra planta del pie en el suelo; deja la mancuerna bajo el hombro sin girar el tronco.",
    "incline-bench-dumbbell-row": "Túmbate boca abajo con el pecho apoyado en un banco inclinado y los pies firmes; deja las mancuernas a los lados del banco.",
    "bent-over-barbell-row": "Inclina el tronco desde la cadera con las rodillas algo flexionadas y toma la barra con agarre prono; conserva la espalda estable y la barra cerca del cuerpo.",
    "supinated-barbell-row": "Inclina el tronco desde la cadera con rodillas algo flexionadas y toma la barra con palmas hacia delante; conserva muñecas y tronco estables.",
    "plate-loaded-machine-row": "Carga y asegura los discos de la máquina de remo, ajusta el asiento y apoya el pecho antes de tomar las asas.",
    "incline-dumbbell-reverse-fly": "Apoya el pecho en banco inclinado y deja las mancuernas bajo los hombros con codos ligeramente flexionados.",
    "cable-reverse-fly": "Coloca las poleas a la altura del pecho y toma cada agarre con la mano contraria, con brazos al frente y tronco estable.",
    "seated-dumbbell-biceps-curl": "Siéntate con pies firmes y mancuernas a los lados, con muñecas alineadas y codos junto al cuerpo.",
    "dumbbell-hammer-curl": "Ponte de pie con las mancuernas a los lados y las palmas enfrentadas; conserva esa orientación durante el movimiento.",
    "incline-dumbbell-curl": "Apoya la espalda en un banco inclinado, deja los brazos a los lados y evita llevar el hombro muy atrás si no controlas esa posición.",
    "barbell-biceps-curl": "De pie, sujeta la barra con palmas hacia arriba y muñecas alineadas; mantén los codos junto al cuerpo sin arquear la espalda.",
    "cable-biceps-curl": "De pie frente a la polea baja, sujeta la barra con palmas hacia arriba y sitúa los codos a los lados del tronco.",
    "machine-preacher-curl": "Ajusta el asiento para apoyar por completo la parte alta de los brazos en el predicador y alinear los codos con el eje de la máquina.",
    "rope-cable-hammer-curl": "Coloca una cuerda en la polea baja y sujeta sus extremos con palmas enfrentadas, con codos junto al cuerpo.",
    "dumbbell-shrug": "De pie, sujeta las mancuernas a los lados con los brazos extendidos y mira al frente, sin adelantar la cabeza.",
    "machine-shrug": "Ajusta la máquina de encogimientos y toma sus asas con los brazos extendidos y los pies firmes sobre el apoyo.",
    "horizontal-leg-press": "Ajusta la distancia del asiento de la prensa horizontal, apoya espalda y pelvis en el respaldo y coloca ambos pies completos sobre la plataforma.",
    "goblet-squat": "De pie con una base estable, sujeta la mancuerna delante del pecho con ambas manos y conserva los codos cerca del cuerpo.",
    "dumbbell-box-squat": "Coloca un banco firme detrás de ti, sujeta una mancuerna delante del pecho y toca el banco con la cadera sin dejarte caer ni relajarte sobre él.",
    "machine-hack-squat": "Apoya espalda y hombros en la máquina hack, coloca ambos pies sobre la plataforma y ajusta los seguros antes de iniciar el descenso.",
    "smith-squat": "Coloca la barra de la Smith sobre la parte alta de la espalda, sin apoyarla en el cuello, y fija los seguros; usa una posición de pies que puedas controlar.",
    "barbell-romanian-deadlift": "De pie, toma la barra con ambas manos delante de los muslos, con rodillas ligeramente flexionadas y la carga cerca del cuerpo.",
    "dumbbell-kickstand-romanian-deadlift": "De pie con mancuernas, retrasa un pie dejando su punta como apoyo; carga principalmente la pierna delantera y mantén la pelvis orientada al frente.",
    "lying-machine-leg-curl": "Túmbate boca abajo en la máquina de curl y ajusta el eje con las rodillas y el rodillo sobre la parte baja de las piernas; apoya la pelvis.",
    "standing-machine-leg-curl": "De pie en la máquina de curl unilateral, ajusta el rodillo de la pierna que trabaja y conserva el otro pie firme y las manos en los apoyos.",
    "barbell-hip-thrust": "Apoya la parte alta de la espalda en un banco inmóvil y coloca la barra con protección sobre la cadera; planta ambos pies antes de elevarla.",
    "machine-hip-thrust": "Ajusta respaldo, plataforma y cinturón o apoyo de cadera de la máquina de hip thrust; conserva los pies completos sobre el apoyo.",
    "dumbbell-glute-bridge": "Túmbate boca arriba con rodillas flexionadas y pies firmes; sujeta una mancuerna con protección sobre la cadera antes de elevarla.",
    "seated-machine-calf-raise": "Siéntate en la máquina de gemelos, ajusta el apoyo sobre los muslos y coloca la parte delantera de los pies en la plataforma.",
    "leg-press-calf-raise": "Ajusta los seguros de la prensa y conserva espalda y pelvis apoyadas; coloca la parte delantera de ambos pies firmemente en la plataforma, con rodillas sin bloqueo.",
    "standing-dumbbell-calf-raise": "De pie sobre suelo firme, sujeta las mancuernas a los lados; usa una carga que te permita mantener el equilibrio sin subirte a objetos inestables.",
}

_SOURCE_FAMILIES = {
    "chest_press": "https://www.nasm.org/resource-center/exercise-library/barbell-bench-press",
    "vertical_pull": "https://www.nasm.org/resource-center/blog/training/the-biomechanics-of-the-lat-pulldown-muscles-grip-and-form",
    "knee_dominant": "https://www.nasm.org/resource-center/blog/training/biomechanics-of-the-squat",
    "hip_hinge": "https://www.nasm.org/resource-center/exercise-library/dumbbell-romanian-deadlift",
    "knee_flexion": "https://www.nasm.org/resource-center/exercise-library/seated-leg-curl",
    "core": "https://www.nasm.org/resource-center/exercise-library",
}


def get_exercise_catalog():
    """Return fresh editorial variants; no profile, I/O or random selection."""
    from copy import deepcopy
    records = []
    for session in _base_program()["sessions"]:
        for source in session["exercises"]:
            record = deepcopy(source)
            group, slot, keys = _EXISTING[record["id"]]
            record.update(session=group, slot=slot, equipment_keys=list(keys),
                          experience_min="inicial", muscles=_SLOTS[slot][0].split(" · "),
                          source_url=_SOURCE_FAMILIES.get(slot, "https://www.nasm.org/resource-center/exercise-library"),
                          source_scope="Referencia de familia; selección y técnica resumida editoriales")
            record["sets"] = {"minimum": 1, "maximum": 1}
            if record["id"] == "dumbbell-romanian-deadlift":
                record["experience_min"] = "intermedio"
            if record["id"] == "leg-press":
                record["source_url"] = "https://www.nasm.org/resource-center/exercise-library/leg-press"
            elif record["id"] == "forearm-plank":
                record["source_url"] = "https://www.nasm.org/resource-center/exercise-library/plank"
            records.append(record)
    for identifier, name, session, slot, keys, level in _ADDITIONS:
        muscles, setup, movement = _SLOTS[slot]
        equipment = [_EQUIPMENT[key] for key in keys]
        if "machine" in keys:
            equipment[0] = name
        seconds = identifier == "side-plank"
        repetitions = "15–25 por lado" if seconds else "8–12"
        if slot in {"chest_fly", "lateral_raise", "triceps", "rear_delt", "biceps", "scapula", "knee_extension", "knee_flexion", "hip_accessory", "calf"}:
            repetitions = "10–15"
        if identifier in {"single-arm-lat-pulldown", "single-arm-cable-row", "one-arm-dumbbell-row", "single-arm-cable-lateral-raise", "cross-body-cable-triceps-extension", "standing-machine-leg-curl", "standing-cable-hip-abduction", "dumbbell-reverse-lunge", "dumbbell-split-squat", "dumbbell-kickstand-romanian-deadlift", "dead-bug", "cable-pallof-press"}:
            repetitions += " por lado"
        cues = _SPECIAL_CUES[identifier] if identifier in _SPECIAL_CUES else [_SETUP_CUES[identifier], movement]
        record = _exercise(identifier, name, equipment, list(cues),
            {"name": name + " · práctica con menos resistencia", "equipment": list(equipment),
             "cue": "Practica este mismo movimiento con menos resistencia y un recorrido cómodo antes de progresar."},
            rest=120 if slot in {"chest_press", "shoulder_press", "vertical_pull", "horizontal_pull", "knee_dominant", "hip_hinge", "hip_extension"} else 60,
            repetitions=repetitions, repetition_unit="seconds" if seconds else "repetitions")
        record["sets"] = {"minimum": 1, "maximum": 1}
        record.update(session=session, slot=slot, equipment_keys=list(keys),
                      experience_min=level, muscles=muscles.split(" · "),
                      source_url=_SOURCE_FAMILIES.get(slot, "https://www.nasm.org/resource-center/exercise-library"),
                      source_scope="Referencia de familia; selección y técnica resumida editoriales")
        if identifier == "machine-hip-adduction":
            record["muscles"] = ["Aductores de cadera"]
        elif identifier in {"machine-hip-abduction", "standing-cable-hip-abduction"}:
            record["muscles"] = ["Glúteo medio", "Abductores de cadera"]
        if identifier == "horizontal-leg-press":
            record["source_url"] = "https://www.nasm.org/resource-center/exercise-library/leg-press"
        elif identifier in {"side-plank", "dead-bug"}:
            record["source_url"] = "https://www.nasm.org/resource-center/exercise-library/" + identifier
        records.append(record)
    return records


def get_routine_program():
    """A six-exercise-per-session baseline; generation is a separate action."""
    from core.routine_generator import build_routine
    program = build_routine({})
    program["generated"] = False
    return program
