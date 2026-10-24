"""Self-request and atomic account closure. Erasure is a separate owned job."""
import logging
import uuid
from fastapi import HTTPException
from sqlalchemy import select, update
from web.database.models import (Base, PrivacyRequest, PrivacyDispositionItem, Usuario,
    UserRole, Subscription, Payment, PurchaseIntent, RefreshToken, AuthAuditLog)
from web.database.tenant_context import bind_verified_subject
from web.services import mfa_service as mfa
from web.services.account_security import PENDING, factory_or_default
from web.services.privacy_policy import INVENTORY, load_policy

logger = logging.getLogger(__name__)
MAX_VERSION = 2147483647


def fail(status,code):
    raise HTTPException(status,{'code':code,'message':'La solicitud requiere revisión o una nueva verificación de tu cuenta.'})


def bump(row, now):
    if type(row.version) is not int or not 1 <= row.version < MAX_VERSION:
        fail(409,'privacy_version_exhausted')
    row.version += 1
    row.updated_at = now


def summary(db,request):
    items = db.scalars(select(PrivacyDispositionItem).where(PrivacyDispositionItem.request_id==request.id,
        PrivacyDispositionItem.subject_id==request.subject_id).order_by(PrivacyDispositionItem.category)).all()
    return {'id':request.id,'version':request.version,'state':request.state,'reason':request.reason,
        'account_closed':request.closed_at is not None,'erasure_complete':request.state=='completed',
        'policy':None if request.policy_id is None else {'id':request.policy_id,'version':request.policy_version,'digest':request.policy_digest},
        'items':[{'category':row.category,'status':row.status,'reason':row.reason,'deleted_rows':row.deleted_rows} for row in items]}


def _commit(db):
    try:
        db.commit()
    except Exception as error:
        logger.error('Privacy commit unconfirmed class=%s',type(error).__name__)
        mfa.rollback(db)
        fail(503,'privacy_commit_unconfirmed')


def _request(db, subject, request_id, *, expected_version=None):
    row = db.scalar(select(PrivacyRequest).where(PrivacyRequest.id==request_id,PrivacyRequest.subject_id==subject).with_for_update(nowait=True))
    if row is None:
        fail(404,'privacy_request_unavailable')
    if expected_version is not None and row.version != expected_version:
        fail(409,'privacy_request_changed')
    return row


def create_request(expected, idempotency_key, *, factory=None, now=None):
    # A canonical UUID supplies idempotency only; it is never read authority.
    if str(uuid.UUID(idempotency_key)) != idempotency_key:
        fail(422,'privacy_invalid_key')
    with factory_or_default(factory)() as db:
        try:
            user,_ = mfa.lock_actor(db,expected)
            bind_verified_subject(db,user.id)
            row = db.scalar(select(PrivacyRequest).where(PrivacyRequest.subject_id==user.id,
                PrivacyRequest.idempotency_key==idempotency_key))
            if row is None:
                current=mfa.instant(now)
                row=PrivacyRequest(subject_id=user.id,idempotency_key=idempotency_key,intent='erase_personal_data',
                    state='blocked',reason='policy_required',created_at=current,updated_at=current)
                db.add(row);db.flush()
            output=summary(db,row)
            _commit(db)
            return output
        except HTTPException:
            mfa.rollback(db);raise


def read_request(expected, request_id, *, factory=None):
    with factory_or_default(factory)() as db:
        user,_=mfa.lock_actor(db,expected)
        bind_verified_subject(db,user.id)
        return summary(db,_request(db,user.id,request_id))


def closure_blocker(db,user):
    # An owner portfolio or professional membership is never adopted/deleted.
    if user.role==UserRole.OWNER or user.tipo in {'gym','admin'} or user.team_gym_id:
        return 'professional_obligations_require_review'
    if db.scalar(select(Usuario.id).where(Usuario.team_gym_id==user.id).limit(1)):
        return 'team_obligations_require_review'
    if db.scalar(select(Subscription.id).where(Subscription.gym_id==user.id).limit(1)):
        return 'subscription_requires_explicit_resolution'
    if db.scalar(select(Payment.id).where(Payment.gym_id==user.id).limit(1)):
        return 'payment_records_require_review'
    if db.scalar(select(PurchaseIntent.id).where(PurchaseIntent.subject_id==user.id).limit(1)):
        return 'purchase_intent_requires_review'
    return None


def prepare_items(db,row,policy,now):
    decisions=policy.admit(Base.metadata.tables,now=now)
    if row.policy_digest is not None and row.policy_digest!=policy.digest():
        fail(409,'privacy_policy_changed')
    existing={item.category for item in db.scalars(select(PrivacyDispositionItem).where(
        PrivacyDispositionItem.request_id==row.id,PrivacyDispositionItem.subject_id==row.subject_id))}
    row.policy_id,row.policy_version,row.policy_digest=policy.policy_id,policy.version,policy.digest()
    statuses={'delete':'pending','retain':'retained_by_policy','block':'blocked','external_confirmation':'pending_confirmation'}
    for category in INVENTORY:
        if category not in existing:
            decision=decisions[category]
            db.add(PrivacyDispositionItem(request_id=row.id,subject_id=row.subject_id,category=category,
                status=statuses[decision.action],reason=decision.basis_id,updated_at=now))


def close_account(expected,access,request_id,expected_version,proof_token,*,code=None,recovery_code=None,
                  policy_provider=None,factory=None,now=None):
    with factory_or_default(factory)() as db:
        try:
            user,_=mfa.lock_actor(db,expected)  # Global Usuario locks precede request and refresh rows.
            bind_verified_subject(db,user.id)
            row=_request(db,user.id,request_id,expected_version=expected_version)
            current=mfa.instant(now)
            if row.closed_at is not None:
                return summary(db,row)
            blocker=closure_blocker(db,user)
            policy=None
            if blocker is None:
                try:
                    policy=load_policy(policy_provider,subject_id=user.id,now=current,tables=Base.metadata.tables)
                except ValueError:
                    blocker='policy_inventory_or_holds_unresolved'
            if blocker:
                row.state,row.reason='blocked',blocker;bump(row,current)
                output=summary(db,row);_commit(db);return output
            # Success consumes primary+current factor in THIS transaction. Failed
            # factor budgets preserve the existing durable failure commit path.
            user=mfa.consume_privacy_reauthentication(db,expected,access,proof_token,
                code=code,recovery_code=recovery_code,now=current)
            prepare_items(db,row,policy,current)
            user.session_version+=1
            user.activo=False
            user.invitation_token=user.invitation_expires=None
            user.password_reset_hash=user.password_reset_expires_at=user.password_reset_session_version=None
            for name in PENDING:setattr(user,name,None)
            row.closed_at=current;row.state='eligible';row.reason='account_closed_erasure_pending';bump(row,current)
            db.flush()
            db.execute(update(RefreshToken).where(RefreshToken.user_id==user.id).values(revoked=True))
            db.add(AuthAuditLog(user_id=user.id,event_type='privacy_account_closed',
                event_metadata={'request_id':row.id,'policy_digest':row.policy_digest},created_at=current))
            db.flush();output=summary(db,row);_commit(db)
            return {**output,'sessions_revoked':True,'state_available':'authorized_operator_only_after_closure'}
        except HTTPException:
            mfa.rollback(db);raise
        except Exception as error:
            logger.error('Privacy closure unconfirmed class=%s',type(error).__name__)
            mfa.rollback(db);fail(503,'privacy_commit_unconfirmed')
