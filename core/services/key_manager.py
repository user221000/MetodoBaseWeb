"""
KeyManager: gestiona claves de cifrado con rotacion segura.

- No embebe claves en codigo.
- Permite claves via variable de entorno o archivo fuera del repo.
- Expone API para crear, cargar y rotar claves.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

from config.constantes import APP_DATA_DIR


_ENV_MASTER_KEY = "METODO_BASE_MASTER_KEY"


@dataclass(frozen=True)
class KeyInfo:
    key_id: str
    key_b64: str
    created_at: str


class KeyManager:
    """Administra claves de cifrado y rotacion.

    Si existe la variable de entorno METODO_BASE_MASTER_KEY,
    se usa como clave activa y NO se escribe a disco.
    """

    def __init__(self, key_path: Optional[Path] = None) -> None:
        if key_path is None:
            key_path = Path(APP_DATA_DIR) / "keys" / "mb_keys.json"
        self._key_path = key_path
        self._key_path.parent.mkdir(parents=True, exist_ok=True)

    def load_key(self) -> KeyInfo:
        """Carga la clave activa desde env o archivo seguro."""
        env_key = os.environ.get(_ENV_MASTER_KEY, "").strip()
        if env_key:
            return KeyInfo(key_id="env", key_b64=env_key, created_at="env")

        if not self._key_path.exists():
            raise FileNotFoundError("No se encontro archivo de claves.")

        data = self._read_key_file()
        active = data.get("active")
        if not active:
            raise ValueError("Archivo de claves invalido: falta clave activa.")
        return KeyInfo(
            key_id=active.get("key_id", ""),
            key_b64=active.get("key_b64", ""),
            created_at=active.get("created_at", ""),
        )

    def create_key(self) -> KeyInfo:
        """Crea una nueva clave activa y la guarda a disco."""
        key_b64 = Fernet.generate_key().decode("ascii")
        now = datetime.now(timezone.utc).isoformat()
        key_id = f"k_{now.replace(':', '').replace('-', '').replace('.', '')}"
        info = KeyInfo(key_id=key_id, key_b64=key_b64, created_at=now)
        data = {
            "active": info.__dict__,
            "previous": [],
        }
        self._write_key_file(data)
        return info

    def rotate_key(self) -> KeyInfo:
        """Rota la clave activa, conservando la anterior para descifrado."""
        env_key = os.environ.get(_ENV_MASTER_KEY, "").strip()
        if env_key:
            raise RuntimeError("Rotacion no permitida cuando la clave viene de env.")

        previous_data = []
        if self._key_path.exists():
            data = self._read_key_file()
            active = data.get("active")
            if active:
                previous_data = data.get("previous", [])
                previous_data.insert(0, active)

        new_info = self.create_key()
        data = {
            "active": new_info.__dict__,
            "previous": previous_data[:3],
        }
        self._write_key_file(data)
        return new_info

    def get_previous_keys(self) -> list[KeyInfo]:
        """Devuelve claves previas para descifrar tokens antiguos."""
        env_key = os.environ.get(_ENV_MASTER_KEY, "").strip()
        if env_key:
            return []

        if not self._key_path.exists():
            return []
        data = self._read_key_file()
        prev = []
        for item in data.get("previous", []):
            prev.append(KeyInfo(
                key_id=item.get("key_id", ""),
                key_b64=item.get("key_b64", ""),
                created_at=item.get("created_at", ""),
            ))
        return prev

    def save_key(self, key_info: KeyInfo) -> None:
        """Guarda una clave como activa (solo archivo)."""
        env_key = os.environ.get(_ENV_MASTER_KEY, "").strip()
        if env_key:
            raise RuntimeError("No se puede guardar clave cuando se usa env.")
        data = {
            "active": key_info.__dict__,
            "previous": [],
        }
        self._write_key_file(data)

    def _read_key_file(self) -> dict:
        with open(self._key_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_key_file(self, data: dict) -> None:
        with open(self._key_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        try:
            os.chmod(self._key_path, 0o600)
        except OSError:
            # En algunos entornos (Windows), chmod puede fallar.
            pass
