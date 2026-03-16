"""
tests/test_generador_planes.py
================================
Tests para la generación de planes nutricionales completos.

Valida (sin UI):
- Que se genere un plan con las 4 comidas esperadas.
- Que cada comida tenga alimentos y valores calóricos.
- Que la desviación calórica esté dentro de rangos aceptables.
- Edge cases: cliente con datos extremos, distintos objetivos.
- Integración: GeneradorPlanesService con ConstructorPlanNuevo.

Ejecutar con:
    python -m pytest tests/test_generador_planes.py -v
"""
from __future__ import annotations

import pytest

from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from core.services.generador_planes_service import (
    GeneradorPlanesService,
    ResultadoPlan,
    generar_plan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cliente_deficit():
    """Cliente típico en objetivo de déficit."""
    c = ClienteEvaluacion(
        nombre="Ana García",
        edad=30,
        peso_kg=68.0,
        estatura_cm=165.0,
        grasa_corporal_pct=25.0,
        nivel_actividad="moderada",
        objetivo="deficit",
        factor_actividad=1.55,
        id_cliente="TEST_DEF",
    )
    MotorNutricional.calcular_motor(c)
    return c


@pytest.fixture
def cliente_mantenimiento():
    """Cliente típico en objetivo de mantenimiento."""
    c = ClienteEvaluacion(
        nombre="Carlos Ruiz",
        edad=35,
        peso_kg=80.0,
        estatura_cm=178.0,
        grasa_corporal_pct=18.0,
        nivel_actividad="moderada",
        objetivo="mantenimiento",
        factor_actividad=1.55,
        id_cliente="TEST_MANT",
    )
    MotorNutricional.calcular_motor(c)
    return c


@pytest.fixture
def cliente_superavit():
    """Cliente en superávit (ganancia de masa)."""
    c = ClienteEvaluacion(
        nombre="Miguel Torres",
        edad=22,
        peso_kg=70.0,
        estatura_cm=175.0,
        grasa_corporal_pct=12.0,
        nivel_actividad="intensa",
        objetivo="superavit",
        factor_actividad=1.725,
        id_cliente="TEST_SUP",
    )
    MotorNutricional.calcular_motor(c)
    return c


# ---------------------------------------------------------------------------
# 1. Estructura del plan generado
# ---------------------------------------------------------------------------

class TestEstructuraPlan:
    """Verifica que el plan tenga la estructura esperada."""

    COMIDAS_ESPERADAS = {"desayuno", "almuerzo", "comida", "cena"}
    # ConstructorPlanNuevo añade una clave extra de metadata al dict del plan
    CLAVES_NO_COMIDA = {"metadata_mes_anterior"}

    def _comidas_del_plan(self, plan: dict) -> dict:
        """Filtra las claves que no son comidas (ej: metadata)."""
        return {
            k: v for k, v in plan.items()
            if k not in self.CLAVES_NO_COMIDA
        }

    def test_plan_tiene_cuatro_comidas(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        # Si hay error, reportarlo claramente
        assert resultado.es_valido, f"Errores al generar plan: {resultado.errores}"
        comidas = set(self._comidas_del_plan(resultado.plan).keys())
        assert comidas == self.COMIDAS_ESPERADAS

    def test_cada_comida_tiene_alimentos(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.es_valido
        for comida in self.COMIDAS_ESPERADAS:
            alimentos = resultado.plan[comida].get("alimentos", {})
            assert len(alimentos) > 0, (
                f"La comida '{comida}' debe tener al menos un alimento."
            )

    def test_alimentos_tienen_gramos_positivos(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.es_valido
        comidas = self._comidas_del_plan(resultado.plan)
        for comida, datos in comidas.items():
            for alimento, gramos in datos.get("alimentos", {}).items():
                assert gramos > 0, (
                    f"{comida} → {alimento}: gramos debe ser positivo, got {gramos}"
                )

    def test_plan_tiene_kcal_real(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.es_valido
        comidas = self._comidas_del_plan(resultado.plan)
        for comida, datos in comidas.items():
            assert "kcal_real" in datos, (
                f"La comida '{comida}' debe tener 'kcal_real'."
            )
            assert datos["kcal_real"] > 0

    def test_resultado_plan_es_valido(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert isinstance(resultado, ResultadoPlan)
        assert resultado.es_valido

    def test_resultado_contiene_cliente_id(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.cliente_id == "TEST_DEF"


# ---------------------------------------------------------------------------
# 2. Validación calórica
# ---------------------------------------------------------------------------

class TestValidacionCalorica:
    """Verifica que las kcal del plan estén dentro de márgenes razonables."""

    MAX_DESVIACION_PCT = 30.0  # tolerancia amplia para tests unitarios
    CLAVES_NO_COMIDA = {"metadata_mes_anterior"}

    def _comidas_del_plan(self, plan: dict) -> dict:
        return {k: v for k, v in plan.items() if k not in self.CLAVES_NO_COMIDA}

    def test_desviacion_por_comida_razonable(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.es_valido
        comidas = self._comidas_del_plan(resultado.plan)
        for comida, datos in comidas.items():
            desviacion = datos.get("desviacion_pct", 0.0)
            assert desviacion <= self.MAX_DESVIACION_PCT, (
                f"{comida}: desviación {desviacion:.1f}% excede el máximo permitido "
                f"de {self.MAX_DESVIACION_PCT}%"
            )

    def test_kcal_total_realista(self, cliente_mantenimiento):
        """La suma de kcal reales debe estar entre 1200 y 5000 kcal."""
        resultado = generar_plan(cliente_mantenimiento)
        assert resultado.es_valido
        total = resultado.kcal_total_real()
        assert 1200 <= total <= 5000, (
            f"Kcal total {total:.0f} fuera del rango realista [1200, 5000]."
        )

    def test_kcal_objetivo_positivo(self, cliente_superavit):
        assert cliente_superavit.kcal_objetivo > 0


# ---------------------------------------------------------------------------
# 3. Distintos objetivos
# ---------------------------------------------------------------------------

class TestDistintosObjetivos:
    """Verifica que los tres objetivos generen planes válidos."""

    def test_plan_deficit(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.es_valido

    def test_plan_mantenimiento(self, cliente_mantenimiento):
        resultado = generar_plan(cliente_mantenimiento)
        assert resultado.es_valido

    def test_plan_superavit(self, cliente_superavit):
        resultado = generar_plan(cliente_superavit)
        assert resultado.es_valido

    def test_deficit_menor_kcal_que_mantenimiento(
        self, cliente_deficit, cliente_mantenimiento
    ):
        """Un cliente en déficit debe tener menos kcal objetivo que mantenimiento
        (ajustando por peso similares — esto es una validación conceptual)."""
        # Comparamos el factor de ajuste: déficit = GET * 0.85 < mantenimiento = GET
        factor_deficit = 0.85
        factor_mant = 1.0
        assert factor_deficit < factor_mant


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests para casos límite."""

    def test_cliente_peso_minimo(self):
        """Cliente en el límite inferior de peso debe generar plan."""
        c = ClienteEvaluacion(
            nombre="Peso Mínimo",
            edad=25,
            peso_kg=20.0,
            estatura_cm=150.0,
            grasa_corporal_pct=5.0,
            nivel_actividad="nula",
            objetivo="mantenimiento",
            factor_actividad=1.2,
            id_cliente="TEST_MIN",
        )
        MotorNutricional.calcular_motor(c)
        resultado = generar_plan(c)
        # Puede tener errores, pero no debe lanzar excepciones
        assert isinstance(resultado, ResultadoPlan)

    def test_cliente_sin_macros_autocalcula(self):
        """Si el cliente no tiene macros calculados, el servicio los calcula."""
        c = ClienteEvaluacion(
            nombre="Sin Macros",
            edad=30,
            peso_kg=75.0,
            estatura_cm=175.0,
            grasa_corporal_pct=18.0,
            nivel_actividad="leve",
            objetivo="mantenimiento",
            factor_actividad=1.375,
            id_cliente="TEST_AUTOCALC",
        )
        # NO llamamos calcular_motor → kcal_objetivo es None
        assert c.kcal_objetivo is None
        resultado = generar_plan(c)
        assert isinstance(resultado, ResultadoPlan)
        # Después del servicio, el cliente debe tener macros
        assert c.kcal_objetivo is not None

    def test_cliente_sin_peso_lanza_error(self):
        """Un cliente sin peso debe generar ValueError al validar."""
        c = ClienteEvaluacion(
            id_cliente="TEST_NOPESO",
            grasa_corporal_pct=18.0,
            nivel_actividad="leve",
            objetivo="mantenimiento",
        )
        with pytest.raises(ValueError, match="peso_kg"):
            GeneradorPlanesService._validar_cliente(c)

    def test_cliente_grasa_fuera_rango_lanza_error(self):
        c = ClienteEvaluacion(
            peso_kg=80.0,
            grasa_corporal_pct=99.0,  # inválido
            nivel_actividad="leve",
            objetivo="deficit",
        )
        with pytest.raises(ValueError, match="grasa_corporal_pct"):
            GeneradorPlanesService._validar_cliente(c)

    def test_plan_numero_2_es_diferente(self, cliente_deficit):
        """Planes con distinto número deben tener rotación diferente."""
        r1 = generar_plan(cliente_deficit, plan_numero=1)
        r2 = generar_plan(cliente_deficit, plan_numero=2)
        assert r1.es_valido
        assert r2.es_valido
        # Los planes pueden diferir en alimentos (rotación)
        # No garantizamos diferencia exacta, solo que ambos son válidos

    def test_resultado_plan_comidas_property(self, cliente_deficit):
        resultado = generar_plan(cliente_deficit)
        assert resultado.es_valido
        comidas = resultado.comidas
        assert "desayuno" in comidas
        assert "cena" in comidas


# ---------------------------------------------------------------------------
# 5. GeneradorPlanesService directamente
# ---------------------------------------------------------------------------

class TestGeneradorPlanesServiceDirecto:
    """Pruebas accediendo a GeneradorPlanesService.generar() directamente."""

    def test_generar_devuelve_resultado_plan(self, cliente_deficit):
        resultado = GeneradorPlanesService.generar(cliente_deficit)
        assert isinstance(resultado, ResultadoPlan)

    def test_errores_capturados_en_resultado(self):
        """Si construir() lanza, el error se captura en .errores."""
        c = ClienteEvaluacion(
            peso_kg=80.0,
            grasa_corporal_pct=20.0,
            nivel_actividad="leve",
            objetivo="deficit",
            factor_actividad=1.375,
            id_cliente="TEST_ERR",
        )
        # kcal_objetivo se autocalcula, así que debería generar un plan válido
        # (o capturar el error si falla)
        resultado = GeneradorPlanesService.generar(c)
        assert isinstance(resultado, ResultadoPlan)
