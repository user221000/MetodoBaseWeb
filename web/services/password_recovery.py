"""One-use credential recovery using existing account control-plane authority."""
from datetime import datetime,timedelta,timezone
import hashlib
import logging
import re
import secrets
from threading import Lock
from urllib.parse import urlsplit,urlunsplit,urlencode

from fastapi import HTTPException
from sqlalchemy import select,update

from web.account_values import normalize_account_email,validate_new_password
from web.database.models import Usuario,RefreshToken,AuthAuditLog,UserRole
from web.database.tenant_context import bind_verified_subject,current_tenant

logger=logging.getLogger(__name__)
RESET_LIFETIME=timedelta(minutes=30)
MAX_SESSION_VERSION=2147483647
_counter_lock=Lock()
_counters={key:0 for key in ('accepted','unconfirmed','ineligible','issue_failed','completed','notification_unconfirmed')}


def note(outcome):
    with _counter_lock:
        _counters[outcome]+=1


def recovery_status():
    with _counter_lock:
        return {'scope':'process','queue_durable':False,**_counters}


def clock(now=None):
    value=datetime.now(timezone.utc) if now is None else now
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Recovery requires an aware clock')
    return value.astimezone(timezone.utc)


def digest(token):
    return hashlib.sha256(('password-reset-v1:'+token).encode('ascii')).hexdigest()


def public_origin(settings):
    try:
        parsed=urlsplit(settings.BASE_URL)
        if (not parsed.hostname or parsed.username or parsed.password or parsed.path not in {'','/'}
                or parsed.query or parsed.fragment or any(ord(char)<33 for char in settings.BASE_URL)
                or '\\' in parsed.netloc or '%' in parsed.netloc
                or parsed.scheme not in {'https','http'}
                or (parsed.scheme=='http' and (settings.is_production or parsed.hostname not in {'127.0.0.1','localhost','::1'}))):
            raise ValueError('Recovery origin unavailable')
        _=parsed.port
        return urlunsplit((parsed.scheme,parsed.netloc,'','',''))
    except (ValueError,TypeError,AttributeError):
        raise HTTPException(503,{'code':'password_reset_service_unavailable','message':'La recuperacion no esta disponible temporalmente.'}) from None


def request_configuration(settings):
    origin=public_origin(settings)
    if not settings.RESEND_API_KEY or (settings.is_production and not settings.REDIS_URL):
        raise HTTPException(503,{'code':'password_reset_service_unavailable','message':'La recuperacion no esta disponible temporalmente.'})
    return origin


def _eligible(db,user):
    if (user is None or not user.activo or user.deleted_at is not None or user.invitation_token
            or user.tipo not in {'gym','usuario','admin'} or user.role not in set(UserRole)
            or type(user.session_version) is not int or not 0<=user.session_version<MAX_SESSION_VERSION):
        return False
    if user.team_gym_id:
        if user.role==UserRole.OWNER:
            return False
        return db.scalar(select(Usuario.id).where(Usuario.id==user.team_gym_id,Usuario.tipo=='gym',
            Usuario.activo.is_(True),Usuario.deleted_at.is_(None))) is not None
    return True


def _rollback(db):
    try:
        db.rollback()
    except Exception as error:
        logger.error('Recovery rollback failed class=%s',type(error).__name__)


def issue_request(email,origin,*,now=None,factory=None,sender=None):
    """Worker-only. Return no bearer; release DB resources before transport."""
    from web.database.engine import SessionLocal
    from web.services.email_service import send_password_reset
    factory=SessionLocal if factory is None else factory
    sender=send_password_reset if sender is None else sender
    if current_tenant.get():
        note('issue_failed')
        return
    instant=clock(now)
    try:
        with factory() as db:
            user=db.scalar(select(Usuario).where(Usuario.email==normalize_account_email(email)))
            if not _eligible(db,user):
                note('ineligible')
                return
            identity=user.id
            db.execute(update(Usuario).where(Usuario.id==identity).values(id=Usuario.id))
            user=db.scalar(select(Usuario).where(Usuario.id==identity).execution_options(populate_existing=True))
            if not _eligible(db,user) or user.email!=normalize_account_email(email):
                note('ineligible')
                return
            instant=clock(now)
            token=secrets.token_urlsafe(32)
            user.password_reset_hash=digest(token)
            user.password_reset_expires_at=instant+RESET_LIFETIME
            user.password_reset_session_version=user.session_version
            recipient,name=user.email,user.nombre
            db.add(AuthAuditLog(user_id=identity,event_type='password_reset_request',
                event_metadata={'channel':'email_link'},created_at=instant))
            db.commit()
        link=origin+'/auth/reset-password#'+urlencode({'token':token})
        try:
            accepted=sender(recipient,name,link)
        except Exception as error:
            logger.error('Recovery transport failed class=%s',type(error).__name__)
            accepted=False
        note('accepted' if accepted is True else 'unconfirmed')
    except Exception as error:
        # Context manager closes/rolls back on failure. Uncertain commit must
        # never trigger a send, nor a compensating password/account mutation.
        logger.error('Recovery issue failed class=%s',type(error).__name__)
        note('issue_failed')


def _unavailable():
    raise HTTPException(400,{'code':'password_reset_unavailable','message':'El enlace no esta disponible. Solicita uno nuevo.'})


def _valid_state(db,user,instant):
    if not _eligible(db,user) or user.password_reset_expires_at is None:
        return False
    expires=user.password_reset_expires_at
    expires=expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires.astimezone(timezone.utc)
    return expires>instant and user.password_reset_session_version==user.session_version


def consume(db,token,new_password,*,now=None):
    """Caller supplies a local non-autocommitting Session; one atomic COMMIT."""
    try:
        try:
            validate_new_password(new_password)
        except ValueError:
            raise HTTPException(422,{'code':'password_reset_invalid_input','message':'Revisa la contraseña nueva.'}) from None
        if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
            _unavailable()
        instant=clock(now)
        hashed=digest(token)
        user=db.scalar(select(Usuario).where(Usuario.password_reset_hash==hashed))
        if not _valid_state(db,user,instant):
            _unavailable()
        identity,version=user.id,user.session_version
        # The email bearer, not an input email/tenant, supplies the subject.
        try:
            bind_verified_subject(db,identity)
        except ValueError:
            _unavailable()
        from web.auth import hash_password
        password_hash=hash_password(new_password)
        db.execute(update(Usuario).where(Usuario.id==identity).values(id=Usuario.id))
        user=db.scalar(select(Usuario).where(Usuario.id==identity).execution_options(populate_existing=True))
        instant=clock(now)
        if not _valid_state(db,user,instant) or user.password_reset_hash!=hashed or user.session_version!=version:
            _unavailable()
        recipient,name=user.email,user.nombre
        result=db.execute(update(Usuario).where(Usuario.id==identity,Usuario.password_reset_hash==hashed,
            Usuario.session_version==version,Usuario.password_reset_session_version==version,
            Usuario.password_reset_expires_at>instant,Usuario.activo.is_(True),Usuario.deleted_at.is_(None),
            Usuario.invitation_token.is_(None)).values(password_hash=password_hash,session_version=version+1,
            password_reset_hash=None,password_reset_expires_at=None,password_reset_session_version=None)
            .execution_options(synchronize_session=False))
        if result.rowcount!=1:
            _unavailable()
        db.execute(update(RefreshToken).where(RefreshToken.user_id==identity).values(revoked=True))
        db.add(AuthAuditLog(user_id=identity,event_type='password_reset_complete',
            event_metadata={'channel':'email_link'},created_at=instant))
        db.commit()
        note('completed')
        return recipient,name
    except HTTPException:
        _rollback(db)
        raise
    except Exception as error:
        logger.error('Recovery consume failed class=%s',type(error).__name__)
        _rollback(db)
        raise HTTPException(503,{'code':'password_reset_unconfirmed',
            'message':'No pudimos confirmar el cambio. Intenta iniciar sesion con la nueva contraseña o pide otro enlace.'}) from None


def notify_changed(email,name):
    from web.services.email_service import send_password_changed
    try:
        accepted=send_password_changed(email,name)
    except Exception as error:
        logger.error('Recovery notification failed class=%s',type(error).__name__)
        accepted=False
    if accepted is not True:
        note('notification_unconfirmed')
