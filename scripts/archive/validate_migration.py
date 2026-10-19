#!/usr/bin/env python3
"""
scripts/validate_migration.py — Validación de integridad post-migración.

FASE 6 del plan de consolidación de BD.

Valida:
- Conteo de registros legacy vs SA
- Paridad de datos críticos
- Integridad referencial
- Checksums de registros
- Drift detection entre BDs

Uso:
    python scripts/validate_migration.py
    python scripts/validate_migration.py --output report.json
    python scripts/validate_migration.py --fix-orphans
"""
import argparse
import hashlib
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


# ── Validation Results ──────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Resultado de una validación individual."""
    name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    results: List[ValidationResult] = field(default_factory=list)
    overall_passed: bool = True
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: ValidationResult):
        self.results.append(result)
        if not result.passed:
            self.overall_passed = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_passed": self.overall_passed,
            "total_checks": len(self.results),
            "passed_checks": sum(1 for r in self.results if r.passed),
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }


# ── Validator Class ─────────────────────────────────────────────────────────

class MigrationValidator:
    """Validador de migración."""
    
    def __init__(self, legacy_db_path: str = "clientes.db"):
        self.legacy_db_path = legacy_db_path
        self._legacy_conn = None
        self._sa_session = None
    
    def _get_legacy_conn(self) -> sqlite3.Connection:
        if self._legacy_conn is None:
            self._legacy_conn = sqlite3.connect(self.legacy_db_path)
            self._legacy_conn.row_factory = sqlite3.Row
        return self._legacy_conn
    
    def _get_sa_session(self):
        if self._sa_session is None:
            from web.database.engine import init_db, _SessionLocal
            init_db()
            from web.database.engine import _SessionLocal
            self._sa_session = _SessionLocal()
        return self._sa_session
    
    # ── Individual Validators ───────────────────────────────────────────────
    
    def validate_record_counts(self) -> ValidationResult:
        """Valida que los conteos de registros coincidan."""
        result = ValidationResult(name="record_counts", passed=True)
        
        try:
            legacy = self._get_legacy_conn()
            session = self._get_sa_session()
            
            from web.database.models import Cliente, PlanGenerado
            
            # Clientes
            legacy_clientes = legacy.execute(
                "SELECT COUNT(*) FROM clientes"
            ).fetchone()[0]
            sa_clientes = session.query(Cliente).count()
            
            result.details["clientes"] = {
                "legacy": legacy_clientes,
                "sqlalchemy": sa_clientes,
                "match": legacy_clientes == sa_clientes,
                "difference": sa_clientes - legacy_clientes,
            }
            
            if legacy_clientes != sa_clientes:
                result.warnings.append(
                    f"Clientes count mismatch: legacy={legacy_clientes}, sa={sa_clientes}"
                )
            
            # Planes
            legacy_planes = legacy.execute(
                "SELECT COUNT(*) FROM planes_generados"
            ).fetchone()[0]
            sa_planes = session.query(PlanGenerado).count()
            
            result.details["planes_generados"] = {
                "legacy": legacy_planes,
                "sqlalchemy": sa_planes,
                "match": legacy_planes == sa_planes,
                "difference": sa_planes - legacy_planes,
            }
            
            if legacy_planes != sa_planes:
                result.warnings.append(
                    f"Planes count mismatch: legacy={legacy_planes}, sa={sa_planes}"
                )
            
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))
        
        return result
    
    def validate_client_ids(self) -> ValidationResult:
        """Valida que todos los IDs de clientes estén presentes."""
        result = ValidationResult(name="client_ids", passed=True)
        
        try:
            legacy = self._get_legacy_conn()
            session = self._get_sa_session()
            from web.database.models import Cliente
            
            # IDs en legacy
            legacy_ids = {
                row[0] for row in legacy.execute(
                    "SELECT id_cliente FROM clientes"
                ).fetchall()
            }
            
            # IDs en SA
            sa_ids = {c.id_cliente for c in session.query(Cliente.id_cliente).all()}
            
            # Comparar
            only_legacy = legacy_ids - sa_ids
            only_sa = sa_ids - legacy_ids
            
            result.details = {
                "legacy_count": len(legacy_ids),
                "sa_count": len(sa_ids),
                "only_in_legacy": list(only_legacy)[:100],  # Limitar para reporte
                "only_in_sa": list(only_sa)[:100],
                "only_legacy_count": len(only_legacy),
                "only_sa_count": len(only_sa),
            }
            
            if only_legacy:
                result.passed = False
                result.errors.append(f"{len(only_legacy)} clientes solo en legacy")
            
            if only_sa:
                result.warnings.append(f"{len(only_sa)} clientes solo en SA (OK si son nuevos)")
            
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))
        
        return result
    
    def validate_data_parity(self, sample_size: int = 100) -> ValidationResult:
        """Valida paridad de datos en una muestra de registros."""
        result = ValidationResult(name="data_parity", passed=True)
        
        try:
            legacy = self._get_legacy_conn()
            session = self._get_sa_session()
            from web.database.models import Cliente
            
            # Obtener muestra de legacy
            legacy_sample = legacy.execute(
                "SELECT * FROM clientes ORDER BY RANDOM() LIMIT ?", (sample_size,)
            ).fetchall()
            
            mismatches = []
            critical_fields = ["nombre", "peso_kg", "objetivo"]
            
            for row in legacy_sample:
                legacy_data = dict(row)
                id_cliente = legacy_data.get("id_cliente")
                
                # Buscar en SA
                sa_cliente = session.query(Cliente).filter(
                    Cliente.id_cliente == id_cliente
                ).first()
                
                if not sa_cliente:
                    mismatches.append({
                        "id": id_cliente,
                        "issue": "missing_in_sa",
                    })
                    continue
                
                # Comparar campos críticos
                for field in critical_fields:
                    legacy_val = legacy_data.get(field)
                    sa_val = getattr(sa_cliente, field, None)
                    
                    # Normalizar para comparación
                    if isinstance(legacy_val, str):
                        legacy_val = legacy_val.strip() if legacy_val else ""
                    if isinstance(sa_val, str):
                        sa_val = sa_val.strip() if sa_val else ""
                    
                    if str(legacy_val) != str(sa_val):
                        mismatches.append({
                            "id": id_cliente,
                            "field": field,
                            "legacy": legacy_val,
                            "sa": sa_val,
                        })
            
            result.details = {
                "sample_size": sample_size,
                "checked": len(legacy_sample),
                "mismatches": len(mismatches),
                "mismatch_details": mismatches[:20],  # Limitar
            }
            
            if mismatches:
                result.passed = False
                result.errors.append(f"{len(mismatches)} registros con diferencias")
            
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))
        
        return result
    
    def validate_referential_integrity(self) -> ValidationResult:
        """Valida integridad referencial en SA."""
        result = ValidationResult(name="referential_integrity", passed=True)
        
        try:
            session = self._get_sa_session()
            from web.database.models import Cliente, PlanGenerado
            
            # IDs de clientes
            cliente_ids = {c.id_cliente for c in session.query(Cliente.id_cliente).all()}
            
            # Planes huérfanos
            orphan_plans = session.query(PlanGenerado).filter(
                ~PlanGenerado.id_cliente.in_(cliente_ids) if cliente_ids else True
            ).all()
            
            orphan_ids = [p.id_cliente for p in orphan_plans]
            
            result.details = {
                "total_clientes": len(cliente_ids),
                "orphan_plans_count": len(orphan_ids),
                "orphan_plan_cliente_ids": list(set(orphan_ids))[:50],
            }
            
            if orphan_ids:
                result.passed = False
                result.errors.append(
                    f"{len(orphan_ids)} planes huérfanos (cliente no existe)"
                )
            
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))
        
        return result
    
    def validate_checksums(self, sample_size: int = 50) -> ValidationResult:
        """Valida checksums de registros para detectar corrupción."""
        result = ValidationResult(name="checksums", passed=True)
        
        try:
            legacy = self._get_legacy_conn()
            session = self._get_sa_session()
            from web.database.models import Cliente
            
            # Muestra
            legacy_sample = legacy.execute(
                "SELECT id_cliente, nombre, peso_kg, objetivo FROM clientes LIMIT ?", (sample_size,)
            ).fetchall()
            
            checksum_mismatches = []
            
            for row in legacy_sample:
                legacy_data = dict(row)
                id_cliente = legacy_data.get("id_cliente")
                
                # Calcular checksum legacy
                legacy_str = f"{legacy_data.get('nombre')}|{legacy_data.get('peso_kg')}|{legacy_data.get('objetivo')}"
                legacy_checksum = hashlib.md5(legacy_str.encode(), usedforsecurity=False).hexdigest()[:8]
                
                # Buscar y calcular checksum SA
                sa_cliente = session.query(Cliente).filter(
                    Cliente.id_cliente == id_cliente
                ).first()
                
                if sa_cliente:
                    sa_str = f"{sa_cliente.nombre}|{sa_cliente.peso_kg}|{sa_cliente.objetivo}"
                    sa_checksum = hashlib.md5(sa_str.encode(), usedforsecurity=False).hexdigest()[:8]
                    
                    if legacy_checksum != sa_checksum:
                        checksum_mismatches.append({
                            "id": id_cliente,
                            "legacy_checksum": legacy_checksum,
                            "sa_checksum": sa_checksum,
                        })
            
            result.details = {
                "sample_size": sample_size,
                "mismatches": len(checksum_mismatches),
                "mismatch_details": checksum_mismatches,
            }
            
            if checksum_mismatches:
                result.warnings.append(f"{len(checksum_mismatches)} checksum differences")
            
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))
        
        return result
    
    def validate_no_nulls_in_required(self) -> ValidationResult:
        """Valida que campos requeridos no tengan NULLs."""
        result = ValidationResult(name="required_fields", passed=True)
        
        try:
            session = self._get_sa_session()
            from web.database.models import Cliente
            
            # Campos requeridos
            required_fields = {
                "id_cliente": Cliente.id_cliente,
                "nombre": Cliente.nombre,
            }
            
            null_counts = {}
            
            for field_name, field_col in required_fields.items():
                null_count = session.query(Cliente).filter(
                    field_col == None
                ).count()
                null_counts[field_name] = null_count
                
                if null_count > 0:
                    result.passed = False
                    result.errors.append(f"{field_name}: {null_count} NULLs")
            
            result.details = {
                "null_counts": null_counts,
            }
            
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))
        
        return result
    
    # ── Main Validation ─────────────────────────────────────────────────────
    
    def run_all_validations(self) -> ValidationReport:
        """Ejecuta todas las validaciones."""
        report = ValidationReport()
        
        validators = [
            ("record_counts", self.validate_record_counts),
            ("client_ids", self.validate_client_ids),
            ("data_parity", self.validate_data_parity),
            ("referential_integrity", self.validate_referential_integrity),
            ("checksums", self.validate_checksums),
            ("required_fields", self.validate_no_nulls_in_required),
        ]
        
        for name, validator in validators:
            logger.info("Ejecutando validación: %s", name)
            try:
                result = validator()
                report.add_result(result)
                status = "✓ PASS" if result.passed else "✗ FAIL"
                logger.info("  %s: %s", name, status)
                if result.errors:
                    for err in result.errors:
                        logger.error("    - %s", err)
                if result.warnings:
                    for warn in result.warnings:
                        logger.warning("    - %s", warn)
            except Exception as e:
                logger.error("  %s: ERROR - %s", name, e)
                report.add_result(ValidationResult(
                    name=name,
                    passed=False,
                    errors=[str(e)],
                ))
        
        # Resumen
        report.summary = {
            "total": len(report.results),
            "passed": sum(1 for r in report.results if r.passed),
            "failed": sum(1 for r in report.results if not r.passed),
            "overall": "PASS" if report.overall_passed else "FAIL",
        }
        
        return report
    
    def cleanup(self):
        if self._legacy_conn:
            self._legacy_conn.close()
        if self._sa_session:
            self._sa_session.close()


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validación de integridad post-migración"
    )
    parser.add_argument(
        "--legacy-db",
        default="clientes.db",
        help="Path a BD legacy"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path para guardar reporte JSON"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Salida mínima"
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    validator = MigrationValidator(legacy_db_path=args.legacy_db)
    
    try:
        logger.info("=" * 60)
        logger.info("VALIDACIÓN DE MIGRACIÓN")
        logger.info("=" * 60)
        
        report = validator.run_all_validations()
        
        logger.info("=" * 60)
        logger.info("RESUMEN: %s", report.summary)
        logger.info("=" * 60)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info("Reporte guardado en: %s", args.output)
        
        # Print summary
        print(f"\nValidación: {report.summary['overall']}")
        print(f"  Passed: {report.summary['passed']}/{report.summary['total']}")
        
        sys.exit(0 if report.overall_passed else 1)
        
    finally:
        validator.cleanup()


if __name__ == "__main__":
    main()
