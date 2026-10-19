"""R12 transaction ownership, persisted principals and total-order account locks."""
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import logging
import re

from fastapi import HTTPException
from sqlalchemy import select,text,update
from sqlalchemy.exc import DBAPIError,IntegrityError

from web.account_values import normalize_account_email
from web.database.models import Usuario,UserRole
from web.database.tenant_context import bind_verified_subject,current_tenant

logger=logging.getLogger(__name__)
MAX_VERSION=2147483647
MAX_RESPONSE_BYTES=512*1024


def fail(status,code,message):
    raise HTTPException(status,{'code':code,'message':message})


def unavailable(kind='link'):
    fail(404,'member_'+kind+'_unavailable','No se encontro este recurso autorizado.')


def version(current,expected):
    if type(current) is not int or not 1<=current<=MAX_VERSION:
        fail(409,'member_state_requires_review','El estado requiere una revision autorizada.')
    if current!=expected:fail(409,'member_version_conflict','Este recurso cambio. Vuelve a consultarlo.')
    if current==MAX_VERSION:fail(409,'member_version_overflow','La version requiere una revision autorizada.')


def utc(value):
    if value is None:return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()


def clock(db,now=None):
    if now is not None:
        if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:raise ValueError('R12 requires an aware clock')
        return now.astimezone(timezone.utc)
    if db.get_bind().dialect.name=='postgresql':
        return db.scalar(text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")).replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def digest(token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):unavailable('invitation')
    return hashlib.sha256(('client-account-invite-v1:'+token).encode('ascii')).hexdigest()


def bounded(value):
    try:
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    except (TypeError,ValueError,UnicodeError,OverflowError):
        fail(409,'member_state_requires_review','El estado requiere una revision autorizada.')
    if len(raw)>MAX_RESPONSE_BYTES:fail(413,'member_response_limit','El resultado supera el volumen permitido.')
    return value


def rollback(db):
    try:db.rollback()
    except Exception as error:
        logger.error('Member rollback failed class=%s',type(error).__name__)
        return False
    return True


def commit(db):
    db.info['member_commit_attempted']=True
    db.commit()
    db.info['member_commit_confirmed']=True


def audit(db,actor,action,identity):
    from web.database.models import AuthAuditLog
    # This is durable security evidence in the same transaction. No bearer,
    # digest, destination address, URL, projection or provider detail is stored.
    db.add(AuthAuditLog(user_id=actor.id,event_type='client_link_'+action,
        event_metadata={'resource_id':identity,'protocol':'client_account_link_v1'}))


@contextmanager
def operation(db):
    """One fresh root transaction; no nested recovery or implicit final commit."""
    if db.in_transaction() or db.in_nested_transaction():
        fail(503,'member_transaction_unavailable','La operacion no esta disponible temporalmente.')
    db.info['member_commit_attempted']=False
    db.info['member_commit_confirmed']=False
    try:
        yield
    except Exception as error:
        confirmed=db.info.get('member_commit_confirmed',False)
        attempted=db.info.get('member_commit_attempted',False)
        clean=rollback(db)
        if isinstance(error,HTTPException) and clean:raise
        logger.error('Member operation failed class=%s',type(error).__name__)
        if not clean or attempted and not confirmed:
            fail(503,'member_link_reconciliation_required','No fue posible confirmar la operacion. Consulta tus vinculos antes de reintentar.')
        state=getattr(getattr(error,'orig',None),'pgcode',None)
        if state=='55P03':fail(409,'member_operation_busy','Otra operacion esta en curso. Vuelve a intentarlo.')
        if isinstance(error,IntegrityError):fail(409,'member_link_conflict','El recurso cambio o no admite esta asociacion.')
        if isinstance(error,DBAPIError) and state=='23514':fail(409,'member_state_conflict','No fue posible verificar este estado autorizado.')
        fail(503,'member_service_unavailable','La operacion no esta disponible temporalmente.')


def _load_user(db,identity):
    return db.scalar(select(Usuario).where(Usuario.id==identity).execution_options(populate_existing=True))


def canonical_gym(user):
    return bool(user is not None and user.tipo=='gym' and user.role==UserRole.OWNER and not user.team_gym_id
        and user.activo and user.deleted_at is None and user.invitation_token is None)


def valid_actor(user,parent=None):
    if (user is None or not user.activo or user.deleted_at is not None or user.invitation_token is not None
            or user.role not in set(UserRole) or type(user.session_version) is not int
            or not 0<=user.session_version<=MAX_VERSION):return False
    if user.role==UserRole.OWNER:return canonical_gym(user)
    if user.team_gym_id:return canonical_gym(parent)
    return user.tipo=='usuario'


def _claims(principal):
    if (not isinstance(principal,dict) or not isinstance(principal.get('id'),str) or not 1<=len(principal['id'])<=36
            or type(principal.get('session_version')) is not int):
        fail(401,'member_identity_unavailable','Inicia sesion nuevamente.')
    return principal['id'],principal['session_version']


def actor_snapshot(db,principal):
    identity,_=_claims(principal)
    actor=_load_user(db,identity)
    if actor is not None and actor.role==UserRole.OWNER and not canonical_gym(actor):
        fail(409,'member_context_requires_review','La autoridad de esta cuenta requiere una revision.')
    parent=_load_user(db,actor.team_gym_id) if actor is not None and actor.team_gym_id else None
    if not valid_actor(actor,parent):fail(401,'member_identity_unavailable','Inicia sesion nuevamente.')
    return actor


def bind_scope(db,identity):
    try:bind_verified_subject(db,identity)
    except ValueError:fail(403,'member_context_mismatch','Abre el contexto autorizado para esta operacion.')
    if db.get_bind().dialect.name=='postgresql':
        if db.scalar(text('SHOW transaction_isolation'))!='read committed':
            fail(503,'member_isolation_unavailable','La operacion no esta disponible temporalmente.')


def professional_scope(db,principal,allowed):
    actor=actor_snapshot(db,principal)
    gym=actor.team_gym_id or (actor.id if canonical_gym(actor) else None)
    if gym is None or actor.role not in allowed:
        fail(403,'member_permission_denied','No tienes permiso para esta operacion profesional.')
    bind_scope(db,gym)
    return actor,gym


def recipient_scope(db,principal):
    actor=actor_snapshot(db,principal)
    bind_scope(db,actor.id)
    return actor


def lock_contexts(db,principal,actor,gyms,*,write,require_eligible_gym=True):
    """All account IDs first, total order/NOWAIT; never add a parent afterwards."""
    identity,expected_sv=_claims(principal)
    parent_before=actor.team_gym_id
    gyms=set(gyms)
    required={identity,*gyms}
    if parent_before:required.add(parent_before)
    locked={}
    for key in sorted(required):
        if db.get_bind().dialect.name=='sqlite' and write:
            db.execute(update(Usuario).where(Usuario.id==key).values(id=Usuario.id).execution_options(synchronize_session=False))
        query=select(Usuario).where(Usuario.id==key).execution_options(populate_existing=True)
        if db.get_bind().dialect.name=='postgresql':query=query.with_for_update(read=not write,nowait=True)
        row=db.scalar(query)
        if row is None:unavailable()
        locked[key]=row
    current=locked[identity]
    recalculated={identity,*gyms}
    if current.team_gym_id:recalculated.add(current.team_gym_id)
    if recalculated!=required:
        fail(409,'member_context_changed','La pertenencia cambio. Vuelve a iniciar la operacion.')
    if current.session_version!=expected_sv or not valid_actor(current,locked.get(current.team_gym_id)):
        fail(401,'member_identity_unavailable','Inicia sesion nuevamente.')
    if require_eligible_gym and any(not canonical_gym(locked.get(gym)) for gym in gyms):unavailable()
    if (current_tenant.get() and current_tenant.get()!=db.info.get('tenant_id')):
        fail(403,'member_context_mismatch','Abre el contexto autorizado para esta operacion.')
    return current,{gym:locked[gym] for gym in gyms}


def lock_context(db,principal,actor,gym,*,write,require_eligible_gym=True):
    current,owners=lock_contexts(db,principal,actor,{gym},write=write,require_eligible_gym=require_eligible_gym)
    return current,owners[gym]


def require_professional_after_lock(actor,gym,allowed):
    if actor.role not in allowed or (actor.team_gym_id or (actor.id if canonical_gym(actor) else None))!=gym:
        fail(403,'member_permission_denied','No tienes permiso para esta operacion profesional.')


def install_proof(db,actor,token):
    if db.in_nested_transaction() or db.info.get('tenant_id')!=actor.id:
        fail(403,'member_context_mismatch','Abre el contexto autorizado para esta operacion.')
    hashed=digest(token)
    if actor.email!=normalize_account_email(actor.email):
        fail(409,'member_context_requires_review','La autoridad de esta cuenta requiere una revision.')
    if db.get_bind().dialect.name=='postgresql':
        db.execute(text("SELECT set_config('app.client_invitation_digest',:digest,true)"),{'digest':hashed})
    return hashed
