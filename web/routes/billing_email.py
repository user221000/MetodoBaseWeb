"""Authenticated, bounded email confirmation before subscription capabilities."""
from typing import Literal
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool
from web.auth_deps import get_usuario_actual
from web.services import billing_email_identity as identity
from web.services import billing_email_verification as service

MAX_BODY_BYTES = 4096
HEADERS = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'}
Action = Literal['gym_stripe_checkout', 'gym_stripe_subscribe', 'gym_mp_preference',
    'personal_stripe_checkout', 'personal_stripe_subscribe', 'personal_mp_preference',
    'gym_stripe_portal', 'personal_stripe_portal', 'legacy_stripe_checkout', 'legacy_mp_preference']


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def private(request):
            try:
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({'detail': error.detail}, status_code=error.status_code,
                    headers={**HEADERS, **(error.headers or {})})
            response.headers.update(HEADERS)
            return response
        return private


router = APIRouter(prefix='/billing/email-verification', tags=['Verificación de compra'], route_class=PrivateRoute)


class Begin(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Action
    plan: Literal['standard', 'gym_comercial', 'clinica', 'pro', 'manage']


class Verify(Begin):
    challenge: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')
    code: str = Field(min_length=6, max_length=6, pattern=r'^[0-9]{6}$')


class ConfirmedContact(BaseModel):
    """Current persisted contact; this response is not a payment authorization."""
    model_config = ConfigDict(extra='forbid')
    email_verification_required: Literal[False]
    email_verified: Literal[True]


class PendingCode(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email_verification_required: Literal[True]
    challenge: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')
    expires_at: str = Field(json_schema_extra={'format': 'date-time'})
    masked_email: str
    resend_after_seconds: int = Field(ge=1)


class VerificationGrant(BaseModel):
    model_config = ConfigDict(extra='forbid')
    verification_token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')
    expires_in_seconds: int = Field(ge=1)


def _documented_body(model):
    """Expose the same DTO while preserving bounded, duplicate-aware parsing.

    FastAPI cannot infer a body schema from a dependency reading Request.stream.
    Using a second Body dependency would bypass the transport-size boundary.
    """
    return {'requestBody': {'required': True, 'content': {'application/json': {
        'schema': model.model_json_schema()}}}}


_ERROR_RESPONSES = {
    400: {'description': 'Código incorrecto, agotado, reutilizado o vencido.'},
    401: {'description': 'Sesión ausente, revocada o cambiada.'},
    403: {'description': 'La cuenta no tiene permiso para esta operación.'},
    409: {'description': 'El contacto o la identidad cambió; iniciar una verificación nueva.'},
    413: {'description': 'Cuerpo mayor de 4096 bytes; no se procesa.'},
    415: {'description': 'Se requiere un único Content-Type application/json.'},
    422: {'description': 'JSON inválido, campos extra/duplicados o acción y plan incompatibles.'},
    429: {'description': 'Límite de intentos o reenvío; respetar Retry-After.'},
    503: {'description': 'Verificación o envío sin confirmar; no autoriza la compra.'},
}


def bounded(model):
    adapter = TypeAdapter(model)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate verification field')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite verification value')
    async def parse(request: Request):
        content_types = request.headers.getlist('content-type')
        if len(content_types) != 1 or content_types[0].split(';', 1)[0].strip().lower() != 'application/json':
            raise HTTPException(415, {'code': 'billing_email_invalid_input', 'message': 'Usa una solicitud JSON válida.'})
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BODY_BYTES:
                raise HTTPException(413, {'code': 'billing_email_body_limit', 'message': 'La solicitud es demasiado grande.'})
            raw.extend(chunk)
        try:
            value = adapter.validate_python(json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant))
        except (ValidationError, ValueError, TypeError, UnicodeError, RecursionError):
            raise HTTPException(422, {'code': 'billing_email_invalid_input', 'message': 'Revisa el plan y el código de seis cifras.'}) from None
        identity.validate_action_plan(value.action, value.plan)
        return value
    return parse


@router.post('/request', summary='Comprobar contacto o solicitar código para una compra',
    response_model=ConfirmedContact | PendingCode, responses=_ERROR_RESPONSES,
    openapi_extra=_documented_body(Begin),
    description='Usa el contacto persistido de la cuenta autenticada. Si sigue confirmado, '
        'no envía correo ni emite una autorización. En otro caso solicita un código '
        'de diez minutos con espera de reenvío. Las respuestas son privadas (no-store).')
async def request_verification(request: Request, actor=Depends(get_usuario_actual), data=Depends(bounded(Begin))):
    binding, email, _, verified = await run_in_threadpool(identity.owned_contact_snapshot, actor, request, data.action, data.plan)
    if verified:
        return {'email_verification_required': False, 'email_verified': True}
    result = await service.begin(binding, email, request)
    current, _, _ = await run_in_threadpool(identity.owned_snapshot, actor, request, data.action, data.plan)
    if current != binding:
        identity.fail(409, 'billing_email_identity_changed', 'La cuenta cambió. Solicita un nuevo código.')
    return result


@router.post('/verify', summary='Consumir código y confirmar el contacto de la compra',
    response_model=VerificationGrant, responses=_ERROR_RESPONSES,
    openapi_extra=_documented_body(Verify),
    description='Consume un código ASCII de seis cifras, de un solo uso y hasta cinco intentos. '
        'Confirma el contacto vigente y devuelve una prueba opaca de cinco minutos; '
        'MFA, permisos e intención exacta se revalidan antes del pago. No acredita un pago. '
        'Las respuestas son privadas (no-store).')
async def verify_code(request: Request, actor=Depends(get_usuario_actual), data=Depends(bounded(Verify))):
    binding, _, _ = await run_in_threadpool(identity.owned_snapshot, actor, request, data.action, data.plan)
    result = await service.verify(binding, data.challenge, data.code, request)
    await run_in_threadpool(identity.confirm_contact, actor, request, data.action, data.plan, binding)
    return result
