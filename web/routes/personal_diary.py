"""Authenticated personal diary; bounded streamed inputs, no implicit commits."""
from datetime import date
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, ValidationError

from web.auth_deps import get_usuario_actual
from web.personal_diary_schemas import DiaryPatch
from web.services.personal_diary_persistence import patch_diary_day, read_diary_day, read_diary_range
from web.services.personal_diary_service import _clock, local_today

router = APIRouter(tags=['Diario personal'])
MAX_OPERATION_BYTES = 16 * 1024
_PATCH = TypeAdapter(DiaryPatch)
_HEADERS = {'Cache-Control':'no-store', 'Referrer-Policy':'no-referrer', 'X-Content-Type-Options':'nosniff'}


def _operation_schema():
    schema = _PATCH.json_schema()
    definitions = schema.pop('$defs', {})
    def inline(value):
        if isinstance(value, list):
            return [inline(item) for item in value]
        if not isinstance(value, dict):
            return value
        if '$ref' in value:
            return inline(definitions[value['$ref'].rsplit('/', 1)[-1]])
        return {key:inline(item) for key,item in value.items()
            if key != 'mapping'}  # Discriminator propertyName remains; refs are inlined.
    return inline(schema)


def diary_session():
    """Only patch_diary_day owns COMMIT; reads and dependency exit never commit."""
    from web.database.engine import SessionLocal
    with SessionLocal() as db:
        yield db


def calendar_date(value: str) -> date:
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Expected ISO date')
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, {'code':'invalid_diary_day', 'message':'Elige una fecha valida con formato AAAA-MM-DD.'}) from None


async def operation_body(request: Request):
    """Stop reading at the first over-limit chunk, before JSON/DTO parsing."""
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk) > MAX_OPERATION_BYTES:
            raise HTTPException(413, {'code':'diary_body_limit', 'message':'La solicitud supera el volumen permitido.'})
        raw.extend(chunk)
    try:
        return _PATCH.validate_json(raw)
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(422, {'code':'invalid_diary_operation', 'message':'Revisa los campos de la operacion.'}) from None


@router.get('/usuario/diario')
def calendar_range(start: str | None = None, end: str | None = None,
                   usuario=Depends(get_usuario_actual), db=Depends(diary_session)):
    instant = _clock(None)
    if start is None and end is None:
        first = last = local_today(instant)
    elif start is None or end is None:
        raise HTTPException(422, {'code':'invalid_diary_range', 'message':'Indica las dos fechas del periodo.'})
    else:
        first, last = calendar_date(start), calendar_date(end)
    return JSONResponse(read_diary_range(db, usuario['id'], first, last, now=instant), headers=_HEADERS)


@router.get('/usuario/diario/{day}')
def calendar_day(day: str, usuario=Depends(get_usuario_actual), db=Depends(diary_session)):
    return JSONResponse(read_diary_day(db, usuario['id'], calendar_date(day)), headers=_HEADERS)


@router.patch('/usuario/diario/{day}', openapi_extra={'requestBody':{'required':True,
    'content':{'application/json':{'schema':_operation_schema()}}}})
def patch_day(day: str, usuario=Depends(get_usuario_actual), db=Depends(diary_session), operation=Depends(operation_body)):
    return JSONResponse(patch_diary_day(db, usuario['id'], calendar_date(day), operation), headers=_HEADERS)
