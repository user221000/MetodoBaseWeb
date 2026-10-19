"""Explicit password + current factor + Google subject association.

Admission commits before provider I/O; no lock/transaction spans the await.
Only one confirmed transaction publishes the binding, intent consumption and
session revocation. No token, contact update, account creation or email merge.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hmac
import logging
import re
import secrets
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from web.database.models import AuthExternalIdentity, GoogleLinkIntent
from web.services import mfa_service as mfa
from web.services.google_identity import ISSUER, VerifiedGooglePrimary, bound_user_id
from web.services.mfa_crypto import access_digest, opaque_digest

logger = logging.getLogger(__name__)
PURPOSE = "google_link"


def fail(status, code):
    raise HTTPException(status, {"code":code,"message":{
        "google_link_required":"Inicia sesion con tu contrasena o recupera tu cuenta para vincular Google.",
        "google_link_unconfirmed":"No pudimos confirmar el resultado. Inicia sesion de nuevo para consultar el estado.",
        "google_link_conflict":"No se puede confirmar este vinculo. Consulta el estado de tu cuenta.",
        "google_link_verification_failed":"No pudimos verificar esta solicitud.",
        "google_link_session_version_exhausted":"La cuenta requiere revision antes de cambiar una identidad de acceso.",
    }.get(code,"No se pudo confirmar este vinculo de acceso.")})


def commit(db):
    try:
        db.info["google_link_commit_attempted"] = True
        db.commit()
    except IntegrityError:
        rollback(db)
        fail(409,"google_link_conflict")
    except Exception as error:
        logger.error("Google link commit unconfirmed class=%s",type(error).__name__)
        rollback(db)
        fail(503,"google_link_unconfirmed")


def rollback(db):
    try:
        db.rollback()
    except Exception as error:
        logger.error("Google link rollback unconfirmed class=%s",type(error).__name__)
        fail(503,"google_link_unconfirmed")


@contextmanager
def _write_conflicts(db):
    """Classify constraint races across every flush in an owned write.

    Rollback must succeed before publishing a conflict. Rollback uncertainty
    remains 503; this boundary never retries, re-queries or adopts a winner.
    """
    try:
        yield
    except IntegrityError:
        rollback(db)
        fail(409,"google_link_conflict")


def close_owned_session(db):
    """Cleanup only a newly owned Google Session, before publishing a response."""
    try:
        db.close()
    except Exception as error:
        logger.error("Google owned-session close unavailable class=%s",type(error).__name__)
        try:
            db.invalidate()
        except Exception as invalidation:
            logger.error("Google owned-session invalidation unavailable class=%s",type(invalidation).__name__)
        # Even an HTTPException raised by a faulty cleanup is uncertainty,
        # not the HTTP result of the already executed business operation.
        raise RuntimeError("Google owned-session cleanup unconfirmed") from None


def _actor(db, expected, access, now):
    user, identity = mfa.lock_actor(db,expected)
    now=mfa.instant(now)
    claims = mfa._locked_access(access,user,identity,now)
    if user.session_version >= mfa.MAX_SV:
        fail(409,"google_link_session_version_exhausted")
    return user,claims,now


def admit(db, expected, access, *, phase, now=None):
    """Every attempt counts durably even if Google, factor, CAS or SQL fails."""
    if phase not in {"start","confirm","unlink"}:
        raise ValueError("Closed link budget purpose")
    user,_,now=_actor(db,expected,access,now)
    row=mfa.credential(db,user.id,create=True)
    mfa._budget(row,"google_link:"+phase,now,failure=True)
    commit(db)


def _binding(db,issuer,subject):
    return db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.issuer==issuer,
        AuthExternalIdentity.subject==subject).execution_options(populate_existing=True))


def _local_primary(db,user,row,command,now):
    from web.auth import verify_password
    # Knowing this password demonstrates the usable independent local primary;
    # a generated unknown Google-only password cannot pass by its mere presence.
    if not verify_password(command.password,user.password_hash):
        fail(401,"google_link_verification_failed")
    if row.enabled_at is not None:
        mfa.verify_factor(db,row,code=command.code,recovery_code=command.recovery_code,
            purpose="google_link",now=now)
    elif command.code is not None or command.recovery_code is not None:
        fail(422,"google_link_invalid_input")


def start(db, expected, access, command, primary, *, now=None):
    user,claims,now=_actor(db,expected,access,now)
    row=mfa.credential(db,user.id,create=True)
    _local_primary(db,user,row,command,now)
    if (not isinstance(primary,VerifiedGooglePrimary) or primary.issuer!=ISSUER
            or not 0 <= (now-primary.authenticated_at).total_seconds() < mfa.PROOF_TTL.total_seconds()):
        fail(401,"google_link_verification_failed")
    existing=_binding(db,primary.issuer,primary.subject)
    if existing is not None and (existing.user_id!=user.id or existing.revoked_at is None or existing.version>=mfa.MAX_SV):
        fail(409,"google_link_conflict")
    token=secrets.token_urlsafe(32)
    expires=min(now+mfa.PROOF_TTL,primary.authenticated_at+mfa.PROOF_TTL,
                datetime.fromtimestamp(claims["exp"],timezone.utc))
    db.add(GoogleLinkIntent(token_hash=opaque_digest(PURPOSE,token),user_id=user.id,
        issuer=primary.issuer,subject=primary.subject,purpose=PURPOSE,access_hash=access_digest(access),
        session_version=user.session_version,generation=row.generation,created_at=now,expires_at=expires))
    mfa.audit(db,user,"google_link_intent",now)
    result={"intent":token,"expires_at":expires,"provider":"google",
        "google_email":primary.email,"confirmation_required":True}
    commit(db)
    return result


def confirm(db, expected, access, token, *, now=None):
    user,_,now=_actor(db,expected,access,now)
    row=mfa.credential(db,user.id)
    if not isinstance(token,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}",token):
        fail(400,"google_link_intent_unavailable")
    intent=db.scalar(select(GoogleLinkIntent).where(GoogleLinkIntent.token_hash==opaque_digest(PURPOSE,token),
        GoogleLinkIntent.user_id==user.id).execution_options(populate_existing=True))
    if (not intent or intent.purpose!=PURPOSE or intent.issuer!=ISSUER or intent.consumed_at is not None
            or intent.session_version!=user.session_version or not row or intent.generation!=row.generation
            or not hmac.compare_digest(intent.access_hash,access_digest(access))
            or mfa.aware(intent.created_at)>now or mfa.aware(intent.expires_at)<=now):
        fail(409,"google_link_intent_unavailable")
    existing=_binding(db,intent.issuer,intent.subject)
    if existing is not None and (existing.user_id!=user.id or existing.revoked_at is None or existing.version>=mfa.MAX_SV):
        fail(409,"google_link_conflict")
    with _write_conflicts(db):
        if existing is None:
            linked=AuthExternalIdentity(id=str(uuid.uuid4()),user_id=user.id,
                issuer=intent.issuer,subject=intent.subject,created_at=now,version=1)
            db.add(linked)
        else:
            existing.revoked_at=None;existing.version+=1
            linked=existing
        intent.consumed_at=now
        mfa._revoke_sessions(db,user)
        mfa.audit(db,user,"google_identity_linked",now,identity_id=linked.id,version=linked.version)
        result={"success":True,"provider":"google","linked":True,"reauthenticate":True}
        commit(db)
    return result


def unlink(db,expected,access,command,*,now=None):
    user,_,now=_actor(db,expected,access,now)
    factor=mfa.credential(db,user.id,create=True)
    _local_primary(db,user,factor,command,now)
    row=db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.id==command.identity_id,
        AuthExternalIdentity.user_id==user.id,AuthExternalIdentity.issuer==ISSUER,
        AuthExternalIdentity.revoked_at.is_(None)).execution_options(populate_existing=True))
    if row is None or row.version!=command.expected_version or row.version>=mfa.MAX_SV:
        fail(409,"google_link_conflict")
    row.revoked_at=now;row.version+=1
    mfa._revoke_sessions(db,user)
    mfa.audit(db,user,"google_identity_unlinked",now,identity_id=row.id,version=row.version)
    result={"success":True,"provider":"google","identity_id":row.id,"version":row.version,
        "linked":False,"reauthenticate":True}
    commit(db)
    return result


def status(db, expected, *, after=None):
    from web.database.models import Usuario
    user=db.get(Usuario,expected["id"],populate_existing=True)
    identity=mfa.current_identity(db,user)
    if identity["session_version"]!=expected.get("session_version",expected.get("sv",0)):
        fail(401,"google_link_identity_unavailable")
    query=select(AuthExternalIdentity).where(AuthExternalIdentity.user_id==user.id,AuthExternalIdentity.issuer==ISSUER)
    if after is not None:query=query.where(AuthExternalIdentity.id>after)
    rows=db.scalars(query.order_by(AuthExternalIdentity.id).limit(21)).all()
    items=[{"id":row.id,"version":row.version,"active":row.revoked_at is None,
        "created_at":row.created_at,"revoked_at":row.revoked_at} for row in rows[:20]]
    return {"provider":"google","can_link":user.session_version<mfa.MAX_SV,
        "items":items,"next_after":items[-1]["id"] if len(rows)>20 else None}


def resolve_or_register(db,info,tipo,*,now=None):
    """A new empty container only; existing or revoked bindings never move user."""
    from web.auth import hash_password
    from web.database.models import Usuario,UserRole
    from web.database.tenant_context import bind_verified_subject
    now=mfa.instant(now)
    existing=_binding(db,info["iss"],info["sub"])
    if existing is not None:
        if existing.revoked_at is not None:
            fail(409,"google_link_required")
        return mfa.current_identity(db,db.get(Usuario,existing.user_id,populate_existing=True))
    if db.scalar(select(Usuario.id).where(Usuario.email==info["email"])) is not None:
        fail(409,"google_link_required")
    kind=tipo if tipo in {"usuario","gym"} else "usuario"
    given=info.get("given_name",info.get("name","Usuario"))
    family=info.get("family_name","")
    # Provider display metadata never becomes a role, owner or contact update.
    given=given.strip() if isinstance(given,str) else "Usuario"
    family=family.strip() if isinstance(family,str) else ""
    row=Usuario(id=str(uuid.uuid4()),email=info["email"],password_hash=hash_password(secrets.token_urlsafe(48)),
        nombre=(given or "Usuario")[:150],apellido=family[:150],tipo=kind,
        role=UserRole.OWNER if kind=="gym" else UserRole.VIEWER,activo=True,session_version=0,fecha_registro=now)
    with _write_conflicts(db):
        db.add(row)
        db.flush()
        db.add(AuthExternalIdentity(id=str(uuid.uuid4()),user_id=row.id,issuer=info["iss"],subject=info["sub"],created_at=now,version=1))
        if kind=="gym":
            from web.database.repository import crear_gym_profile
            bind_verified_subject(db,row.id)
            crear_gym_profile(db,row.id,{"nombre_negocio":row.nombre},initialize_memberships=True)
        identity=mfa.current_identity(db,row)
        mfa.audit(db,row,"google_identity_registered",now)
        commit(db)
    return identity
