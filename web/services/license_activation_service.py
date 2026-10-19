"""Persisted issuer authority for desktop activation; no subscription writes.

Unassociated legacy activations remain preserved for explicit reconciliation.
They cannot be claimed using a public hardware identifier or an email address.
"""
from datetime import datetime, timezone
import hashlib

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config.constantes import PLANES_LICENCIA
from web.database.models import GymLicense, LicenseActivation, Usuario, UserRole


class LicenseError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status, self.code, self.message = status, code, message


def utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def usable(issued: GymLicense, now: datetime) -> bool:
    return (bool(issued.is_active) and issued.revoked_at is None
            and issued.plan_tier in PLANES_LICENCIA
            and isinstance(issued.max_clients, int) and issued.max_clients >= 0
            and (issued.expires_at is None or utc(issued.expires_at) > now))


def activate(db: Session, *, gym_id: str, key: str, hardware_id: str, email: str) -> dict:
    """Serialize by persisted owner; an idempotent repeat never extends expiry."""
    owner_query = select(Usuario).where(
        Usuario.id == gym_id, Usuario.tipo == "gym", Usuario.role == UserRole.OWNER,
        Usuario.team_gym_id.is_(None), Usuario.activo.is_(True), Usuario.deleted_at.is_(None))
    if db.bind.dialect.name == "sqlite":
        # SQLite has no SELECT FOR UPDATE. Acquire its writer lock before reads.
        db.execute(update(Usuario).where(Usuario.id == gym_id).values(
            session_version=Usuario.session_version).execution_options(synchronize_session=False))
    owner = db.execute(owner_query.with_for_update()).scalar_one_or_none()
    if owner is None:
        raise LicenseError(403, "license_owner_required", "Se requiere la cuenta propietaria del gimnasio.")
    issued = db.execute(select(GymLicense).where(
        GymLicense.gym_id == gym_id, GymLicense.license_key == key).with_for_update()).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if issued is None or not usable(issued, now):
        raise LicenseError(400, "license_unavailable", "La licencia emitida no está disponible para esta cuenta.")
    existing = db.execute(select(LicenseActivation).where(
        LicenseActivation.gym_id == gym_id,
        LicenseActivation.hardware_id == hardware_id).with_for_update()).scalar_one_or_none()
    expiry = utc(issued.expires_at)
    if existing is not None:
        if existing.revocada or not existing.activa:
            raise LicenseError(409, "activation_revoked", "La activación requiere revisión antes de volver a utilizarse.")
        if existing.issued_license_id == issued.id and existing.expira is not None:
            expiry = min(utc(existing.expira), expiry) if expiry else utc(existing.expira)
            if expiry <= now:
                raise LicenseError(400, "activation_expired", "La activación venció. Utiliza una licencia renovada.")
        existing.issued_license_id = issued.id
        existing.clave_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        existing.email, existing.plan, existing.expira = email, issued.plan_tier, expiry
    else:
        existing = LicenseActivation(gym_id=gym_id, issued_license_id=issued.id,
            hardware_id=hardware_id, clave_hash=hashlib.sha256(key.encode("utf-8")).hexdigest(),
            email=email, plan=issued.plan_tier, activa=True, revocada=False, expira=expiry)
        db.add(existing)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise LicenseError(409, "device_binding_unavailable", "No se pudo vincular el dispositivo. Solicita revisión de la activación.") from None
    return {"activa": True, "plan": issued.plan_tier, "max_clientes": issued.max_clients,
            "multi_usuario": PLANES_LICENCIA[issued.plan_tier]["multi_usuario"],
            "expira": expiry.isoformat() if expiry else None}


def status(db: Session, *, gym_id: str, hardware_id: str) -> dict:
    pair = db.execute(select(LicenseActivation, GymLicense).join(GymLicense,
        LicenseActivation.issued_license_id == GymLicense.id).where(
            LicenseActivation.gym_id == gym_id, GymLicense.gym_id == gym_id,
            LicenseActivation.hardware_id == hardware_id)).one_or_none()
    if pair is None:
        raise LicenseError(404, "activation_unavailable", "Licencia no encontrada.")
    activation, issued = pair
    now = datetime.now(timezone.utc)
    dates = [utc(value) for value in (activation.expira, issued.expires_at) if value is not None]
    expiry = min(dates) if dates else None
    revoked = bool(activation.revocada or issued.revoked_at is not None)
    return {"activa": bool(activation.activa and not revoked and usable(issued, now)
                           and (expiry is None or expiry > now)),
            "plan": issued.plan_tier, "revocada": revoked,
            "dias_restantes": max(0, (expiry - now).days) if expiry else None}
