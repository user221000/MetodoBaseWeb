"""
core/services/generador_planes_service.py
==========================================
Servicio de orquestación para la generación de planes nutricionales completos.

Sin dependencias de GUI/frontend. Expone el flujo completo desde un objeto
``ClienteEvaluacion`` hasta un plan nutricional diario listo para exportar.

Flujo del plan
--------------
1. Calcular macros del cliente (Katch-McArdle).
2. Distribuir kcal por comida (20/25/30/25 %).
3. Seleccionar alimentos con rotación determinista.
4. Calcular gramos por alimento (Proteína → Carbs → Grasas).
5. Validar límites estrictos y desviación energética.

Clases principales
------------------
- :class:`GeneradorPlanesService` — Orquestador sin estado.
- :func:`generar_plan` — Función de conveniencia de alto nivel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from core.generador_planes import ConstructorPlanNuevo

__all__ = [
    "GeneradorPlanesService",
    "ResultadoPlan",
    "generar_plan",
]


# ---------------------------------------------------------------------------
# DTO resultado
# ---------------------------------------------------------------------------

@dataclass
class ResultadoPlan:
    """Resultado de la generación de un plan nutricional diario.

    Attributes:
        plan: Diccionario con las comidas del día.
              Claves: ``'desayuno'``, ``'almuerzo'``, ``'comida'``, ``'cena'``.
              Cada comida tiene ``'alimentos'``, ``'kcal_objetivo'``,
              ``'kcal_real'``, ``'desviacion_pct'``.
        cliente_id: ID del cliente para el que se generó el plan.
        plan_numero: Número de plan generado (afecta la rotación).
        ajuste_calorico_aplicado: ``True`` si se aplicó ajuste mensual de ±5 %.
        errores: Lista de mensajes de error si algo falló.
    """
    plan: dict[str, Any]
    cliente_id: str
    plan_numero: int = 1
    ajuste_calorico_aplicado: bool = False
    errores: list[str] = field(default_factory=list)

    @property
    def es_valido(self) -> bool:
        """``True`` si el plan fue generado sin errores."""
        return not self.errores

    @property
    def comidas(self) -> list[str]:
        """Lista de claves de comidas presentes en el plan."""
        return list(self.plan.keys())

    def kcal_total_real(self) -> float:
        """Suma de kcal reales de todas las comidas."""
        return sum(
            comida.get("kcal_real", 0.0)
            for comida in self.plan.values()
            if isinstance(comida, dict)
        )


# ---------------------------------------------------------------------------
# Servicio principal
# ---------------------------------------------------------------------------

class GeneradorPlanesService:
    """Servicio sin estado que orquesta la generación de planes nutricionales.

    Encapsula ``ConstructorPlanNuevo`` y añade:
    - Pre-validación de que el cliente tenga macros calculados.
    - Captura de errores con mensajes descriptivos.
    - Devolución de un :class:`ResultadoPlan` tipado en lugar de un dict crudo.
    """

    @staticmethod
    def generar(
        cliente: ClienteEvaluacion,
        plan_numero: int = 1,
        directorio_planes: str = ".",
        max_intentos: int = 3,
    ) -> ResultadoPlan:
        """Genera un plan nutricional diario completo para el cliente.

        Si el cliente no tiene macros calculados (``kcal_objetivo`` es None),
        se calculan automáticamente antes de generar el plan.

        Args:
            cliente: Instancia de :class:`~core.modelos.ClienteEvaluacion`
                     con al menos ``peso_kg``, ``grasa_corporal_pct``,
                     ``nivel_actividad`` y ``objetivo`` establecidos.
            plan_numero: Número de plan (1-7). Afecta la rotación de alimentos.
            directorio_planes: Ruta donde se guardan/leen planes anteriores
                               para el ajuste calórico mensual.
            max_intentos: Reintentos máximos si el plan inicial no pasa validación.

        Returns:
            :class:`ResultadoPlan` con el plan generado y metadatos.

        Raises:
            ValueError: Si el cliente no tiene los campos mínimos requeridos.
        """
        GeneradorPlanesService._validar_cliente(cliente)

        # Calcular macros si no están disponibles
        if cliente.kcal_objetivo is None:
            MotorNutricional.calcular_motor(cliente)

        try:
            plan_dict = ConstructorPlanNuevo.construir(
                cliente=cliente,
                plan_numero=plan_numero,
                directorio_planes=directorio_planes,
                max_intentos=max_intentos,
            )
            # ConstructorPlanNuevo puede retornar None en edge cases extremos
            if plan_dict is None:
                return ResultadoPlan(
                    plan={},
                    cliente_id=cliente.id_cliente,
                    plan_numero=plan_numero,
                    errores=["El generador retornó un plan vacío."],
                )
            return ResultadoPlan(
                plan=plan_dict,
                cliente_id=cliente.id_cliente,
                plan_numero=plan_numero,
            )
        except Exception as exc:  # noqa: BLE001
            return ResultadoPlan(
                plan={},
                cliente_id=cliente.id_cliente,
                plan_numero=plan_numero,
                errores=[str(exc)],
            )

    @staticmethod
    def _validar_cliente(cliente: ClienteEvaluacion) -> None:
        """Verifica que el cliente tenga los campos mínimos necesarios.

        Args:
            cliente: Objeto cliente a validar.

        Raises:
            ValueError: Si falta algún campo requerido o está fuera de rango.
        """
        campos_requeridos = [
            "peso_kg", "grasa_corporal_pct", "nivel_actividad", "objetivo"
        ]
        for campo in campos_requeridos:
            valor = getattr(cliente, campo, None)
            if valor is None:
                raise ValueError(
                    f"El cliente no tiene el campo requerido '{campo}'."
                )

        if not (20 <= cliente.peso_kg <= 300):
            raise ValueError(
                f"peso_kg={cliente.peso_kg} fuera de rango fisiológico [20, 300]."
            )
        if not (2 <= cliente.grasa_corporal_pct <= 60):
            raise ValueError(
                f"grasa_corporal_pct={cliente.grasa_corporal_pct} fuera de rango [2, 60]."
            )


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def generar_plan(
    cliente: ClienteEvaluacion,
    plan_numero: int = 1,
    directorio_planes: str = ".",
) -> ResultadoPlan:
    """Genera un plan nutricional diario. Función de conveniencia de alto nivel.

    Args:
        cliente: Datos del cliente con campos nutricionales básicos.
        plan_numero: Número de plan dentro de la semana (1-7).
        directorio_planes: Directorio donde se guardan planes anteriores.

    Returns:
        :class:`ResultadoPlan` con el plan y metadatos.

    Examples:
        >>> from core.modelos import ClienteEvaluacion
        >>> from core.services.generador_planes_service import generar_plan
        >>> cliente = ClienteEvaluacion(
        ...     nombre="Test", peso_kg=80, grasa_corporal_pct=18,
        ...     nivel_actividad="moderada", objetivo="deficit",
        ...     factor_actividad=1.55
        ... )
        >>> resultado = generar_plan(cliente)
        >>> resultado.es_valido
        True
        >>> "desayuno" in resultado.plan
        True
    """
    return GeneradorPlanesService.generar(
        cliente=cliente,
        plan_numero=plan_numero,
        directorio_planes=directorio_planes,
    )
