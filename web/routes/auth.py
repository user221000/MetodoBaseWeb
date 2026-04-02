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

_login_rate_limit = [Depends(rate_limit_dependency(requests_per_minute=5, window_seconds=900))]


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/auth/login", dependencies=_login_rate_limit)
async def login_universal(data: LoginRequest, request: Request):
    """
    Login universal: soporta owners (tipo=gym), usuarios regulares y team members.

    Busca primero en auth SQLite (legacy), luego en SQLAlchemy (team members).
    """
    from web.auth import verificar_credenciales, crear_token_pair, verify_password
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    from sqlalchemy.orm import Session as SASession
    from sqlalchemy import select
    from web.services.auth_audit import log_auth_event_from_request, AuthEventType

    _ip = request.client.host if request.client else "unknown"

    # 1. Intentar login tradicional (auth SQLite)
    usuario = verificar_credenciales(data.email, data.password, ip=_ip)

    if usuario:
        _sync_user_to_sa(usuario)
        tokens = crear_token_pair(usuario, remember_me=data.remember_me)

        await log_auth_event_from_request(
            AuthEventType.LOGIN_SUCCESS,
            request,
            gym_id=usuario.get("gym_id", usuario.get("id")),
            user_id=usuario["id"],
            metadata={"tipo": usuario["tipo"], "remember_me": data.remember_me, "source": "legacy"},
        )

        return {
            "token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "tipo": usuario["tipo"],
            "role": usuario.get("role", "owner" if usuario["tipo"] in ("gym", "usuario") else "viewer"),
            "nombre": f"{usuario['nombre']} {usuario['apellido']}".strip(),
            "email": usuario["email"],
        }

    # 2. Buscar en SQLAlchemy (team members invitados)
    engine = get_engine()
    with SASession(engine) as session:
        sa_user = session.execute(
            select(Usuario).where(
                Usuario.email == data.email.strip().lower(),
                Usuario.activo == True,
                Usuario.team_gym_id.isnot(None),
            )
        ).scalar_one_or_none()

        if sa_user:
            if verify_password(data.password, sa_user.password_hash):
                user_dict = {
                    "id": sa_user.id,
                    "email": sa_user.email,
                    "nombre": sa_user.nombre,
                    "apellido": sa_user.apellido,
                    "tipo": sa_user.tipo,
                    "role": sa_user.role.value if sa_user.role else UserRole.VIEWER.value,
                    "team_gym_id": sa_user.team_gym_id,
                }
                tokens = crear_token_pair(user_dict, remember_me=data.remember_me)

                await log_auth_event_from_request(
                    AuthEventType.LOGIN_SUCCESS,
                    request,
                    gym_id=sa_user.team_gym_id,
                    user_id=sa_user.id,
                    metadata={
                        "tipo": sa_user.tipo,
                        "role": user_dict["role"],
                        "remember_me": data.remember_me,
                        "source": "team_member",
                    },
                )

                return {
                    "token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "tipo": sa_user.tipo,
                    "role": sa_user.role.value if sa_user.role else UserRole.VIEWER.value,
                    "team_gym_id": sa_user.team_gym_id,
                    "nombre": f"{sa_user.nombre} {sa_user.apellido}".strip(),
                    "email": sa_user.email,
                }

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
    import httpx
    import uuid
    from datetime import datetime, timezone
    from config.settings import Settings
    from web.auth import crear_token_pair
    from web.services.auth_audit import log_auth_event_from_request, AuthEventType

    settings = Settings()
    client_id = settings.GOOGLE_CLIENT_ID.strip()
    if not client_id:
        raise HTTPException(501, "Google login no está configurado.")

    # Verificar el ID token con Google
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": data.credential},
        )

    if resp.status_code != 200:
        raise HTTPException(401, "Token de Google inválido.")

    google_info = resp.json()

    # Verificar audience (aud) = nuestro client_id
    if google_info.get("aud") != client_id:
        raise HTTPException(401, "Token de Google no pertenece a esta aplicación.")

    # Verificar email verificado
    if google_info.get("email_verified") != "true":
        raise HTTPException(401, "El email de Google no está verificado.")

    email = google_info["email"].strip().lower()
    nombre = google_info.get("given_name", google_info.get("name", "")).strip()
    apellido = google_info.get("family_name", "").strip()

    # Tipo válido
    tipo = data.tipo if data.tipo in ("usuario", "gym") else "usuario"

    # Buscar usuario existente via SQLAlchemy
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from sqlalchemy.orm import Session as _SASession

    engine = get_engine()
    with _SASession(engine) as session:
        row = session.query(Usuario).filter(
            Usuario.email == email,
            Usuario.activo == True,
        ).first()

        if row:
            # Usuario existe — login
            usuario = {
                "id": row.id,
                "email": row.email,
                "nombre": row.nombre,
                "apellido": row.apellido,
                "tipo": row.tipo,
                "role": "owner" if row.tipo in ("gym", "usuario") else "viewer",
            }
        else:
            # Crear usuario nuevo
            uid = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            # Generar password hash aleatorio (el usuario no necesita password, usa Google)
            random_pw_hash = hash_password(uuid.uuid4().hex + uuid.uuid4().hex)
            new_user = Usuario(
                id=uid, email=email, password_hash=random_pw_hash,
                nombre=nombre, apellido=apellido, tipo=tipo,
                activo=True, fecha_registro=now,
            )
            session.add(new_user)
            session.commit()

            usuario = {"id": uid, "email": email, "nombre": nombre, "apellido": apellido, "tipo": tipo, "role": "owner" if tipo in ("gym", "usuario") else "viewer"}

            # Auto-crear GymProfile si es gym
            if tipo == "gym":
                from web.database import repository as _repo
                _repo.crear_gym_profile(session, uid, {"nombre_negocio": nombre})
                session.commit()

    _sync_user_to_sa(usuario)
    tokens = crear_token_pair(usuario, remember_me=True)

    await log_auth_event_from_request(
        AuthEventType.LOGIN_SUCCESS,
        request,
        gym_id=usuario.get("id") if usuario["tipo"] == "gym" else None,
        user_id=usuario["id"],
        metadata={"tipo": usuario["tipo"], "source": "google", "google_email": email},
    )

    return {
        "token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "tipo": usuario["tipo"],
        "role": usuario.get("role", "viewer"),
        "nombre": f"{usuario['nombre']} {usuario.get('apellido', '')}".strip(),
        "email": usuario["email"],
    }


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
    except ValueError as e:
        raise HTTPException(400, str(e))
    _sync_user_to_sa(usuario)
    tokens = crear_token_pair(usuario)

    # Auto-crear GymProfile si el tipo es gym
    if usuario["tipo"] == "gym":
        from web.database.engine import get_engine as _ge
        from sqlalchemy.orm import Session as _SASession
        from web.database import repository as _repo

        with _SASession(_ge()) as _s:
            _repo.crear_gym_profile(_s, usuario["id"], {"nombre_negocio": usuario["nombre"]})
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
    """Revoca todos los refresh tokens del usuario."""
    from web.auth import revocar_refresh_tokens_usuario

    revocar_refresh_tokens_usuario(usuario["id"])
    return {"message": "Sesión cerrada. Todos los refresh tokens revocados."}


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


# ── Admin: fix user tipo ──────────────────────────────────────────────────

class FixUserTipoRequest(BaseModel):
    email: str
    nuevo_tipo: str  # "gym" | "usuario"
    admin_secret: str


@router.post("/admin/fix-user-tipo")
async def fix_user_tipo(data: FixUserTipoRequest, db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para corregir el tipo de un usuario en la DB.
    Requiere admin_secret == SECRET_KEY del entorno.
    """
    from web.settings import get_settings
    settings = get_settings()

    if data.admin_secret != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="No autorizado.")

    if data.nuevo_tipo not in ("gym", "usuario"):
        raise HTTPException(status_code=400, detail="nuevo_tipo debe ser 'gym' o 'usuario'.")

    from web.database.models import Usuario as UsuarioModel
    from web.auth import _get_session as _auth_session

    # Update en SQLAlchemy DB
    user_sa = db.query(UsuarioModel).filter(UsuarioModel.email == data.email.strip().lower()).first()
    if not user_sa:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    old_tipo = user_sa.tipo
    user_sa.tipo = data.nuevo_tipo
    db.commit()

    # Update en auth DB (puede ser el mismo engine o diferente)
    try:
        from web.database.models import Usuario as AuthUsuario
        auth_sess = _auth_session()
        auth_user = auth_sess.query(AuthUsuario).filter(AuthUsuario.email == data.email.strip().lower()).first()
        if auth_user and auth_user is not user_sa:
            auth_user.tipo = data.nuevo_tipo
            auth_sess.commit()
        auth_sess.close()
    except Exception:
        pass  # Same DB — already updated above

    logger.info("[ADMIN] fix-user-tipo: %s %s → %s", data.email, old_tipo, data.nuevo_tipo)

    return {
        "ok": True,
        "email": data.email,
        "tipo_anterior": old_tipo,
        "tipo_nuevo": data.nuevo_tipo,
        "mensaje": "Tipo actualizado. El usuario debe cerrar sesión y volver a iniciar.",
    }
