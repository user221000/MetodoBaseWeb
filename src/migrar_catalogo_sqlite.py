#!/usr/bin/env python3
"""
Script operativo de migración: catálogo de alimentos → SQLite.

Uso:
    python -m src.migrar_catalogo_sqlite [--force] [--dry-run]

- Sin flags: solo inserta semillas faltantes sin sobrescribir datos existentes.
- --force: fuerza reinicialización completa (borra y recrea la BD de alimentos).
- --dry-run: muestra lo que haría sin escribir.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Asegurar que el proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alimentos_seed_runtime import (
    ALIMENTOS_BASE_SEED,
    CATEGORIAS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED,
    LIMITES_ALIMENTOS_SEED,
)
from src.alimentos_sqlite import _db_path, inicializar_db_si_es_necesario
from utils.logger import logger


def _contar_registros(db: Path) -> dict:
    conn = sqlite3.connect(db)
    c = conn.cursor()
    counts = {}
    for table in ("alimentos", "categorias", "limites", "equivalencias"):
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = c.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0
    conn.close()
    return counts


def migrar(force: bool = False, dry_run: bool = False) -> None:
    db = _db_path()
    print(f"Base de datos: {db}")

    if dry_run:
        print("[DRY-RUN] Semillas a insertar:")
        print(f"  Alimentos:     {len(ALIMENTOS_BASE_SEED)}")
        print(f"  Categorías:    {sum(len(v) for v in CATEGORIAS_SEED.values())} entradas")
        print(f"  Límites:       {len(LIMITES_ALIMENTOS_SEED)}")
        print(f"  Equivalencias: {len(EQUIVALENCIAS_PRACTICAS_SEED)}")
        if db.exists():
            before = _contar_registros(db)
            print(f"  Estado actual DB: {before}")
        else:
            print("  BD no existe todavía — se crearía desde cero.")
        return

    if force and db.exists():
        backup = db.with_suffix(".db.bak")
        db.rename(backup)
        print(f"[FORCE] BD respaldada en {backup}")
        logger.info("[MIGRACIÓN] BD respaldada en %s", backup)

    before = _contar_registros(db) if db.exists() else {}

    inicializar_db_si_es_necesario(
        ALIMENTOS_BASE_SEED,
        CATEGORIAS_SEED,
        LIMITES_ALIMENTOS_SEED,
        EQUIVALENCIAS_PRACTICAS_SEED,
    )

    after = _contar_registros(db)
    print("Migración completada:")
    for table in ("alimentos", "categorias", "limites", "equivalencias"):
        b = before.get(table, 0)
        a = after.get(table, 0)
        diff = a - b
        sign = f"+{diff}" if diff > 0 else str(diff)
        print(f"  {table:15s}: {b} → {a}  ({sign})")
    logger.info("[MIGRACIÓN] Completada: %s", after)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrar catálogo de alimentos a SQLite")
    parser.add_argument("--force", action="store_true", help="Reinicializar BD completa")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no escribir")
    args = parser.parse_args()
    migrar(force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
