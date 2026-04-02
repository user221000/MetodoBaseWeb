"""
web/constants.py — Constantes exclusivas de la aplicación web.

Este módulo centraliza TODAS las constantes que la app web necesita,
eliminando la dependencia con config/constantes.py (que es shared/desktop).

Para constantes de negocio nutricional (alimentos, macros, factores),
los módulos core/ siguen siendo la fuente de verdad.
"""
import os
from pathlib import Path

# ============================================================================
# VERSION
# ============================================================================

VERSION = "2.0.0"

# ============================================================================
# RUTAS DE DATOS — Resolución independiente (sin config/constantes.py)
# ============================================================================

_data_override = os.getenv("METODOBASE_DATA_DIR")
if _data_override:
    WEB_DATA_DIR = Path(_data_override)
else:
    _xdg = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    WEB_DATA_DIR = Path(_xdg) / "MetodoBase"

CARPETA_REGISTROS = str(WEB_DATA_DIR / "registros")
CARPETA_PLANES = str(WEB_DATA_DIR / "planes")
CARPETA_SALIDA = CARPETA_PLANES

# Nota: NO crear directorios al importar — causa PermissionError en Docker/Railway
# Usar ensure_data_dirs() desde create_app() en su lugar
_DATA_DIRS_INITIALIZED = False


def ensure_data_dirs():
    """Crea directorios de datos de forma lazy (llamar desde startup, no en import)."""
    global _DATA_DIRS_INITIALIZED
    if _DATA_DIRS_INITIALIZED:
        return
    for _carpeta in (CARPETA_REGISTROS, CARPETA_PLANES):
        try:
            Path(_carpeta).mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            import logging
            logging.getLogger(__name__).warning("Could not create %s: %s", _carpeta, e)
    _DATA_DIRS_INITIALIZED = True

# ============================================================================
# PLANES DE LICENCIA (sincronizar con Stripe Products)
# ============================================================================

PLANES_LICENCIA = {
    "free": {
        "precio_mxn": 0,
        "max_clientes": 5,
        "max_sesiones": 1,
        "max_planes_diarios": 5,
        "max_registros_diarios": 5,
        "max_planes_por_cliente_dia": 5,
        "multi_usuario": False,
        "preferencias_alimentos": False,
        "gestion_suscripciones": False,
        "progresion_clientes": False,
        "stripe_price_id": None,
        "features": ["pdf_export"],
        "descripcion": "Prueba gratuita",
    },
    "standard": {
        "precio_mxn": 159,
        "max_clientes": 25,
        "max_sesiones": 2,
        "max_planes_diarios": 1,
        "max_registros_diarios": 25,
        "max_planes_por_cliente_dia": 1,
        "multi_usuario": False,
        "preferencias_alimentos": False,
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
        "max_clientes": 0,
        "max_sesiones": 0,
        "max_planes_diarios": 0,
        "max_registros_diarios": 0,
        "max_planes_por_cliente_dia": 0,
        "multi_usuario": True,
        "preferencias_alimentos": True,
        "gestion_suscripciones": True,
        "progresion_clientes": True,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_CLINICA", ""),
        "features": ["pdf_export", "excel_export", "api_access", "custom_branding", "templates", "multi_user", "priority_support", "food_preferences", "client_subscriptions", "client_progression"],
        "descripcion": "Sin límites, para clínicas y equipos grandes",
    },
    "pro_usuario": {
        "precio_mxn": 79,
        "max_clientes": 1,
        "max_sesiones": 1,
        "max_planes_diarios": 5,
        "max_registros_diarios": 0,
        "max_planes_por_cliente_dia": 5,
        "multi_usuario": False,
        "preferencias_alimentos": False,
        "gestion_suscripciones": False,
        "progresion_clientes": False,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PRO_USUARIO", ""),
        "features": ["pdf_export", "priority_support"],
        "descripcion": "Plan Pro para usuarios individuales",
    },
}

# Trial configuration
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "14"))
TRIAL_MAX_CLIENTES = int(os.getenv("TRIAL_MAX_CLIENTES", "50"))

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
