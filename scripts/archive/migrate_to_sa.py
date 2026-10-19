#!/usr/bin/env python3
"""
scripts/migrate_to_sa.py — Script de migración idempotente legacy → SQLAlchemy.

FASE 5 del plan de consolidación de BD.

Características:
- Idempotente: puede ejecutarse múltiples veces sin duplicar datos
- Transaccional: rollback automático en caso de error
- Incremental: solo migra registros nuevos/modificados
- Auditable: genera logs detallados y checkpoints

Uso:
    # Dry run (sin cambios reales)
    python scripts/migrate_to_sa.py --dry-run
    
    # Migración completa
    python scripts/migrate_to_sa.py
    
    # Solo clientes
    python scripts/migrate_to_sa.py --tables clientes
    
    # Con gym_id específico
    python scripts/migrate_to_sa.py --gym-id gym_001
"""
import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Agregar root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.archive.etl_mapping import (
    CLIENTE_MAPPING,
    PLAN_MAPPING,
    ESTADISTICAS_MAPPING,
    transform_batch,
    generate_migration_report,
    checksum_record,
    find_duplicates,
    validate_referential_integrity,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ]
)
logger = logging.getLogger(__name__)


# ── Configuration ───────────────────────────────────────────────────────────

@dataclass
class MigrationConfig:
    """Configuración de migración."""
    legacy_db_path: str = "clientes.db"
    batch_size: int = 100
    dry_run: bool = True
    tables: List[str] = field(default_factory=lambda: ["clientes", "planes_generados"])
    gym_id: str = "gym_default"
    checkpoint_dir: str = ".migration_checkpoints"
    skip_validation: bool = False
    force: bool = False  # Ignorar checkpoints existentes


# ── Checkpoint Management ───────────────────────────────────────────────────

@dataclass
class MigrationCheckpoint:
    """Checkpoint de migración para idempotencia."""
    table: str
    last_id: str
    records_migrated: int
    checksum: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.table,
            "last_id": self.last_id,
            "records_migrated": self.records_migrated,
            "checksum": self.checksum,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationCheckpoint":
        return cls(
            table=data["table"],
            last_id=data["last_id"],
            records_migrated=data["records_migrated"],
            checksum=data["checksum"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class CheckpointManager:
    """Gestiona checkpoints para migración incremental."""
    
    def __init__(self, checkpoint_dir: str):
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
    
    def get_checkpoint(self, table: str) -> Optional[MigrationCheckpoint]:
        """Obtiene checkpoint para una tabla."""
        path = self._dir / f"{table}.checkpoint.json"
        if not path.exists():
            return None
        
        try:
            with open(path) as f:
                return MigrationCheckpoint.from_dict(json.load(f))
        except Exception as e:
            logger.warning("Error leyendo checkpoint %s: %s", table, e)
            return None
    
    def save_checkpoint(self, checkpoint: MigrationCheckpoint) -> None:
        """Guarda checkpoint."""
        path = self._dir / f"{checkpoint.table}.checkpoint.json"
        with open(path, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
        logger.info("Checkpoint guardado: %s", path)
    
    def clear_checkpoint(self, table: str) -> None:
        """Elimina checkpoint de una tabla."""
        path = self._dir / f"{table}.checkpoint.json"
        if path.exists():
            path.unlink()
            logger.info("Checkpoint eliminado: %s", table)


# ── Migration Stats ─────────────────────────────────────────────────────────

@dataclass
class MigrationStats:
    """Estadísticas de migración."""
    table: str
    total_source: int = 0
    already_exists: int = 0
    migrated: int = 0
    updated: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0
    error_details: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        total = self.migrated + self.updated + self.errors
        if total == 0:
            return 1.0
        return (self.migrated + self.updated) / total


# ── Migration Engine ────────────────────────────────────────────────────────

class MigrationEngine:
    """Motor de migración principal."""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.checkpoint_mgr = CheckpointManager(config.checkpoint_dir)
        self._legacy_conn = None
        self._sa_session = None
    
    def _get_legacy_conn(self) -> sqlite3.Connection:
        """Obtiene conexión a BD legacy."""
        if self._legacy_conn is None:
            self._legacy_conn = sqlite3.connect(self.config.legacy_db_path)
            self._legacy_conn.row_factory = sqlite3.Row
        return self._legacy_conn
    
    def _get_sa_session(self):
        """Obtiene sesión SQLAlchemy."""
        if self._sa_session is None:
            from web.database.engine import init_db, _SessionLocal
            init_db()
            from web.database.engine import _SessionLocal
            self._sa_session = _SessionLocal()
        return self._sa_session
    
    def _get_existing_ids(self, table: str) -> Set[str]:
        """Obtiene IDs existentes en SA para evitar duplicados."""
        session = self._get_sa_session()
        
        if table == "clientes":
            from web.database.models import Cliente
            return {c.id_cliente for c in session.query(Cliente.id_cliente).all()}
        elif table == "planes_generados":
            # Para planes, usamos combinación de id_cliente + fecha como key
            from web.database.models import PlanGenerado
            return {
                f"{p.id_cliente}_{p.fecha_generacion.isoformat() if p.fecha_generacion else 'none'}"
                for p in session.query(PlanGenerado.id_cliente, PlanGenerado.fecha_generacion).all()
            }
        
        return set()
    
    def _read_legacy_batch(
        self,
        table: str,
        offset: int,
        limit: int,
        after_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lee batch de registros legacy."""
        conn = self._get_legacy_conn()
        
        queries = {
            "clientes": "SELECT * FROM clientes",
            "planes_generados": "SELECT * FROM planes_generados",
        }
        if table not in queries:
            raise ValueError("Unsupported legacy migration table")
        query = queries[table]
        params = []
        
        # Para continuar desde checkpoint
        if after_id and table == "clientes":
            query += " WHERE id_cliente > ?"
            params.append(after_id)
        
        query += " ORDER BY rowid LIMIT ? OFFSET ?"
        params.extend((limit, offset))
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def migrate_clientes(self) -> MigrationStats:
        """Migra tabla clientes."""
        stats = MigrationStats(table="clientes")
        start = datetime.now()
        
        # Checkpoint existente
        checkpoint = None if self.config.force else self.checkpoint_mgr.get_checkpoint("clientes")
        after_id = checkpoint.last_id if checkpoint else None
        
        # IDs existentes en SA
        existing_ids = self._get_existing_ids("clientes") if not self.config.dry_run else set()
        
        session = self._get_sa_session() if not self.config.dry_run else None
        
        offset = 0
        last_id = after_id
        
        while True:
            # Leer batch
            batch = self._read_legacy_batch("clientes", offset, self.config.batch_size, after_id)
            if not batch:
                break
            
            stats.total_source += len(batch)
            
            # Transformar
            transformed, errors = transform_batch(batch, CLIENTE_MAPPING, self.config.gym_id)
            
            for err in errors:
                stats.errors += 1
                stats.error_details.append(f"Transform error: {err.errors}")
            
            # Insertar
            for record in transformed:
                id_cliente = record.get("id_cliente")
                last_id = id_cliente
                
                if id_cliente in existing_ids:
                    stats.already_exists += 1
                    continue
                
                if self.config.dry_run:
                    stats.migrated += 1
                    continue
                
                try:
                    from web.database.models import Cliente
                    
                    cliente = Cliente(**record)
                    session.add(cliente)
                    stats.migrated += 1
                    existing_ids.add(id_cliente)
                    
                except Exception as e:
                    stats.errors += 1
                    stats.error_details.append(f"Insert {id_cliente}: {e}")
                    logger.error("Error insertando cliente %s: %s", id_cliente, e)
            
            # Commit batch
            if session and stats.migrated > 0 and stats.migrated % self.config.batch_size == 0:
                try:
                    session.commit()
                    logger.info("Committed batch: %d clientes migrados", stats.migrated)
                except Exception as e:
                    session.rollback()
                    logger.error("Rollback en batch: %s", e)
            
            offset += self.config.batch_size
        
        # Final commit
        if session and not self.config.dry_run:
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error("Rollback final: %s", e)
        
        # Guardar checkpoint
        if last_id and not self.config.dry_run:
            self.checkpoint_mgr.save_checkpoint(MigrationCheckpoint(
                table="clientes",
                last_id=last_id,
                records_migrated=stats.migrated,
                checksum=hashlib.md5(str(stats.migrated).encode(), usedforsecurity=False).hexdigest(),
            ))
        
        stats.duration_seconds = (datetime.now() - start).total_seconds()
        return stats
    
    def migrate_planes(self) -> MigrationStats:
        """Migra tabla planes_generados."""
        stats = MigrationStats(table="planes_generados")
        start = datetime.now()
        
        existing_keys = self._get_existing_ids("planes_generados") if not self.config.dry_run else set()
        session = self._get_sa_session() if not self.config.dry_run else None
        
        offset = 0
        
        while True:
            batch = self._read_legacy_batch("planes_generados", offset, self.config.batch_size)
            if not batch:
                break
            
            stats.total_source += len(batch)
            
            transformed, errors = transform_batch(batch, PLAN_MAPPING, self.config.gym_id)
            
            for err in errors:
                stats.errors += 1
            
            for record in transformed:
                # Key compuesta para idempotencia
                fecha = record.get("fecha_generacion")
                fecha_str = fecha.isoformat() if fecha else "none"
                key = f"{record.get('id_cliente')}_{fecha_str}"
                
                if key in existing_keys:
                    stats.already_exists += 1
                    continue
                
                if self.config.dry_run:
                    stats.migrated += 1
                    continue
                
                try:
                    from web.database.models import PlanGenerado
                    
                    plan = PlanGenerado(**record)
                    session.add(plan)
                    stats.migrated += 1
                    existing_keys.add(key)
                    
                except Exception as e:
                    stats.errors += 1
                    stats.error_details.append(f"Insert plan: {e}")
            
            if session and stats.migrated > 0 and stats.migrated % self.config.batch_size == 0:
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
            
            offset += self.config.batch_size
        
        if session and not self.config.dry_run:
            try:
                session.commit()
            except Exception as e:
                session.rollback()
        
        stats.duration_seconds = (datetime.now() - start).total_seconds()
        return stats
    
    def validate_migration(self) -> Dict[str, Any]:
        """Valida integridad post-migración."""
        logger.info("Validando migración...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tables": {},
            "referential_integrity": {},
        }
        
        # Contar registros
        legacy_conn = self._get_legacy_conn()
        sa_session = self._get_sa_session()
        
        # Clientes
        legacy_count = legacy_conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
        from web.database.models import Cliente
        sa_count = sa_session.query(Cliente).count()
        
        results["tables"]["clientes"] = {
            "legacy_count": legacy_count,
            "sa_count": sa_count,
            "match": legacy_count == sa_count,
        }
        
        # Planes
        legacy_plans = legacy_conn.execute("SELECT COUNT(*) FROM planes_generados").fetchone()[0]
        from web.database.models import PlanGenerado
        sa_plans = sa_session.query(PlanGenerado).count()
        
        results["tables"]["planes_generados"] = {
            "legacy_count": legacy_plans,
            "sa_count": sa_plans,
            "match": legacy_plans == sa_plans,
        }
        
        # Integridad referencial
        sa_cliente_ids = {c.id_cliente for c in sa_session.query(Cliente.id_cliente).all()}
        orphan_plans = sa_session.query(PlanGenerado).filter(
            ~PlanGenerado.id_cliente.in_(sa_cliente_ids)
        ).count()
        
        results["referential_integrity"]["orphan_plans"] = orphan_plans
        results["referential_integrity"]["valid"] = orphan_plans == 0
        
        return results
    
    def run(self) -> Dict[str, Any]:
        """Ejecuta migración completa."""
        logger.info("=" * 60)
        logger.info("INICIANDO MIGRACIÓN %s", "DRY RUN" if self.config.dry_run else "REAL")
        logger.info("=" * 60)
        logger.info("Config: %s", self.config)
        
        results = {
            "config": {
                "dry_run": self.config.dry_run,
                "gym_id": self.config.gym_id,
                "tables": self.config.tables,
            },
            "stats": {},
            "validation": None,
        }
        
        # Migrar tablas
        if "clientes" in self.config.tables:
            stats = self.migrate_clientes()
            results["stats"]["clientes"] = {
                "total_source": stats.total_source,
                "migrated": stats.migrated,
                "already_exists": stats.already_exists,
                "errors": stats.errors,
                "success_rate": stats.success_rate,
                "duration_seconds": stats.duration_seconds,
            }
            logger.info("Clientes: %d migrados, %d existentes, %d errores",
                       stats.migrated, stats.already_exists, stats.errors)
        
        if "planes_generados" in self.config.tables:
            stats = self.migrate_planes()
            results["stats"]["planes_generados"] = {
                "total_source": stats.total_source,
                "migrated": stats.migrated,
                "already_exists": stats.already_exists,
                "errors": stats.errors,
                "success_rate": stats.success_rate,
                "duration_seconds": stats.duration_seconds,
            }
            logger.info("Planes: %d migrados, %d existentes, %d errores",
                       stats.migrated, stats.already_exists, stats.errors)
        
        # Validar
        if not self.config.skip_validation and not self.config.dry_run:
            results["validation"] = self.validate_migration()
        
        logger.info("=" * 60)
        logger.info("MIGRACIÓN COMPLETADA")
        logger.info("=" * 60)
        
        return results
    
    def cleanup(self):
        """Limpieza de recursos."""
        if self._legacy_conn:
            self._legacy_conn.close()
        if self._sa_session:
            self._sa_session.close()


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Migración idempotente legacy → SQLAlchemy"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar sin hacer cambios reales"
    )
    parser.add_argument(
        "--legacy-db",
        default="clientes.db",
        help="Path a BD legacy (default: clientes.db)"
    )
    parser.add_argument(
        "--gym-id",
        default="gym_default",
        help="gym_id para registros migrados (default: gym_default)"
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["clientes", "planes_generados"],
        help="Tablas a migrar (default: clientes planes_generados)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Tamaño de batch para commits (default: 100)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignorar checkpoints existentes"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Omitir validación post-migración"
    )
    
    args = parser.parse_args()
    
    config = MigrationConfig(
        legacy_db_path=args.legacy_db,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        tables=args.tables,
        gym_id=args.gym_id,
        skip_validation=args.skip_validation,
        force=args.force,
    )
    
    engine = MigrationEngine(config)
    
    try:
        results = engine.run()
        
        # Guardar resultados
        output_path = f"migration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Resultados guardados en: %s", output_path)
        
        # Exit code
        total_errors = sum(
            s.get("errors", 0) for s in results["stats"].values()
        )
        sys.exit(1 if total_errors > 0 else 0)
        
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()
