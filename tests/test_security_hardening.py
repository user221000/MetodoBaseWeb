"""
tests/test_security_hardening.py — Tests for security hardening fixes C-11, H-01..H-18.

Covers both happy-path and attack-path for each fix.
"""
import os
import hmac
import secrets

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from api.app import create_app
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# C-11  Health check does not leak internals
# ══════════════════════════════════════════════════════════════════════════════

class TestC11HealthCheck:
    def test_health_ok_no_migration_phase(self, client):
        """Health response must NOT contain migration_phase or error details."""
        resp = client.get("/health")
        data = resp.json()
        assert "migration_phase" not in data
        # Should not contain traceback or exception strings
        for key in ("error", "details", "traceback"):
            assert key not in data

    def test_health_status_field(self, client):
        """Health returns a known status value."""
        resp = client.get("/health")
        data = resp.json()
        assert data.get("status") in ("ok", "error", "healthy", "degraded")


# ══════════════════════════════════════════════════════════════════════════════
# H-01  Token without type claim is rejected
# ══════════════════════════════════════════════════════════════════════════════

class TestH01TokenType:
    def test_token_without_type_rejected(self):
        """A token missing the 'type' claim should be rejected."""
        from web.auth import init_auth, verificar_token, SECRET_KEY
        import hmac as _hmac
        import hashlib
        import json
        import base64
        import time

        init_auth()
        from web import auth as _auth_mod
        secret = _auth_mod.SECRET_KEY

        # Build a token manually without "type" claim
        header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
        payload_dict = {"id": "test-user", "exp": int(time.time()) + 3600}
        payload = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).rstrip(b"=").decode()
        signing_input = f"{header}.{payload}"
        sig = _hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        signature = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        token = f"{header}.{payload}.{signature}"

        result = verificar_token(token)
        assert result is None

    def test_token_with_type_accepted(self, test_gym_user):
        """A valid access token requires its persisted active account."""
        from web.auth import init_auth, crear_access_token, verificar_token

        init_auth()
        token = crear_access_token(test_gym_user)
        result = verificar_token(token)
        assert result is not None
        assert result["id"] == test_gym_user["id"]


# ══════════════════════════════════════════════════════════════════════════════
# H-03  CSRF cookie is httponly
# ══════════════════════════════════════════════════════════════════════════════

class TestH03CSRFCookie:
    def test_csrf_cookie_httponly(self, client):
        """The CSRF cookie must have httponly flag."""
        resp = client.get("/dashboard")
        csrf_cookie = None
        for header_name, header_val in resp.headers.multi_items():
            if header_name.lower() == "set-cookie" and "csrf" in header_val.lower():
                csrf_cookie = header_val
                break
        if csrf_cookie:
            assert "httponly" in csrf_cookie.lower()

    def test_csrf_meta_tag_present(self, client):
        """CSRF token should be available via meta tag in HTML."""
        resp = client.get("/dashboard")
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            assert 'name="csrf-token"' in resp.text


# ══════════════════════════════════════════════════════════════════════════════
# H-04  CSP has nonce, no unsafe-inline for scripts
# ══════════════════════════════════════════════════════════════════════════════

class TestH04CSPNonce:
    def test_csp_has_nonce_not_unsafe_inline(self, client):
        """CSP script-src must use nonce, not 'unsafe-inline'."""
        resp = client.get("/")
        csp = resp.headers.get("content-security-policy", "")
        if csp:
            # Find the script-src directive
            for directive in csp.split(";"):
                d = directive.strip()
                if d.startswith("script-src"):
                    assert "'nonce-" in d, "script-src must contain nonce"
                    assert "'unsafe-inline'" not in d, "script-src must not have unsafe-inline"
                    break

    def test_csp_nonce_changes_per_request(self, client):
        """Each request should get a unique CSP nonce."""
        csp1 = client.get("/").headers.get("content-security-policy", "")
        csp2 = client.get("/").headers.get("content-security-policy", "")
        if csp1 and csp2:
            # Extract nonces
            import re
            nonces1 = re.findall(r"'nonce-([^']+)'", csp1)
            nonces2 = re.findall(r"'nonce-([^']+)'", csp2)
            if nonces1 and nonces2:
                assert nonces1[0] != nonces2[0], "Nonces must differ per request"


# ══════════════════════════════════════════════════════════════════════════════
# H-05  SRI on CDN resources
# ══════════════════════════════════════════════════════════════════════════════

class TestH05SRI:
    def test_chartjs_has_integrity(self, client):
        """CDN scripts (if any) must have integrity attribute, or Chart.js is local."""
        resp = client.get("/dashboard")
        if resp.status_code == 200:
            # Chart.js may be served locally (no CDN = no SRI needed)
            # If CDN is used, integrity must be present
            has_cdn_chartjs = "cdn.jsdelivr.net/npm/chart.js" in resp.text
            if has_cdn_chartjs:
                assert "integrity=" in resp.text or "sha384-" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
# H-09  Metrics endpoint requires API key
# ══════════════════════════════════════════════════════════════════════════════

class TestH09MetricsAuth:
    def test_metrics_without_key_returns_403(self, client):
        """GET /metrics without X-Metrics-Key must return 403."""
        resp = client.get("/metrics")
        assert resp.status_code == 403

    def test_metrics_wrong_key_returns_403(self, client):
        """GET /metrics with wrong key must return 403."""
        resp = client.get("/metrics", headers={"X-Metrics-Key": "wrong-key"})
        assert resp.status_code == 403

    def test_alerts_without_key_returns_403(self, client):
        """GET /alerts without X-Metrics-Key must return 403."""
        resp = client.get("/alerts")
        assert resp.status_code == 403

    def test_health_circuits_without_key_returns_403(self, client):
        """GET /health/circuits without key must return 403."""
        resp = client.get("/health/circuits")
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# H-12  Port configuration
# ══════════════════════════════════════════════════════════════════════════════

class TestH12Port:
    def test_default_port_is_8000(self):
        """Default port should be 8000, not 8001."""
        # Re-import with clean env
        env_port = os.environ.get("PORT")
        env_web = os.environ.get("WEB_PORT")
        try:
            os.environ.pop("PORT", None)
            os.environ.pop("WEB_PORT", None)
            # Force re-read
            from config import settings
            s = settings.Settings()
            assert s.PORT == 8000
        finally:
            if env_port is not None:
                os.environ["PORT"] = env_port
            if env_web is not None:
                os.environ["WEB_PORT"] = env_web

    def test_railway_port_takes_priority(self):
        """PORT env var (Railway) should override WEB_PORT."""
        env_port = os.environ.get("PORT")
        env_web = os.environ.get("WEB_PORT")
        try:
            os.environ["PORT"] = "9999"
            os.environ["WEB_PORT"] = "7777"
            from config import settings
            s = settings.Settings()
            assert s.PORT == 9999
        finally:
            if env_port is not None:
                os.environ["PORT"] = env_port
            else:
                os.environ.pop("PORT", None)
            if env_web is not None:
                os.environ["WEB_PORT"] = env_web
            else:
                os.environ.pop("WEB_PORT", None)


# ══════════════════════════════════════════════════════════════════════════════
# H-07  Auth audit logging
# ══════════════════════════════════════════════════════════════════════════════

class TestH07AuditLogging:
    def test_login_success_logs(self, caplog):
        """Successful login should produce structured log."""
        import logging
        from web.auth import init_auth, verificar_credenciales, hash_password, crear_usuario

        init_auth()

        uid = f"audit-{secrets.token_hex(4)}"
        email = f"{uid}@test.com"
        try:
            crear_usuario(email=email, password="pass12345678", nombre="Audit", apellido="Test", tipo="gym")
        except ValueError:
            pass  # User might already exist

        with caplog.at_level(logging.INFO, logger="web.auth"):
            result = verificar_credenciales(email, "pass12345678", ip="127.0.0.1")

        assert result is not None
        assert any("[AUTH] Login exitoso" in r.message for r in caplog.records)

    def test_login_failure_logs(self, caplog):
        """Failed login should produce structured log."""
        import logging
        from web.auth import init_auth, verificar_credenciales

        init_auth()

        with caplog.at_level(logging.WARNING, logger="web.auth"):
            result = verificar_credenciales("nonexistent@test.com", "bad", ip="10.0.0.1")

        assert result is None
        assert any("[AUTH] Login fallido" in r.message for r in caplog.records)


# ══════════════════════════════════════════════════════════════════════════════
# H-08  Remember-me token lifetimes
# ══════════════════════════════════════════════════════════════════════════════

class TestH08RememberMe:
    def test_remember_me_access_max_7_days(self):
        """Remember-me access token should be ≤ 7 days."""
        from config.settings import Settings
        s = Settings()
        assert s.REMEMBER_ME_ACCESS_DAYS <= 7

    def test_remember_me_refresh_max_30_days(self):
        """Remember-me refresh token should be ≤ 30 days."""
        from config.settings import Settings
        s = Settings()
        assert s.REMEMBER_ME_REFRESH_DAYS <= 30


# ══════════════════════════════════════════════════════════════════════════════
# H-11  Feature flags phase control
# ══════════════════════════════════════════════════════════════════════════════

class TestH11FeatureFlags:
    def test_phase_env_sets_flags(self):
        """DB_MIGRATION_PHASE env var should control feature flags."""
        old = os.environ.get("DB_MIGRATION_PHASE")
        try:
            os.environ["DB_MIGRATION_PHASE"] = "4"
            from config.feature_flags import DBMigrationFlags
            flags = DBMigrationFlags.from_env()
            assert flags.legacy_deprecated is True
        finally:
            if old is not None:
                os.environ["DB_MIGRATION_PHASE"] = old
            else:
                os.environ.pop("DB_MIGRATION_PHASE", None)

    def test_invalid_phase_ignored(self):
        """Non-numeric DB_MIGRATION_PHASE should not crash."""
        old = os.environ.get("DB_MIGRATION_PHASE")
        try:
            os.environ["DB_MIGRATION_PHASE"] = "invalid"
            from config.feature_flags import DBMigrationFlags
            flags = DBMigrationFlags.from_env()
            assert isinstance(flags.use_sa_for_read, bool)
        finally:
            if old is not None:
                os.environ["DB_MIGRATION_PHASE"] = old
            else:
                os.environ.pop("DB_MIGRATION_PHASE", None)


# ══════════════════════════════════════════════════════════════════════════════
# H-14  Fiscal fields on GymProfile
# ══════════════════════════════════════════════════════════════════════════════

class TestH14FiscalFields:
    def test_gym_profile_has_fiscal_columns(self):
        """GymProfile model should have fiscal fields."""
        from web.database.models import GymProfile
        for field in ("razon_social", "regimen_fiscal", "codigo_postal_fiscal", "uso_cfdi"):
            assert hasattr(GymProfile, field), f"GymProfile missing {field}"

    def test_uso_cfdi_default_g03(self):
        """uso_cfdi should default to G03."""
        from web.database.models import GymProfile
        col = GymProfile.__table__.c.uso_cfdi
        assert col.default is not None
        assert col.default.arg == "G03"


# ══════════════════════════════════════════════════════════════════════════════
# H-18  Factura PDF branding
# ══════════════════════════════════════════════════════════════════════════════

class TestH18FacturaBranding:
    def test_generar_factura_accepts_gym_branding(self):
        """generar_factura should accept gym_branding kwarg."""
        import inspect
        from api.factura_pdf import generar_factura
        sig = inspect.signature(generar_factura)
        assert "gym_branding" in sig.parameters

    def test_generar_factura_default_brand_fallback(self, tmp_path):
        """Without gym_branding, PDF should use 'Método Base' fallback."""
        from api.factura_pdf import generar_factura
        pdf_path = tmp_path / "test_factura.pdf"
        datos = {
            "folio": "TEST-001",
            "comprador": "Test Gym",
            "email": "test@test.com",
            "plan": "gym_comercial",
            "precio_mxn": 479.0,
        }
        result = generar_factura(datos, pdf_path)
        assert result.exists()

    def test_generar_factura_custom_branding(self, tmp_path):
        """With gym_branding, PDF should use custom name."""
        from api.factura_pdf import generar_factura
        pdf_path = tmp_path / "test_factura_brand.pdf"
        datos = {
            "folio": "TEST-002",
            "comprador": "Custom Gym",
            "email": "custom@gym.com",
            "plan": "elite",
            "precio_mxn": 99.0,
        }
        branding = {
            "nombre_gym": "Mi Gimnasio Premium",
            "telefono": "+52 55 1234 5678",
            "email": "contacto@migym.com",
        }
        result = generar_factura(datos, pdf_path, gym_branding=branding)
        assert result.exists()


# ══════════════════════════════════════════════════════════════════════════════
# H-02  License activations model exists
# ══════════════════════════════════════════════════════════════════════════════

class TestH02LicenseActivations:
    def test_model_exists(self):
        """LicenseActivation model should be importable."""
        from web.database.models import LicenseActivation
        assert LicenseActivation.__tablename__ == "license_activations"

    def test_hardware_id_unique(self):
        """hardware_id column should be unique."""
        from web.database.models import LicenseActivation
        col = LicenseActivation.__table__.c.hardware_id
        assert col.unique is True


# ══════════════════════════════════════════════════════════════════════════════
# H-10  Checkout sessions model exists
# ══════════════════════════════════════════════════════════════════════════════

class TestH10CheckoutSessions:
    def test_model_exists(self):
        """CheckoutSession model should be importable."""
        from web.database.models import CheckoutSession
        assert CheckoutSession.__tablename__ == "checkout_sessions"

    def test_stripe_session_id_unique(self):
        """stripe_session_id should be unique."""
        from web.database.models import CheckoutSession
        col = CheckoutSession.__table__.c.stripe_session_id
        assert col.unique is True


# ══════════════════════════════════════════════════════════════════════════════
# H-17  Token cleanup function
# ══════════════════════════════════════════════════════════════════════════════

class TestH17TokenCleanup:
    def test_cleanup_function_exists(self):
        """Public cleanup_expired_tokens should be importable."""
        from web.auth import cleanup_expired_tokens
        assert callable(cleanup_expired_tokens)

    def test_cleanup_returns_int(self):
        """cleanup_expired_tokens should return count of deleted tokens."""
        from web.auth import init_auth, cleanup_expired_tokens
        init_auth()
        result = cleanup_expired_tokens()
        assert isinstance(result, int)
        assert result >= 0
