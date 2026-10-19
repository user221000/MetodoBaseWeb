"""
tests/test_multi_tenant_isolation.py — Tests de aislamiento multi-tenant.

Verifica que:
1. Cada gym solo puede ver sus propios clientes
2. No hay IDOR (Insecure Direct Object Reference)
3. Tokens inválidos son rechazados
4. Cross-tenant access está bloqueado
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone


@pytest.fixture
def app():
    """Crea instancia de la app para testing."""
    from api.app import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Cliente HTTP de prueba."""
    return TestClient(app)


@pytest.fixture
def mock_jwt_gym_a():
    """Mock de token JWT para gym A."""
    return {
        "id": "gym_a_id_12345",
        "email": "gym_a@test.com",
        "tipo": "gym",
        "nombre": "Gym A",
    }


@pytest.fixture
def mock_jwt_gym_b():
    """Mock de token JWT para gym B."""
    return {
        "id": "gym_b_id_67890",
        "email": "gym_b@test.com",
        "tipo": "gym",
        "nombre": "Gym B",
    }


@pytest.fixture
def mock_jwt_usuario():
    """Mock de token JWT para usuario normal (no gym)."""
    return {
        "id": "user_12345",
        "email": "user@test.com",
        "tipo": "usuario",
        "nombre": "Usuario Normal",
    }


class TestUnauthenticatedAccess:
    """Tests de acceso sin autenticación."""
    
    def test_clientes_sin_token_401(self, client):
        """GET /api/clientes sin token devuelve 401."""
        response = client.get("/api/clientes")
        assert response.status_code == 401
    
    def test_crear_cliente_sin_token_401(self, client):
        """POST /api/clientes sin token devuelve 401."""
        response = client.post("/api/clientes", json={
            "nombre": "Test",
            "telefono": "1234567890",
            "edad": 30,
            "peso_kg": 70,
            "estatura_cm": 170,
        })
        assert response.status_code == 401
    
    def test_estadisticas_sin_token_401(self, client):
        """GET /api/estadisticas sin token devuelve 401."""
        response = client.get("/api/estadisticas")
        assert response.status_code == 401
    
    def test_generar_plan_sin_token_401(self, client):
        """POST /api/generar-plan sin token devuelve 401."""
        response = client.post("/api/generar-plan", json={
            "id_cliente": "test123",
            "plan_numero": 1,
        })
        assert response.status_code == 401
    
    def test_pagos_stripe_sin_token_401(self, client):
        """POST /api/pagos/stripe/session sin token devuelve 401."""
        response = client.post("/api/pagos/stripe/session", json={
            "plan": "standard",
            "email": "test@test.com",
        })
        assert response.status_code == 401
    
    def test_pagos_mp_sin_token_401(self, client):
        """POST /api/pagos/mp/preference sin token devuelve 401."""
        response = client.post("/api/pagos/mp/preference", json={
            "plan": "standard",
            "email": "test@test.com",
        })
        assert response.status_code == 401


@pytest.fixture
def tenant_pair(auth_client, test_gym_user):
    """Persist both gyms and clients; HTTP/repository authorization is real.

    SQLite exercises application filtering here. PostgreSQL RLS has its own
    mandatory acceptance module and is never inferred from these results.
    """
    import uuid
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole, Cliente
    gym_a = test_gym_user["id"]
    gym_b = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Usuario(id=gym_b, email=f"{gym_b}@example.test", password_hash="unused-synthetic",
                       nombre="Gym B", tipo="gym", role=UserRole.OWNER, activo=True))
        db.commit()
        db.add_all([Cliente(id_cliente="client-a", gym_id=gym_a, nombre="Client A"),
                    Cliente(id_cliente="client-b", gym_id=gym_b, nombre="Client B")])
        db.commit()
    return auth_client, gym_a, gym_b


class TestCrossTenantIsolation:
    """Two persisted tenants, no mocked identity or empty repository response."""

    def test_gym_a_no_ve_clientes_gym_b(self, tenant_pair):
        client, _, _ = tenant_pair
        response = client.get("/api/clientes")
        assert response.status_code == 200
        assert [row["id_cliente"] for row in response.json()["clientes"]] == ["client-a"]
        assert response.json()["total"] == 1

    def test_idor_cliente_otro_gym_devuelve_404(self, tenant_pair):
        client, _, _ = tenant_pair
        assert client.get("/api/clientes/client-b").status_code == 404
        assert client.get("/api/clientes/client-a").status_code == 200

    def test_actualizar_cliente_otro_gym_devuelve_404(self, tenant_pair):
        from sqlalchemy.orm import Session
        from web.database.engine import get_engine
        from web.database.models import Cliente
        client, _, _ = tenant_pair
        response = client.put("/api/clientes/client-b", json={"nombre": "Unauthorized"})
        assert response.status_code == 404
        with Session(get_engine()) as db:
            assert db.query(Cliente).filter_by(id_cliente="client-b").one().nombre == "Client B"

    def test_eliminar_cliente_otro_gym_devuelve_404(self, tenant_pair):
        from sqlalchemy.orm import Session
        from web.database.engine import get_engine
        from web.database.models import Cliente
        client, _, _ = tenant_pair
        assert client.delete("/api/clientes/client-b").status_code == 404
        with Session(get_engine()) as db:
            assert db.query(Cliente).filter_by(id_cliente="client-b").one().activo is True


class TestUserTypeRestrictions:
    """Tests de restricción por tipo de usuario."""
    
    def test_usuario_normal_no_accede_endpoints_gym(self, client, mock_jwt_usuario):
        """
        Usuarios tipo "usuario" (no gym) no pueden acceder a endpoints de gym.
        """
        with patch("web.auth.verificar_token") as mock_verify:
            mock_verify.return_value = mock_jwt_usuario
            
            # get_usuario_gym debería rechazar usuarios tipo "usuario"
            response = client.get(
                "/api/clientes",
                headers={"Authorization": "Bearer fake_token"}
            )
            
            # Debería ser 403 (forbidden) porque el usuario existe pero no tiene permisos
            # O 401 si get_usuario_gym no reconoce el tipo
            assert response.status_code in (401, 403)


class TestTokenValidation:
    """Tests de validación de tokens."""
    
    def test_token_malformado_401(self, client):
        """Token malformado devuelve 401."""
        response = client.get(
            "/api/clientes",
            headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        assert response.status_code == 401
    
    def test_token_sin_bearer_401(self, client):
        """Token sin prefijo Bearer devuelve 401."""
        response = client.get(
            "/api/clientes",
            headers={"Authorization": "just_a_token"}
        )
        assert response.status_code == 401
    
    def test_token_vacio_401(self, client):
        """Token vacío devuelve 401."""
        response = client.get(
            "/api/clientes",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401


class TestHealthEndpointsNoAuth:
    """Verificar que endpoints públicos no requieren auth."""
    
    def test_health_no_requiere_auth(self, client):
        """GET /health no requiere autenticación."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_ready_no_requiere_auth(self, client):
        """GET /health/ready no requiere autenticación."""
        response = client.get("/health/ready")
        # Puede ser 200 o 503 dependiendo de si hay BD, pero no 401
        assert response.status_code in (200, 503)
    
    def test_metrics_no_requiere_auth(self, client):
        """GET /metrics requiere X-Metrics-Key (H-09)."""
        # Sin key → 403
        response = client.get("/metrics")
        assert response.status_code == 403


class TestRepositoryGymIdFiltering:
    """Check stored tenant identity rather than mock call presence."""

    def test_listar_clientes_usa_gym_id(self, tenant_pair):
        from sqlalchemy.orm import Session
        from web.database.engine import get_engine
        from web.database import repository as repo
        _, gym_a, gym_b = tenant_pair
        with Session(get_engine()) as db:
            rows_a, total_a = repo.listar_clientes(db, gym_a, "")
            rows_b, total_b = repo.listar_clientes(db, gym_b, "")
            assert [row["id_cliente"] for row in rows_a] == ["client-a"]
            assert [row["id_cliente"] for row in rows_b] == ["client-b"]
            assert total_a == total_b == 1

    def test_crear_cliente_asigna_gym_id(self, tenant_pair):
        from sqlalchemy.orm import Session
        from web.database.engine import get_engine
        from web.database.models import Cliente
        from web.database import repository as repo
        _, gym_a, gym_b = tenant_pair
        with Session(get_engine()) as db:
            created = repo.crear_cliente(db, gym_a, {"nombre": "Synthetic created client"})
            db.commit()
            assert db.query(Cliente).filter_by(id_cliente=created["id_cliente"]).one().gym_id == gym_a
            assert repo.obtener_cliente(db, gym_b, created["id_cliente"]) is None
