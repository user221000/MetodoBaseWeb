"""Pydantic schemas para MetodoBase API v2."""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from utils.validadores import RANGO_EDAD, RANGO_PESO, RANGO_ESTATURA, RANGO_GRASA
from web.profile_schemas import NutritionValidationMixin

_NIVELES = {"nula", "leve", "moderada", "intensa"}
_OBJETIVOS = {"deficit", "mantenimiento", "superavit"}


class ClienteCreate(NutritionValidationMixin):
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre completo")
    telefono: Optional[str] = Field(None, description="Teléfono 10 dígitos")
    email: Optional[str] = Field(None, description="Correo electrónico")
    edad: int = Field(..., ge=RANGO_EDAD[0], le=RANGO_EDAD[1], description=f"Edad en años ({RANGO_EDAD[0]}–{RANGO_EDAD[1]})")
    sexo: Optional[str] = Field(None, description="M / F / Otro")
    peso_kg: float = Field(..., ge=RANGO_PESO[0], le=RANGO_PESO[1], description=f"Peso en kg ({RANGO_PESO[0]}–{RANGO_PESO[1]})")
    estatura_cm: float = Field(..., ge=RANGO_ESTATURA[0], le=RANGO_ESTATURA[1], description=f"Estatura en cm ({RANGO_ESTATURA[0]}–{RANGO_ESTATURA[1]})")
    grasa_corporal_pct: Optional[float] = Field(None, ge=RANGO_GRASA[0], le=RANGO_GRASA[1], description=f"% grasa corporal ({RANGO_GRASA[0]}–{RANGO_GRASA[1]})")
    nivel_actividad: str = Field(..., description="nula | leve | moderada | intensa")
    objetivo: str = Field(..., description="deficit | mantenimiento | superavit")
    notas: Optional[str] = Field(None, max_length=500)
    alimentos_excluidos: Optional[list[str]] = Field(None, description="Lista de alimentos a excluir del plan")
    fecha_suscripcion: Optional[datetime] = Field(None, description="Fecha de inicio de suscripción")
    fecha_fin_suscripcion: Optional[datetime] = Field(None, description="Fecha de fin de suscripción")

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v.title()

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if not v or v.strip() == "":
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) not in (10, 12):
            raise ValueError("Teléfono debe tener 10 dígitos")
        return digits

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or v.strip() == "":
            return None
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v.strip()):
            raise ValueError("Email inválido")
        return v.strip().lower()

    @field_validator("sexo")
    @classmethod
    def validar_sexo(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip()
        mapping = {"m": "M", "f": "F", "otro": "Otro", "OTRO": "Otro"}
        normalized = mapping.get(v, mapping.get(v.lower()))
        if normalized is None:
            raise ValueError("Sexo debe ser M, F, u Otro")
        return normalized

    @field_validator("nivel_actividad")
    @classmethod
    def validar_nivel(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in _NIVELES:
            raise ValueError(f"nivel_actividad debe ser uno de: {sorted(_NIVELES)}")
        return v

    @field_validator("objetivo")
    @classmethod
    def validar_objetivo(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in _OBJETIVOS:
            raise ValueError(f"objetivo debe ser uno de: {sorted(_OBJETIVOS)}")
        return v


class ClienteUpdate(NutritionValidationMixin):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = None
    email: Optional[str] = None
    edad: Optional[int] = Field(None, ge=RANGO_EDAD[0], le=RANGO_EDAD[1])
    sexo: Optional[str] = None
    peso_kg: Optional[float] = Field(None, ge=RANGO_PESO[0], le=RANGO_PESO[1])
    estatura_cm: Optional[float] = Field(None, ge=RANGO_ESTATURA[0], le=RANGO_ESTATURA[1])
    grasa_corporal_pct: Optional[float] = Field(None, ge=RANGO_GRASA[0], le=RANGO_GRASA[1])
    nivel_actividad: Optional[str] = None
    objetivo: Optional[str] = None
    notas: Optional[str] = Field(None, max_length=500)
    alimentos_excluidos: Optional[list[str]] = Field(None, description="Lista de alimentos a excluir del plan")
    fecha_suscripcion: Optional[datetime] = None
    fecha_fin_suscripcion: Optional[datetime] = None
    plantilla_tipo: Optional[str] = Field(None, description="menu_fijo | opciones | general")

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v.title()

    validar_telefono = field_validator("telefono")(classmethod(ClienteCreate.validar_telefono.__func__))
    validar_email = field_validator("email")(classmethod(ClienteCreate.validar_email.__func__))

    @field_validator("nivel_actividad")
    @classmethod
    def validar_nivel(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in _NIVELES:
            raise ValueError(f"nivel_actividad debe ser uno de: {sorted(_NIVELES)}")
        return v

    @field_validator("objetivo")
    @classmethod
    def validar_objetivo(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in _OBJETIVOS:
            raise ValueError(f"objetivo debe ser uno de: {sorted(_OBJETIVOS)}")
        return v


_TIPOS_PLAN = {"menu_fijo", "opciones"}


class PlanRequest(BaseModel):
    id_cliente: str = Field(..., min_length=1, description="ID del cliente")
    plan_numero: int = Field(1, ge=1, le=9999, description="Número de plan para rotación")
    tipo_plan: str = Field("menu_fijo", description="menu_fijo | opciones")

    @field_validator("tipo_plan")
    @classmethod
    def validar_tipo_plan(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in _TIPOS_PLAN:
            raise ValueError(f"tipo_plan debe ser uno de: {sorted(_TIPOS_PLAN)}")
        return v
