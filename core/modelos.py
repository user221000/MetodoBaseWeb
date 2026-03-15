"""Modelo de datos: ClienteEvaluacion."""
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ClienteEvaluacion:
    """Modelo de datos para la evaluación de un cliente de gym."""
    
    # Datos básicos del cliente (REQUERIDOS)
    nombre: str | None = None
    telefono: str | None = None
    edad: int | None = None
    peso_kg: float | None = None
    estatura_cm: float | None = None
    grasa_corporal_pct: float | None = None
    nivel_actividad: str | None = None
    objetivo: str | None = None
    plantilla_tipo: str = "general"
    
    # ID único OPCIONAL (con defaults)
    id_cliente: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    
    # Preferencias y cálculos OPCIONALES
    factor_actividad: float = 1.2
    
    # Metadata OPCIONAL
    fecha_creacion: str = field(default_factory=lambda: datetime.now().isoformat())
    validado: bool = False
    errores: list = field(default_factory=list)
    
    # Cálculos del motor (Katch-McArdle) OPCIONALES
    masa_magra: float | None = None
    tmb: float | None = None
    get_total: float | None = None
    kcal_objetivo: float | None = None
    proteina_g: float | None = None
    grasa_g: float | None = None
    carbs_g: float | None = None
    kcal_proteína: float | None = None
    kcal_grasa: float | None = None
    kcal_carbs: float | None = None
    
    def __repr__(self) -> str:
        return (f"ClienteEvaluacion(id={self.id_cliente}, nombre={self.nombre}, "
                f"edad={self.edad}, peso={self.peso_kg}kg, estatura={self.estatura_cm}cm, "
                f"grasa={self.grasa_corporal_pct}%, actividad={self.nivel_actividad}, "
                f"objetivo={self.objetivo}, validado={self.validado})")
