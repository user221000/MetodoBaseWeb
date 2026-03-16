# -*- coding: utf-8 -*-
"""
GestorPreferencias — Almacén ligero de preferencias por usuario.

Guarda un JSON por usuario en ~/.metodobase/prefs/<id_usuario>.json.
Contiene: perfil corporal, alimentos excluidos, idioma, etc.

API pública
───────────
  gestor = GestorPreferencias(id_usuario)
  datos  = gestor.cargar()               # dict (vacío si no existe)
  gestor.guardar(datos)                  # persiste
  gestor.actualizar(clave, valor)        # actualiza un subconjunto y persiste
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from utils.logger import logger


_BASE_DIR = Path.home() / ".metodobase" / "prefs"


def _prefs_path(id_usuario: str) -> Path:
    """Devuelve la ruta del archivo de preferencias para un usuario."""
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    # Normalizar id para nombre de archivo seguro
    safe_id = "".join(c for c in id_usuario if c.isalnum() or c in "-_")
    return _BASE_DIR / f"{safe_id}.json"


class GestorPreferencias:
    """Gestor de preferencias persistentes por usuario (JSON en disco)."""

    def __init__(self, id_usuario: str) -> None:
        if not id_usuario:
            raise ValueError("id_usuario no puede estar vacío.")
        self._id = id_usuario
        self._path = _prefs_path(id_usuario)

    # ── API pública ───────────────────────────────────────────────────────

    def cargar(self) -> dict[str, Any]:
        """Lee las preferencias desde disco. Devuelve dict vacío si no existe."""
        if not self._path.exists():
            return {}
        try:
            with open(self._path, encoding="utf-8") as fh:
                datos = json.load(fh)
            if not isinstance(datos, dict):
                logger.warning("[PREFS] Archivo de prefs corrupto para %s. Reiniciando.", self._id)
                return {}
            return datos
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[PREFS] No se pudo cargar prefs de %s: %s", self._id, exc)
            return {}

    def guardar(self, datos: dict[str, Any]) -> bool:
        """Escribe el dict de preferencias a disco. Retorna True en éxito."""
        if not isinstance(datos, dict):
            raise TypeError("datos debe ser un dict.")
        try:
            _BASE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(datos, fh, ensure_ascii=False, indent=2)
            tmp.replace(self._path)
            return True
        except OSError as exc:
            logger.error("[PREFS] No se pudo guardar prefs de %s: %s", self._id, exc)
            return False

    def actualizar(self, clave: str, valor: Any) -> bool:
        """Carga, establece clave=valor y persiste."""
        datos = self.cargar()
        datos[clave] = valor
        return self.guardar(datos)

    def obtener(self, clave: str, default: Any = None) -> Any:
        """Lee un valor específico sin cargar todo el dict en memoria."""
        return self.cargar().get(clave, default)
