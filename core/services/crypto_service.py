"""
CryptoService: cifrado/descifrado de campos sensibles.

Formato de token:
    v1:<key_id>:<fernet_token>
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.services.key_manager import KeyManager, KeyInfo


@dataclass(frozen=True)
class CryptoToken:
    version: str
    key_id: str
    token: str


class CryptoService:
    """Servicio de cifrado de texto con rotacion segura de llaves."""

    _VERSION = "v1"

    def __init__(self, key_manager: KeyManager) -> None:
        self._km = key_manager

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        info = self._km.load_key()
        fernet = Fernet(info.key_b64)
        token = fernet.encrypt(plain_text.encode("utf-8")).decode("ascii")
        return f"{self._VERSION}:{info.key_id}:{token}"

    def decrypt(self, payload: str) -> str:
        if not payload:
            return ""
        token = self._parse(payload)
        keys = [self._km.load_key()] + self._km.get_previous_keys()
        for info in keys:
            if info.key_id != token.key_id:
                continue
            try:
                fernet = Fernet(info.key_b64)
                return fernet.decrypt(token.token.encode("ascii")).decode("utf-8")
            except InvalidToken:
                raise ValueError("Token invalido o clave incorrecta")
        # Intento fallback por si no hay key_id (migracion)
        for info in keys:
            try:
                fernet = Fernet(info.key_b64)
                return fernet.decrypt(token.token.encode("ascii")).decode("utf-8")
            except InvalidToken:
                continue
        raise ValueError("No se pudo descifrar: clave no encontrada")

    @classmethod
    def _parse(cls, payload: str) -> CryptoToken:
        if payload.startswith(f"{cls._VERSION}:"):
            parts = payload.split(":", 2)
            if len(parts) == 3:
                return CryptoToken(version=parts[0], key_id=parts[1], token=parts[2])
        # Formato legacy: solo token
        return CryptoToken(version="legacy", key_id="", token=payload)
