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

from core.plan_catalog import get_plan_catalog

PLANES_LICENCIA = get_plan_catalog("web", stripe_prices={
    "standard": os.environ.get("STRIPE_PRICE_STANDARD", ""),
    "gym_comercial": os.environ.get("STRIPE_PRICE_GYM_COMERCIAL", ""),
    "clinica": os.environ.get("STRIPE_PRICE_CLINICA", ""),
    "pro_usuario": os.environ.get("STRIPE_PRICE_PRO_USUARIO", ""),
})

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
