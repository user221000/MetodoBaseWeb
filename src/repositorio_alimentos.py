"""
Repositorio de alimentos — capa de abstracción sobre SQLite.

Provee una interfaz desacoplada (clase) para todas las operaciones
del catálogo de alimentos: CRUD, búsqueda, categorías, seeds.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from src import alimentos_sqlite
from utils.logger import logger


class RepositorioAlimentos:
    """Repositorio formal para el catálogo de alimentos."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path
        self._asegurar_db()

    def _asegurar_db(self) -> None:
        alimentos_sqlite._asegurar_db()

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def listar(self, filtro: str | None = None) -> List[str]:
        """Lista nombres de alimentos, opcionalmente filtrados."""
        return alimentos_sqlite.listar_alimentos(filtro=filtro, db_path=self._db_path)

    def obtener(self, nombre: str) -> Optional[dict]:
        """Obtiene el detalle completo de un alimento."""
        return alimentos_sqlite.obtener_detalle(nombre, db_path=self._db_path)

    def listar_categorias(self) -> List[str]:
        """Lista categorías existentes."""
        return alimentos_sqlite.listar_categorias(db_path=self._db_path)

    def cargar_todo(self) -> dict:
        """Carga todos los datos: alimentos_base, limites, equivalencias, categorias."""
        return alimentos_sqlite.cargar_datos(db_path=self._db_path)

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, detalle: dict) -> None:
        """Inserta o actualiza un alimento y sus relaciones."""
        alimentos_sqlite.guardar_alimento(detalle, db_path=self._db_path)
        logger.info("[REPO] Alimento guardado: %s", detalle.get("nombre"))

    def eliminar(self, nombre: str) -> None:
        """Elimina un alimento y sus relaciones."""
        alimentos_sqlite.eliminar_alimento(nombre, db_path=self._db_path)
        logger.info("[REPO] Alimento eliminado: %s", nombre)

    # ------------------------------------------------------------------
    # Validación de negocio
    # ------------------------------------------------------------------

    def existe(self, nombre: str) -> bool:
        """Verifica si un alimento existe en el catálogo."""
        return alimentos_sqlite.obtener_detalle(nombre, db_path=self._db_path) is not None

    def contar(self) -> int:
        """Retorna el número total de alimentos."""
        return len(alimentos_sqlite.listar_alimentos(db_path=self._db_path))
