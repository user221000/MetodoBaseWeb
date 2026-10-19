"""
web/services/auth_audit.py — Authentication Audit Logging Service

Servicio para logging detallado de eventos de autenticación y seguridad.
Registra en la tabla auth_audit_log para compliance y detective controls.

Eventos registrados:
- login_success / login_failed
- logout
- password_change
- password_reset_request
- password_reset_complete
- token_refresh
- mfa_enabled / mfa_disabled (futuro)
- account_locked / account_unlocked (futuro)

Uso:
    from web.services.auth_audit import log_auth_event, AuthEventType
    
    # En login exitoso:
    log_auth_event(
        event_type=AuthEventType.LOGIN_SUCCESS,
        gym_id=user["gym_id"],
        user_id=user["id"],
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        request_id=request.state.request_id,
        metadata={"method": "password", "remember_me": True}
    )
"""
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from web.database.engine import SessionLocal
from web.database.models import AuthAuditLog

logger = logging.getLogger(__name__)


# ── Event Types ───────────────────────────────────────────────────────────

class AuthEventType(str, Enum):
    """Tipos de eventos de autenticación."""
    
    # Login/Logout
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    
    # Password management
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    
    # Token management
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"
    
    # Account management (futuro)
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


# ── Service Functions ─────────────────────────────────────────────────────

def log_auth_event(
    event_type: AuthEventType,
    gym_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> None:
    """
    Registra un evento de autenticación en la tabla auth_audit_log.
    
    Args:
        event_type: Tipo de evento (ver AuthEventType)
        gym_id: ID del gym al que pertenece el usuario
        user_id: ID del usuario (None si login fallido)
        ip_address: IP del cliente
        user_agent: User-Agent del cliente
        request_id: ID de la request (para correlación con logs)
        metadata: Datos adicionales en formato JSON
        db: Sesión SQLAlchemy (opcional, se crea una si no se provee)
    
    Examples:
        # Login exitoso
        log_auth_event(
            AuthEventType.LOGIN_SUCCESS,
            gym_id=1,
            user_id=42,
            ip_address="192.168.1.1",
            metadata={"method": "password", "remember_me": True}
        )
        
        # Login fallido
        log_auth_event(
            AuthEventType.LOGIN_FAILED,
            gym_id=1,
            ip_address="192.168.1.1",
            metadata={"email": "test@example.com", "reason": "invalid_password"}
        )
    """
    should_close = db is None
    try:
        # Crear o usar sesión existente
        if db is None:
            db = SessionLocal()
        
        # Crear registro de auditoría
        audit_log = AuthAuditLog(
            gym_id=gym_id,
            user_id=user_id,
            event_type=event_type.value,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            event_metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info("Auth audit persisted event=%s", event_type.value)
    
    except Exception as e:
        logger.error("Auth audit failed class=%s", type(e).__name__)
        # No propagar el error - el logging de auditoría no debe romper el flujo
        if should_close and db is not None:
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error("Auth audit rollback_failed class=%s", type(rollback_error).__name__)
    finally:
        if should_close and db is not None:
            try:
                db.close()
            except Exception as close_error:
                logger.error("Auth audit close_failed class=%s", type(close_error).__name__)


def get_recent_login_attempts(
    email: str,
    since_minutes: int = 15,
    db: Optional[Session] = None,
) -> list[AuthAuditLog]:
    """
    Obtiene intentos de login recientes para un email.
    
    Útil para detectar patrones de fuerza bruta.
    
    Args:
        email: Email del usuario
        since_minutes: Ventana temporal en minutos
        db: Sesión SQLAlchemy
        
    Returns:
        Lista de registros de auditoría (login_success y login_failed)
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
        
        from sqlalchemy import cast, String, func
        from web.database.engine import get_engine
        
        engine = get_engine()
        is_postgres = "postgresql" in str(engine.url)
        
        if is_postgres:
            email_filter = AuthAuditLog.event_metadata["email"].astext == email
        else:
            email_filter = func.json_extract(AuthAuditLog.event_metadata, "$.email") == email
        
        logs = db.query(AuthAuditLog)\
            .filter(
                AuthAuditLog.event_type.in_(["login_success", "login_failed"]),
                AuthAuditLog.created_at >= cutoff,
                email_filter
            )\
            .order_by(AuthAuditLog.created_at.desc())\
            .all()
        
        return logs
    
    finally:
        if should_close:
            db.close()


def get_login_stats_for_gym(
    gym_id: str,
    since_days: int = 7,
    db: Optional[Session] = None,
) -> Dict[str, int]:
    """
    Estadísticas de login para un gym.
    
    Args:
        gym_id: ID del gym
        since_days: Ventana temporal en días
        db: Sesión SQLAlchemy
        
    Returns:
        {
            "total_logins": 150,
            "failed_logins": 10,
            "unique_ips": 8,
            "unique_users": 5
        }
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        
        logs = db.query(AuthAuditLog)\
            .filter(
                AuthAuditLog.gym_id == gym_id,
                AuthAuditLog.event_type.in_(["login_success", "login_failed"]),
                AuthAuditLog.created_at >= cutoff
            )\
            .all()
        
        total_logins = sum(1 for log in logs if log.event_type == "login_success")
        failed_logins = sum(1 for log in logs if log.event_type == "login_failed")
        unique_ips = len(set(log.ip_address for log in logs if log.ip_address))
        unique_users = len(set(log.user_id for log in logs if log.user_id))
        
        return {
            "total_logins": total_logins,
            "failed_logins": failed_logins,
            "unique_ips": unique_ips,
            "unique_users": unique_users,
        }
    
    finally:
        if should_close:
            db.close()


# ── Helper for FastAPI ────────────────────────────────────────────────────

async def log_auth_event_from_request(
    event_type: AuthEventType,
    request,  # FastAPI Request object
    gym_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Helper para logging de auditoría desde un request de FastAPI.
    
    Extrae automáticamente IP, user-agent, request_id del request.
    
    Example:
        @app.post("/api/auth/login")
        async def login(data: LoginRequest, request: Request):
            user = verificar_credenciales(data.email, data.password)
            if user:
                await log_auth_event_from_request(
                    AuthEventType.LOGIN_SUCCESS,
                    request,
                    gym_id=user["gym_id"],
                    user_id=user["id"],
                    metadata={"remember_me": data.remember_me}
                )
    """
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, "request_id", None)
    
    log_auth_event(
        event_type=event_type,
        gym_id=gym_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        metadata=metadata,
    )
