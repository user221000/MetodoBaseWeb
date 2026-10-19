"""
tests/test_medium_fixes.py — Tests para los 15 hallazgos medios (M-01..M-15).

Mínimo 2 tests por fix. Ejecutar con:
    pytest tests/test_medium_fixes.py -v
"""
from __future__ import annotations

import importlib
import logging
import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# M-01 — print() → logger
# ═══════════════════════════════════════════════════════════════════════════════

class TestM01PrintToLogger:
    """Verifica que archivos clave usan logger en vez de print()."""

    _FILES = [
        "api_server.py",
        "web/database/migrate_legacy.py",
        "orchestrator/pipeline.py",
    ]

    @pytest.mark.parametrize("rel_path", _FILES)
    def test_no_bare_print_calls(self, rel_path):
        """Archivos de producción no deben usar print() directamente."""
        full = Path(__file__).resolve().parents[1] / rel_path
        source = full.read_text(encoding="utf-8")
        # Match print( at start of line or after spaces — skip comments and strings
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            # Detect bare print( calls (not inside strings)
            if re.match(r'\s*print\s*\(', line):
                pytest.fail(f"{rel_path}:{i} still uses print(): {line.strip()}")

    def test_api_server_has_logger(self):
        """api_server.py debe tener logger configurado."""
        import api_server
        assert hasattr(api_server, "logger")


# ═══════════════════════════════════════════════════════════════════════════════
# M-02 + M-05 — datetime.utcnow() eliminated
# ═══════════════════════════════════════════════════════════════════════════════

class TestM02M05UtcnowEliminated:
    """Verifica que datetime.utcnow() no se usa en código de producción."""

    _PROD_DIRS = ["api/", "web/", "core/", "config/", "src/"]

    def test_no_utcnow_in_production_code(self):
        root = Path(__file__).resolve().parents[1]
        violations = []
        for d in self._PROD_DIRS:
            for py in (root / d).rglob("*.py"):
                if "__pycache__" in str(py) or "alembic" in str(py):
                    continue
                text = py.read_text(encoding="utf-8")
                for i, line in enumerate(text.splitlines(), 1):
                    if "utcnow" in line and not line.lstrip().startswith("#"):
                        violations.append(f"{py.relative_to(root)}:{i}")
        assert not violations, f"utcnow found in: {violations}"

    def test_models_use_timezone_aware_defaults(self):
        """Los defaults de Column en models.py deben ser timezone-aware."""
        from web.database.models import Usuario
        col = Usuario.__table__.columns["fecha_registro"]
        assert col.default and callable(col.default.arg)
        # SQLAlchemy may wrap with context; call directly
        fn = col.default.arg
        try:
            ts = fn()
        except TypeError:
            ts = fn(None)
        assert ts.tzinfo is not None, "fecha_registro default should be tz-aware"


# ═══════════════════════════════════════════════════════════════════════════════
# M-03 — Pagination limit ≤ 100
# ═══════════════════════════════════════════════════════════════════════════════

class TestM03PaginationLimit:

    def test_clientes_list_max_100(self):
        """El endpoint de clientes usa constante centralizada para paginación."""
        source = (
            Path(__file__).resolve().parents[1] / "api" / "routes" / "clientes.py"
        ).read_text(encoding="utf-8")
        assert "MAX_PAGE_SIZE" in source, "Pagination limit should use MAX_PAGE_SIZE constant"

    def test_no_500_limit_anywhere_in_routes(self):
        """Ningun endpoint de api/routes tiene le=500 hardcoded."""
        routes = Path(__file__).resolve().parents[1] / "api" / "routes"
        for py in routes.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            assert "le=500" not in text, f"{py.name} still has hardcoded le=500"


# ═══════════════════════════════════════════════════════════════════════════════
# M-04 — Rate limiter forced in production
# ═══════════════════════════════════════════════════════════════════════════════

class TestM04RateLimiterProduction:

    def test_rate_limiter_forced_when_production(self, monkeypatch):
        """En producción, RATE_LIMIT_ENABLED debe ser True incluso si env dice false."""
        from config.settings import get_settings
        import web.middleware.rate_limiter as rl
        try:
            with monkeypatch.context() as environment:
                environment.setenv("METODOBASE_ENV", "production")
                environment.setenv("RATE_LIMIT_ENABLED", "false")
                get_settings.cache_clear()
                importlib.reload(rl)
                assert rl.RATE_LIMIT_ENABLED is True
        finally:
            # The environment is restored before rebuilding cached settings.
            get_settings.cache_clear()
            importlib.reload(rl)

    def test_rate_limiter_respects_env_in_development(self, monkeypatch):
        """En development, se respeta RATE_LIMIT_ENABLED=false."""
        from config.settings import get_settings
        import web.middleware.rate_limiter as rl
        try:
            with monkeypatch.context() as environment:
                environment.setenv("METODOBASE_ENV", "development")
                environment.setenv("RATE_LIMIT_ENABLED", "false")
                get_settings.cache_clear()
                importlib.reload(rl)
                assert rl.RATE_LIMIT_ENABLED is False
        finally:
            get_settings.cache_clear()
            importlib.reload(rl)


# ═══════════════════════════════════════════════════════════════════════════════
# M-06 — CTk references cleaned
# ═══════════════════════════════════════════════════════════════════════════════

class TestM06CtkReferences:

    def test_helpers_no_ctk(self):
        text = (Path(__file__).resolve().parents[1] / "utils" / "helpers.py").read_text(encoding="utf-8")
        assert "CTk" not in text, "utils/helpers.py should not reference CTk"

    def test_iconos_no_ctk(self):
        text = (Path(__file__).resolve().parents[1] / "utils" / "iconos.py").read_text(encoding="utf-8")
        assert "CTk" not in text, "utils/iconos.py should not reference CTk"


# ═══════════════════════════════════════════════════════════════════════════════
# M-07 — Request ID in error responses
# ═══════════════════════════════════════════════════════════════════════════════

class TestM07RequestID:

    def test_global_error_handler_includes_request_id(self):
        """_global_error handler should add request_id to response body."""
        source = (Path(__file__).resolve().parents[1] / "api" / "app.py").read_text(encoding="utf-8")
        assert "request_id" in source, "api/app.py should reference request_id"
        assert "X-Request-ID" in source, "api/app.py should set X-Request-ID header"

    def test_global_error_handler_gets_from_request_state(self):
        """Handler should read from request.state.request_id."""
        source = (Path(__file__).resolve().parents[1] / "api" / "app.py").read_text(encoding="utf-8")
        assert "request.state" in source


# ═══════════════════════════════════════════════════════════════════════════════
# M-08 — exc_info=DEBUG only
# ═══════════════════════════════════════════════════════════════════════════════

class TestM08ExcInfoDebug:

    def test_no_exc_info_true_in_app(self):
        """api/app.py should NOT have bare exc_info=True."""
        text = (Path(__file__).resolve().parents[1] / "api" / "app.py").read_text(encoding="utf-8")
        assert "exc_info=True" not in text

    def test_no_exc_info_true_in_pagos(self):
        """api/routes/pagos.py should NOT have bare exc_info=True."""
        text = (Path(__file__).resolve().parents[1] / "api" / "routes" / "pagos.py").read_text(encoding="utf-8")
        assert "exc_info=True" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# M-09 — Index on fecha_fin_suscripcion
# ═══════════════════════════════════════════════════════════════════════════════

class TestM09Index:

    def test_column_has_index(self):
        from web.database.models import Cliente
        col = Cliente.__table__.columns["fecha_fin_suscripcion"]
        assert col.index is True, "fecha_fin_suscripcion should have index=True"

    def test_alembic_migration_exists(self):
        versions = Path(__file__).resolve().parents[1] / "web" / "database" / "alembic" / "versions"
        migration_files = list(versions.glob("*fecha_fin*"))
        assert migration_files, "Alembic migration for fecha_fin_suscripcion should exist"


# ═══════════════════════════════════════════════════════════════════════════════
# M-10 — Invitation expiry uses timezone-aware comparison
# ═══════════════════════════════════════════════════════════════════════════════

class TestM10InvitationExpiry:

    def test_accept_invitation_uses_tz_aware(self):
        """team.py accept_invitation uses datetime.now(timezone.utc) for expiry check."""
        source = (Path(__file__).resolve().parents[1] / "web" / "routes" / "team.py").read_text(encoding="utf-8")
        # Should use datetime.now(timezone.utc) not utcnow
        assert "datetime.now(timezone.utc)" in source
        assert "utcnow" not in source

    def test_invitation_link_uses_tz_aware(self):
        """Invitation resend also uses tz-aware datetime."""
        source = (Path(__file__).resolve().parents[1] / "web" / "routes" / "team.py").read_text(encoding="utf-8")
        lines = [l for l in source.splitlines() if "new_expires" in l and "datetime" in l]
        for line in lines:
            assert "timezone.utc" in line


# ═══════════════════════════════════════════════════════════════════════════════
# M-11 — Rename _aplicar_redondeo_clinico_desayuno → _aplicar_redondeo_clinico
# ═══════════════════════════════════════════════════════════════════════════════

class TestM11RenameRedondeo:

    def test_old_name_gone(self):
        source = (
            Path(__file__).resolve().parents[1] / "core" / "generador_planes.py"
        ).read_text(encoding="utf-8")
        assert "_aplicar_redondeo_clinico_desayuno" not in source

    def test_rounding_uses_request_catalog_and_recomputes_energy(self):
        from core.food_catalog import FoodCatalog
        from core.generador_planes import _aplicar_redondeo_clinico

        catalog = FoodCatalog.from_data(
            {"p": {"kcal": 100}, "c": {"kcal": 200},
             "g": {"kcal": 300}, "v": {"kcal": 50}},
            {"proteina": ["p"], "carbs": ["c"], "grasa": ["g"], "verdura": ["v"]})
        meal = {"alimentos": {"p": 27, "c": 34, "g": 7, "v": 26}, "kcal_objetivo": 100}
        result = _aplicar_redondeo_clinico(meal, catalogo=catalog)
        assert result["alimentos"] == {"p": 25, "c": 30, "g": 5, "v": 30}
        assert result["kcal_real"] == pytest.approx(115)
        assert result["desviacion_pct"] == pytest.approx(15)


# ═══════════════════════════════════════════════════════════════════════════════
# M-12 — TRIAL_DAYS / TRIAL_MAX_CLIENTES from env vars
# ═══════════════════════════════════════════════════════════════════════════════

class TestM12TrialEnvVars:

    def test_trial_days_default(self):
        from config.constantes import TRIAL_DAYS
        assert TRIAL_DAYS == 14

    def test_trial_max_clientes_default(self):
        from config.constantes import TRIAL_MAX_CLIENTES
        assert TRIAL_MAX_CLIENTES == 50

    def test_trial_days_from_env(self, monkeypatch):
        monkeypatch.setenv("TRIAL_DAYS", "30")
        import config.constantes as cc
        importlib.reload(cc)
        try:
            assert cc.TRIAL_DAYS == 30
        finally:
            monkeypatch.delenv("TRIAL_DAYS", raising=False)
            importlib.reload(cc)

    def test_trial_max_clientes_from_env(self, monkeypatch):
        monkeypatch.setenv("TRIAL_MAX_CLIENTES", "100")
        import config.constantes as cc
        importlib.reload(cc)
        try:
            assert cc.TRIAL_MAX_CLIENTES == 100
        finally:
            monkeypatch.delenv("TRIAL_MAX_CLIENTES", raising=False)
            importlib.reload(cc)


# ═══════════════════════════════════════════════════════════════════════════════
# M-13 — Email invitations
# ═══════════════════════════════════════════════════════════════════════════════

class TestM13EmailInvitations:

    def test_send_team_invitation_exists(self):
        from web.services.email_service import send_team_invitation
        assert callable(send_team_invitation)

    def test_send_team_invitation_returns_bool(self):
        """Without RESEND_API_KEY, function returns False gracefully."""
        from web.services.email_service import send_team_invitation
        result = send_team_invitation(
            email="test@example.com",
            nombre="Test User",
            gym_name="Test Gym",
            role="viewer",
            invite_url="http://localhost:8000/auth/accept-invite?token=abc",
        )
        assert result is False  # No API key configured

    def test_settings_has_base_url(self):
        from config.settings import get_settings
        s = get_settings()
        assert hasattr(s, "BASE_URL")
        assert s.BASE_URL  # non-empty


# ═══════════════════════════════════════════════════════════════════════════════
# M-14 — utils/updater.py deleted
# ═══════════════════════════════════════════════════════════════════════════════

class TestM14UpdaterDeleted:

    def test_file_does_not_exist(self):
        assert not (Path(__file__).resolve().parents[1] / "utils" / "updater.py").exists()

    def test_no_imports_of_updater(self):
        """No production file should import from utils.updater."""
        root = Path(__file__).resolve().parents[1]
        for py in root.rglob("*.py"):
            if "__pycache__" in str(py) or "test_" in py.name:
                continue
            text = py.read_text(encoding="utf-8")
            assert "from utils.updater" not in text, f"{py.relative_to(root)} imports updater"
            assert "import updater" not in text or "utils" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# M-15 — Horarios de comida configurable per gym
# ═══════════════════════════════════════════════════════════════════════════════

class TestM15HorariosComidas:

    def test_gym_profile_has_horarios_column(self):
        from web.database.models import GymProfile
        assert "horarios_comidas" in GymProfile.__table__.columns

    def test_get_horarios_comidas_default(self):
        from config.constantes import get_horarios_comidas, HORARIOS_COMIDAS
        result = get_horarios_comidas()
        assert result == HORARIOS_COMIDAS

    def test_get_horarios_comidas_with_profile(self):
        from config.constantes import get_horarios_comidas
        custom = {"desayuno": {"hora_ideal": "08:00"}}
        profile = SimpleNamespace(horarios_comidas=custom)
        result = get_horarios_comidas(profile)
        assert result == custom

    def test_get_horarios_comidas_profile_none_horarios(self):
        from config.constantes import get_horarios_comidas, HORARIOS_COMIDAS
        profile = SimpleNamespace(horarios_comidas=None)
        result = get_horarios_comidas(profile)
        assert result == HORARIOS_COMIDAS

    def test_alembic_migration_exists(self):
        versions = Path(__file__).resolve().parents[1] / "web" / "database" / "alembic" / "versions"
        migration_files = list(versions.glob("*horarios_comidas*"))
        assert migration_files, "Alembic migration for horarios_comidas should exist"
