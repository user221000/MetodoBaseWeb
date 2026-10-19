"""Shared professional follow-up adapter; no write, provider or implicit action."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.database.engine import get_db_readonly
from web.services.followup_service import get_followup
from web.services.permissions import has_permission, verify_permission

router = APIRouter(tags=['Seguimiento'])
logger = logging.getLogger(__name__)
PRIVATE = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}


@router.get('/estadisticas/seguimiento')
def followup(response: Response, limit: int = Query(50, ge=1, le=100),
             db: Session = Depends(get_db_readonly), usuario: dict = Depends(get_usuario_actual)):
    verify_permission(usuario, 'read', 'stats')
    verify_permission(usuario, 'read', 'cliente')
    # The persisted identity may be an ambiguous historical personal OWNER.
    # Role alone must never turn its personal records into a portfolio.
    if not usuario.get('team_gym_id') and usuario.get('tipo') != 'gym':
        raise HTTPException(403, {'code': 'professional_context_required',
            'message': 'Abre el contexto profesional para consultar el seguimiento.'}, headers=PRIVATE)
    try:
        body = get_followup(db, get_effective_gym_id(usuario), limit)
    except Exception as exc:
        logger.error('Follow-up unavailable class=%s', type(exc).__name__)
        # The web factory's legacy HTTPException handler drops exc.headers.
        # Preserve this endpoint's private, structured failure without changing
        # global handlers or inventing an empty successful result.
        return JSONResponse({'detail': {'code': 'followup_unavailable',
            'message': 'No fue posible consultar el seguimiento. Vuelve a intentar.'}}, status_code=503, headers=PRIVATE)
    body['capabilities'] = {'review_client': has_permission(usuario, 'read', 'cliente'),
                            'prepare_plan': has_permission(usuario, 'create', 'plan')}
    response.headers.update(PRIVATE)
    return body
