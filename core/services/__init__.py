"""
core/services — Capa de servicios puros del Motor Nutricional MetodoBase.

Todos los módulos aquí son completamente independientes de cualquier UI/frontend.
No importan tkinter, PyQt, ni ningún otro framework de interfaz gráfica.

Módulos disponibles:
    - alimentos_alias       : Mapa centralizado de alias/nombres canónicos
    - motor_nutricional_service   : Cálculos Katch-McArdle, macros, GET
    - selector_alimentos_service  : Selección y rotación de alimentos
    - rotacion_service            : Ventana deslizante y penalizaciones
    - generador_planes_service    : Orquestador completo de generación de planes
"""

from core.services.motor_nutricional_service import (
    calcular_plan_nutricional,
    MotorNutricionalService,
)
from core.services.selector_alimentos_service import SelectorAlimentosService
from core.services.rotacion_service import RotacionService
from core.services.generador_planes_service import GeneradorPlanesService
from core.services.crypto_service import CryptoService
from core.services.key_manager import KeyManager
from core.services.password_hasher import PasswordHasher, PasswordPolicy
from core.services.cliente_service import ClienteService

__all__ = [
    "calcular_plan_nutricional",
    "MotorNutricionalService",
    "SelectorAlimentosService",
    "RotacionService",
    "GeneradorPlanesService",
    "CryptoService",
    "KeyManager",
    "PasswordHasher",
    "PasswordPolicy",
    "ClienteService",
]
