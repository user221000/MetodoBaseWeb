"""
PasswordHasher: hashing y verificacion de contrasenas.

- bcrypt directo (compatible con bcrypt >= 4.x).
- Valida fuerza minima.
- Evita doble hash accidental.

Nota: passlib 1.7.4 no es compatible con bcrypt >= 4.0 (API breaking changes).
Se usa el modulo bcrypt directamente para garantizar compatibilidad futura.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import bcrypt as _bcrypt_lib


@dataclass(frozen=True)
class PasswordPolicy:
    min_length: int = 12
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True
    require_symbol: bool = True


# Prefijo de hash bcrypt para detección de doble-hash
_BCRYPT_PREFIX = b"$2b$"
_BCRYPT_ALT_PREFIXES = (b"$2a$", b"$2y$")


class PasswordHasher:
    def __init__(self, policy: PasswordPolicy | None = None, rounds: int = 12) -> None:
        self._policy = policy or PasswordPolicy()
        self._rounds = rounds

    def hash_password(self, plain_password: str) -> str:
        self._ensure_not_hash(plain_password)
        self._validate_strength(plain_password)
        salt = _bcrypt_lib.gensalt(rounds=self._rounds)
        hashed = _bcrypt_lib.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("ascii")

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        self._ensure_not_hash(plain_password)
        try:
            return _bcrypt_lib.checkpw(
                plain_password.encode("utf-8"),
                password_hash.encode("ascii"),
            )
        except Exception:
            return False

    def needs_update(self, password_hash: str) -> bool:
        """Indica si el hash requiere rehash por politica nueva (rounds distintos)."""
        try:
            extracted = _bcrypt_lib.gensalt(rounds=self._rounds)
            current_rounds = int(password_hash.split("$")[2])
            return current_rounds < self._rounds
        except Exception:
            return False

    def _ensure_not_hash(self, value: str) -> None:
        encoded = value.encode("ascii", errors="ignore")
        if encoded.startswith(_BCRYPT_PREFIX) or any(
            encoded.startswith(p) for p in _BCRYPT_ALT_PREFIXES
        ):
            raise ValueError("Valor parece un hash; evita doble hash.")

    def _validate_strength(self, value: str) -> None:
        if len(value) < self._policy.min_length:
            raise ValueError("Contrasena demasiado corta.")
        if self._policy.require_upper and not re.search(r"[A-Z]", value):
            raise ValueError("Debe incluir mayusculas.")
        if self._policy.require_lower and not re.search(r"[a-z]", value):
            raise ValueError("Debe incluir minusculas.")
        if self._policy.require_digit and not re.search(r"\d", value):
            raise ValueError("Debe incluir numeros.")
        if self._policy.require_symbol and not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Debe incluir simbolos.")
