"""
core/services/selector_alimentos_service.py
============================================
Servicio puro de selección y rotación de alimentos.

Sin dependencias de GUI/frontend. Expone la funcionalidad de
``core/selector_alimentos.py`` a través de una API de alto nivel
con integración del mapa de alias para garantizar nombres canónicos.

Funciones principales
---------------------
- :class:`SelectorAlimentosService` — Selecciona alimentos por tipo y comida.
- :func:`generar_seed` / :func:`generar_seed_bloques` — re-exportados.
- :func:`obtener_alimentos_por_comida` — Devuelve listas listas para usar.
"""
from __future__ import annotations

from core.selector_alimentos import (
    SelectorAlimentos,
    generar_seed,
    generar_seed_bloques,
    obtener_lista_rotada,
    aplicar_penalizacion_semana,
)
from core.services.alimentos_alias import resolver_lista
from core.modelos import ClienteEvaluacion

__all__ = [
    "SelectorAlimentos",
    "SelectorAlimentosService",
    "generar_seed",
    "generar_seed_bloques",
    "obtener_alimentos_por_comida",
]


class SelectorAlimentosService:
    """Servicio de alto nivel para selección de alimentos por comida.

    Integra el mapa de alias para garantizar que los nombres devueltos
    sean siempre canónicos (presentes en ``ALIMENTOS_BASE``).

    Attributes:
        cliente: El cliente para el que se seleccionan alimentos.
        seed: Semilla determinista para reproducibilidad entre semanas.
        plan_numero: Número de plan dentro de la semana (1-7).
    """

    NOMBRES_COMIDA = {0: "desayuno", 1: "almuerzo", 2: "comida", 3: "cena"}

    def __init__(
        self,
        cliente: ClienteEvaluacion,
        seed: int | None = None,
        plan_numero: int = 1,
        gym_id: str = "default",
    ):
        """Inicializa el selector para un cliente específico.

        Args:
            cliente: Instancia de :class:`~core.modelos.ClienteEvaluacion`.
            seed: Semilla entero para rotación determinista. Si es ``None``,
                  se genera automáticamente desde los datos del cliente.
            plan_numero: Número de plan (afecta la rotación).
            gym_id: Identificador del gimnasio (afecta la semilla).
        """
        self.cliente = cliente
        self.gym_id = gym_id
        self.plan_numero = plan_numero
        self.seed = seed if seed is not None else generar_seed(
            cliente, semana=1, gym_id=gym_id
        )

    def obtener_proteinas(
        self,
        meal_idx: int,
        alimentos_usados: set[str] | None = None,
        alimentos_penalizados: dict | None = None,
        pesos_ponderados: dict[str, float] | None = None,
    ) -> list[str]:
        """Devuelve la lista de proteínas para la comida indicada.

        Args:
            meal_idx: Índice de comida (0=desayuno, 1=almuerzo, 2=comida, 3=cena).
            alimentos_usados: Alimentos ya usados en el plan actual.
            alimentos_penalizados: Dict ``{cat: [alimentos]}`` penalizados.
            pesos_ponderados: Dict ``{alimento: peso}`` para ordenamiento.

        Returns:
            Lista de nombres canónicos de proteínas ordenados por prioridad.
        """
        lista = SelectorAlimentos.seleccionar_lista(
            tipo="proteina",
            meal_idx=meal_idx,
            alimentos_usados=alimentos_usados or set(),
            seed=self.seed,
            plan_numero=self.plan_numero,
            alimentos_penalizados=alimentos_penalizados,
            pesos_ponderados=pesos_ponderados,
        )
        return resolver_lista(lista)

    def obtener_carbs(
        self,
        meal_idx: int,
        alimentos_usados: set[str] | None = None,
        alimentos_penalizados: dict | None = None,
        pesos_ponderados: dict[str, float] | None = None,
    ) -> list[str]:
        """Devuelve la lista de carbohidratos para la comida indicada.

        Args:
            meal_idx: Índice de comida (0=desayuno, 1=almuerzo, 2=comida, 3=cena).
            alimentos_usados: Alimentos ya usados en el plan actual.
            alimentos_penalizados: Dict ``{cat: [alimentos]}`` penalizados.
            pesos_ponderados: Dict ``{alimento: peso}`` para ordenamiento.

        Returns:
            Lista de nombres canónicos de carbohidratos ordenados por prioridad.
        """
        lista = SelectorAlimentos.seleccionar_lista(
            tipo="carbs",
            meal_idx=meal_idx,
            alimentos_usados=alimentos_usados or set(),
            seed=self.seed,
            plan_numero=self.plan_numero,
            alimentos_penalizados=alimentos_penalizados,
            pesos_ponderados=pesos_ponderados,
        )
        return resolver_lista(lista)

    def obtener_grasas(
        self,
        meal_idx: int,
        alimentos_usados: set[str] | None = None,
        alimentos_penalizados: dict | None = None,
        pesos_ponderados: dict[str, float] | None = None,
    ) -> list[str]:
        """Devuelve la lista de grasas para la comida indicada.

        Args:
            meal_idx: Índice de comida (0=desayuno, 1=almuerzo, 2=comida, 3=cena).
            alimentos_usados: Alimentos ya usados en el plan actual.
            alimentos_penalizados: Dict ``{cat: [alimentos]}`` penalizados.
            pesos_ponderados: Dict ``{alimento: peso}`` para ordenamiento.

        Returns:
            Lista de nombres canónicos de grasas ordenados por prioridad.
        """
        lista = SelectorAlimentos.seleccionar_lista(
            tipo="grasa",
            meal_idx=meal_idx,
            alimentos_usados=alimentos_usados or set(),
            seed=self.seed,
            plan_numero=self.plan_numero,
            alimentos_penalizados=alimentos_penalizados,
            pesos_ponderados=pesos_ponderados,
        )
        return resolver_lista(lista)


def obtener_alimentos_por_comida(
    cliente: ClienteEvaluacion,
    meal_idx: int,
    seed: int | None = None,
    plan_numero: int = 1,
    gym_id: str = "default",
) -> dict[str, list[str]]:
    """Devuelve un dict con las listas de alimentos disponibles para una comida.

    Función de conveniencia que no requiere instanciar el servicio.

    Args:
        cliente: Datos del cliente.
        meal_idx: Índice de comida (0=desayuno, 1=almuerzo, 2=comida, 3=cena).
        seed: Semilla para rotación determinista (generado automáticamente si es None).
        plan_numero: Número de plan dentro de la semana.
        gym_id: Identificador del gimnasio.

    Returns:
        Diccionario con claves ``'proteinas'``, ``'carbs'``, ``'grasas'``, cada
        una con la lista de alimentos canónicos disponibles para esa comida.

    Examples:
        >>> from core.modelos import ClienteEvaluacion
        >>> c = ClienteEvaluacion(id_cliente="TEST01", peso_kg=80,
        ...     grasa_corporal_pct=18, objetivo="deficit",
        ...     nivel_actividad="moderada", factor_actividad=1.55)
        >>> alimentos = obtener_alimentos_por_comida(c, meal_idx=0)
        >>> isinstance(alimentos["proteinas"], list)
        True
    """
    svc = SelectorAlimentosService(
        cliente=cliente, seed=seed, plan_numero=plan_numero, gym_id=gym_id
    )
    return {
        "proteinas": svc.obtener_proteinas(meal_idx),
        "carbs": svc.obtener_carbs(meal_idx),
        "grasas": svc.obtener_grasas(meal_idx),
    }
