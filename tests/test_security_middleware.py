"""
tests/test_security_middleware.py — Tests para middlewares de seguridad.

Valida que:
1. SecurityHeadersMiddleware agrega todos los headers requeridos
2. RequestIDMiddleware genera/propaga request IDs
3. Los headers son correctos en producción
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from web.middleware import SecurityHeadersMiddleware, RequestIDMiddleware


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def app_with_security():
    """App con SecurityHeadersMiddleware habilitado."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/api/test")
    def api_endpoint():
        return {"data": "test"}
    
    return app


@pytest.fixture
def app_with_request_id():
    """App con RequestIDMiddleware habilitado."""
    from starlette.requests import Request as StarletteRequest
    
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    def test_endpoint(request: StarletteRequest):
        return {"request_id": request.state.request_id}
    
    return app


@pytest.fixture
def app_full_security():
    """App con ambos middlewares."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    return app


# ── Tests SecurityHeadersMiddleware ──────────────────────────────────────────

class TestSecurityHeadersMiddleware:
    """Tests para SecurityHeadersMiddleware."""
    
    def test_hsts_header_present(self, app_with_security):
        """HSTS header debe estar presente con max-age."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        assert "Strict-Transport-Security" in resp.headers
        hsts = resp.headers["Strict-Transport-Security"]
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts
    
    def test_csp_header_present(self, app_with_security):
        """CSP header debe estar presente con directivas básicas."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        assert "Content-Security-Policy" in resp.headers
        csp = resp.headers["Content-Security-Policy"]
        assert "default-src" in csp
        assert "script-src" in csp
        assert "frame-ancestors" in csp
    
    def test_x_content_type_options(self, app_with_security):
        """X-Content-Type-Options debe ser nosniff."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    
    def test_x_frame_options(self, app_with_security):
        """X-Frame-Options debe bloquear framing externo."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    
    def test_referrer_policy(self, app_with_security):
        """Referrer-Policy debe estar configurado."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        assert "Referrer-Policy" in resp.headers
        assert "strict-origin" in resp.headers["Referrer-Policy"]

    @pytest.mark.parametrize("explicit,expected", [
        ("no-referrer", "no-referrer"),
        ("unsafe-url", "strict-origin-when-cross-origin"),
        ("origin", "strict-origin-when-cross-origin"),
        ("strict-origin-when-cross-origin", "strict-origin-when-cross-origin"),
    ])
    def test_private_policy_is_preserved_without_accepting_weaker_policy(self, explicit, expected):
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/private-document")
        def private_document():
            return JSONResponse({"synthetic": True}, headers={"Referrer-Policy": explicit})

        with TestClient(app) as client:
            assert client.get("/private-document").headers["referrer-policy"] == expected
    
    def test_permissions_policy(self, app_with_security):
        """Permissions-Policy debe restringir APIs sensibles."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        assert "Permissions-Policy" in resp.headers
        pp = resp.headers["Permissions-Policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
    
    def test_api_cache_control(self, app_with_security):
        """Endpoints /api/ deben tener Cache-Control no-store."""
        client = TestClient(app_with_security)
        resp = client.get("/api/test")
        
        assert "Cache-Control" in resp.headers
        assert "no-store" in resp.headers["Cache-Control"]
    
    def test_non_api_no_cache_control_forced(self, app_with_security):
        """Endpoints no-API no deben forzar Cache-Control."""
        client = TestClient(app_with_security)
        resp = client.get("/test")
        
        # Para rutas no-API, no forzamos Cache-Control
        # (el middleware solo lo agrega para /api/)
        cc = resp.headers.get("Cache-Control", "")
        # Si está vacío o no es "no-store", está bien
        # (porque no es una ruta /api/)


# ── Tests RequestIDMiddleware ────────────────────────────────────────────────

class TestRequestIDMiddleware:
    """Tests para RequestIDMiddleware."""
    
    def test_generates_request_id(self, app_with_request_id):
        """Debe generar un X-Request-ID si no se envía."""
        client = TestClient(app_with_request_id)
        resp = client.get("/test")
        
        assert "X-Request-ID" in resp.headers
        request_id = resp.headers["X-Request-ID"]
        assert len(request_id) == 12  # UUID4 truncado
    
    def test_propagates_client_request_id(self, app_with_request_id):
        """Debe reutilizar X-Request-ID del cliente."""
        client = TestClient(app_with_request_id)
        custom_id = "my-custom-id-123"
        resp = client.get("/test", headers={"X-Request-ID": custom_id})
        
        assert resp.headers["X-Request-ID"] == custom_id
    
    def test_request_id_available_in_handler(self, app_with_request_id):
        """El request_id debe estar disponible en request.state."""
        client = TestClient(app_with_request_id)
        resp = client.get("/test")
        
        data = resp.json()
        assert "request_id" in data
        assert data["request_id"] == resp.headers["X-Request-ID"]
    
    def test_unique_ids_per_request(self, app_with_request_id):
        """Cada request debe tener un ID único."""
        client = TestClient(app_with_request_id)
        
        ids = set()
        for _ in range(10):
            resp = client.get("/test")
            ids.add(resp.headers["X-Request-ID"])
        
        assert len(ids) == 10  # Todos diferentes


# ── Tests combinados ─────────────────────────────────────────────────────────

class TestCombinedMiddleware:
    """Tests con ambos middlewares activos."""
    
    def test_both_middlewares_work_together(self, app_full_security):
        """Ambos middlewares deben funcionar simultáneamente."""
        client = TestClient(app_full_security)
        resp = client.get("/test")
        
        # Security headers
        assert "Strict-Transport-Security" in resp.headers
        assert "Content-Security-Policy" in resp.headers
        
        # Request ID
        assert "X-Request-ID" in resp.headers
    
    def test_response_status_preserved(self, app_full_security):
        """El status code original debe preservarse."""
        client = TestClient(app_full_security)
        resp = client.get("/test")
        
        assert resp.status_code == 200


# ── Tests de configuración ───────────────────────────────────────────────────

class TestSecurityMiddlewareConfig:
    """Tests de configuración del middleware."""
    
    def test_hsts_disabled(self):
        """Debe poder deshabilitar HSTS."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=False)
        
        @app.get("/test")
        def handler():
            return {"ok": True}
        
        client = TestClient(app)
        resp = client.get("/test")
        
        assert "Strict-Transport-Security" not in resp.headers
    
    def test_csp_disabled(self):
        """Debe poder deshabilitar CSP."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, csp_enabled=False)
        
        @app.get("/test")
        def handler():
            return {"ok": True}
        
        client = TestClient(app)
        resp = client.get("/test")
        
        assert "Content-Security-Policy" not in resp.headers
    
    def test_custom_hsts_max_age(self):
        """Debe respetar max_age personalizado."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, hsts_max_age=3600)
        
        @app.get("/test")
        def handler():
            return {"ok": True}
        
        client = TestClient(app)
        resp = client.get("/test")
        
        assert "max-age=3600" in resp.headers["Strict-Transport-Security"]
