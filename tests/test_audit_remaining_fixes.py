"""Tests for remaining audit fixes (2026-03-28).

Covers: H-01 through H-07, M-01 through M-04.
"""
import importlib
import inspect
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# H-01 — Redis rate limiter module exists and is wired
# ═══════════════════════════════════════════════════════════════════════════════

class TestH01RedisRateLimiter:

    def test_redis_module_importable(self):
        """web.rate_limiter_redis should be importable."""
        mod = importlib.import_module("web.rate_limiter_redis")
        assert hasattr(mod, "RedisRateLimitMiddleware")

    def test_redis_middleware_has_dispatch(self):
        """RedisRateLimitMiddleware must implement dispatch."""
        from web.rate_limiter_redis import RedisRateLimitMiddleware
        assert hasattr(RedisRateLimitMiddleware, "dispatch")

    def test_redis_imports_shared_rules(self):
        """Redis limiter should reuse RATE_RULES from in-memory module."""
        from web.rate_limiter_redis import RATE_RULES
        assert isinstance(RATE_RULES, list) and len(RATE_RULES) > 0

    def test_settings_has_redis_url(self):
        """Settings must expose REDIS_URL field."""
        from config.settings import get_settings
        s = get_settings()
        assert hasattr(s, "REDIS_URL")

    def test_app_selects_redis_when_url_set(self):
        """When REDIS_URL is set, app.py should pick RedisRateLimitMiddleware."""
        source = Path(__file__).resolve().parents[1] / "api" / "app.py"
        text = source.read_text(encoding="utf-8")
        assert "RedisRateLimitMiddleware" in text
        assert "REDIS_URL" in text


# ═══════════════════════════════════════════════════════════════════════════════
# H-02 — CATEGORIAS race condition protection
# ═══════════════════════════════════════════════════════════════════════════════

class TestH02ConcurrentExclusions:

    def test_request_catalog_cannot_mutate_nested_foods_or_categories(self):
        """R06 replaces the historical global lock with immutable snapshots."""
        from core.food_catalog import FoodCatalog
        from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS

        catalog = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["huevo"])
        food = next(iter(catalog.alimentos))
        nutrient = next(iter(catalog.alimentos[food]))
        with pytest.raises(TypeError):
            catalog.alimentos[food][nutrient] = -1
        with pytest.raises(TypeError):
            catalog.categorias["proteina"] = ("huevo",)
        assert isinstance(catalog.categorias["proteina"], tuple)
        assert "huevo" not in catalog.alimentos

    def test_concurrent_selectors_preserve_each_requests_exclusions_and_global_catalog(self):
        """Concurrent requests must never publish another request's foods."""
        import copy
        from core.food_catalog import FoodCatalog
        from core.selector_alimentos import SelectorAlimentos
        from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS

        original = copy.deepcopy((ALIMENTOS_BASE, CATEGORIAS))
        barrier = threading.Barrier(8)

        def select(index):
            excluded = (("huevo", "avena"), ("arroz_blanco", "nueces"))[index % 2]
            catalog = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, excluded)
            barrier.wait(timeout=10)
            for iteration in range(20):
                for meal in range(4):
                    for category in ("proteina", "carbs", "grasa"):
                        selected = SelectorAlimentos.seleccionar_lista(category, meal,
                            seed=iteration + 1, catalogo=catalog)
                        assert selected and set(selected).isdisjoint(excluded)
                        assert set(selected).issubset(catalog.alimentos)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(select, range(8)))
        assert (ALIMENTOS_BASE, CATEGORIAS) == original


# ═══════════════════════════════════════════════════════════════════════════════
# H-03 — PDF path traversal guard
# ═══════════════════════════════════════════════════════════════════════════════

class TestH03PDFPathTraversal:

    def test_generar_factura_resolves_path(self):
        """generar_factura should resolve() the output path."""
        source = Path(__file__).resolve().parents[1] / "api" / "factura_pdf.py"
        text = source.read_text(encoding="utf-8")
        assert ".resolve()" in text

    def test_generar_factura_rejects_dotdot(self):
        """generar_factura should reject paths containing '..'."""
        source = Path(__file__).resolve().parents[1] / "api" / "factura_pdf.py"
        text = source.read_text(encoding="utf-8")
        assert '".."' in text or "path traversal" in text.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# H-04 — MercadoPago webhook signature verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestH04MPWebhookSignature:

    @pytest.mark.parametrize("change", [None, "signature", "processed_id", "expired"])
    def test_mp_webhook_checks_signature(self, monkeypatch, change):
        """Shared adapter authenticates the resource actually processed."""
        import hashlib
        import hmac
        import json
        from types import SimpleNamespace
        from fastapi import HTTPException, Request
        from web.services import mercadopago_service as service

        secret = "synthetic-webhook-secret"
        monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(
            MERCADOPAGO_WEBHOOK_SECRET=secret))
        stamp = "1800000000"
        manifest = f"id:payment-123;request-id:request-123;ts:{stamp};"
        signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        if change == "signature":
            signature = "0" * 64
        request = Request({"type": "http", "method": "POST", "path": "/webhook",
            "query_string": b"data.id=payment-123",
            "headers": [(b"x-request-id", b"request-123"),
                        (b"x-signature", f"ts={stamp},v1={signature}".encode())]})
        body = {"id": "event-123", "type": "payment", "data": {
            "id": "other-payment" if change == "processed_id" else "payment-123"}}
        now = int(stamp) + (301 if change == "expired" else 0)
        if change:
            with pytest.raises(HTTPException) as rejected:
                service.verify_notification(request, json.dumps(body).encode(), now=now)
            assert rejected.value.status_code == 401
        else:
            verified, event_id = service.verify_notification(request, json.dumps(body).encode(), now=now)
            assert verified == body and event_id.startswith("mp:")

    def test_settings_has_mp_webhook_secret(self):
        """Settings must have MERCADOPAGO_WEBHOOK_SECRET."""
        from config.settings import get_settings
        s = get_settings()
        assert hasattr(s, "MERCADOPAGO_WEBHOOK_SECRET")


# ═══════════════════════════════════════════════════════════════════════════════
# H-05 — Feature flags strict mode
# ═══════════════════════════════════════════════════════════════════════════════

class TestH05FeatureFlagsStrict:

    def test_known_flags_frozenset_exists(self):
        """KNOWN_FEATURE_FLAGS should be a frozenset."""
        from config.feature_flags import KNOWN_FEATURE_FLAGS
        assert isinstance(KNOWN_FEATURE_FLAGS, frozenset)
        assert "pdf_multi_options" in KNOWN_FEATURE_FLAGS

    def test_is_feature_enabled_known_flag(self):
        """Known flags should return their value."""
        from config import feature_flags
        feature_flags._feature_flags = None  # reset singleton
        result = feature_flags.is_feature_enabled("pdf_multi_options")
        assert isinstance(result, bool)

    def test_is_feature_enabled_unknown_strict(self, monkeypatch):
        """Unknown flag should raise ValueError in strict mode."""
        from config import feature_flags
        feature_flags._feature_flags = None  # reset singleton
        monkeypatch.setenv("FEATURE_FLAGS_STRICT", "true")
        # Reset settings cache
        from config.settings import get_settings
        get_settings.cache_clear()
        try:
            with pytest.raises(ValueError, match="Unknown feature flag"):
                feature_flags.is_feature_enabled("nonexistent_flag_xyz")
        finally:
            get_settings.cache_clear()
            feature_flags._feature_flags = None


# ═══════════════════════════════════════════════════════════════════════════════
# H-07 — RBAC C1 FIX comments removed
# ═══════════════════════════════════════════════════════════════════════════════

class TestH07RBACCommentsRemoved:

    def test_no_c1_fix_comments_in_routes(self):
        """All 'C1 FIX' TODO comments should be removed from route files."""
        routes_dir = Path(__file__).resolve().parents[1] / "web" / "routes"
        for py in routes_dir.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            assert "C1 FIX" not in text, f"{py.name} still has C1 FIX comment"

    def test_rbac_checks_still_present(self):
        """verify_permission calls should still be in place."""
        files = [
            "web/routes/planes.py",
            "web/routes/clientes.py",
            "web/routes/billing.py",
            "web/routes/stats.py",
            "web/routes/gym_profile.py",
        ]
        root = Path(__file__).resolve().parents[1]
        for f in files:
            text = (root / f).read_text(encoding="utf-8")
            assert "verify_permission" in text, f"{f} missing verify_permission"


# ═══════════════════════════════════════════════════════════════════════════════
# M-02 — Dead CSS removed
# ═══════════════════════════════════════════════════════════════════════════════

class TestM02DeadCSSRemoved:

    def test_dead_classes_removed_from_styles(self):
        """Major dead CSS classes should be gone from styles.css."""
        import re
        css = (Path(__file__).resolve().parents[1] / "web" / "static" / "css" / "styles.css").read_text(encoding="utf-8")
        # Check for standalone dead selectors (not compound like .kpi-card.kpi-hero)
        dead_standalone = [
            r"^\.welcome-hero\s*\{", r"^\.top-bar\s*\{",
            r"^\.quick-action-card\s*\{", r"^\.donut-center\s*\{",
            r"^\.glass-card\s*\{",
        ]
        for pattern in dead_standalone:
            assert not re.search(pattern, css, re.MULTILINE), \
                f"Dead standalone selector {pattern} still in styles.css"

    def test_demo_hint_removed_from_auth(self):
        """.demo-hint should be removed from styles-auth.css."""
        css = (Path(__file__).resolve().parents[1] / "web" / "static" / "css" / "styles-auth.css").read_text(encoding="utf-8")
        assert ".demo-hint" not in css


# ═══════════════════════════════════════════════════════════════════════════════
# M-03 — Hardcoded values use constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestM03HardcodedConstants:

    def test_constantes_has_pagination(self):
        """config.constantes must export pagination constants."""
        from config.constantes import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
        assert DEFAULT_PAGE_SIZE > 0
        assert MAX_PAGE_SIZE >= DEFAULT_PAGE_SIZE

    def test_constantes_has_periods(self):
        """config.constantes must export period constants."""
        from config.constantes import PERIODO_SEMANA_DIAS, PERIODO_MES_DIAS, PERIODO_ANIO_DIAS
        assert PERIODO_SEMANA_DIAS == 7
        assert PERIODO_MES_DIAS == 30
        assert PERIODO_ANIO_DIAS == 365

    def test_constantes_has_error_messages(self):
        """config.constantes must export error message constants."""
        from config.constantes import ERR_CLIENTE_NO_ENCONTRADO, ERR_PAGOS_NO_CONFIGURADOS
        assert isinstance(ERR_CLIENTE_NO_ENCONTRADO, str)
        assert isinstance(ERR_PAGOS_NO_CONFIGURADOS, str)

    def test_constantes_has_upload_limits(self):
        """config.constantes must export upload limit constants."""
        from config.constantes import UPLOAD_ALLOWED_IMAGE_EXTENSIONS, UPLOAD_MAX_LOGO_SIZE_BYTES
        assert ".png" in UPLOAD_ALLOWED_IMAGE_EXTENSIONS
        assert UPLOAD_MAX_LOGO_SIZE_BYTES == 2 * 1024 * 1024

    def test_web_clientes_uses_constants(self):
        """web/routes/clientes.py should import from web.constants."""
        source = (Path(__file__).resolve().parents[1] / "web" / "routes" / "clientes.py").read_text(encoding="utf-8")
        assert "ERR_CLIENTE_NO_ENCONTRADO" in source
        assert "DEFAULT_PAGE_SIZE" in source

    def test_web_stats_uses_period_constants(self):
        """web/routes/stats.py should use PERIODO_ constants."""
        source = (Path(__file__).resolve().parents[1] / "web" / "routes" / "stats.py").read_text(encoding="utf-8")
        assert "PERIODO_SEMANA_DIAS" in source
        assert "PERIODO_ANIO_DIAS" in source

    def test_invitation_expiry_uses_constant(self):
        """web/routes/team.py should use INVITATION_EXPIRY_DAYS."""
        source = (Path(__file__).resolve().parents[1] / "web" / "routes" / "team.py").read_text(encoding="utf-8")
        assert "INVITATION_EXPIRY_DAYS" in source


# ═══════════════════════════════════════════════════════════════════════════════
# M-04 — Dual DB consolidation plan exists
# ═══════════════════════════════════════════════════════════════════════════════

class TestM04DualDBPlan:

    def test_consolidation_plan_exists(self):
        """docs/DUAL_DB_CONSOLIDATION_PLAN.md must exist."""
        plan = Path(__file__).resolve().parents[1] / "docs" / "DUAL_DB_CONSOLIDATION_PLAN.md"
        assert plan.exists(), "Migration plan document missing"
        text = plan.read_text(encoding="utf-8")
        assert "Phase 1" in text
        assert "Phase 2" in text
        assert "Phase 3" in text
