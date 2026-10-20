"""One explicit subject/UUID, durable fencing, no scheduler or automatic resend."""
from dataclasses import dataclass
from datetime import timedelta
import hmac,secrets

from sqlalchemy import select,func
from web.database.models import Usuario,NotificationOutbox as Outbox,NotificationAttempt as Attempt
from web.database.tenant_context import bind_verified_subject
from web.services import notifications as app
from web.services.notification_domain import (instant,aware,naive,secret_hash,contact_hash,LEASE,EXCLUDE_TTL,
    qualifies,SendResult,DisabledPort)
from web.services.notification_transports import ReminderMessage


@dataclass(frozen=True)
class Claim:
    user_id:str
    context:str
    identifier:str
    fence:int
    token:str


def worker_actor(db,user_id,context,*,authorize=True):
    version=db.scalar(select(Usuario.session_version).where(Usuario.id==user_id))
    return app.actor(db,{"id":user_id,"session_version":version},context,write=True,authorize=authorize)


def _row(db,user,identifier):
    row=db.scalar(select(Outbox).where(Outbox.id==identifier,Outbox.user_id==user).with_for_update(nowait=True))
    if row is None:app.fail(404,"notification_unavailable")
    return row


def _owns(row,claim,now):
    return (row.context==claim.context and row.version==claim.fence and row.lease_hash is not None
        and hmac.compare_digest(row.lease_hash,secret_hash("notification_lease36:v1",claim.token))
        and row.lease_until is not None and now<aware(row.lease_until))


def claim(user_id,context,identifier,*,factory=None,now=None):
    now=instant(now)
    with app.owned(factory) as db:
        worker_actor(db,user_id,context)
        row=_row(db,user_id,identifier)
        if row.context!=context:app.fail(404,"notification_unavailable")
        allowed=row.state in {"pending","retry_wait"} and aware(row.next_attempt_at)<=now
        allowed=allowed or (row.state=="leased" and aware(row.lease_until)<=now)
        if not allowed:app.fail(409,"notification_conflict")
        token=secrets.token_urlsafe(32)
        row.state="leased";row.version=app._next(row.version);row.updated_at=naive(now)
        row.lease_hash=secret_hash("notification_lease36:v1",token);row.lease_until=naive(now+LEASE)
        result=Claim(user_id,context,identifier,row.version,token)
        app.commit(db);return result


def frequency_until(db,user,context,interval,now):
    scope=(Attempt.user_id==user,Attempt.context==context,Attempt.kind=="handoff")
    recent_count=db.scalar(select(func.count()).select_from(Attempt).where(*scope,Attempt.created_at>naive(now-timedelta(days=7))))
    last=db.scalar(select(func.max(Attempt.created_at)).where(*scope))
    until=now
    if last is not None:until=max(until,aware(last)+timedelta(hours=interval))
    if recent_count>=3:
        third_latest=db.scalar(select(Attempt.created_at).where(*scope,Attempt.created_at>naive(now-timedelta(days=7)))
            .order_by(Attempt.created_at.desc(),Attempt.id.desc()).offset(2).limit(1))
        until=max(until,aware(third_latest)+timedelta(days=7))
    return until


def prepare_handoff(claimed,origin,*,factory=None,now=None):
    """Revalidation and sending declaration commit before exposing message."""
    from web.services.password_recovery import public_origin
    from web.settings import get_settings
    try:canonical=public_origin(get_settings())
    except Exception:app.fail(503,"notification_disabled")
    if origin!=canonical:app.fail(503,"notification_disabled")
    now=instant(now)
    with app.owned(factory) as db:
        user=worker_actor(db,claimed.user_id,claimed.context)
        row=_row(db,user.id,claimed.identifier)
        if row.state!="leased" or not _owns(row,claimed,now):app.fail(409,"notification_conflict")
        pref=app.latest_preference(db,user.id,claimed.context,row.purpose)
        fact=app.latest_fact(db,user.id,claimed.context)
        destination=app.email(db,user.id)
        valid=(pref is not None and pref.enabled and pref.id==row.preference_id and pref.contact_hash==row.contact_hash
            and pref.contact_version==row.contact_version==user.notification_contact_version
            and hmac.compare_digest(row.contact_hash,contact_hash(destination)) and fact is not None
            and fact.source_hash==row.source_hash and qualifies(fact,row.purpose,now))
        if valid:
            try:valid=app.valid_source(db,user,claimed.context,fact,now,lock=True)
            except Exception as error:
                from fastapi import HTTPException
                if not isinstance(error,HTTPException) or error.status_code!=404:raise
                valid=False
        if not valid:
            app.suppress(db,row,"authorization_changed",now);app.commit(db);return None
        until=frequency_until(db,user.id,claimed.context,pref.interval_hours,now)
        if until>now:
            row.state="retry_wait";row.version=app._next(row.version);row.updated_at=naive(now)
            row.next_attempt_at=naive(until);row.lease_hash=None;row.lease_until=None;row.last_reason="frequency_limited"
            app.commit(db);return None
        exclude=secrets.token_urlsafe(32)
        row.state="sending";row.version=app._next(row.version);row.attempt_count+=1
        row.sending_at=naive(now);row.updated_at=naive(now)
        row.exclude_protocol=1;row.exclude_purpose="notification_exclude"
        row.exclude_hash=secret_hash("notification_exclude36:v1",exclude);row.exclude_expires_at=naive(now+EXCLUDE_TTL)
        db.flush();app.add_attempt(db,row,"handoff","authorized_handoff",now)
        # No names, invoice identifiers, amounts or health data in the message.
        path="/usuario" if claimed.context=="personal" else "/suscripciones"
        message=ReminderMessage(destination,row.purpose,origin+path,origin+"/notificaciones/excluir#token="+exclude,
            "notification36/"+row.id)
        result=(Claim(user.id,claimed.context,row.id,row.version,claimed.token),message)
        app.commit(db);return result


def finish(claimed,outcome,*,factory=None,now=None):
    """Persist only a receipt for the exact confirmed handoff; no new send."""
    now=instant(now)
    if not isinstance(outcome,SendResult):outcome=SendResult("uncertain")
    try:outcome.validate()
    except (ValueError,TypeError):outcome=SendResult("uncertain")
    with app.owned(factory) as db:
        app._begin(db,True);bind_verified_subject(db,claimed.user_id)
        # This is receipt recording, even if account eligibility changed after
        # an already authorized handoff. It grants no new authority/contact.
        db.scalar(select(Usuario.id).where(Usuario.id==claimed.user_id).with_for_update(nowait=True))
        row=_row(db,claimed.user_id,claimed.identifier)
        if row.state!="sending" or not _owns(row,claimed,now):app.fail(409,"notification_conflict")
        row.version=app._next(row.version);row.updated_at=naive(now)
        row.lease_hash=None;row.lease_until=None
        if outcome.kind=="accepted":
            row.state="accepted";row.provider_id=outcome.provider_id;row.accepted_at=naive(now)
            kind="accepted";reason="provider_accepted"
        elif outcome.kind=="uncertain":
            row.state="uncertain";kind="uncertain";reason="transport_unconfirmed"
        else:
            row.state="retry_wait" if outcome.kind=="not_sent_retryable" and row.attempt_count<3 else "failed"
            row.next_attempt_at=naive(now+timedelta(seconds=60 if row.attempt_count==1 else 300))
            kind="not_sent";reason="definite_not_sent"
        row.last_reason=reason
        db.flush();app.add_attempt(db,row,kind,reason,now)
        result={"outbox":app.outbox_dto(row)}
        app.commit(db);return result


def recover_expired_sending(user_id,context,identifier,*,factory=None,now=None):
    """A lost sending lease is uncertain, never an automatic duplicate."""
    now=instant(now)
    with app.owned(factory) as db:
        app._begin(db,True);bind_verified_subject(db,user_id)
        db.scalar(select(Usuario.id).where(Usuario.id==user_id).with_for_update(nowait=True))
        row=_row(db,user_id,identifier)
        if row.context!=context or row.state!="sending" or aware(row.lease_until)>now:app.fail(409,"notification_conflict")
        row.state="uncertain";row.version=app._next(row.version);row.updated_at=naive(now)
        row.lease_hash=None;row.lease_until=None;row.last_reason="sending_lease_expired"
        db.flush();app.add_attempt(db,row,"uncertain","sending_lease_expired",now)
        result={"outbox":app.outbox_dto(row)};app.commit(db);return result


def run_one(user_id,context,identifier,origin,port=None,*,factory=None,now=None):
    port=port or DisabledPort()
    if port.enabled is not True:app.fail(503,"notification_disabled")
    claimed=claim(user_id,context,identifier,factory=factory,now=now)
    prepared=prepare_handoff(claimed,origin,factory=factory,now=now)
    if prepared is None:return {"processed":True,"handed_off":False}
    claimed,message=prepared
    try:outcome=port.send(message)
    except Exception:outcome=SendResult("uncertain")
    return finish(claimed,outcome,factory=factory,now=now)
