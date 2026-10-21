"""Reviewed, generic resistance-training examples; no profile or generated data.

This catalogue is educational organisation, not an individual prescription or
a claim that a three-day PPL split meets every public-health recommendation.
Each call creates an independent inert value; no user state lives here.
"""


def _exercise(identifier, name, equipment, cues, alternative, *, rest=90, per_side=False):
    return {
        "id": identifier, "name": name, "sets": {"minimum": 1, "maximum": 2},
        "repetitions": "8–12 por lado" if per_side else "8–12",
        "rest_seconds": rest, "equipment": equipment, "cues": cues,
        "alternative": alternative,
    }


def get_routine_program():
    """Return the same bounded, unpersonalised programme for every account."""
    return {
        "id": "ppl-basico-v1", "title": "Una semana para empezar a moverte",
        "audience": "Ejemplo general para adultos sanos principiantes",
        "summary": "Tres sesiones sencillas: empujar, tirar y trabajar piernas. Elige días no consecutivos y empieza con calma.",
        "schedule": {
            "sessions_per_week": 3, "nonconsecutive": True,
            "default_days": [0, 2, 4],
            "days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            "note": "Es una forma de organizar ejercicios, no una rutina adaptada a tu salud ni una garantía de cumplir todas las guías de actividad física.",
        },
        "warmup": [
            "Camina o muévete suavemente durante 5–10 minutos.",
            "Ensaya los movimientos sin carga o con una carga ligera antes de las series.",
        ],
        "starting_point": "Empieza con 1 serie por ejercicio. Considera una segunda sólo si mantienes la técnica y te recuperas bien. Elige una carga manejable; no necesitas llegar al fallo.",
        "cautions": [
            "Muévete con control y respira sin contener el aire. Una alternativa sustituye al ejercicio; no se suma como trabajo extra.",
            "Si aparece dolor, detente. Si tienes lesiones, síntomas o una condición de salud, consulta con un profesional antes de usar este ejemplo.",
        ],
        "guideline_note": "CDC y ACSM recomiendan trabajar los grandes grupos musculares al menos dos días por semana. Este ejemplo Push/Pull/Legs de tres días no asegura esa frecuencia para cada grupo ni sustituye la actividad aeróbica.",
        "sessions": [
            {"id": "push", "name": "Push", "label": "Empuje", "focus": "Pecho · hombros · tríceps", "description": "Empuja con control, con apoyo estable y una carga fácil de manejar.", "exercises": [
                _exercise("chest-press", "Press de pecho en máquina", ["Máquina de pecho"],
                    ["Ajusta el asiento para que las asas queden a la altura del pecho.", "Apoya la espalda; empuja y vuelve despacio sin bloquear los codos."],
                    {"name": "Flexión en pared", "equipment": ["Pared firme"], "cue": "Apoya las manos a la altura del pecho y acerca el cuerpo en bloque; usa una posición cómoda."}),
                _exercise("shoulder-press", "Press de hombros sentado", ["Mancuernas ligeras", "Banco con respaldo"],
                    ["Siéntate con la espalda apoyada y los pies firmes.", "Eleva las mancuernas sin arquear la espalda; baja hasta una posición cómoda."],
                    {"name": "Press de hombros en máquina", "equipment": ["Máquina de hombros"], "cue": "Ajusta asiento y recorrido; mantén la espalda apoyada."}),
                _exercise("lateral-raise", "Elevación lateral", ["Mancuernas ligeras"],
                    ["Mantén los codos ligeramente flexionados y los hombros relajados.", "Eleva con control hasta una altura cómoda, como máximo a la altura de los hombros; evita balancearte."],
                    {"name": "Elevación lateral sin carga", "equipment": ["Sin equipo"], "cue": "Ensaya el mismo recorrido despacio y sin encoger los hombros."}, rest=60),
                _exercise("triceps-extension", "Extensión de tríceps en polea", ["Polea alta", "Cuerda o barra"],
                    ["Mantén los codos cerca del cuerpo y el tronco estable.", "Extiende sin bloquear el codo y vuelve lentamente, sin mover el hombro."],
                    {"name": "Extensión con banda", "equipment": ["Banda", "Anclaje alto seguro"], "cue": "Comprueba banda y anclaje antes; usa poca resistencia y los codos junto al cuerpo."}, rest=60),
            ]},
            {"id": "pull", "name": "Pull", "label": "Tirón", "focus": "Espalda · parte posterior del hombro · bíceps", "description": "Tira sin impulsos y deja que los brazos vuelvan despacio.", "exercises": [
                _exercise("lat-pulldown", "Jalón al pecho", ["Polea alta con asiento"],
                    ["Ajusta el apoyo de las piernas y sujeta con un agarre cómodo.", "Lleva la barra hacia la parte alta del pecho, nunca detrás del cuello; evita balancearte."],
                    {"name": "Jalón con banda", "equipment": ["Banda", "Anclaje alto seguro"], "cue": "Usa un anclaje diseñado para la banda; tira hacia el pecho con el tronco estable."}),
                _exercise("supported-row", "Remo con apoyo de pecho", ["Máquina de remo con apoyo"],
                    ["Ajusta el asiento y apoya el pecho sin forzar la postura.", "Lleva los codos hacia atrás sin encoger los hombros y vuelve con control."],
                    {"name": "Remo sentado con banda", "equipment": ["Banda", "Anclaje seguro a la altura del pecho"], "cue": "Siéntate estable, revisa el anclaje y tira sin inclinar el tronco."}),
                _exercise("reverse-fly", "Apertura posterior en máquina", ["Máquina de apertura posterior"],
                    ["Ajusta las asas a una altura cómoda y apoya el pecho.", "Abre los brazos suavemente con los codos algo flexionados; no eleves los hombros."],
                    {"name": "Apertura con banda ligera", "equipment": ["Banda ligera"], "cue": "Sujeta la banda delante del pecho y abre sólo hasta un recorrido cómodo, sin tirones."}, rest=60),
                _exercise("biceps-curl", "Curl de bíceps", ["Mancuernas ligeras"],
                    ["Mantén los codos junto al cuerpo y las muñecas alineadas.", "Flexiona y baja despacio sin balancear la espalda."],
                    {"name": "Curl sentado", "equipment": ["Mancuernas ligeras", "Silla estable"], "cue": "Apoya los pies y realiza el movimiento con poca carga, sin impulsarte."}, rest=60),
            ]},
            {"id": "legs", "name": "Legs", "label": "Piernas", "focus": "Piernas · cadera · zona media", "description": "Busca estabilidad y un recorrido cómodo antes de añadir resistencia.", "exercises": [
                _exercise("chair-squat", "Sentarse y levantarse de una silla", ["Silla firme sin ruedas"],
                    ["Coloca la silla contra una pared y apoya ambos pies.", "Lleva la cadera atrás para sentarte con control; levántate sin dejar caer las rodillas hacia dentro."],
                    {"name": "Sentadilla a banco alto", "equipment": ["Banco alto estable"], "cue": "Usa un apoyo más alto para reducir el recorrido y evita dejarte caer."}),
                _exercise("glute-bridge", "Puente de cadera", ["Colchoneta"],
                    ["Túmbate boca arriba, flexiona las rodillas y apoya los pies.", "Eleva la cadera sin arquear la zona lumbar y vuelve lentamente."],
                    {"name": "Puente con recorrido corto", "equipment": ["Colchoneta"], "cue": "Eleva menos la cadera y mantén un movimiento cómodo y controlado."}),
                _exercise("low-step-up", "Subida a escalón bajo", ["Escalón bajo estable", "Barandilla o apoyo firme"],
                    ["Apoya todo el pie en el escalón y usa el apoyo para equilibrarte.", "Sube y baja despacio; termina un lado y después cambia."],
                    {"name": "Sentarse y levantarse", "equipment": ["Silla firme"], "cue": "Si no hay un escalón seguro, usa la silla; no improvises con objetos apilados."}, per_side=True),
                _exercise("calf-raise", "Elevación de talones con apoyo", ["Suelo firme", "Apoyo estable"],
                    ["Apoya una mano para equilibrarte y mantén los pies sobre el suelo.", "Eleva ambos talones y baja despacio, sin rebotes."],
                    {"name": "Elevación de talones sentado", "equipment": ["Silla firme"], "cue": "Apoya los pies y sube los talones suavemente con las rodillas flexionadas."}, rest=60),
                _exercise("heel-slide", "Deslizamiento de talón", ["Colchoneta"],
                    ["Túmbate boca arriba con las rodillas flexionadas y respira con normalidad.", "Desliza un talón hacia delante sin arquear la espalda; vuelve y cambia de lado."],
                    {"name": "Marcha sentado", "equipment": ["Silla firme"], "cue": "Siéntate erguido y levanta un pie cada vez, sin inclinar el tronco."}, rest=60, per_side=True),
            ]},
        ],
        "sources": [
            {"label": "ACSM · Guías de fuerza 2026", "url": "https://acsm.org/resistance-training-guidelines-update-2026/"},
            {"label": "CDC · Actividad física para adultos", "url": "https://www.cdc.gov/physical-activity-basics/guidelines/adults.html"},
            {"label": "Gobierno de Victoria · Iniciarse en fuerza", "url": "https://www.betterhealth.vic.gov.au/health/healthyliving/resistance-training-health-benefits"},
        ],
    }
