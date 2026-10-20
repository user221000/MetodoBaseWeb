"""First-party MFA API. Secrets are bounded, body-only and never reflected."""
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_actual
from web.browser_session import BrowserAuthRoute
from web.database.engine import SessionLocal
from web.middleware.rate_limiter import get_client_identifier
from web.services import mfa_service as service

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 32768
Proof = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Factor(Input):
    code: str | None = Field(None, pattern=r"^[0-9]{6}$")
    recovery_code: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{22}$")

    @model_validator(mode="after")
    def one_factor(self):
        if self.code is not None and self.recovery_code is not None:
            raise ValueError("One factor evidence only")
        return self


class Reauth(Input):
    password: str | None = Field(None, min_length=1, max_length=128)
    google_credential: str | None = Field(None, min_length=1, max_length=16384)

    @model_validator(mode="after")
    def one_primary(self):
        if bool(self.password) == bool(self.google_credential):
            raise ValueError("One primary proof required")
        return self


class Enrollment(Factor):
    reauthentication_token: Proof


class Confirmation(Input):
    enrollment_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    code: str = Field(pattern=r"^[0-9]{6}$")


class LoginVerification(Factor):
    challenge: Proof


class Change(Factor):
    reauthentication_token: Proof


class StepUp(Factor):
    method: str = Field(pattern=r"^(POST|PATCH|DELETE)$")
    path: str = Field(min_length=1, max_length=160)
    body: dict
    idempotency_key: str | None = Field(None, min_length=1, max_length=200)


class MfaRoute(BrowserAuthRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except service.HTTPException:
                raise
            except Exception as error:
                logger.error("MFA request unconfirmed class=%s", type(error).__name__)
                service.fail(503, "mfa_unconfirmed")
        return handle


def session():
    # Every service owns exactly one commit; no success-then-finalizer commit.
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            service.rollback(db)
            raise


async def parse(request, schema):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY_BYTES:
            service.fail(413, "mfa_input_too_large")
        raw.extend(chunk)
    try:
        # Reject duplicate keys and nonfinite values before schema validation.
        def pairs(values):
            output = {}
            for key, value in values:
                if key in output:
                    raise ValueError("Duplicate field")
                output[key] = value
            return output
        value = json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite input")))
        return schema.model_validate(value)
    except (ValueError, TypeError, RecursionError, ValidationError):
        service.fail(422, "mfa_invalid_input")


def access(request):
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        service.fail(401, "mfa_identity_unavailable")
    return value[7:]


async def mfa_rate_limit(request: Request):
    """MFA admission cannot be disabled by the legacy general limiter flag."""
    from web.rate_limiter_redis import check_rate_limit
    from web.settings import get_settings
    service.configuration()
    key = "rl:mfa31:" + request.url.path + ":" + get_client_identifier(request)
    allowed, info, _ = await check_rate_limit(key, 30, 300,
        use_redis=bool(get_settings().REDIS_URL), sensitive=True)
    if not allowed:
        raise service.HTTPException(429, {"code": "mfa_throttled", "message": "Espera antes de volver a verificar."},
            headers={"Retry-After": str(info["retry_after"])})


router = APIRouter(prefix="/auth/mfa", tags=["MFA"], route_class=MfaRoute,
    dependencies=[Depends(mfa_rate_limit)])


@router.get("/status")
def status(actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    return service.status(db, actor)


@router.post("/reauth")
async def reauth(request: Request, actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    data = await parse(request, Reauth)
    primary = None
    if data.google_credential:
        # Count the persisted actor before leaving for the provider. Neither a
        # new credential nor a different source IP resets this shared budget.
        service.admit_google_reauthentication(db, actor)
        from web.services.google_identity import verified_google_reauthentication
        primary = await verified_google_reauthentication(data.google_credential, now=service.instant())
    return service.reauthenticate(db, actor, access(request), password=data.password, google_identity=primary)


@router.post("/enroll")
async def enroll(request: Request, actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    data = await parse(request, Enrollment)
    return service.enroll(db, actor, access(request), data.reauthentication_token,
        code=data.code, recovery_code=data.recovery_code)


@router.post("/enroll/confirm")
async def confirm(request: Request, actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    data = await parse(request, Confirmation)
    return service.confirm_enrollment(db, actor, data.enrollment_id, data.code)


@router.post("/login/verify")
async def login_verify(request: Request, db: Session = Depends(session)):
    data = await parse(request, LoginVerification)
    return service.verify_login(db, data.challenge, code=data.code, recovery_code=data.recovery_code)


@router.post("/step-up")
async def step_up(request: Request, actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    data = await parse(request, StepUp)
    return service.issue_step_up(db, actor, access(request), data.method, data.path, data.body,
        idempotency_key=data.idempotency_key, code=data.code, recovery_code=data.recovery_code)


@router.post("/recovery-codes/regenerate")
async def regenerate(request: Request, actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    data = await parse(request, Change)
    return service.change_factor(db, actor, access(request), data.reauthentication_token,
        code=data.code, recovery_code=data.recovery_code)


@router.post("/revoke")
async def revoke(request: Request, actor=Depends(get_usuario_actual), db: Session = Depends(session)):
    data = await parse(request, Change)
    return service.change_factor(db, actor, access(request), data.reauthentication_token,
        revoke=True, code=data.code, recovery_code=data.recovery_code)
