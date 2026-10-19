"""Personal privacy export adapter; integration is gated by independent review."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_actual
from web.database.engine import get_db_readonly
from web.services.privacy_export import MAX_PAGE_SIZE, export_personal_data

router = APIRouter(tags=["Privacidad personal"])


def _uuid_cursor(value: str | None):
    if value is not None:
        UUID(value)
    # Stored UUIDs are String(36): case affects their lexical keyset order.
    # Validate syntax without reconstructing or normalizing an emitted cursor.
    return value


@router.get("/usuario/privacidad/exportar")
def export_personal(
    usuario: Annotated[dict, Depends(get_usuario_actual)],
    db: Annotated[Session, Depends(get_db_readonly)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 100,
    after_profile: Annotated[int | None, Query(ge=0)] = None,
    after_plan: Annotated[int | None, Query(ge=0)] = None,
    after_measurement: Annotated[int | None, Query(ge=0)] = None,
    after_purchase: Annotated[str | None, Query(min_length=36, max_length=36), AfterValidator(_uuid_cursor)] = None,
    after_generation: Annotated[str | None, Query(min_length=36, max_length=36), AfterValidator(_uuid_cursor)] = None,
):
    data = export_personal_data(db, usuario["id"], limit=limit, cursors={
        "profile": after_profile, "plan": after_plan, "measurement": after_measurement,
        "purchase": after_purchase, "generation": after_generation,
    })
    return JSONResponse(data, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": 'attachment; filename="metodobase-datos-personales.json"'})
