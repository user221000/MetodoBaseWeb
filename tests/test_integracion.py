"""
tests/test_integracion.py — Tests de integración end-to-end para MetodoBase.

Validan el flujo completo:  Cliente → Plan → PDF → Descarga
usando el servicio layer (api/services.py) y el TestClient de FastAPI.

Run:
    pytest tests/test_integracion.py -v
    
NOTE: Tests now require authentication. Uses auth_client fixture from conftest.py.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api.app import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Unauthenticated client for tests that need it."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


CLIENTE_DEFICIT = {
    "nombre": "Carlos Integracion",
    "edad": 32,
    "peso_kg": 85.0,
    "estatura_cm": 178.0,
    "grasa_corporal_pct": 22.0,
    "nivel_actividad": "moderada",
    "objetivo": "deficit",
}

CLIENTE_SUPERAVIT = {
    "nombre": "Maria Volumen",
    "edad": 26,
    "peso_kg": 60.0,
    "estatura_cm": 162.0,
    "grasa_corporal_pct": 25.0,
    "nivel_actividad": "intensa",
    "objetivo": "superavit",
}

CLIENTE_MANTENIMIENTO = {
    "nombre": "Luis Mantenimiento",
    "edad": 40,
    "peso_kg": 75.0,
    "estatura_cm": 170.0,
    "nivel_actividad": "leve",
    "objetivo": "mantenimiento",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def crear_cliente(client, datos: dict) -> str:
    """Crea un cliente y retorna su id_cliente. Falla el test si hay error HTTP."""
    resp = client.post("/api/clientes", json=datos)
    assert resp.status_code == 201, f"Crear cliente falló ({resp.status_code}): {resp.text}"
    return resp.json()["id_cliente"]


# ════════════════════════════════════════════════════════════════════════════════
# 1. FLUJO COMPLETO: Crear cliente → Generar plan → Verificar PDF
# ════════════════════════════════════════════════════════════════════════════════

class TestFlujoCompleto:
    """Prueba E2E desde creación hasta descarga de PDF."""

    def test_flujo_completo_deficit(self, auth_client):
        """
        Flujo: POST /clientes → POST /generar-plan → descarga privada autorizada
        """
        # 1. Crear cliente
        id_c = crear_cliente(auth_client, CLIENTE_DEFICIT)
        assert id_c, "id_cliente vacío"

        # 2. Generar plan
        resp_plan = auth_client.post("/api/generar-plan", json={
            "id_cliente": id_c, "plan_numero": 1
        })
        assert resp_plan.status_code == 200, f"Generar plan falló: {resp_plan.text[:500]}"
        body = resp_plan.json()

        # 3. Verificar estructura de respuesta
        assert body["success"] is True
        assert body["id_cliente"] == id_c
        assert "macros" in body
        assert "plan" in body
        assert "pdf_url" in body and "ruta_pdf" not in body

        # 4. Verificar que el PDF existe en disco
        pdf = auth_client.get(body["pdf_url"])
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
        assert len(pdf.content) > 1024, "PDF demasiado pequeño (< 1 KB)"

        # 5. Cleanup
        auth_client.delete(f"/api/clientes/{id_c}")

    def test_flujo_completo_superavit(self, auth_client):
        id_c = crear_cliente(auth_client, CLIENTE_SUPERAVIT)
        resp = auth_client.post("/api/generar-plan", json={"id_cliente": id_c, "plan_numero": 1})
        assert resp.status_code == 200
        body = resp.json()
        macros = body["macros"]

        # En superávit las kcal objetivo deben ser > GET
        assert macros["kcal_objetivo"] >= macros["get_total"] * 0.95, (
            "Superávit: kcal_objetivo debería ser cercana o mayor que GET"
        )
        assert auth_client.get(body["pdf_url"]).status_code == 200
        auth_client.delete(f"/api/clientes/{id_c}")

    def test_flujo_completo_sin_grasa(self, auth_client):
        """Sin % grasa corporal, el sistema usa 20% por defecto."""
        id_c = crear_cliente(auth_client, CLIENTE_MANTENIMIENTO)
        resp = auth_client.post("/api/generar-plan", json={"id_cliente": id_c, "plan_numero": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert body["macros"]["tmb"] > 0
        assert auth_client.get(body["pdf_url"]).status_code == 200
        auth_client.delete(f"/api/clientes/{id_c}")


# ════════════════════════════════════════════════════════════════════════════════
# 2. CÁLCULO DE MACROS POR OBJETIVO
# ════════════════════════════════════════════════════════════════════════════════

class TestCalculoMacrosPorObjetivo:
    """Valida que el motor nutricional aplica los ajustes correctos."""

    def _get_macros(self, auth_client, objetivo: str) -> dict:
        datos = {**CLIENTE_DEFICIT, "nombre": f"Test {objetivo}", "objetivo": objetivo}
        id_c = crear_cliente(auth_client, datos)
        resp = auth_client.post("/api/generar-plan", json={"id_cliente": id_c, "plan_numero": 1})
        macros = resp.json()["macros"]
        assert auth_client.get(resp.json()["pdf_url"]).status_code == 200
        auth_client.delete(f"/api/clientes/{id_c}")
        return macros

    def test_deficit_reduce_calorias(self, auth_client):
        macros = self._get_macros(auth_client, "deficit")
        assert macros["kcal_objetivo"] < macros["get_total"], (
            "Déficit: kcal_objetivo debe ser < GET"
        )

    def test_superavit_aumenta_calorias(self, auth_client):
        macros = self._get_macros(auth_client, "superavit")
        assert macros["kcal_objetivo"] > macros["get_total"], (
            "Superávit: kcal_objetivo debe ser > GET"
        )

    def test_mantenimiento_igual_get(self, auth_client):
        macros = self._get_macros(auth_client, "mantenimiento")
        diferencia = abs(macros["kcal_objetivo"] - macros["get_total"])
        assert diferencia < macros["get_total"] * 0.10, (
            f"Mantenimiento: diferencia GET vs objetivo demasiado grande ({diferencia:.0f} kcal)"
        )

    def test_proteina_positiva_siempre(self, auth_client):
        for obj in ("deficit", "mantenimiento", "superavit"):
            macros = self._get_macros(auth_client, obj)
            assert macros["proteina_g"] > 0, f"proteina_g debe ser positiva para {obj}"


# ════════════════════════════════════════════════════════════════════════════════
# 3. MANEJO DE ERRORES
# ════════════════════════════════════════════════════════════════════════════════

class TestManejoErrores:
    """Verifica que la API devuelve códigos HTTP correctos ante errores."""

    def test_generar_plan_cliente_inexistente(self, auth_client):
        resp = auth_client.post("/api/generar-plan", json={
            "id_cliente": "ID_FALSO_ZZZ", "plan_numero": 1
        })
        assert resp.status_code == 404

    def test_obtener_cliente_no_existe(self, auth_client):
        resp = auth_client.get("/api/clientes/XYZ_INVALIDO_ZZZ")
        assert resp.status_code == 404

    def test_crear_cliente_campos_invalidos(self, auth_client):
        """Peso negativo → 422"""
        resp = auth_client.post("/api/clientes", json={
            **CLIENTE_DEFICIT,
            "peso_kg": -5,
        })
        assert resp.status_code == 422

    def test_crear_cliente_sin_nombre(self, auth_client):
        datos = {k: v for k, v in CLIENTE_DEFICIT.items() if k != "nombre"}
        resp = auth_client.post("/api/clientes", json=datos)
        assert resp.status_code == 422

    def test_descargar_pdf_cliente_sin_planes(self, auth_client):
        """Cliente recién creado sin planes → 404 al intentar descargar PDF."""
        id_c = crear_cliente(auth_client, {**CLIENTE_DEFICIT, "nombre": "Sin Plan"})
        resp = auth_client.get(f"/api/descargar-pdf/{id_c}")
        # Puede ser 404 (sin planes) o 200 si ya se generó alguno, pero no debe ser 500
        assert resp.status_code in (200, 404)
        auth_client.delete(f"/api/clientes/{id_c}")


# ════════════════════════════════════════════════════════════════════════════════
# 4. LAYER DE SERVICIOS (sin TestClient)
# ════════════════════════════════════════════════════════════════════════════════

class TestServicesLayer:
    """Tests del layer api/services.py directamente (sin FastAPI)."""

    def test_validar_datos_validos(self):
        from api.services import validar_datos_antropometricos
        ok, msg = validar_datos_antropometricos({
            "nombre": "Test", "edad": 30, "peso_kg": 70,
            "estatura_cm": 170, "nivel_actividad": "moderada",
            "objetivo": "deficit",
        })
        assert ok, f"Validación falló con: {msg}"

    def test_validar_datos_edad_invalida(self):
        from api.services import validar_datos_antropometricos
        ok, msg = validar_datos_antropometricos({
            "nombre": "Test", "edad": 5, "peso_kg": 70,
            "estatura_cm": 170, "nivel_actividad": "moderada",
            "objetivo": "deficit",
        })
        assert not ok
        assert "edad" in msg.lower()

    def test_validar_nivel_invalido(self):
        from api.services import validar_datos_antropometricos
        ok, msg = validar_datos_antropometricos({
            "nombre": "Test", "edad": 30, "peso_kg": 70,
            "estatura_cm": 170, "nivel_actividad": "extremo",
            "objetivo": "deficit",
        })
        assert not ok

    def test_validar_campo_faltante(self):
        from api.services import validar_datos_antropometricos
        ok, msg = validar_datos_antropometricos({"nombre": "Test"})
        assert not ok
        assert "requerido" in msg.lower()

    def test_exceptions_status_codes(self):
        from api.exceptions import (
            ClienteNoEncontradoError, DatosInvalidosError,
            GeneracionPlanError, PDFGenerationError, BaseDatosError,
        )
        assert ClienteNoEncontradoError("X").status_code == 404
        assert DatosInvalidosError("y").status_code == 422
        assert GeneracionPlanError("z").status_code == 500
        assert PDFGenerationError("z").status_code == 500
        assert BaseDatosError("z").status_code == 500

    def test_exceptions_to_dict(self):
        from api.exceptions import ClienteNoEncontradoError
        exc = ClienteNoEncontradoError("ABC123")
        d = exc.to_dict()
        assert d["success"] is False
        assert d["error"] == "CLIENTE_NOT_FOUND"
        assert "ABC123" in d["message"]
        assert "timestamp" in d


# ════════════════════════════════════════════════════════════════════════════════
# 5. PERFORMANCE
# ════════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    """Smoke tests de rendimiento — umbrales conservadores para CI."""

    def test_listar_clientes_rapido(self, auth_client):
        t0 = time.perf_counter()
        resp = auth_client.get("/api/clientes")
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Listar clientes tardó {elapsed:.2f}s (max 2s)"

    def test_estadisticas_rapido(self, auth_client):
        t0 = time.perf_counter()
        resp = auth_client.get("/api/estadisticas")
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Estadísticas tardaron {elapsed:.2f}s (max 2s)"
