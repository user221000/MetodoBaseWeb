"""
config/settings.py — Configuración centralizada para MetodoBase.

- Lee TODAS las variables de entorno desde un solo lugar.
- En producción (METODOBASE_ENV=production), falla si faltan secrets críticos.
- En desarrollo, usa defaults seguros para localhost.

Uso:
    from config.settings import get_settings
    settings = get_settings()
    print(settings.SECRET_KEY)
"""
import os
from functools import lru_cache
from pathlib import Path

# Cargar .env desde la raíz del proyecto (una sola vez al importar)
_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


class Settings:
    """Configuración del sistema. Single source of truth."""

    def __init__(self) -> None:
        self.ENV: str = os.getenv("METODOBASE_ENV", "development")
        self.is_production: bool = self.ENV == "production"
        self.DEBUG: bool = not self.is_production

        # ── Auth / Tokens ─────────────────────────────────────────────────
        self.SECRET_KEY: str = self._require_in_prod(
            "WEB_SECRET_KEY",
            dev_default="metodobase_dev_secret_2026_localhost_only",
        )
        if self.is_production and len(self.SECRET_KEY) < 32:
            raise RuntimeError(
                "FATAL: WEB_SECRET_KEY debe tener al menos 32 caracteres en producción."
            )
        # Refresh token system
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
        )
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
        )
        # Remember-me durations (access tokens are stateless/non-revocable, keep short)
        self.REMEMBER_ME_ACCESS_DAYS: int = int(
            os.getenv("REMEMBER_ME_ACCESS_DAYS", "7")
        )
        self.REMEMBER_ME_REFRESH_DAYS: int = int(
            os.getenv("REMEMBER_ME_REFRESH_DAYS", "30")
        )

        # ── CORS ──────────────────────────────────────────────────────────
        import logging as _logging
        _settings_logger = _logging.getLogger("config.settings")
        if self.is_production:
            raw_origins = os.getenv("CORS_ORIGINS", "")
            if not raw_origins:
                raise RuntimeError(
                    "FATAL: CORS_ORIGINS requerido en producción. "
                    "Configure los orígenes permitidos (ej: https://app.metodobase.com)."
                )
        else:
            raw_origins = os.getenv(
                "CORS_ORIGINS",
                "http://localhost:8000,http://localhost:8001,http://127.0.0.1:8000,http://127.0.0.1:8001",
            )
        self.CORS_ORIGINS: list[str] = [
            o.strip() for o in raw_origins.split(",") if o.strip()
        ]
        _settings_logger.info("[CORS] Origins: %s", self.CORS_ORIGINS)

        # ── Redis ─────────────────────────────────────────────────────────
        self.REDIS_URL: str = os.getenv("REDIS_URL", "")

        # ── Base de datos ─────────────────────────────────────────────────
        self.DB_PATH: str | None = os.getenv("DB_PATH", None)
        self.DATA_DIR: str | None = os.getenv("METODOBASE_DATA_DIR", None)

        # ── Stripe ────────────────────────────────────────────────────────
        self.STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
        self.STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        # ── Stripe Payment Links (pre-built Stripe checkout pages) ────────
        self.STRIPE_PAYMENT_LINK_STANDARD: str = os.getenv("STRIPE_PAYMENT_LINK_STANDARD", "")
        self.STRIPE_PAYMENT_LINK_GYM_COMERCIAL: str = os.getenv("STRIPE_PAYMENT_LINK_GYM_COMERCIAL", "")
        self.STRIPE_PAYMENT_LINK_CLINICA: str = os.getenv("STRIPE_PAYMENT_LINK_CLINICA", "")
        self.STRIPE_PAYMENT_LINK_PRO_USUARIO: str = os.getenv("STRIPE_PAYMENT_LINK_PRO_USUARIO", "")
        # ── MercadoPago ───────────────────────────────────────────────────
        self.MERCADOPAGO_ACCESS_TOKEN: str = os.getenv(
            "MERCADOPAGO_ACCESS_TOKEN", ""
        )
        self.MERCADOPAGO_WEBHOOK_SECRET: str = os.getenv(
            "MERCADOPAGO_WEBHOOK_SECRET", ""
        )

        # ── Google OAuth ──────────────────────────────────────────────
        self.GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", ""
        )

        # ── Stripe Price IDs ──────────────────────────────────────────────
        self.STRIPE_PRICE_STANDARD: str = os.getenv("STRIPE_PRICE_STANDARD", "")
        self.STRIPE_PRICE_GYM_COMERCIAL: str = os.getenv("STRIPE_PRICE_GYM_COMERCIAL", "")
        self.STRIPE_PRICE_CLINICA: str = os.getenv("STRIPE_PRICE_CLINICA", "")
        # Support both STRIPE_PRICE_PRO_USUARIO and STRIPE_PRICE_PRO (legacy)
        self.STRIPE_PRICE_PRO_USUARIO: str = os.getenv("STRIPE_PRICE_PRO_USUARIO", "") or os.getenv("STRIPE_PRICE_PRO", "")

        # ── Licencias ────────────────────────────────────────────────────
        self.LICENSE_SALT: str = self._require_in_prod(
            "METODO_BASE_SALT",
            dev_default="METODO_BASE_2026_CH",
        )

        # ── Server ────────────────────────────────────────────────────────
        self.HOST: str = os.getenv("WEB_HOST", "127.0.0.1")
        # Railway inyecta PORT (sin prefijo). Leer PORT primero, WEB_PORT como fallback.
        self.PORT: int = int(os.getenv("PORT", os.getenv("WEB_PORT", "8000")))

        # ── Email transaccional ───────────────────────────────────────────
        self.RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

        # ── Demo seed ─────────────────────────────────────────────────────
        self.SEED_DEMO: bool = os.getenv("METODOBASE_SEED_DEMO", "") == "1"

        # ── Feature flags ─────────────────────────────────────────────────
        self.FEATURE_FLAGS_STRICT: bool = (
            os.getenv("FEATURE_FLAGS_STRICT", "true" if self.is_production else "false").lower() == "true"
        )

        # ── Migration check ───────────────────────────────────────────────
        self.SKIP_MIGRATION_CHECK: bool = (
            os.getenv("SKIP_MIGRATION_CHECK", "false").lower() == "true"
        )

        # ── Docs ──────────────────────────────────────────────────────────
        self.DOCS_ENABLED: bool = not self.is_production or os.getenv(
            "ENABLE_DOCS", ""
        ) == "1"

        # ── Sentry ────────────────────────────────────────────────────────
        self.SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
        self.SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", self.ENV)
        self.SENTRY_TRACES_SAMPLE_RATE: float = float(
            os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")
        )
        self.SENTRY_PROFILES_SAMPLE_RATE: float = float(
            os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")
        )

        # ── HTTP Timeouts ─────────────────────────────────────────────────
        self.BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
        self.HTTP_CONNECT_TIMEOUT: float = float(
            os.getenv("HTTP_CONNECT_TIMEOUT", "5.0")
        )
        self.HTTP_READ_TIMEOUT: float = float(
            os.getenv("HTTP_READ_TIMEOUT", "30.0")
        )
        self.STRIPE_TIMEOUT: float = float(
            os.getenv("STRIPE_TIMEOUT", "30.0")
        )
        self.MERCADOPAGO_TIMEOUT: float = float(
            os.getenv("MERCADOPAGO_TIMEOUT", "30.0")
        )

        # ── Validación de producción ───────────────────────────────────────
        if self.is_production:
            missing = []
            if not os.getenv("WEB_SECRET_KEY"):
                missing.append("WEB_SECRET_KEY")
            if not os.getenv("METODO_BASE_SALT"):
                missing.append("METODO_BASE_SALT")
            if not os.getenv("DATABASE_URL") and not self.DB_PATH:
                missing.append("DATABASE_URL")
            if missing:
                raise RuntimeError(
                    f"FATAL: Variables obligatorias en producción no configuradas: "
                    f"{', '.join(missing)}. El servidor NO puede arrancar."
                )
            
            # Validar payment gateway keys en producción
            if not self.STRIPE_SECRET_KEY:
                _settings_logger.critical("[PAYMENTS] STRIPE_SECRET_KEY no configurada")
                raise RuntimeError("STRIPE_SECRET_KEY requerida en producción")
            if self.STRIPE_SECRET_KEY.startswith("sk_test_"):
                raise RuntimeError(
                    "FATAL: STRIPE_SECRET_KEY es una clave de prueba (sk_test_*). "
                    "En producción se requiere una clave live (sk_live_*)."
                )
            if not self.STRIPE_WEBHOOK_SECRET:
                _settings_logger.critical("[PAYMENTS] STRIPE_WEBHOOK_SECRET no configurada")
                raise RuntimeError("STRIPE_WEBHOOK_SECRET requerida en producción")
            if self.STRIPE_SECRET_KEY and not self.STRIPE_PUBLISHABLE_KEY:
                _settings_logger.critical("[PAYMENTS] STRIPE_PUBLISHABLE_KEY no configurada")
                raise RuntimeError("STRIPE_PUBLISHABLE_KEY requerida en producción")
            if self.STRIPE_PUBLISHABLE_KEY and self.STRIPE_PUBLISHABLE_KEY.startswith("pk_test_"):
                raise RuntimeError(
                    "FATAL: STRIPE_PUBLISHABLE_KEY es una clave de prueba (pk_test_*). "
                    "En producción se requiere una clave live (pk_live_*)."
                )
            # Validate Stripe Price IDs are set in production
            _missing_prices = []
            if not self.STRIPE_PRICE_STANDARD:
                _missing_prices.append("STRIPE_PRICE_STANDARD")
            if not self.STRIPE_PRICE_GYM_COMERCIAL:
                _missing_prices.append("STRIPE_PRICE_GYM_COMERCIAL")
            if not self.STRIPE_PRICE_CLINICA:
                _missing_prices.append("STRIPE_PRICE_CLINICA")
            if not self.STRIPE_PRICE_PRO_USUARIO:
                _missing_prices.append("STRIPE_PRICE_PRO_USUARIO")
            if _missing_prices:
                raise RuntimeError(
                    f"FATAL: Stripe Price IDs requeridos en producción: "
                    f"{', '.join(_missing_prices)}. "
                    f"Créalos en Stripe Dashboard > Products y configura las variables."
                )
            if not self.MERCADOPAGO_ACCESS_TOKEN:
                _settings_logger.warning("[PAYMENTS] MERCADOPAGO_ACCESS_TOKEN no configurada — MP desactivado")

            # Validar BASE_URL no sea localhost en producción
            if "localhost" in self.BASE_URL or "127.0.0.1" in self.BASE_URL:
                raise RuntimeError(
                    "FATAL: BASE_URL contiene localhost. "
                    "En producción configura el dominio real: BASE_URL=https://tudominio.com"
                )

            # Validar Google OAuth (warn, no block — login con email sigue funcionando)
            if not self.GOOGLE_CLIENT_ID:
                _settings_logger.warning(
                    "[AUTH] GOOGLE_CLIENT_ID no configurada — "
                    "Login con Google desactivado en producción"
                )

    def _require_in_prod(self, key: str, dev_default: str) -> str:
        """En producción, exige la variable; en dev, usa el default."""
        val = os.getenv(key, "")
        if val:
            return val
        if self.is_production:
            raise RuntimeError(
                f"❌ Variable de entorno requerida en producción: {key}\n"
                f"   Configúrala antes de iniciar el servidor."
            )
        return dev_default


@lru_cache()
def get_settings() -> Settings:
    """Singleton cacheado. Se crea una sola vez por proceso."""
    return Settings()
