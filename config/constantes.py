"""Constantes y configuración global del sistema Método Base."""
import os
import sys
from pathlib import Path

VERSION = "2.0.0"


def resource_path(relative_path: str) -> str:
    """Resuelve rutas portables para PyInstaller y desarrollo."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# ============================================================================
# CLASIFICACIÓN DE PROTEÍNAS Y GRASAS PARA COMPOSICIÓN DE COMIDAS
# ============================================================================

LEAN_PROTEINS = {
    "pechuga_de_pollo",
    "pescado_blanco",
    "atun",  # alias → atun_en_agua
    "claras_huevo",
    "pavo",
    "pavo_molido_93",
    "cerdo_lomo",
    "lomo_cerdo",
    "camarones",
    "jamon_pavo",
}

FATTY_PROTEINS = {
    "salmon",
    "huevo",
    "carne_molida",  # alias → carne_molida_res
    "carne_magra_res",
    "sardina",
    "queso_panela",
}

LIGHT_FATS = {
    "aceite_de_oliva",
    "aceite_de_aguacate",
}

HEAVY_FATS = {
    "mantequilla_mani",
    "almendras",
    "nueces",
    "aguacate",
    "cacahuates",
    "semillas_girasol",
    "semillas_chia",
    "pistaches",
    "semillas_calabaza",
    "linaza",
    "aceitunas_verdes",
}

PROTEIN_FOODS = LEAN_PROTEINS | FATTY_PROTEINS | {
    "queso_panela", "proteina_suero", "yogurt_griego_light", "yogurt_natural",
    "queso_cottage", "leche_descremada", "tofu",
    "queso_cottage_bajo_grasa", "edamame_cocido",
    "pescado_blanco", "carne_magra_res",
}


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

FACTORES_ACTIVIDAD = {
    'nula': 1.2,
    'leve': 1.375,
    'moderada': 1.55,
    'intensa': 1.725,
}

OBJETIVOS_VALIDOS = {'deficit', 'mantenimiento', 'superavit'}

NIVELES_ACTIVIDAD = {'nula', 'leve', 'moderada', 'intensa'}

# ============================================================================
# PLANES DE LICENCIA (sincronizar con Stripe Products)
# ============================================================================

PLANES_LICENCIA = {
    "free": {
        "precio_mxn": 0,
        "max_clientes": 10,
        "max_sesiones": 1,
        "max_planes_diarios": 1,
        "max_registros_diarios": 5,
        "max_planes_por_cliente_dia": 1,
        "multi_usuario": False,
        "preferencias_alimentos": True,
        "gestion_suscripciones": False,
        "progresion_clientes": False,
        "stripe_price_id": None,
        "features": ["pdf_export"],
        "descripcion": "Para empezar",
    },
    "standard": {
        "precio_mxn": 159,
        "max_clientes": 25,
        "max_sesiones": 2,
        "max_planes_diarios": 1,
        "max_registros_diarios": 25,
        "max_planes_por_cliente_dia": 1,
        "multi_usuario": False,
        "preferencias_alimentos": True,
        "gestion_suscripciones": False,
        "progresion_clientes": False,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_STANDARD", ""),
        "features": ["pdf_export", "excel_export", "api_access"],
        "descripcion": "Para nutriólogos independientes",
    },
    "gym_comercial": {
        "precio_mxn": 479,
        "max_clientes": 75,
        "max_sesiones": 4,
        "max_planes_diarios": 3,
        "max_registros_diarios": 0,
        "max_planes_por_cliente_dia": 3,
        "multi_usuario": False,
        "preferencias_alimentos": True,
        "gestion_suscripciones": True,
        "progresion_clientes": False,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_GYM_COMERCIAL", ""),
        "features": ["pdf_export", "excel_export", "api_access", "custom_branding", "templates", "food_preferences", "client_subscriptions"],
        "descripcion": "Para gimnasios en crecimiento",
    },
    "clinica": {
        "precio_mxn": 979,
        "max_clientes": 0,  # 0 = unlimited
        "max_sesiones": 0,  # 0 = unlimited
        "max_planes_diarios": 0,  # 0 = unlimited
        "max_registros_diarios": 0,  # 0 = unlimited
        "max_planes_por_cliente_dia": 0,  # 0 = unlimited
        "multi_usuario": True,
        "preferencias_alimentos": True,
        "gestion_suscripciones": True,
        "progresion_clientes": True,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_CLINICA", ""),
        "features": ["pdf_export", "excel_export", "api_access", "custom_branding", "templates", "multi_user", "priority_support", "food_preferences", "client_subscriptions", "client_progression"],
        "descripcion": "Sin límites, para clínicas y equipos grandes",
    },
}

# Trial configuration
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "14"))
TRIAL_MAX_CLIENTES = int(os.getenv("TRIAL_MAX_CLIENTES", "50"))  # Durante trial tienen límites de Starter

# Modo estricto: Si True, desviación > 5% invalida el plan; si False, solo warning
MODO_ESTRICTO = True


# ============================================================================
# HORARIOS DE COMIDAS RECOMENDADOS
# ============================================================================

HORARIOS_COMIDAS = {
    'desayuno': {
        'hora_ideal': '07:00',
        'rango': '07:00 - 08:30',
        'contexto': 'primera cosa en la mañana',
        'flexibilidad': '±1-2 horas'
    },
    'almuerzo': {
        'hora_ideal': '12:30',
        'rango': '12:30 - 13:30',
        'contexto': 'media mañana/mediodía',
        'flexibilidad': '±30-60 min'
    },
    'comida': {
        'hora_ideal': '15:00',
        'rango': '15:00 - 16:00',
        'contexto': 'post-entreno (si aplica)',
        'flexibilidad': '±30-60 min'
    },
    'cena': {
        'hora_ideal': '19:30',
        'rango': '19:30 - 20:30',
        'contexto': 'última comida del día (2-3h antes de dormir)',
        'flexibilidad': '±30-60 min'
    }
}


def get_horarios_comidas(gym_profile=None) -> dict:
    """Return meal schedules: gym-specific if set, otherwise defaults."""
    if gym_profile and getattr(gym_profile, "horarios_comidas", None):
        return gym_profile.horarios_comidas
    return HORARIOS_COMIDAS


# ============================================================================
# EXPLICACIÓN DE OBJETIVOS
# ============================================================================

EXPLICACION_OBJETIVOS = {
    'deficit': {
        'descripcion': 'DÉFICIT CALÓRICO (PERDER GRASA)',
        'calculo': 'Calorías: -15% vs mantenimiento',
        'proteina_razon': 'Proteína alta (1.8g/kg) preserva músculo durante pérdida de peso',
        'resultado_esperado': '-0.5kg/semana (grasa)',
        'duracion': '8-12 semanas máximo, luego descanso de 4-8 semanas',
        'notas': [
            'Come en déficit para reducir grasa corporal',
            'Mantén proteína alta para no perder músculo',
            'El cardio está OK, no es obligatorio',
            'Duerme bien (7-9 horas) para recuperación'
        ]
    },
    'mantenimiento': {
        'descripcion': 'MANTENIMIENTO (PRESERVAR PESO)',
        'calculo': 'Calorías: ~GET (ajustadas a tu actividad)',
        'proteina_razon': 'Proteína moderada-alta (1.8g/kg) para mantener masa muscular',
        'resultado_esperado': '±0kg/mes (peso estable)',
        'duracion': 'Indefinido, es tu baseline',
        'notas': [
            'Come matching your activity level',
            'Proteína suficiente para mantener músculos',
            'Ideal para "recomp" si es nuevo en gym'
        ]
    },
    'superavit': {
        'descripcion': 'SUPERÁVIT CALÓRICO (GANAR MASA)',
        'calculo': 'Calorías: +10% vs mantenimiento',
        'proteina_razon': 'Proteína alta (1.8g/kg) construcción de nuevo tejido muscular',
        'resultado_esperado': '+0.5kg/semana (incluye %agua y grasa)',
        'duracion': '8-12 semanas, luego déficit para "definir"',
        'notas': [
            'Come en superávit para ganar masa muscular',
            'Proteína es CRÍTICA para crecimiento',
            'Entreno de fuerza es OBLIGATORIO (pesas)',
            'Ganancia de grasa es normal (~20-30% de ganancia total)'
        ]
    }
}


# ============================================================================
# RUTAS DE DATOS DE LA APP
# ============================================================================

# METODOBASE_DATA_DIR permite override total (para Docker/Railway)
_data_override = os.getenv("METODOBASE_DATA_DIR")
if _data_override:
    APP_DATA_DIR = Path(_data_override)
elif os.getenv("APPDATA"):
    APP_DATA_DIR = Path(os.getenv("APPDATA")) / "MetodoBase"
elif sys.platform == "win32":
    APP_DATA_DIR = Path.home() / "AppData" / "Roaming" / "MetodoBase"
else:
    # Linux / macOS: usar XDG o ~/.local/share
    _xdg = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    APP_DATA_DIR = Path(_xdg) / "MetodoBase"

CARPETA_CONFIG = str(APP_DATA_DIR / "config")
CARPETA_REGISTROS = str(APP_DATA_DIR / "registros")
CARPETA_PLANES = str(APP_DATA_DIR / "planes")
CARPETA_SALIDA = CARPETA_PLANES

for carpeta in (CARPETA_CONFIG, CARPETA_REGISTROS, CARPETA_PLANES):
    Path(carpeta).mkdir(parents=True, exist_ok=True)

RUTA_LOGO = resource_path("assets/logo.png")

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Facturación — desactivada temporalmente.
# Para reactivar: cambiar a True.
# El código del módulo (facturacion_panel.py, sidebar "Facturación")
# permanece en el repositorio; sólo queda oculto en la UI.
ENABLE_BILLING = False


# ============================================================================
# MÍNIMOS REALISTAS POR ALIMENTO
# ============================================================================

MINIMOS_POR_ALIMENTO = {
    'avena': 40,
    'pan_integral': 50,
    'pan_blanco': 50,
    'tortilla_maiz': 2,
    'platano': 100,
    'arroz_blanco': 50,
    'arroz_integral': 50,
    'papa': 80,
    'camote': 80,
    'salmon': 100,
    'pescado_blanco': 80,
    'pechuga_de_pollo': 80,
    'carne_magra_res': 90,
    'almendras': 20,
    'nueces': 20,
    'aguacate': 80,
    'frijoles': 50,
    'lentejas': 50,
    'garbanzos': 50,
    'pasta_integral': 50,
    'quinoa': 50,
    'elote': 80,
    'platano_macho': 80,
    'tortilla_harina': 30,
    'cereal_integral': 30,
    'granola': 20,
    'atun': 80,
    'carne_molida': 80,
    'pavo': 80,
    'cerdo_lomo': 80,
    'camarones': 80,
    'sardina': 60,
    'queso_cottage': 50,
    'queso_cottage_bajo_grasa': 80,
    'yogurt_natural': 100,
    'jamon_pavo': 30,
    'leche_descremada': 100,
    'tofu': 80,
    'pavo_molido_93': 100,
    'lomo_cerdo': 100,
    'edamame_cocido': 80,
    'yuca': 80,
    'bulgur': 60,
    'cebada_perlada': 60,
    'cuscus': 60,
    'aceite_de_aguacate': 5,
    'semillas_girasol': 15,
    'semillas_chia': 10,
    'cacahuates': 20,
    'pistaches': 20,
    'semillas_calabaza': 15,
    'linaza': 10,
    'aceitunas_verdes': 30,
}


# ============================================================================
# ALIMENTOS CON LÍMITES ESTRICTOS (sin expansión permitida, máximo 200g)
# ============================================================================

ALIMENTOS_LIMITE_ESTRICTO = {'frijoles'}


# ============================================================================
# LÍMITES DUROS POR ALIMENTO (máx expansión 1.2x)
# ============================================================================

LIMITES_DUROS_ALIMENTOS = {
    # PROTEÍNAS (g por comida)
    'huevo':               200,
    'pechuga_de_pollo':    200,
    'carne_magra_res':     180,
    'pescado_blanco':      200,
    'salmon':              150,
    'claras_huevo':        300,
    'queso_panela':        100,
    'yogurt_griego_light': 200,
    'yogurt_natural':      200,
    'proteina_suero':       40,
    'atun':                200,
    'carne_molida':        200,
    'pavo':                250,
    'cerdo_lomo':          200,
    'camarones':           200,
    'sardina':             120,
    'queso_cottage':       200,
    'jamon_pavo':          100,
    'leche_descremada':    300,
    'tofu':                200,
    'pavo_molido_93':      220,
    'lomo_cerdo':          220,
    'queso_cottage_bajo_grasa': 220,
    'edamame_cocido':      180,
    # CARBOHIDRATOS
    'arroz_blanco':        200,
    'arroz_integral':      200,
    'papa':                250,
    'camote':              250,
    'avena':               100,
    'pan_integral':        100,
    'tortilla_maiz':       120,
    'frijoles':            250,
    'lentejas':            200,
    'garbanzos':           200,
    'pasta_integral':      250,
    'quinoa':              200,
    'elote':               200,
    'platano_macho':       200,
    'tortilla_harina':     100,
    'pan_blanco':          100,
    'cereal_integral':      80,
    'granola':              60,
    'platano':             200,
    'yuca':                250,
    'bulgur':              220,
    'cebada_perlada':      220,
    'cuscus':              220,
    # GRASAS
    'aguacate':            100,
    'nueces':               40,
    'almendras':            40,
    'aceite_de_oliva':      20,
    'mantequilla_mani':     30,
    'aceite_de_aguacate':   20,
    'semillas_girasol':     40,
    'semillas_chia':        30,
    'cacahuates':           50,
    'pistaches':            40,
    'semillas_calabaza':    35,
    'linaza':               20,
    'aceitunas_verdes':     80,
    # VEGETALES
    'brocoli':             300,
    'espinaca':            300,
    'lechuga_romana':      300,
    'pepino':              300,
    'tomate':              300,
    'zanahoria':           300,
    'calabaza':            300,
    'calabacita':          300,
    'col':                 300,
    'champiñones':         300,
    'coliflor':            300,
    'nopal':               300,
    'ejotes':              300,
    'chayote':             300,
    'apio':                300,
    'pimiento_verde':      300,
    'pimiento_rojo':       300,
    'cebolla':             200,
    'jicama':              300,
    'betabel':             300,
    'esparragos':          300,
    'berenjena':           300,
    'coles_bruselas':      300,
    'alcachofa':           250,
}


# ============================================================================
# FRECUENCIA MÁXIMA SEMANAL POR ALIMENTO
# ============================================================================

FRECUENCIA_MAXIMA_SEMANAL: dict[str, int] = {
    # Alimentos de costo elevado o ingesta limitada
    'salmon':              2,
    'aguacate':            4,
    'proteina_suero':      5,
    'nueces':              5,
    'almendras':           5,
    'camarones':           3,
    'sardina':             3,
    'atun':                3,
    'semillas_chia':       5,
    'semillas_girasol':    5,
    'cacahuates':          5,
    'aceite_de_aguacate':  5,
    'granola':             4,
    'pavo_molido_93':      4,
    'lomo_cerdo':          4,
    'queso_cottage_bajo_grasa': 5,
    'edamame_cocido':      5,
    'pistaches':           5,
    'semillas_calabaza':   5,
    'linaza':              5,
    'aceitunas_verdes':    5,
    # Alimentos económicos: sin restricción práctica
    'frijoles':           99,
    'lentejas':           99,
    'garbanzos':          99,
    'huevo':              99,
    'arroz_blanco':       99,
    'arroz_integral':     99,
    'papa':               99,
    'camote':             99,
    'avena':              99,
    'tortilla_maiz':      99,
    'pasta_integral':     99,
    'quinoa':             99,
    'elote':              99,
    'platano_macho':      99,
}


# ============================================================================
# CLASIFICACIÓN ESTRUCTURAL DE ALIMENTOS
# ============================================================================

PROTEINAS_ESTRUCTURALES = {
    'pechuga_de_pollo', 'carne_magra_res', 'pescado_blanco', 'salmon',
    'atun', 'pavo', 'cerdo_lomo', 'camarones',
    'pavo_molido_93', 'lomo_cerdo',
}

PROTEINAS_MIXTAS = {
    'huevo', 'frijoles', 'lentejas', 'queso_panela',
    'queso_cottage', 'queso_cottage_bajo_grasa', 'yogurt_griego_light',
    'yogurt_natural', 'tofu', 'sardina', 'edamame_cocido',
}

CARBOS_DENSOS = {
    'arroz_blanco', 'arroz_integral', 'papa', 'camote',
    'pasta_integral', 'quinoa', 'platano_macho',
    'yuca', 'bulgur', 'cebada_perlada', 'cuscus',
}

CARBOS_SECUNDARIOS = {
    'pan_integral', 'tortilla_maiz', 'avena', 'tortilla_harina',
    'pan_blanco', 'cereal_integral', 'granola', 'elote',
}

LEGUMINOSAS = {
    'frijoles', 'lentejas', 'garbanzos',
}


# ============================================================================
# LÍMITES PORCENTUALES DE KCAL POR COMIDA
# ============================================================================

LIMITES_PORCENTUALES_KCAL = {
    'proteina_principal': 0.45,
    'carb_principal': 0.50,
    'grasas_puras': 0.30,
    'leguminosas': 0.35,
}


# ============================================================================
# PAGINATION DEFAULTS
# ============================================================================

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE_PLANES = 50
MAX_PAGE_SIZE_PLANES = 200


# ============================================================================
# STATS PERIOD DURATIONS (days)
# ============================================================================

PERIODO_SEMANA_DIAS = 7
PERIODO_MES_DIAS = 30
PERIODO_ANIO_DIAS = 365


# ============================================================================
# BUSINESS RULE DURATIONS
# ============================================================================

LICENSE_EXPIRY_DAYS = 365
INVITATION_EXPIRY_DAYS = 7


# ============================================================================
# UPLOAD LIMITS
# ============================================================================

UPLOAD_ALLOWED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
UPLOAD_MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


# ============================================================================
# ERROR MESSAGES (centralized for i18n readiness)
# ============================================================================

ERR_CLIENTE_NO_ENCONTRADO = "Cliente no encontrado"
ERR_PAGOS_NO_CONFIGURADOS = "Pagos no configurados"
