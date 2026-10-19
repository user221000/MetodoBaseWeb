"""
scripts/etl_mapping.py — Mapeo ETL y transformaciones para migración.

FASE 3 del plan de consolidación de BD.

Define:
- Mapeo de campos legacy → SA
- Transformaciones de datos
- Validadores de integridad
- Funciones de conversión
"""
import re
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Field Mapping Definitions ───────────────────────────────────────────────

@dataclass
class FieldMapping:
    """Define mapeo de un campo legacy a SA."""
    legacy_name: str
    sa_name: str
    transform: Optional[Callable[[Any], Any]] = None
    default: Any = None
    required: bool = False
    validator: Optional[Callable[[Any], bool]] = None
    notes: str = ""


@dataclass  
class TableMapping:
    """Define mapeo completo de una tabla legacy a SA."""
    legacy_table: str
    sa_table: str
    fields: List[FieldMapping]
    key_field: str
    multi_tenant_field: str = "gym_id"
    multi_tenant_default: str = "gym_default"  # Para registros sin gym


# ── Transformadores ─────────────────────────────────────────────────────────

def normalize_whitespace(value: str) -> str:
    """Normaliza espacios en blanco."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def normalize_name(value: str) -> str:
    """Normaliza nombre: trim, title case."""
    if value is None:
        return ""
    return normalize_whitespace(value).title()


def normalize_phone(value: str) -> str:
    """Normaliza teléfono: solo dígitos + código país."""
    if value is None:
        return ""
    digits = re.sub(r'\D', '', str(value))
    if digits and not digits.startswith('52'):
        digits = '52' + digits
    return digits


def normalize_email(value: str) -> str:
    """Normaliza email: lowercase, trim."""
    if value is None:
        return ""
    return str(value).strip().lower()


def parse_fecha(value: Any) -> Optional[datetime]:
    """Parsea fecha desde varios formatos."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    
    logger.warning("No se pudo parsear fecha: %s", value)
    return None


def bool_to_int(value: Any) -> int:
    """Convierte bool a int."""
    if value is None:
        return 0
    return 1 if value else 0


def int_to_bool(value: Any) -> bool:
    """Convierte int a bool."""
    if value is None:
        return False
    return bool(int(value))


def safe_float(value: Any) -> Optional[float]:
    """Convierte a float de forma segura."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """Convierte a int de forma segura."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def sexo_normalizer(value: str) -> str:
    """Normaliza campo sexo."""
    if value is None:
        return "M"
    v = str(value).upper().strip()
    if v in ("M", "MASCULINO", "MALE", "H", "HOMBRE"):
        return "M"
    if v in ("F", "FEMENINO", "FEMALE", "MUJER"):
        return "F"
    return "M"  # Default


def nivel_actividad_normalizer(value: str) -> str:
    """Normaliza nivel de actividad."""
    if value is None:
        return "moderado"
    v = str(value).lower().strip()
    
    mapping = {
        "sedentario": "sedentario",
        "ligero": "ligero",
        "ligeramente activo": "ligero",
        "moderado": "moderado",
        "moderadamente activo": "moderado",
        "activo": "activo",
        "muy activo": "muy_activo",
        "muy_activo": "muy_activo",
        "extra activo": "extra_activo",
        "extra_activo": "extra_activo",
    }
    
    return mapping.get(v, "moderado")


def objetivo_normalizer(value: str) -> str:
    """Normaliza objetivo nutricional."""
    if value is None:
        return "mantener"
    v = str(value).lower().strip()
    
    mapping = {
        "perder peso": "perder_peso",
        "perder_peso": "perder_peso",
        "bajar de peso": "perder_peso",
        "deficit": "perder_peso",
        "déficit": "perder_peso",
        "mantener": "mantener",
        "mantenimiento": "mantener",
        "ganar musculo": "ganar_musculo",
        "ganar_musculo": "ganar_musculo",
        "ganar músculo": "ganar_musculo",
        "volumen": "ganar_musculo",
        "superavit": "ganar_musculo",
        "superávit": "ganar_musculo",
    }
    
    return mapping.get(v, "mantener")


# ── Validadores ─────────────────────────────────────────────────────────────

def validate_not_empty(value: Any) -> bool:
    """Valida que no esté vacío."""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    return True


def validate_positive(value: Any) -> bool:
    """Valida que sea positivo."""
    if value is None:
        return False
    try:
        return float(value) > 0
    except:
        return False


def validate_peso(value: Any) -> bool:
    """Valida peso razonable (30-300 kg)."""
    if value is None:
        return True  # Opcional
    try:
        v = float(value)
        return 30 <= v <= 300
    except:
        return False


def validate_estatura(value: Any) -> bool:
    """Valida estatura razonable (100-250 cm)."""
    if value is None:
        return True
    try:
        v = float(value)
        return 100 <= v <= 250
    except:
        return False


def validate_edad(value: Any) -> bool:
    """Valida edad razonable (1-120)."""
    if value is None:
        return True
    try:
        v = int(value)
        return 1 <= v <= 120
    except:
        return False


def validate_grasa_corporal(value: Any) -> bool:
    """Valida % grasa corporal (3-60%)."""
    if value is None:
        return True
    try:
        v = float(value)
        return 3 <= v <= 60
    except:
        return False


def validate_email_format(value: Any) -> bool:
    """Valida formato de email básico."""
    if value is None or value == "":
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(value)))


def validate_phone_format(value: Any) -> bool:
    """Valida formato de teléfono (10+ dígitos)."""
    if value is None or value == "":
        return True
    digits = re.sub(r'\D', '', str(value))
    return len(digits) >= 10


# ── Table Mappings ──────────────────────────────────────────────────────────

CLIENTE_MAPPING = TableMapping(
    legacy_table="clientes",
    sa_table="clientes",
    key_field="id_cliente",
    fields=[
        FieldMapping("id_cliente", "id_cliente", required=True, validator=validate_not_empty),
        FieldMapping("nombre", "nombre", normalize_name, required=True, validator=validate_not_empty),
        FieldMapping("telefono", "telefono", normalize_phone, validator=validate_phone_format),
        FieldMapping("email", "email", normalize_email, validator=validate_email_format),
        FieldMapping("edad", "edad", safe_int, validator=validate_edad),
        FieldMapping("sexo", "sexo", sexo_normalizer),
        FieldMapping("peso_kg", "peso_kg", safe_float, validator=validate_peso),
        FieldMapping("estatura_cm", "estatura_cm", safe_float, validator=validate_estatura),
        FieldMapping("grasa_corporal_pct", "grasa_corporal_pct", safe_float, validator=validate_grasa_corporal),
        FieldMapping("masa_magra_kg", "masa_magra_kg", safe_float),
        FieldMapping("nivel_actividad", "nivel_actividad", nivel_actividad_normalizer),
        FieldMapping("objetivo", "objetivo", objetivo_normalizer),
        FieldMapping("plantilla_tipo", "plantilla_tipo", lambda x: x or "general"),
        FieldMapping("fecha_registro", "fecha_registro", parse_fecha),
        FieldMapping("ultimo_plan", "ultimo_plan", parse_fecha),
        FieldMapping("total_planes_generados", "total_planes_generados", safe_int, default=0),
        FieldMapping("activo", "activo", int_to_bool, default=True),
        FieldMapping("notas", "notas", normalize_whitespace),
        # gym_id se añade automáticamente
    ]
)


PLAN_MAPPING = TableMapping(
    legacy_table="planes_generados",
    sa_table="planes_generados",
    key_field="id",
    fields=[
        # Nota: 'id' no se mapea directamente (AUTOINCREMENT)
        FieldMapping("id_cliente", "id_cliente", required=True),
        FieldMapping("fecha_generacion", "fecha_generacion", parse_fecha),
        FieldMapping("tmb", "tmb", safe_float),
        FieldMapping("get_total", "get_total", safe_float),
        FieldMapping("kcal_objetivo", "kcal_objetivo", safe_float),
        FieldMapping("kcal_real", "kcal_real", safe_float),
        FieldMapping("proteina_g", "proteina_g", safe_float),
        FieldMapping("carbs_g", "carbs_g", safe_float),
        FieldMapping("grasa_g", "grasa_g", safe_float),
        FieldMapping("objetivo", "objetivo", objetivo_normalizer),
        FieldMapping("nivel_actividad", "nivel_actividad", nivel_actividad_normalizer),
        FieldMapping("plantilla_tipo", "plantilla_tipo", lambda x: x or "general"),
        FieldMapping("tipo_plan", "tipo_plan", lambda x: x or "menu_fijo"),
        FieldMapping("ruta_pdf", "ruta_pdf"),
        FieldMapping("desviacion_maxima_pct", "desviacion_maxima_pct", safe_float),
        FieldMapping("peso_en_momento", "peso_en_momento", safe_float),
        FieldMapping("grasa_en_momento", "grasa_en_momento", safe_float),
    ]
)


ESTADISTICAS_MAPPING = TableMapping(
    legacy_table="estadisticas_gym",
    sa_table="estadisticas_gym",  # Puede migrar a gym_profiles
    key_field="id",
    fields=[
        FieldMapping("fecha", "fecha", parse_fecha),
        FieldMapping("total_clientes", "total_clientes", safe_int),
        FieldMapping("planes_generados_dia", "planes_generados_dia", safe_int),
        FieldMapping("clientes_activos", "clientes_activos", safe_int),
    ]
)


# ── ETL Functions ───────────────────────────────────────────────────────────

@dataclass
class TransformResult:
    """Resultado de transformación de un registro."""
    success: bool
    data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def transform_record(
    source: Dict[str, Any],
    mapping: TableMapping,
    gym_id: Optional[str] = None,
) -> TransformResult:
    """
    Transforma un registro usando el mapeo definido.
    
    Args:
        source: Registro fuente (legacy)
        mapping: Definición de mapeo
        gym_id: gym_id a asignar (multi-tenant)
    
    Returns:
        TransformResult con datos transformados y errores/warnings
    """
    result = TransformResult(success=True, data={})
    
    for field_map in mapping.fields:
        value = source.get(field_map.legacy_name, field_map.default)
        
        # Aplicar transformación
        if field_map.transform and value is not None:
            try:
                value = field_map.transform(value)
            except Exception as e:
                result.warnings.append(
                    f"Error transformando {field_map.legacy_name}: {e}"
                )
                value = field_map.default
        
        # Validar
        if field_map.required and (value is None or value == ""):
            result.errors.append(f"Campo requerido vacío: {field_map.legacy_name}")
            result.success = False
        
        if field_map.validator and value is not None:
            if not field_map.validator(value):
                result.warnings.append(
                    f"Validación falló para {field_map.legacy_name}: {value}"
                )
        
        result.data[field_map.sa_name] = value
    
    # Añadir gym_id si aplica
    if mapping.multi_tenant_field:
        result.data[mapping.multi_tenant_field] = gym_id or mapping.multi_tenant_default
    
    return result


def transform_batch(
    records: List[Dict[str, Any]],
    mapping: TableMapping,
    gym_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[TransformResult]]:
    """
    Transforma un batch de registros.
    
    Returns:
        Tuple de (registros transformados exitosos, resultados con errores)
    """
    success = []
    errors = []
    
    for record in records:
        result = transform_record(record, mapping, gym_id)
        if result.success:
            success.append(result.data)
        else:
            errors.append(result)
    
    return success, errors


# ── Data Quality Functions ──────────────────────────────────────────────────

def checksum_record(record: Dict[str, Any], key_fields: List[str]) -> str:
    """Genera checksum de un registro para comparación."""
    values = [str(record.get(k, "")) for k in sorted(key_fields)]
    content = "|".join(values)
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()


def find_duplicates(
    records: List[Dict[str, Any]],
    key_field: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """Encuentra registros duplicados por campo clave."""
    seen = {}
    duplicates = {}
    
    for record in records:
        key = record.get(key_field)
        if key in seen:
            if key not in duplicates:
                duplicates[key] = [seen[key]]
            duplicates[key].append(record)
        else:
            seen[key] = record
    
    return duplicates


def validate_referential_integrity(
    clientes: List[Dict[str, Any]],
    planes: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Valida integridad referencial entre tablas."""
    cliente_ids = {c.get("id_cliente") for c in clientes}
    
    orphan_planes = []
    for plan in planes:
        id_cliente = plan.get("id_cliente")
        if id_cliente and id_cliente not in cliente_ids:
            orphan_planes.append(id_cliente)
    
    return {
        "orphan_plan_cliente_ids": list(set(orphan_planes)),
        "total_orphans": len(orphan_planes),
    }


def generate_migration_report(
    source_counts: Dict[str, int],
    transformed_counts: Dict[str, int],
    error_counts: Dict[str, int],
) -> str:
    """Genera reporte de migración."""
    lines = [
        "=" * 60,
        "REPORTE DE MIGRACIÓN ETL",
        "=" * 60,
        f"Timestamp: {datetime.now().isoformat()}",
        "",
        "RESUMEN POR TABLA:",
        "-" * 40,
    ]
    
    for table in source_counts:
        src = source_counts.get(table, 0)
        trans = transformed_counts.get(table, 0)
        err = error_counts.get(table, 0)
        pct = (trans / src * 100) if src > 0 else 0
        
        lines.extend([
            f"  {table}:",
            f"    Source:       {src:>8}",
            f"    Transformed:  {trans:>8} ({pct:.1f}%)",
            f"    Errors:       {err:>8}",
            "",
        ])
    
    lines.extend([
        "=" * 60,
    ])
    
    return "\n".join(lines)


# ── Convenience ─────────────────────────────────────────────────────────────

def get_mapping_for_table(table_name: str) -> Optional[TableMapping]:
    """Obtiene el mapeo para una tabla."""
    mappings = {
        "clientes": CLIENTE_MAPPING,
        "planes_generados": PLAN_MAPPING,
        "estadisticas_gym": ESTADISTICAS_MAPPING,
    }
    return mappings.get(table_name)


def list_available_mappings() -> List[str]:
    """Lista tablas con mapeo definido."""
    return ["clientes", "planes_generados", "estadisticas_gym"]
