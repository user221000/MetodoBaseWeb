"""
web/routes/auth.py — Authentication endpoints (login, registro, refresh, logout, me).

Extracted from web/main_web.py (god function) for maintainability.
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from web.auth_deps import get_usuario_actual
from web.database.engine import get_db
from web.account_values import normalize_account_email
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"])


# ── Schemas ───────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class RegistroRequest(BaseModel):
    email: str
    password: str
    nombre: str
    apellido: str = ""
    tipo: str = "usuario"

class GoogleLoginRequest(BaseModel):
    credential: str
    tipo: str = "usuario"


# ── Helper: sync auth user → SQLAlchemy ───────────────────────────────────
# Extracted to web/sync_user.py — single source of truth.
from web.sync_user import sync_user_to_sa as _sync_user_to_sa  # noqa: E402


# ── Rate limit dependency ─────────────────────────────────────────────────

from web.middleware.rate_limiter import rate_limit_dependency

_login_rate_limit = [Depends(rate_limit_dependency(requests_per_minute=5, window_seconds=900, account_field="email"))]


def _primary_result(identity, *, remember=False, method="password"):
    """No token escapes before the factor/mint decision commits under User lock."""
    from web.database.engine import SessionLocal
    from web.services import mfa_service
    try:
        with SessionLocal() as db:
            result = mfa_service.login(db, identity, remember=remember, method=method)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Primary login unconfirmed class=%s", type(error).__name__)
        mfa_service.fail(503, "mfa_unconfirmed")
    return JSONResponse(jsonable_encoder(result), status_code=202 if result["mfa_required"] else 200,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/auth/login", dependencies=_login_rate_limit)
async def login_universal(data: LoginRequest, request: Request):
    """Password login resolves the same persisted identity as OAuth/refresh."""
    from web.auth import verificar_credenciales
    from web.services.auth_audit import log_auth_event_from_request, AuthEventType

    usuario = verificar_credenciales(
        data.email, data.password,
        ip=request.client.host if request.client else "unknown",
    )
    if usuario:
        response = _primary_result(usuario, remember=data.remember_me)
        if response.status_code == 200:
            await log_auth_event_from_request(
                AuthEventType.LOGIN_SUCCESS, request,
                gym_id=usuario.get("team_gym_id") or usuario["id"],
                user_id=usuario["id"],
                metadata={"tipo": usuario["tipo"], "role": usuario["role"], "remember_me": data.remember_me},
            )
        return response

    # Log login fallido
    await log_auth_event_from_request(
        AuthEventType.LOGIN_FAILED,
        request,
        gym_id=None,
        metadata={"email": data.email, "reason": "invalid_credentials"},
    )
    raise HTTPException(401, "Credenciales incorrectas.")


@router.post("/auth/google", dependencies=_login_rate_limit)
async def google_login(data: GoogleLoginRequest, request: Request):
    """
    Login / registro con Google.

    Recibe el credential (ID token) de Google Identity Services,
    lo verifica contra Google, y crea o busca el usuario en la BD.
    """
    import uuid
    from datetime import datetime, timezone
    from web.auth import identity_from_user
    from web.services.auth_audit import log_auth_event_from_request, AuthEventType

    from web.services.google_identity import verified_google_info
    google_info = await verified_google_info(data.credential)

    email = normalize_account_email(google_info["email"])
    nombre = google_info.get("given_name", google_info.get("name", "")).strip()
    apellido = google_info.get("family_name", "").strip()

    # Tipo válido
    tipo = data.tipo if data.tipo in ("usuario", "gym") else "usuario"

    # Buscar usuario existente via SQLAlchemy
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    from sqlalchemy.orm import Session as _SASession

    engine = get_engine()
    with _SASession(engine) as session:
        row = session.query(Usuario).filter(
            Usuario.email == email,
        ).first()

        if row:
            # Usuario existe — login
            usuario = identity_from_user(row, session)
            if not usuario:
                raise HTTPException(401, "Cuenta no disponible para iniciar sesión.")
        else:
            # Crear usuario nuevo
            uid = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            # Generar password hash aleatorio (el usuario no necesita password, usa Google)
            random_pw_hash = hash_password(uuid.uuid4().hex + uuid.uuid4().hex)
            new_user = Usuario(
                id=uid, email=email, password_hash=random_pw_hash,
                nombre=nombre, apellido=apellido, tipo=tipo,
                role=UserRole.OWNER if tipo == "gym" else UserRole.VIEWER,
                activo=True, fecha_registro=now,
            )
            session.add(new_user)
            session.commit()

            usuario = identity_from_user(new_user, session)

            # Auto-crear GymProfile si es gym
            if tipo == "gym":
                from web.database import repository as _repo
                from web.database.tenant_context import bind_verified_subject
                bind_verified_subject(session, uid)
                _repo.crear_gym_profile(session, uid, {"nombre_negocio": nombre}, initialize_memberships=True)
                session.commit()

    _sync_user_to_sa(usuario)
    response = _primary_result(usuario, remember=True, method="google")

    if response.status_code == 200:
        await log_auth_event_from_request(
            AuthEventType.LOGIN_SUCCESS,
            request,
            gym_id=usuario.get("id") if usuario["tipo"] == "gym" else None,
            user_id=usuario["id"],
            metadata={"tipo": usuario["tipo"], "source": "google"},
        )

    return response


@router.post("/auth/registro", dependencies=_login_rate_limit)
async def registro(data: RegistroRequest):
    from web.auth import crear_usuario, crear_token_pair

    tipo = data.tipo if data.tipo in ("usuario", "gym") else "usuario"

    try:
        usuario = crear_usuario(
            email=data.email,
            password=data.password,
            nombre=data.nombre,
            apellido=data.apellido,
            tipo=tipo,
        )
    except ValueError:
        raise HTTPException(400, {"code": "registration_invalid", "message": "No se pudo crear la cuenta. Revisa email, nombre y contraseña (mínimo 12 caracteres)."}) from None
    _sync_user_to_sa(usuario)
    tokens = crear_token_pair(usuario)

    # Auto-crear GymProfile si el tipo es gym
    if usuario["tipo"] == "gym":
        from web.database.engine import get_engine as _ge
        from sqlalchemy.orm import Session as _SASession
        from web.database import repository as _repo

        with _SASession(_ge()) as _s:
            from web.database.tenant_context import bind_verified_subject
            bind_verified_subject(_s, usuario["id"])
            _repo.crear_gym_profile(_s, usuario["id"], {"nombre_negocio": usuario["nombre"]}, initialize_memberships=True)
            _s.commit()

    # Email de bienvenida (background, no bloquea respuesta)
    from web.services import email_service

    email_service.send_welcome(usuario["email"], usuario["nombre"])

    return {
        "token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "tipo": usuario["tipo"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "message": "Cuenta creada exitosamente.",
    }


@router.post("/auth/refresh")
async def refresh_token(request: Request):
    """Rota un refresh token: devuelve nuevo par access + refresh."""
    from web.auth import rotar_refresh_token

    body = await request.json()
    old_refresh = body.get("refresh_token", "")
    if not old_refresh:
        raise HTTPException(400, "refresh_token requerido.")
    result = rotar_refresh_token(old_refresh)
    if not result:
        raise HTTPException(401, "Refresh token inválido, expirado o revocado.")
    return {
        "token": result["access_token"],
        "refresh_token": result["refresh_token"],
    }


@router.post("/auth/logout")
async def logout(usuario=Depends(get_usuario_actual)):
    """Revoca todas las sesiones access/refresh mediante su versión persistida."""
    from web.auth import revocar_refresh_tokens_usuario

    revocar_refresh_tokens_usuario(usuario["id"])
    return {"success": True, "message": "Sesión cerrada. Todas las sesiones revocadas."}


@router.get("/auth/me")
async def me(
    usuario=Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Retorna info del usuario actual incluyendo role, permisos y features del plan."""
    from web.services.permissions import get_user_permissions, get_role_display_name, UserRole
    from web.auth_deps import get_effective_gym_id
    from web.subscription_guard import _get_gym_plan, _get_plan_config

    role_str = usuario.get("role", "viewer")
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.VIEWER

    # Obtener plan y sus features
    gym_id = get_effective_gym_id(usuario)
    plan_name = _get_gym_plan(db, gym_id)
    plan_cfg = _get_plan_config(plan_name)

    return {
        **usuario,
        "role_display": get_role_display_name(role),
        "permissions": get_user_permissions(usuario),
        "plan": plan_name,
        "plan_features": {
            "preferencias_alimentos": plan_cfg.get("preferencias_alimentos", False),
            "gestion_suscripciones": plan_cfg.get("gestion_suscripciones", False),
            "max_registros_diarios": plan_cfg.get("max_registros_diarios", 0),
            "max_planes_por_cliente_dia": plan_cfg.get("max_planes_por_cliente_dia", 0),
            "max_clientes": plan_cfg.get("max_clientes", 0),
        },
    }
