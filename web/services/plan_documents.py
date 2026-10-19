"""Authorized plan-specific private object reads and bounded legacy transition.

The caller supplies the authenticated effective gym, never a query parameter.
Both the plan and its client must belong to that gym. Legacy files are read
only below the configured private output root, with a bounded payload. New
references require ready metadata, owner, kind, size and SHA256 verification.
"""
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import and_, select

from web.constants import CARPETA_PLANES
from web.database.models import Cliente, PlanGenerado
from web.storage.objects import MAX_OBJECT_BYTES
from web.storage.objects import ObjectUnavailable
from web.services.private_objects import read_private_object


def read_plan_pdf(db, gym_id: str, plan_id: int) -> bytes:
    """Read exactly one owned, non-deleted plan, retaining inactive history.

    No commits, provider calls, path selection by clients, or fallback to the
    client's latest plan. Missing/foreign/deleted/unavailable results share a
    stable404 response; internal paths and filenames are never returned.
    """
    unavailable = HTTPException(404, {"code": "plan_pdf_unavailable",
        "message": "No se encontró el PDF de este plan."})
    plan = db.execute(select(PlanGenerado).join(Cliente, and_(
        Cliente.id_cliente == PlanGenerado.id_cliente, Cliente.gym_id == PlanGenerado.gym_id,
    )).where(PlanGenerado.id == plan_id, PlanGenerado.gym_id == gym_id,
        PlanGenerado.deleted_at.is_(None), Cliente.deleted_at.is_(None))).scalar_one_or_none()
    if plan is None:
        raise unavailable
    if plan.pdf_object_id:
        try:
            content, content_type = read_private_object(db, gym_id, plan.pdf_object_id, "plan_pdf")
            if content_type != "application/pdf" or not content.startswith(b"%PDF-"):
                raise unavailable
            return content
        except ObjectUnavailable:
            # A private reference is authoritative: never substitute legacy
            # bytes or a different plan when its object cannot be verified.
            raise unavailable from None
    if not plan.ruta_pdf:
        raise unavailable
    try:
        root = Path(CARPETA_PLANES).resolve(strict=True)
        original = Path(plan.ruta_pdf)
        path = original.resolve(strict=True)
        if not path.is_relative_to(root) or path == root or not path.is_file():
            raise unavailable
        for candidate in (original, *original.parents):
            if candidate.is_symlink():
                raise unavailable
            if candidate == root:
                break
        with path.open("rb") as source:
            content = source.read(MAX_OBJECT_BYTES + 1)
        if not content.startswith(b"%PDF-") or len(content) > MAX_OBJECT_BYTES:
            raise unavailable
        return content
    except (OSError, ValueError):
        raise unavailable from None
