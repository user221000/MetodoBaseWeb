"""
web/routes/gym_profile.py — Perfil del gimnasio: datos, logo y branding.

Endpoints:
    GET  /api/gym/profile       — Obtener perfil del gym autenticado
    PUT  /api/gym/profile       — Actualizar perfil del gym
    POST /api/gym/logo          — Subir logo del gym (imagen)
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.database.engine import get_db, get_db_readonly
from web.database import repository as repo
from web.services.permissions import verify_permission
from web.routes._utils import get_gym_id
from web.constants import UPLOAD_ALLOWED_IMAGE_EXTENSIONS, UPLOAD_MAX_LOGO_SIZE_BYTES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gym", tags=["GymProfile"])

_ALLOWED_EXTENSIONS = UPLOAD_ALLOWED_IMAGE_EXTENSIONS
_MAX_LOGO_SIZE = UPLOAD_MAX_LOGO_SIZE_BYTES


class GymProfileUpdate(BaseModel):
    nombre_negocio: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=50)
    direccion: Optional[str] = Field(None, max_length=500)
    ciudad: Optional[str] = Field(None, max_length=150)
    estado: Optional[str] = Field(None, max_length=100)
    pais: Optional[str] = Field(None, max_length=100)
    color_primario: Optional[str] = Field(None, max_length=7)
    color_secundario: Optional[str] = Field(None, max_length=7)
    sitio_web: Optional[str] = Field(None, max_length=500)
    rfc: Optional[str] = Field(None, max_length=20)
    instagram: Optional[str] = Field(None, max_length=255)
    facebook: Optional[str] = Field(None, max_length=255)
    tiktok: Optional[str] = Field(None, max_length=255)


@router.get("/profile", summary="Obtener perfil del gym")
def obtener_perfil(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "gym_profile")
    gym_id = get_gym_id(usuario)
    profile = repo.obtener_gym_profile(db, gym_id)
    if not profile:
        # Auto-crear perfil vacío
        profile = repo.crear_gym_profile(db, gym_id)
    return profile


@router.put("/profile", summary="Actualizar perfil del gym")
def actualizar_perfil(
    data: GymProfileUpdate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "gym_profile")
    gym_id = get_gym_id(usuario)
    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(400, "No hay campos para actualizar")
    profile = repo.actualizar_gym_profile(db, gym_id, update_dict)
    return {"success": True, "profile": profile}


@router.post("/logo", summary="Subir logo del gym")
async def subir_logo(
    file: UploadFile = File(..., description="Imagen del logo (PNG/JPG/WebP, máx 2MB)"),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "gym_profile")
    gym_id = get_gym_id(usuario)

    # Validar extensión
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Formato no permitido. Use: {', '.join(_ALLOWED_EXTENSIONS)}")

    content = await file.read(_MAX_LOGO_SIZE + 1)
    from web.services.gym_logos import normalize_logo
    from web.services.private_objects import publish_pending_object, mark_object_ready
    from web.storage.objects import ObjectUnavailable
    from web.database.models import GymProfile
    try:
        normalized, content_type = await run_in_threadpool(normalize_logo, content, ext)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    try:
        descriptor = await run_in_threadpool(publish_pending_object, gym_id, "gym_logo", normalized, content_type)
        object_id = mark_object_ready(db, gym_id, descriptor, "gym_logo")
        profile = db.query(GymProfile).filter_by(gym_id=gym_id).with_for_update().first()
        if profile is None:
            profile = GymProfile(gym_id=gym_id)
            db.add(profile)
        profile.logo_object_id = object_id
        db.flush()
        # Confirm the reference before reporting success. Old objects and legacy
        # files remain available for explicit migration/retention reconciliation.
        db.commit()
    except ObjectUnavailable:
        raise HTTPException(503, {"code": "logo_storage_unavailable",
            "message": "No fue posible guardar el logo. Vuelve a consultar la configuración."}) from None
    return {"success": True, "logo_url": "/api/gym/logo", "has_private_logo": True}


@router.get("/logo", summary="Leer logo privado del gym")
def obtener_logo(db: Session = Depends(get_db_readonly), usuario: dict = Depends(get_usuario_actual)):
    verify_permission(usuario, "read", "gym_profile")
    from web.database.models import GymProfile
    from web.services.private_objects import read_private_object
    from web.storage.objects import ObjectUnavailable
    gym_id = get_gym_id(usuario)
    profile = db.query(GymProfile).filter_by(gym_id=gym_id).first()
    if profile is None or not profile.logo_object_id:
        raise HTTPException(404, "Logo no disponible")
    try:
        content, content_type = read_private_object(db, gym_id, profile.logo_object_id, "gym_logo")
    except ObjectUnavailable:
        raise HTTPException(404, "Logo no disponible") from None
    return Response(content, media_type=content_type, headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
    })


# ── Planes de suscripción (precios configurables) ────────────────────────────

class PlanSuscripcionUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    precio: Optional[float] = Field(None, ge=0)
    moneda: Optional[str] = Field(None, max_length=10)
    activo: Optional[bool] = None


@router.get("/planes-suscripcion", summary="Listar planes de suscripción del gym")
def listar_planes(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "gym_profile")
    gym_id = get_gym_id(usuario)
    planes = repo.listar_planes_suscripcion(db, gym_id)
    return {"planes": planes}


@router.put("/planes-suscripcion/{plan_id}", summary="Actualizar precio de un plan")
def actualizar_plan(
    plan_id: int,
    data: PlanSuscripcionUpdate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "update", "gym_profile")
    gym_id = get_gym_id(usuario)
    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(400, "No hay campos para actualizar")
    result = repo.actualizar_plan_suscripcion(db, gym_id, plan_id, update_dict)
    if not result:
        raise HTTPException(404, "Plan no encontrado")
    return {"success": True, "plan": result}
