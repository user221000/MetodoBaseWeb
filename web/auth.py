"""
web/auth.py — Sistema de autenticación para MetodoBase Web

- Usuarios almacenados en PostgreSQL via SQLAlchemy (producción/Railway)
- Contraseñas con bcrypt (passlib)
- Tokens: HMAC-SHA256 firmados (sin dependencias externas)
- Roles: 'gym' | 'usuario' | 'admin'

SECURITY: bcrypt es OBLIGATORIO. NO hay fallback inseguro.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import math
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from web.account_values import normalize_account_email, validate_new_password

_logger = logging.getLogger(__name__)

# ── Password Hashing — bcrypt OBLIGATORIO ────────────────────────────────────
# Intentamos importar bcrypt (nativo) o passlib.hash.bcrypt
# Si ninguno está disponible, FALLAMOS (no hay fallback inseguro)

_BCRYPT_AVAILABLE = False
_hash_pw = None
_verify_pw = None

try:
    import bcrypt as _bcrypt_lib
    
    def _hash_pw_bcrypt(pw: str) -> str:
        return _bcrypt_lib.hashpw(pw.encode("utf-8"), _bcrypt_lib.gensalt()).decode("utf-8")
    
    def _verify_pw_bcrypt(pw: str, hashed: str) -> bool:
        try:
            return _bcrypt_lib.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    
    _hash_pw = _hash_pw_bcrypt
    _verify_pw = _verify_pw_bcrypt
    _BCRYPT_AVAILABLE = True
    _logger.info("[AUTH] Using native bcrypt for password hashing")
    
except ImportError:
    try:
        from passlib.hash import bcrypt as _pl_bcrypt
        
        def _hash_pw_passlib(pw: str) -> str:
            return _pl_bcrypt.hash(pw)
        
        def _verify_pw_passlib(pw: str, hashed: str) -> bool:
            try:
                return _pl_bcrypt.verify(pw, hashed)
            except Exception:
                return False
        
        _hash_pw = _hash_pw_passlib
        _verify_pw = _verify_pw_passlib
        _BCRYPT_AVAILABLE = True
        _logger.info("[AUTH] Using passlib bcrypt for password hashing")
        
    except ImportError:
        _BCRYPT_AVAILABLE = False


def _ensure_bcrypt_available() -> None:
    """Falla inmediatamente si bcrypt no está disponible."""
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError(
            "❌ SECURITY ERROR: bcrypt no está disponible.\n"
            "   Instala con: pip install bcrypt\n"
            "   O: pip install passlib[bcrypt]\n"
            "   NO se permite autenticación sin bcrypt."
        )


def hash_password(password: str) -> str:
    """Hash password con bcrypt. Falla si bcrypt no disponible."""
    _ensure_bcrypt_available()
    return _hash_pw(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verifica password contra hash bcrypt. Falla si bcrypt no disponible."""
    _ensure_bcrypt_available()
    return _verify_pw(password, hashed)

# ── Configuración (delegada a config/settings.py) ─────────────────────────

def _get_secret_key() -> str:
    from web.settings import get_settings
    return get_settings().SECRET_KEY

def _get_access_expire_minutes() -> int:
    from web.settings import get_settings
    return get_settings().ACCESS_TOKEN_EXPIRE_MINUTES

def _get_refresh_expire_days() -> int:
    from web.settings import get_settings
    return get_settings().REFRESH_TOKEN_EXPIRE_DAYS

# Acceso lazy — se evalúa al primer uso, no al import
SECRET_KEY: str = ""  # se inicializa en init_auth()
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 7


def _get_session():
    """Get a SQLAlchemy session from the shared engine."""
    from web.database.engine import SessionLocal
    return SessionLocal()


def _get_models():
    """Lazy import to avoid circular imports."""
    from web.database.models import Usuario, RefreshToken
    return Usuario, RefreshToken


# ── Esquema ────────────────────────────────────────────────────────────────

def _crear_tablas() -> None:
    """No-op: Alembic migrations handle schema creation."""
    pass


def _seed_demo_users() -> None:
    """Crea usuarios demo si la tabla está vacía y METODOBASE_SEED_DEMO=1."""
    from web.settings import get_settings
    if get_settings().is_production:
        return  # Never seed in production
    if os.getenv("METODOBASE_SEED_DEMO", "") != "1":
        return
    Usuario, _ = _get_models()
    session = _get_session()
    try:
        count = session.query(Usuario).count()
        if count == 0:
            import secrets as _secrets
            demo_pw = _secrets.token_urlsafe(16)
            _logger.debug("Demo seed completed (password not logged for security)")
            now = datetime.now(timezone.utc)
            demos = [
                Usuario(id=str(uuid.uuid4()), email="gym@test.com", password_hash=hash_password(demo_pw),
                        nombre="Mi Gimnasio", apellido="", tipo="gym", activo=True, fecha_registro=now),
                Usuario(id=str(uuid.uuid4()), email="usuario@test.com", password_hash=hash_password(demo_pw),
                        nombre="Juan", apellido="Pérez", tipo="usuario", activo=True, fecha_registro=now),
            ]
            session.add_all(demos)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── API pública ────────────────────────────────────────────────────────────

def init_auth() -> None:
    """Inicializa BD de autenticación y siembra usuarios demo."""
    global SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
    SECRET_KEY = _get_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES = _get_access_expire_minutes()
    REFRESH_TOKEN_EXPIRE_DAYS = _get_refresh_expire_days()
    _crear_tablas()
    try:
        _seed_demo_users()
        _cleanup_expired_refresh_tokens()
    except Exception as e:
        # Tables might not exist yet on first deploy (before Alembic runs)
        _logger.warning("[AUTH] startup_cleanup_failed class=%s", type(e).__name__)


def crear_usuario(
    email: str,
    password: str,
    nombre: str,
    apellido: str = "",
    tipo: str = "usuario",
) -> dict:
    """
    Registra un nuevo usuario.

    Raises:
        ValueError: si el email ya está registrado o el tipo es inválido.
    """
    tipos_validos = {"gym", "usuario"}
    if tipo not in tipos_validos:
        raise ValueError(f"Tipo inválido: {tipo!r}")

    email = normalize_account_email(email)
    if not email or "@" not in email:
        raise ValueError("Email inválido.")
    validate_new_password(password)

    Usuario, _ = _get_models()
    from web.database.models import UserRole
    session = _get_session()
    try:
        existe = session.query(Usuario).filter(Usuario.email == email).first()
        if existe:
            raise ValueError("El email ya está registrado.")

        uid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user = Usuario(
            id=uid,
            email=email,
            password_hash=hash_password(password),
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            tipo=tipo,
            role=UserRole.OWNER if tipo == "gym" else UserRole.VIEWER,
            activo=True,
            fecha_registro=now,
        )
        session.add(user)
        session.commit()
    except ValueError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return _get_user_by_id(uid)


def verificar_credenciales(
    email: str,
    password: str,
    tipo_requerido: Optional[str] = None,
    ip: Optional[str] = None,
) -> Optional[dict]:
    """
    Verifica email + password.

    Args:
        tipo_requerido: si se indica, el usuario debe tener ese tipo (o 'admin').
        ip: Dirección IP del cliente (para audit logging).

    Returns:
        dict con datos del usuario, o None si las credenciales son inválidas.
    """
    email = normalize_account_email(email)
    Usuario, _ = _get_models()
    session = _get_session()
    try:
        row = session.query(Usuario).filter(
            Usuario.email == email,
            Usuario.activo == True,
        ).first()

        if not row:
            _logger.warning("[AUTH] login_failed reason=account_unavailable")
            return None

        if not verify_password(password, row.password_hash):
            _logger.warning("[AUTH] login_failed reason=invalid_credentials")
            return None

        if tipo_requerido and row.tipo not in (tipo_requerido, "admin"):
            _logger.warning("[AUTH] login_failed reason=account_type")
            return None

        identity = identity_from_user(row, session)
        if identity:
            _logger.info("[AUTH] login_success")
        return identity
    finally:
        session.close()


# ── Tokens HMAC ────────────────────────────────────────────────────────────

def _sign(payload_b64: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _make_token(payload: dict) -> str:
    """Genera token HMAC-SHA256: base64(payload).signature"""
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def _decode_token(token: str) -> Optional[dict]:
    """Decodifica y verifica firma. No valida expiración ni tipo."""
    if not isinstance(token, str) or not token or len(token) > 8192:
        return None
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected = _sign(payload_b64)
        if not hmac.compare_digest(sig, expected):
            return None
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def crear_access_token(usuario: dict, remember_me: bool = False) -> str:
    """Access breve; recordar sesión sólo prolonga el refresh revocable."""
    exp = time.time() + ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    # Extraer role para incluir en token
    role = usuario.get("role")
    if role is None:
        # Legacy: tipo='gym' o tipo='usuario' → role='owner'
        if usuario.get("tipo") in ("gym", "usuario"):
            role = "owner"
        else:
            role = "viewer"
    
    payload = {
        "id":     usuario["id"],
        "email":  usuario["email"],
        "nombre": usuario["nombre"],
        "tipo":   usuario["tipo"],
        "role":   role,
        "team_gym_id": usuario.get("team_gym_id"),  # Para multi-tenant
        "sv": usuario.get("session_version", 0),
        "iss": "metodobase",
        "aud": "metodobase-web",
        "v": 1,
        "exp":    exp,
        "type":   "access",
    }
    return _make_token(payload)


def crear_refresh_token(usuario: dict, remember_me: bool = False) -> str:
    """Genera refresh token. 7 días normal, 30 días si remember_me."""
    jti = str(uuid.uuid4())
    if remember_me:
        from web.settings import get_settings
        _s = get_settings()
        exp = time.time() + _s.REMEMBER_ME_REFRESH_DAYS * 86400
    else:
        exp = time.time() + REFRESH_TOKEN_EXPIRE_DAYS * 86400
    now = time.time()

    # Extraer role para incluir en token
    role = usuario.get("role")
    if role is None:
        if usuario.get("tipo") in ("gym", "usuario"):
            role = "owner"
        else:
            role = "viewer"

    payload = {
        "id":    usuario["id"],
        "email": usuario["email"],
        "tipo":  usuario["tipo"],
        "role":  role,
        "team_gym_id": usuario.get("team_gym_id"),
        "sv": usuario.get("session_version", 0),
        "iss": "metodobase",
        "aud": "metodobase-web",
        "v": 1,
        "exp":   exp,
        "type":  "refresh",
        "jti":   jti,
    }

    # Guardar en BD para poder revocar
    _, RefreshToken = _get_models()
    session = _get_session()
    try:
        rt = RefreshToken(jti=jti, user_id=usuario["id"], expires_at=exp, created_at=now)
        session.add(rt)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return _make_token(payload)


def crear_token_pair(usuario: dict, remember_me: bool = False) -> dict:
    """
    Genera par de tokens.
    
    Access siempre breve; remember_me sólo extiende el refresh.
    """
    return {
        "access_token": crear_access_token(usuario, remember_me),
        "refresh_token": crear_refresh_token(usuario, remember_me),
    }


def _valid_token_payload(payload: Optional[dict], token_type: str) -> bool:
    """Accept legacy epoch zero during migration; reject malformed/new contexts."""
    if not payload or payload.get("type") != token_type:
        return False
    expiry = payload.get("exp")
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not math.isfinite(expiry) or expiry <= time.time():
        return False
    if not isinstance(payload.get("id"), str) or not payload["id"]:
        return False
    if "v" in payload and payload.get("v") != 1:
        return False
    if payload.get("iss", "metodobase") != "metodobase" or payload.get("aud", "metodobase-web") != "metodobase-web":
        return False
    if "v" in payload and (payload.get("iss") != "metodobase" or payload.get("aud") != "metodobase-web"):
        return False
    version = payload.get("sv", 0)
    return type(version) is int and version >= 0


def _current_token_identity(payload: dict) -> Optional[dict]:
    """Always resolve live permissions; a changed tenant invalidates the token."""
    current = _get_user_by_id(payload["id"])
    if not current or current["session_version"] != payload.get("sv", 0):
        return None
    if current.get("team_gym_id") != payload.get("team_gym_id"):
        return None
    return current


def verificar_token(token: str) -> Optional[dict]:
    """
    Verifica access token. Rechaza refresh tokens, tokens sin type, y expirados.

    Returns:
        dict con payload (id, email, nombre, tipo, exp) o None si inválido.
    """
    payload = _decode_token(token)
    if not _valid_token_payload(payload, "access"):
        return None
    current = _current_token_identity(payload)
    return {**payload, **current} if current else None


def verificar_refresh_token(token: str) -> Optional[dict]:
    """
    Verifica refresh token: firma, expiración, tipo y no-revocado en BD.

    Returns:
        dict con payload o None si inválido/revocado.
    """
    payload = _decode_token(token)
    if not _valid_token_payload(payload, "refresh") or not _current_token_identity(payload):
        return None

    jti = payload.get("jti")
    if not jti:
        return None

    # Verificar que no esté revocado
    _, RefreshToken = _get_models()
    session = _get_session()
    try:
        rt = session.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if not rt or rt.revoked or rt.user_id != payload["id"] or rt.expires_at <= time.time():
            return None
    finally:
        session.close()

    return payload


def rotar_refresh_token(old_token: str) -> Optional[dict]:
    """
    Rota un refresh token: revoca el viejo, emite par nuevo.

    Si el token ya fue revocado (reuse detection), revoca TODOS los
    refresh tokens del usuario como medida de seguridad.

    Returns:
        dict con {access_token, refresh_token} o None si inválido.
    """
    payload = _decode_token(old_token)
    if not _valid_token_payload(payload, "refresh"):
        return None

    jti = payload.get("jti")
    user_id = payload.get("id")
    if not jti or not user_id:
        return None
    usuario = _current_token_identity(payload)
    if not usuario:
        return None

    with_conn_session = _get_session()
    _, RefreshToken = _get_models()
    try:
        # Atomic UPDATE: revoke token only if not already revoked
        result = with_conn_session.query(RefreshToken).filter(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at > time.time(),
            RefreshToken.revoked == False,
        ).update({"revoked": True})
        with_conn_session.commit()

        if result == 0:
            # Token already revoked — possible reuse attack
            # Revoke ALL tokens for this user as security measure
            Usuario, _ = _get_models()
            with_conn_session.query(Usuario).filter(Usuario.id == user_id).update(
                {Usuario.id: Usuario.id}, synchronize_session=False)
            with_conn_session.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
            ).update({"revoked": True})
            with_conn_session.query(Usuario).filter(Usuario.id == user_id).update(
                {Usuario.session_version: Usuario.session_version + 1}
            )
            with_conn_session.commit()
            _logger.warning("[AUTH] refresh_reuse action=sessions_revoked")
            return None
    except Exception:
        with_conn_session.rollback()
        raise
    finally:
        with_conn_session.close()

    # Obtener datos frescos del usuario desde BD
    usuario = _current_token_identity(payload)
    if not usuario:
        return None

    return crear_token_pair(usuario)


def revocar_refresh_tokens_usuario(user_id: str) -> None:
    """Revoca access y refresh en una transacción (logout/cambio de credenciales)."""
    Usuario, RefreshToken = _get_models()
    session = _get_session()
    try:
        # Same account -> refresh order as recovery and membership changes.
        session.query(Usuario).filter(Usuario.id == user_id).update(
            {Usuario.id: Usuario.id}, synchronize_session=False)
        session.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
        ).update({"revoked": True})
        session.query(Usuario).filter(Usuario.id == user_id).update(
            {Usuario.session_version: Usuario.session_version + 1}
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def identity_from_user(row, session) -> Optional[dict]:
    """Canonical persisted identity for password, Google, invite and refresh.

    Unknown roles and inactive/pending users never receive privileges. A team
    association is valid only while its gym owner remains active.
    """
    from web.database.models import UserRole, Usuario
    if not row.activo or row.invitation_token:
        return None
    try:
        role = UserRole(row.role).value
    except (ValueError, TypeError):
        return None
    if row.team_gym_id:
        owner = session.query(Usuario).filter(Usuario.id == row.team_gym_id, Usuario.activo.is_(True), Usuario.tipo == "gym").first()
        if not owner or role == "owner":
            return None
    return {
        "id": row.id, "email": row.email, "nombre": row.nombre,
        "apellido": row.apellido, "tipo": row.tipo, "role": role,
        "team_gym_id": row.team_gym_id, "session_version": row.session_version,
    }


def _get_user_by_id(user_id: str) -> Optional[dict]:
    """Obtiene usuario desde BD por ID."""
    Usuario, _ = _get_models()
    session = _get_session()
    try:
        row = session.query(Usuario).filter(
            Usuario.id == user_id,
            Usuario.activo == True,
        ).first()

        if not row:
            return None

        return identity_from_user(row, session)
    finally:
        session.close()


def _cleanup_expired_refresh_tokens() -> int:
    """Elimina refresh tokens expirados y revocados de la BD. Retorna count."""
    _, RefreshToken = _get_models()
    session = _get_session()
    try:
        from sqlalchemy import or_
        count = session.query(RefreshToken).filter(
            or_(
                RefreshToken.expires_at < time.time(),
                RefreshToken.revoked == True,
            )
        ).delete(synchronize_session=False)
        session.commit()
        if count > 0:
            _logger.info("[AUTH] Cleaned %d expired/revoked tokens", count)
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def cleanup_expired_tokens() -> int:
    """Public API: elimina refresh tokens expirados y revocados. Retorna count."""
    return _cleanup_expired_refresh_tokens()
