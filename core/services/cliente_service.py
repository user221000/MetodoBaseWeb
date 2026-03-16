"""
Servicio de clientes con cifrado.

Encapsula GestorBDClientes para aplicar cifrado y validaciones antes de persistir.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from core.services.crypto_service import CryptoService
from src.gestor_bd import GestorBDClientes


class ClienteService:
    def __init__(self, gestor_bd: GestorBDClientes, crypto: CryptoService) -> None:
        self._bd = gestor_bd
        self._crypto = crypto

    def crear_id_cliente(self) -> str:
        return str(uuid.uuid4())

    def validar_email(self, email: str) -> None:
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Email invalido.")

    def registrar_cliente_cifrado(self, cliente) -> bool:
        """Inserta cliente con cifrado de campos sensibles."""
        if not getattr(cliente, "id_cliente", ""):
            cliente.id_cliente = self.crear_id_cliente()
        if getattr(cliente, "email", None):
            self.validar_email(cliente.email)
        return self._bd.registrar_cliente(cliente, crypto_service=self._crypto, secure_mode=True)

    def buscar_clientes_seguro(self, termino: str) -> list[dict]:
        return self._bd.buscar_clientes(termino, secure_mode=True, crypto_service=self._crypto)

    def obtener_cliente_seguro(self, id_cliente: str) -> Optional[dict]:
        return self._bd.obtener_cliente_por_id(id_cliente, secure_mode=True, crypto_service=self._crypto)
