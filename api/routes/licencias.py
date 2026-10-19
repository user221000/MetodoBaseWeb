"""Authenticated adapters for licenses already issued to the gym owner."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_gym
from web.database.engine import get_db
from web.services import license_activation_service as licenses

router = APIRouter(tags=["Licencias"])


class ActivarLicenciaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clave: str = Field(..., min_length=10, max_length=255)
    hardware_id: str = Field(..., min_length=8, max_length=128)
    email: str = Field(..., min_length=5, max_length=120)


class LicenciaResponse(BaseModel):
    activa: bool
    plan: str
    max_clientes: int
    multi_usuario: bool
    expira: str | None


class EstadoLicenciaResponse(BaseModel):
    activa: bool
    plan: str
    dias_restantes: int | None
    revocada: bool


@router.post("/licencias/activar", response_model=LicenciaResponse)
def activar_licencia(req: ActivarLicenciaRequest, db: Session = Depends(get_db),
                     owner: dict = Depends(get_usuario_gym)):
    """Bind an issued key; prefixes, contact email and hardware grant no rights."""
    try:
        return licenses.activate(db, gym_id=owner["id"], key=req.clave,
                                 hardware_id=req.hardware_id, email=req.email)
    except licenses.LicenseError as error:
        raise HTTPException(error.status, detail={"code": error.code, "message": error.message}) from None


@router.get("/licencias/estado/{hardware_id}", response_model=EstadoLicenciaResponse)
def estado_licencia(hardware_id: str, db: Session = Depends(get_db),
                    owner: dict = Depends(get_usuario_gym)):
    """Read only the authenticated owner's explicitly associated activation."""
    try:
        return licenses.status(db, gym_id=owner["id"], hardware_id=hardware_id)
    except licenses.LicenseError as error:
        raise HTTPException(error.status, detail={"code": error.code, "message": error.message}) from None
