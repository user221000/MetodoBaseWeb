"""
Carga y almacenamiento de alimentos en SQLite.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from config.constantes import CARPETA_CONFIG
from src.alimentos_seed_runtime import (
    ALIMENTOS_BASE_SEED,
    CATEGORIAS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED,
    LIMITES_ALIMENTOS_SEED,
)
from utils.logger import logger

DB_FILENAME = "alimentos.db"


def _db_path() -> Path:
    return Path(CARPETA_CONFIG) / DB_FILENAME


def _table_empty(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0] == 0


def _asegurar_db() -> Path:
    """Garantiza que la BD y tablas existan y estén inicializadas."""
    return inicializar_db_si_es_necesario(
        ALIMENTOS_BASE_SEED,
        CATEGORIAS_SEED,
        LIMITES_ALIMENTOS_SEED,
        EQUIVALENCIAS_PRACTICAS_SEED,
    )


def _sincronizar_semillas(
    cursor: sqlite3.Cursor,
    alimentos_seed: Dict[str, dict],
    categorias_seed: Dict[str, List[str]],
    limites_seed: Dict[str, float],
    equivalencias_seed: Dict[str, str],
) -> None:
    """Inserta semillas faltantes sin sobrescribir personalizaciones existentes."""
    for nombre, data in alimentos_seed.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO alimentos (nombre, proteina, carbs, grasa, kcal, meal_idx)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                nombre,
                data.get("proteina"),
                data.get("carbs"),
                data.get("grasa"),
                data.get("kcal"),
                json.dumps(data.get("meal_idx", [])),
            ),
        )

    for categoria, alimentos in categorias_seed.items():
        for idx, alimento in enumerate(alimentos):
            cursor.execute(
                """
                INSERT OR IGNORE INTO categorias (categoria, alimento, orden)
                VALUES (?, ?, ?)
                """,
                (categoria, alimento, idx),
            )

    for alimento, limite in limites_seed.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO limites (alimento, limite)
            VALUES (?, ?)
            """,
            (alimento, limite),
        )

    for alimento, equivalencia in equivalencias_seed.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO equivalencias (alimento, equivalencia)
            VALUES (?, ?)
            """,
            (alimento, equivalencia),
        )


def inicializar_db_si_es_necesario(
    alimentos_seed: Dict[str, dict],
    categorias_seed: Dict[str, List[str]],
    limites_seed: Dict[str, float],
    equivalencias_seed: Dict[str, str],
) -> Path:
    """Crea la base SQLite y si está vacía la inicializa con los seeds."""
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS alimentos (
                nombre TEXT PRIMARY KEY,
                proteina REAL,
                carbs REAL,
                grasa REAL,
                kcal REAL,
                meal_idx TEXT
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                categoria TEXT NOT NULL,
                alimento TEXT NOT NULL,
                orden INTEGER NOT NULL,
                PRIMARY KEY (categoria, alimento)
            )
            """
        )

        c.execute("CREATE INDEX IF NOT EXISTS idx_categorias_categoria ON categorias(categoria)")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS limites (
                alimento TEXT PRIMARY KEY,
                limite REAL NOT NULL
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS equivalencias (
                alimento TEXT PRIMARY KEY,
                equivalencia TEXT NOT NULL
            )
            """
        )

        estaba_vacia = _table_empty(c, "alimentos")
        _sincronizar_semillas(
            c,
            alimentos_seed,
            categorias_seed,
            limites_seed,
            equivalencias_seed,
        )

        conn.commit()
        if estaba_vacia:
            logger.info("[ALIMENTOS][DB] Base inicializada con %d alimentos", len(alimentos_seed))
        else:
            logger.info("[ALIMENTOS][DB] Semillas sincronizadas sin sobrescribir datos existentes")
    finally:
        conn.close()

    return db_path


def cargar_datos(db_path: Path | None = None) -> dict:
    """Carga datos de alimentos desde SQLite y retorna los dicts base."""
    if db_path is None:
        db_path = _asegurar_db()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()

        c.execute("SELECT nombre, proteina, carbs, grasa, kcal, meal_idx FROM alimentos")
        alimentos_base: Dict[str, dict] = {}
        for row in c.fetchall():
            meal_idx_raw = row["meal_idx"]
            try:
                meal_idx = json.loads(meal_idx_raw) if meal_idx_raw else []
            except json.JSONDecodeError:
                meal_idx = []
            alimentos_base[row["nombre"]] = {
                "proteina": row["proteina"],
                "carbs": row["carbs"],
                "grasa": row["grasa"],
                "kcal": row["kcal"],
                "meal_idx": meal_idx,
            }

        c.execute("SELECT alimento, limite FROM limites")
        limites_alimentos = {row["alimento"]: row["limite"] for row in c.fetchall()}

        c.execute("SELECT alimento, equivalencia FROM equivalencias")
        equivalencias_practicas = {row["alimento"]: row["equivalencia"] for row in c.fetchall()}

        c.execute(
            """
            SELECT categoria, alimento
            FROM categorias
            ORDER BY categoria, orden
            """
        )
        categorias: Dict[str, List[str]] = {}
        for row in c.fetchall():
            categorias.setdefault(row["categoria"], []).append(row["alimento"])

        return {
            "alimentos_base": alimentos_base,
            "limites_alimentos": limites_alimentos,
            "equivalencias_practicas": equivalencias_practicas,
            "categorias": categorias,
        }
    finally:
        conn.close()


def listar_alimentos(filtro: str | None = None, db_path: Path | None = None) -> List[str]:
    """Lista nombres de alimentos, opcionalmente filtrados."""
    if db_path is None:
        db_path = _asegurar_db()

    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        if filtro:
            termino = f"%{filtro.strip()}%"
            c.execute(
                "SELECT nombre FROM alimentos WHERE nombre LIKE ? ORDER BY nombre",
                (termino,),
            )
        else:
            c.execute("SELECT nombre FROM alimentos ORDER BY nombre")
        return [row[0] for row in c.fetchall()]
    finally:
        conn.close()


def listar_categorias(db_path: Path | None = None) -> List[str]:
    """Lista categorías existentes en la tabla."""
    if db_path is None:
        db_path = _asegurar_db()

    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT categoria FROM categorias ORDER BY categoria")
        return [row[0] for row in c.fetchall()]
    finally:
        conn.close()


def obtener_detalle(alimento: str, db_path: Path | None = None) -> dict | None:
    """Obtiene el detalle completo de un alimento."""
    if db_path is None:
        db_path = _asegurar_db()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute(
            """
            SELECT a.nombre, a.proteina, a.carbs, a.grasa, a.kcal, a.meal_idx,
                   l.limite, e.equivalencia, c.categoria
            FROM alimentos a
            LEFT JOIN limites l ON l.alimento = a.nombre
            LEFT JOIN equivalencias e ON e.alimento = a.nombre
            LEFT JOIN categorias c ON c.alimento = a.nombre
            WHERE a.nombre = ?
            """,
            (alimento,),
        )
        row = c.fetchone()
        if not row:
            return None
        try:
            meal_idx = json.loads(row["meal_idx"]) if row["meal_idx"] else []
        except json.JSONDecodeError:
            meal_idx = []
        return {
            "nombre": row["nombre"],
            "proteina": row["proteina"],
            "carbs": row["carbs"],
            "grasa": row["grasa"],
            "kcal": row["kcal"],
            "meal_idx": meal_idx,
            "limite": row["limite"],
            "equivalencia": row["equivalencia"],
            "categoria": row["categoria"],
        }
    finally:
        conn.close()


def guardar_alimento(detalle: dict, db_path: Path | None = None) -> None:
    """Inserta o actualiza un alimento (y sus tablas relacionadas)."""
    if db_path is None:
        db_path = _asegurar_db()

    nombre = detalle["nombre"].strip()
    categoria = detalle.get("categoria") or ""
    meal_idx = detalle.get("meal_idx", [])
    limite = detalle.get("limite")
    equivalencia = detalle.get("equivalencia")

    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO alimentos (nombre, proteina, carbs, grasa, kcal, meal_idx)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(nombre) DO UPDATE SET
                proteina=excluded.proteina,
                carbs=excluded.carbs,
                grasa=excluded.grasa,
                kcal=excluded.kcal,
                meal_idx=excluded.meal_idx
            """,
            (
                nombre,
                detalle.get("proteina"),
                detalle.get("carbs"),
                detalle.get("grasa"),
                detalle.get("kcal"),
                json.dumps(meal_idx),
            ),
        )

        if categoria:
            c.execute("DELETE FROM categorias WHERE alimento = ?", (nombre,))
            c.execute("SELECT MAX(orden) FROM categorias WHERE categoria = ?", (categoria,))
            max_orden = c.fetchone()[0]
            if max_orden is None:
                max_orden = -1
            c.execute(
                """
                INSERT INTO categorias (categoria, alimento, orden)
                VALUES (?, ?, ?)
                """,
                (categoria, nombre, max_orden + 1),
            )

        if limite is None:
            c.execute("DELETE FROM limites WHERE alimento = ?", (nombre,))
        else:
            c.execute(
                """
                INSERT INTO limites (alimento, limite)
                VALUES (?, ?)
                ON CONFLICT(alimento) DO UPDATE SET
                    limite=excluded.limite
                """,
                (nombre, limite),
            )

        if equivalencia:
            c.execute(
                """
                INSERT INTO equivalencias (alimento, equivalencia)
                VALUES (?, ?)
                ON CONFLICT(alimento) DO UPDATE SET
                    equivalencia=excluded.equivalencia
                """,
                (nombre, equivalencia),
            )
        else:
            c.execute("DELETE FROM equivalencias WHERE alimento = ?", (nombre,))

        conn.commit()
    finally:
        conn.close()


def eliminar_alimento(nombre: str, db_path: Path | None = None) -> None:
    """Elimina un alimento y sus relaciones."""
    if db_path is None:
        db_path = _asegurar_db()

    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        c.execute("DELETE FROM alimentos WHERE nombre = ?", (nombre,))
        c.execute("DELETE FROM categorias WHERE alimento = ?", (nombre,))
        c.execute("DELETE FROM limites WHERE alimento = ?", (nombre,))
        c.execute("DELETE FROM equivalencias WHERE alimento = ?", (nombre,))
        conn.commit()
    finally:
        conn.close()
