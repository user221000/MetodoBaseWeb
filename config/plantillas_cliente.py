"""Plantillas por tipo de cliente para flujo comercial del gym."""

PLANTILLAS_CLIENTE: dict[str, dict[str, str]] = {
    "mujer_principiante": {
        "label": "Mujer Principiante",
        "objetivo_motor": "deficit",
        "actividad_sugerida": "leve",
        "descripcion": "Perfil de arranque con enfoque en adherencia y pérdida gradual de grasa.",
    },
    "hombre_recomposicion": {
        "label": "Hombre Recomposición",
        "objetivo_motor": "mantenimiento",
        "actividad_sugerida": "moderada",
        "descripcion": "Perfil orientado a mejorar composición corporal con entrenamiento constante.",
    },
    "perdida_grasa": {
        "label": "Pérdida de Grasa",
        "objetivo_motor": "deficit",
        "actividad_sugerida": "moderada",
        "descripcion": "Prioriza déficit calórico y adherencia para reducir grasa.",
    },
    "volumen": {
        "label": "Volumen",
        "objetivo_motor": "superavit",
        "actividad_sugerida": "moderada",
        "descripcion": "Prioriza superávit controlado para ganancia de masa.",
    },
    "recomposicion": {
        "label": "Recomposición",
        "objetivo_motor": "mantenimiento",
        "actividad_sugerida": "moderada",
        "descripcion": "Busca mejorar composición corporal con calorías cercanas a mantenimiento.",
    },
}

ORDEN_PLANTILLAS: list[str] = [
    "mujer_principiante",
    "hombre_recomposicion",
    "perdida_grasa",
    "recomposicion",
    "volumen",
]

PLANTILLAS_LABELS: list[str] = [
    PLANTILLAS_CLIENTE[k]["label"] for k in ORDEN_PLANTILLAS if k in PLANTILLAS_CLIENTE
]

PLANTILLAS_POR_LABEL: dict[str, str] = {
    v["label"]: k for k, v in PLANTILLAS_CLIENTE.items()
}
