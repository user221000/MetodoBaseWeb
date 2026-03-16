"""
core/services/motor_nutricional_service.py
==========================================
Servicio puro de cálculos nutricionales basado en Katch-McArdle.

Sin dependencias de GUI/frontend. Expone una API limpia sobre las clases
``MotorNutricional`` y ``AjusteCaloricoMensual`` que viven en
``core/motor_nutricional``.

Funciones de alto nivel
-----------------------
- :func:`calcular_plan_nutricional` — Orquesta el flujo completo para un cliente.

Clases re-exportadas
--------------------
- :class:`MotorNutricionalService` — Wrapper con validación de inputs.
- ``MotorNutricional`` — Clase original con métodos estáticos de bajo nivel.
- ``AjusteCaloricoMensual`` — Ajuste mensual (5 %) basado en progreso.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.motor_nutricional import (
    MotorNutricional,
    AjusteCaloricoMensual,
    AlertaSalud,
)
from core.modelos import ClienteEvaluacion
from config.constantes import FACTORES_ACTIVIDAD, OBJETIVOS_VALIDOS

# ---------------------------------------------------------------------------
# Re-exportaciones para que los consumidores importen desde aquí
# ---------------------------------------------------------------------------
__all__ = [
    "MotorNutricional",
    "AjusteCaloricoMensual",
    "AlertaSalud",
    "MotorNutricionalService",
    "ResultadoNutricional",
    "calcular_plan_nutricional",
]


# ---------------------------------------------------------------------------
# DTO de resultado
# ---------------------------------------------------------------------------

@dataclass
class ResultadoNutricional:
    """Resultado inmutable del cálculo nutricional completo para un cliente.

    Attributes:
        masa_magra: Masa magra en kg (peso * (1 - %grasa/100)).
        tmb: Tasa Metabólica Basal (Katch-McArdle) en kcal.
        get_total: Gasto Energético Total en kcal (TMB * factor_actividad).
        kcal_objetivo: Calorías objetivo ajustadas al objetivo del cliente.
        proteina_g: Gramos de proteína diarios recomendados.
        grasa_g: Gramos de grasa diarios recomendados.
        carbs_g: Gramos de carbohidratos diarios recomendados.
        alertas: Lista de alertas de salud generadas durante el cálculo.
    """
    masa_magra: float
    tmb: float
    get_total: float
    kcal_objetivo: float
    proteina_g: float
    grasa_g: float
    carbs_g: float
    alertas: list[AlertaSalud] = field(default_factory=list)

    @property
    def tiene_alertas(self) -> bool:
        """``True`` si el resultado generó al menos una alerta de salud."""
        return bool(self.alertas)

    @property
    def alertas_criticas(self) -> list[AlertaSalud]:
        """Filtra sólo alertas de nivel ``'error'``."""
        return [a for a in self.alertas if a.nivel == "error"]


# ---------------------------------------------------------------------------
# Servicio de alto nivel
# ---------------------------------------------------------------------------

class MotorNutricionalService:
    """Wrapper con validación de entrada sobre :class:`MotorNutricional`.

    A diferencia de la clase base, este servicio:
    1. Valida que los parámetros estén dentro de rangos fisiológicos.
    2. Devuelve un :class:`ResultadoNutricional` tipado en lugar de un dict.
    3. No tiene efectos secundarios sobre el objeto ``cliente``.
    """

    # Límites fisiológicos para validación de inputs
    _PESO_MIN = 20.0
    _PESO_MAX = 300.0
    _GRASA_MIN = 2.0
    _GRASA_MAX = 60.0
    _FACTOR_MIN = 1.0
    _FACTOR_MAX = 2.5

    @classmethod
    def calcular(
        cls,
        peso_kg: float,
        grasa_corporal_pct: float,
        nivel_actividad: str,
        objetivo: str,
    ) -> ResultadoNutricional:
        """Ejecuta el flujo completo Katch-McArdle y devuelve un resultado tipado.

        Args:
            peso_kg: Peso total del cliente en kilogramos.
            grasa_corporal_pct: Porcentaje de grasa corporal (ej.: 18.0).
            nivel_actividad: Clave de actividad ('nula', 'leve', 'moderada', 'intensa').
            objetivo: Objetivo ('deficit', 'mantenimiento', 'superavit').

        Returns:
            :class:`ResultadoNutricional` con todos los valores calculados.

        Raises:
            ValueError: Si algún parámetro está fuera de rango o es desconocido.
        """
        cls._validar_inputs(peso_kg, grasa_corporal_pct, nivel_actividad, objetivo)

        factor = FACTORES_ACTIVIDAD[nivel_actividad]
        masa_magra = MotorNutricional.calcular_masa_magra(peso_kg, grasa_corporal_pct)
        tmb = MotorNutricional.calcular_tmb(masa_magra)
        get_total = MotorNutricional.calcular_get(tmb, factor)
        kcal_obj = MotorNutricional.calcular_kcal_objetivo(get_total, objetivo)
        macros = MotorNutricional.calcular_macros(peso_kg, kcal_obj)

        # Alerta por déficit excesivo (> 25 %)
        alertas: list[AlertaSalud] = list(macros.get("alertas", []))
        if get_total > 0:
            deficit_pct = (1 - kcal_obj / get_total) * 100
            if deficit_pct > 25:
                alertas.append(AlertaSalud(
                    nivel="error",
                    codigo="DEFICIT_EXCESIVO",
                    mensaje=(
                        f"Déficit calórico excesivo: {deficit_pct:.1f}% "
                        f"(máximo recomendado: 25%)"
                    ),
                    detalle=(
                        f"GET={get_total:.0f} kcal, Objetivo={kcal_obj:.0f} kcal. "
                        "Un déficit superior al 25% puede provocar pérdida de masa muscular."
                    ),
                ))

        return ResultadoNutricional(
            masa_magra=masa_magra,
            tmb=tmb,
            get_total=get_total,
            kcal_objetivo=kcal_obj,
            proteina_g=macros["proteina_g"],
            grasa_g=macros["grasa_g"],
            carbs_g=macros["carbs_g"],
            alertas=alertas,
        )

    @classmethod
    def _validar_inputs(
        cls,
        peso_kg: float,
        grasa_pct: float,
        nivel_actividad: str,
        objetivo: str,
    ) -> None:
        """Valida rangos fisiológicos de los parámetros de entrada.

        Raises:
            ValueError: Descripción del parámetro inválido.
        """
        if not (cls._PESO_MIN <= peso_kg <= cls._PESO_MAX):
            raise ValueError(
                f"peso_kg={peso_kg} fuera de rango [{cls._PESO_MIN}, {cls._PESO_MAX}]"
            )
        if not (cls._GRASA_MIN <= grasa_pct <= cls._GRASA_MAX):
            raise ValueError(
                f"grasa_corporal_pct={grasa_pct} fuera de rango "
                f"[{cls._GRASA_MIN}, {cls._GRASA_MAX}]"
            )
        if nivel_actividad not in FACTORES_ACTIVIDAD:
            raise ValueError(
                f"nivel_actividad='{nivel_actividad}' no reconocido. "
                f"Valores válidos: {sorted(FACTORES_ACTIVIDAD.keys())}"
            )
        if objetivo.lower().strip() not in OBJETIVOS_VALIDOS:
            raise ValueError(
                f"objetivo='{objetivo}' no reconocido. "
                f"Valores válidos: {sorted(OBJETIVOS_VALIDOS)}"
            )


# ---------------------------------------------------------------------------
# Función de conveniencia de alto nivel
# ---------------------------------------------------------------------------

def calcular_plan_nutricional(cliente: ClienteEvaluacion) -> ClienteEvaluacion:
    """Calcula y persiste todos los valores nutricionales en el objeto cliente.

    Equivalente al método ``MotorNutricional.calcular_motor(cliente)`` pero
    con validación de inputs y sin dependencias de UI.

    Args:
        cliente: Instancia de :class:`~core.modelos.ClienteEvaluacion` con
                 los campos ``peso_kg``, ``grasa_corporal_pct``,
                 ``nivel_actividad``, ``objetivo`` y ``factor_actividad``
                 ya establecidos.

    Returns:
        El mismo objeto ``cliente`` con todos los campos nutricionales
        completados (``masa_magra``, ``tmb``, ``get_total``, ``kcal_objetivo``,
        ``proteina_g``, ``grasa_g``, ``carbs_g``, ``alertas_salud``).
    """
    return MotorNutricional.calcular_motor(cliente)
