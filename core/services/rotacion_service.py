"""
core/services/rotacion_service.py
==================================
Servicio puro de rotación de alimentos con ventana deslizante.

Sin dependencias de GUI/frontend. Expone la funcionalidad de
``src/gestor_rotacion.py`` a través de una API limpia.

Clases principales
------------------
- :class:`RotacionService` — Wrapper de alto nivel sobre
  :class:`~src.gestor_rotacion.RotacionInteligenteAlimentos`.
- :func:`obtener_penalizaciones` — Función de conveniencia sin estado.
"""
from __future__ import annotations

from src.gestor_rotacion import (
    RotacionInteligenteAlimentos,
    GestorRotacionAlimentos,
)

__all__ = [
    "RotacionInteligenteAlimentos",
    "GestorRotacionAlimentos",
    "RotacionService",
    "obtener_penalizaciones",
]


class RotacionService:
    """Servicio de rotación inteligente de alimentos para un cliente.

    Encapsula :class:`~src.gestor_rotacion.RotacionInteligenteAlimentos`
    con una API más explícita orientada a la capa de servicios.

    Attributes:
        id_cliente: Identificador único del cliente.
        ventana_planes: Número de planes recientes a considerar para penalizar.
        _rotacion: Instancia subyacente de RotacionInteligenteAlimentos.
    """

    def __init__(self, id_cliente: str, ventana_planes: int = 3):
        """Inicializa el servicio de rotación.

        Args:
            id_cliente: ID único del cliente (se usa para persistencia en disco).
            ventana_planes: Tamaño de la ventana deslizante (default: 3 planes).
        """
        self.id_cliente = id_cliente
        self.ventana_planes = ventana_planes
        self._rotacion = RotacionInteligenteAlimentos(
            id_cliente=id_cliente,
            ventana_planes=ventana_planes,
        )

    def obtener_pesos_penalizacion(self) -> dict[str, float]:
        """Devuelve el dict ``{alimento: peso_penalizacion}`` para los planes recientes.

        Los pesos reflejan qué tan recientemente se usó cada alimento:
        - Plan n-1 (más reciente): peso 1.0
        - Plan n-2: peso 0.6
        - Plan n-3: peso 0.3

        Returns:
            Diccionario con pesos de penalización. Alimentos no vistos en la
            ventana tienen peso implícito 0.0 (no aparecen en el dict).
        """
        return self._rotacion.obtener_penalizaciones_ponderadas()

    def sugerir_infrautilizados(
        self, categoria: str, top_n: int = 3
    ) -> list[str]:
        """Sugiere los alimentos menos usados recientemente en una categoría.

        Args:
            categoria: ``'proteina'``, ``'carbs'``, ``'grasa'``, ``'verdura'``,
                       ``'fruta'``.
            top_n: Cantidad de sugerencias a devolver.

        Returns:
            Lista de nombres de alimentos ordenados de menor a mayor frecuencia
            de uso reciente (los menos utilizados primero).
        """
        return self._rotacion.sugerir_alimentos_infrautilizados(
            categoria=categoria, top_n=top_n
        )

    def registrar_plan(self, plan: dict) -> None:
        """Registra un plan generado en el historial de rotación.

        Args:
            plan: Diccionario de plan generado por el generador de planes.
                  Se espera el mismo formato que usa ``ConstructorPlanNuevo``.
        """
        self._rotacion.registrar_plan_nuevo(plan)

    def obtener_penalizados_por_categoria(self) -> dict[str, list[str]]:
        """Devuelve el historial de alimentos penalizados agrupados por categoría.

        Returns:
            Dict ``{categoria: [alimentos_penalizados]}`` basado en la ventana.
        """
        pesos = self._rotacion.obtener_penalizaciones_ponderadas()
        from config.catalogo_alimentos import CATALOGO_POR_TIPO
        resultado: dict[str, list[str]] = {}
        for cat, alimentos in CATALOGO_POR_TIPO.items():
            penalizados = [a for a in alimentos if pesos.get(a, 0.0) > 0]
            if penalizados:
                resultado[cat] = penalizados
        return resultado


def obtener_penalizaciones(
    id_cliente: str, ventana_planes: int = 3
) -> dict[str, float]:
    """Función de conveniencia: devuelve pesos de penalización sin instanciar el servicio.

    Args:
        id_cliente: ID único del cliente.
        ventana_planes: Tamaño de la ventana deslizante.

    Returns:
        Dict ``{alimento: peso}`` con penalizaciones actuales.
    """
    svc = RotacionService(id_cliente=id_cliente, ventana_planes=ventana_planes)
    return svc.obtener_pesos_penalizacion()
