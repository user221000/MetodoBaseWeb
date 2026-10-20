"""R27 owned sessions, current authority, explicit consent and durable intent.

Every returned value is inert and captured before commit. A failed commit or
owned-session close prevents acknowledgement; no automatic retry/readback.
"""
from contextlib import contextmanager
from dataclasses import asdict,replace
from datetime import timedelta
import hmac,logging,uuid

from fastapi import HTTPException
from sqlalchemy import select,func,text
from sqlalchemy.orm import load_only

from web.database.models import (Usuario,UserRole,Subscription,ProviderSubjectAssociation,PurchaseIntent,
    NotificationPreference as Preference,NotificationBillingFact as Fact,
    NotificationOutbox as Outbox,NotificationAttempt as Attempt)
from web.database.tenant_context import current_tenant,bind_verified_subject
from web.services.notification_domain import (PURPOSES,MAX_VERSION,FRESHNESS,instant,aware,naive,
    contact_hash,request_hash,qualifies,BillingSnapshot,UUID,DisabledPort,secret_hash,digest)
from web.services.notification_transports import BillingReference

logger=logging.getLogger(__name__)


def fail(status,code):
    raise HTTPException(status,{"code":code,"message":"No se pudo confirmar esta operación de notificaciones."})


def rollback(db):
    try:db.rollback()
    except Exception as error:
        logger.error("Notification rollback unconfirmed class=%s",type(error).__name__)
        fail(503,"notification_unconfirmed")


def commit(db):
    try:db.commit()
    except Exception as error:
        logger.error("Notification commit unconfirmed class=%s",type(error).__name__)
        rollback(db);fail(503,"notification_unconfirmed")


@contextmanager
def owned(factory=None):
    """No ambient Session is retagged; cleanup completes before headers."""
    if factory is None:
        from web.database.engine import SessionLocal
        factory=SessionLocal
    token=current_tenant.set("");db=None
    try:
        db=factory();db.expire_on_commit=True
        try:yield db
        except Exception:
            rollback(db);raise
    finally:
        try:
            if db is not None:
                try:db.close()
                except Exception as error:
                    logger.error("Notification close unconfirmed class=%s",type(error).__name__)
                    try:db.invalidate()
                    except Exception as invalid:
                        logger.error("Notification invalidate unconfirmed class=%s",type(invalid).__name__)
                    fail(503,"notification_unconfirmed")
        finally:current_tenant.reset(token)


def _begin(db,write):
    if not write:return
    connection=db.connection()
    if connection.dialect.name=="postgresql" and connection.get_isolation_level()!="READ COMMITTED":
        fail(503,"notification_disabled")
    if connection.dialect.name=="sqlite":
        if not connection.connection.driver_connection.in_transaction:connection.exec_driver_sql("BEGIN IMMEDIATE")


def _valid(user):
    return (user is not None and user.activo is True and user.deleted_at is None
        and user.invitation_token is None and type(user.session_version) is int and 0<=user.session_version<=MAX_VERSION)


def _canonical_gym(user):
    return _valid(user) and user.tipo=="gym" and user.role==UserRole.OWNER and user.team_gym_id is None


def actor(db,expected,context,*,write=False,authorize=True):
    if context not in {"personal","gym"}:fail(422,"notification_invalid_input")
    identity=expected.get("id")
    if not isinstance(identity,str) or not 1<=len(identity)<=36:fail(401,"notification_identity_unavailable")
    version=expected.get("session_version",expected.get("sv",0))
    if type(version) is not int or not 0<=version<=MAX_VERSION:fail(401,"notification_identity_unavailable")
    _begin(db,write)
    bind_verified_subject(db,identity)
    fields=(Usuario.id,Usuario.activo,Usuario.deleted_at,Usuario.invitation_token,Usuario.session_version,Usuario.tipo,Usuario.role,Usuario.team_gym_id,Usuario.notification_contact_version)
    peek=db.scalar(select(Usuario).options(load_only(*fields,raiseload=True)).where(Usuario.id==identity))
    if not _valid(peek):fail(401,"notification_identity_unavailable")
    parent=peek.team_gym_id
    identities=sorted({identity,*([parent] if parent and authorize else [])})
    query=select(Usuario).options(load_only(*fields,raiseload=True)).where(Usuario.id.in_(identities)).order_by(Usuario.id).execution_options(populate_existing=True)
    if write:query=query.with_for_update(nowait=True)
    rows={u.id:u for u in db.scalars(query)}
    user=rows.get(identity)
    if not _valid(user) or user.session_version!=version:fail(401,"notification_identity_unavailable")
    if type(user.notification_contact_version) is not int or not 0<=user.notification_contact_version<=MAX_VERSION:
        fail(503,"notification_unconfirmed")
    if user.team_gym_id!=parent:fail(409,"notification_conflict")
    if authorize:
        if context=="gym":
            if not _canonical_gym(user):fail(403,"notification_context_forbidden")
        elif (user.role not in {UserRole.ADMIN,UserRole.NUTRIOLOGO,UserRole.VIEWER}
                or not (user.tipo=="usuario" or user.team_gym_id)
                or (user.team_gym_id and not _canonical_gym(rows.get(user.team_gym_id)))):
            fail(403,"notification_context_forbidden")
    return user


def email(db,user_id):
    return db.scalar(select(Usuario.email).where(Usuario.id==user_id))


def latest_preference(db,user,context,purpose):
    return db.scalar(select(Preference).where(Preference.user_id==user,Preference.context==context,
        Preference.purpose==purpose).order_by(Preference.version.desc()).limit(1))


def latest_fact(db,user,context):
    return db.scalar(select(Fact).where(Fact.user_id==user,Fact.context==context).order_by(Fact.version.desc()).limit(1))


def preference_dto(row,context,purpose):
    return {"id":row.id if row else None,"context":context,"purpose":purpose,"channel":"email",
        "version":row.version if row else 0,"enabled":row.enabled if row else False,
        "interval_hours":row.interval_hours if row else 24,"updated_at":aware(row.created_at) if row else None}


def outbox_dto(row):
    return {"id":row.id,"context":row.context,"purpose":row.purpose,"channel":row.channel,"state":row.state,
        "version":row.version,"attempt_count":row.attempt_count,"created_at":aware(row.created_at),"updated_at":aware(row.updated_at),
        "capabilities":{"cancel":row.state in {"pending","leased","retry_wait","uncertain"}}}


def context(expected,context,*,factory=None):
    with owned(factory) as db:
        actor(db,expected,context)
        return {"context":context,"purposes":list(PURPOSES),"channels":["email"],"delivery_enabled":False,
            "frequency":{"minimum_hours":24,"maximum_handoffs_7d":3},"timezone":"America/Mexico_City"}


def preferences(expected,context,*,factory=None):
    with owned(factory) as db:
        user=actor(db,expected,context,authorize=False)
        return {"items":[preference_dto(latest_preference(db,user.id,context,p),context,p) for p in PURPOSES]}


def _next(value):
    if type(value) is not int or not 0<=value<MAX_VERSION:fail(409,"notification_version_exhausted")
    return value+1


def add_attempt(db,row,kind,reason,now,key=None,fingerprint=None):
    sequence=db.scalar(select(func.max(Attempt.sequence)).where(Attempt.outbox_id==row.id,Attempt.user_id==row.user_id)) or 0
    db.add(Attempt(id=str(uuid.uuid4()),user_id=row.user_id,context=row.context,created_at=naive(now),outbox_id=row.id,
        sequence=_next(sequence),kind=kind,attempt_no=row.attempt_count,fence=row.version,reason=reason,
        request_key=key,request_hash=fingerprint))


def suppress(db,row,reason,now,key=None,fingerprint=None):
    row.state="suppressed";row.last_reason=reason;row.version=_next(row.version);row.updated_at=naive(now)
    row.lease_hash=None;row.lease_until=None
    db.flush();add_attempt(db,row,"suppressed",reason,now,key,fingerprint)


def set_preference(expected,context,purpose,command,key,*,factory=None,now=None):
    now=instant(now)
    if purpose not in PURPOSES:fail(422,"notification_invalid_input")
    with owned(factory) as db:
        user=actor(db,expected,context,write=True,authorize=command.enabled)
        body=command.model_dump(mode="json");fingerprint=request_hash(user.id,context,"PUT","/api/notificaciones/preferencias/"+purpose,body)
        replay=db.scalar(select(Preference).where(Preference.user_id==user.id,Preference.request_key==key))
        if replay:
            if not hmac.compare_digest(replay.request_hash,fingerprint):fail(409,"notification_conflict")
            return {"preference":preference_dto(replay,context,purpose),"replayed":True,"read_required":True}
        prior=latest_preference(db,user.id,context,purpose)
        if (prior.version if prior else 0)!=command.expected_version:fail(409,"notification_conflict")
        if not command.enabled and prior is None:fail(404,"notification_unavailable")
        row=Preference(id=str(uuid.uuid4()),user_id=user.id,context=context,created_at=naive(now),purpose=purpose,
            channel="email",version=_next(command.expected_version),enabled=command.enabled,interval_hours=command.interval_hours,
            contact_hash=contact_hash(email(db,user.id)) if command.enabled else None,request_key=key,request_hash=fingerprint)
        row.contact_version=user.notification_contact_version
        db.add(row);db.flush()
        pending=db.scalars(select(Outbox).where(Outbox.user_id==user.id,Outbox.context==context,Outbox.purpose==purpose,
            Outbox.state.in_(["pending","leased","retry_wait"])).order_by(Outbox.id).with_for_update()).all()
        for item in pending:suppress(db,item,"preference_changed",now)
        result={"preference":preference_dto(row,context,purpose),"replayed":False,"read_required":False}
        commit(db);return result


def reference(db,user,context,*,lock=False):
    query=select(Subscription).where(Subscription.gym_id==user.id).execution_options(populate_existing=True)
    if lock:query=query.with_for_update(read=True,nowait=True)
    sub=db.scalar(query)
    if sub is None or sub.provider not in {"stripe","mercadopago"}:fail(404,"notification_source_unavailable")
    if (context=="personal")!=(sub.plan=="pro_usuario"):fail(404,"notification_source_unavailable")
    resource_type="subscription" if sub.provider=="stripe" else "payment"
    resource_id=sub.stripe_subscription_id if sub.provider=="stripe" else sub.provider_payment_id
    def association(kind,identifier):
        if not identifier:return None
        query=select(ProviderSubjectAssociation).where(ProviderSubjectAssociation.provider==sub.provider,
            ProviderSubjectAssociation.resource_type==kind,ProviderSubjectAssociation.resource_id==identifier).execution_options(populate_existing=True)
        if lock:query=query.with_for_update(read=True,nowait=True)
        return db.scalar(query)
    mapping=association(resource_type,resource_id)
    if mapping is None or mapping.subject_id!=user.id:fail(404,"notification_source_unavailable")
    associations=[mapping]
    if sub.provider=="stripe":
        customer=association("customer",sub.stripe_customer_id)
        if customer is None or customer.subject_id!=user.id:fail(404,"notification_source_unavailable")
        associations.append(customer)
    query=select(PurchaseIntent).where(PurchaseIntent.subject_id==user.id,PurchaseIntent.provider==sub.provider,
        PurchaseIntent.status=="confirmed",PurchaseIntent.provider_reference_id==resource_id)
    if lock:query=query.with_for_update(read=True,nowait=True)
    purchase=db.scalar(query)
    if sub.provider=="mercadopago" and purchase is None:fail(404,"notification_source_unavailable")
    from web.services.billing_integrity import price_in_cents
    association_proof=digest([{"provider":a.provider,"type":a.resource_type,"resource":a.resource_id,"subject":a.subject_id,
        "provenance":a.provenance,"source":a.source_ref,"created_at":aware(a.created_at).isoformat()} for a in associations])
    return BillingReference(user.id,context,sub.id,sub.provider,resource_type,resource_id,sub.stripe_customer_id,sub.plan,
        price_in_cents(sub.plan),sub.status,aware(sub.current_period_start) if sub.current_period_start else None,
        aware(sub.current_period_end) if sub.current_period_end else None,purchase.id if purchase else None,association_proof,user.notification_contact_version)


def source_fingerprint(snapshot,source):
    reference_data=asdict(source)
    for name in ("period_start","period_end"):
        if reference_data[name] is not None:reference_data[name]=instant(reference_data[name]).isoformat()
    return digest({"snapshot":snapshot.fingerprint(),"persisted_reference":reference_data})


def stored_snapshot(fact):
    data={name:getattr(fact,name) for name in BillingSnapshot.__dataclass_fields__}
    for name in ("period_start","period_end","due_at"):
        if data[name] is not None:data[name]=aware(data[name])
    return BillingSnapshot(**data).validate()


def observe(expected,context,key,port=None,*,factory=None,now=None):
    now=instant(now);port=port or DisabledPort()
    if port.enabled is not True:fail(503,"notification_disabled")
    with owned(factory) as db:
        user=actor(db,expected,context)
        fingerprint=request_hash(user.id,context,"POST","/api/notificaciones/observar",{})
        replay=db.scalar(select(Fact).where(Fact.user_id==user.id,Fact.request_key==key))
        if replay:
            if replay.request_hash!=fingerprint:fail(409,"notification_conflict")
            return {"observed":True,"fact_id":replay.id,"replayed":True,"read_required":True}
        source=reference(db,user,context)
        prior=latest_fact(db,user.id,context)
        previous=stored_snapshot(prior) if prior is not None and valid_source(db,user,context,prior,now) else None
    # No actor/source lock or transaction spans the provider call.
    observation_failed=False
    try:
        snapshot=port.read_billing(source)
        if not isinstance(snapshot,BillingSnapshot):raise ValueError("Untyped notification source")
        snapshot.validate()
        if (snapshot.provider,snapshot.resource_type,snapshot.resource_id)!=(source.provider,source.resource_type,source.resource_id):
            raise ValueError("Notification provider identity changed")
    except Exception as error:
        logger.error("Notification observation unconfirmed class=%s",type(error).__name__)
        if previous is None:fail(503,"notification_unconfirmed")
        # Supersede prior eligibility without inventing invoice/amount data.
        # Quantities are copied from the last typed observation; unknown is a
        # revocation marker, never a new verified provider state/payment.
        snapshot=replace(previous,subscription_status="unknown")
        observation_failed=True
    if (snapshot.subscription_status!=source.database_status or snapshot.period_start!=source.period_start
            or snapshot.period_end!=source.period_end):
        # Persist an observation with unconfirmed canonical state, replacing
        # any earlier eligible source. Never reconcile rights from this reader.
        snapshot=replace(snapshot,subscription_status="unknown")
    with owned(factory) as db:
        user=actor(db,expected,context,write=True)
        if reference(db,user,context,lock=True)!=source:fail(409,"notification_source_changed")
        replay=db.scalar(select(Fact).where(Fact.user_id==user.id,Fact.request_key==key))
        if replay:
            if replay.request_hash!=fingerprint:fail(409,"notification_conflict")
            return {"observed":True,"fact_id":replay.id,"replayed":True,"read_required":True}
        previous=latest_fact(db,user.id,context)
        data=asdict(snapshot)
        for name in ("period_start","period_end","due_at"):
            if data[name] is not None:data[name]=naive(data[name])
        row=Fact(id=str(uuid.uuid4()),user_id=user.id,context=context,created_at=naive(now),
            version=_next(previous.version if previous else 0),request_key=key,request_hash=fingerprint,
            subscription_id=source.subscription_id,source_hash=source_fingerprint(snapshot,source),fresh_until=naive(now+FRESHNESS),**data)
        db.add(row);db.flush();result={"observed":True,"fact_id":row.id,"replayed":False,"read_required":True}
        commit(db)
    if observation_failed:fail(503,"notification_unconfirmed")
    return result


def valid_source(db,user,context,fact,now,*,lock=False):
    if fact is None:return False
    source=reference(db,user,context,lock=lock)
    expected_hash=source_fingerprint(stored_snapshot(fact),source)
    return (fact.subscription_id==source.subscription_id and fact.provider==source.provider and fact.resource_id==source.resource_id
        and fact.subscription_status==source.database_status and hmac.compare_digest(fact.source_hash,expected_hash)
        and aware(fact.created_at)<=now<aware(fact.fresh_until))


def candidates(expected,context,*,factory=None,now=None):
    now=instant(now)
    with owned(factory) as db:
        user=actor(db,expected,context);fact=latest_fact(db,user.id,context)
        valid=False
        try:valid=valid_source(db,user,context,fact,now)
        except HTTPException as error:
            if error.status_code!=404:raise
        return {"context":context,"observed_at":now,"source_state":"verified" if valid else "unknown",
            "candidates":[{"purpose":purpose,"eligible":valid and qualifies(fact,purpose,now),
                "fact_id":fact.id if valid else None,"source_hash":fact.source_hash if valid else None,
                "preference":preference_dto(latest_preference(db,user.id,context,purpose),context,purpose)} for purpose in PURPOSES]}


def queue(expected,context,command,key,*,factory=None,now=None):
    now=instant(now)
    with owned(factory) as db:
        user=actor(db,expected,context,write=True)
        fingerprint=request_hash(user.id,context,"POST","/api/notificaciones/outbox",command.model_dump(mode="json"))
        replay=db.scalar(select(Outbox).where(Outbox.user_id==user.id,Outbox.request_key==key))
        if replay:
            if replay.request_hash!=fingerprint:fail(409,"notification_conflict")
            return {"operation_result":{"id":replay.id},"replayed":True,"read_required":True}
        pref=latest_preference(db,user.id,context,command.purpose)
        if pref is None or not pref.enabled or pref.id!=command.preference_id or pref.version!=command.expected_preference_version:
            fail(409,"notification_conflict")
        destination=email(db,user.id)
        if pref.contact_version!=user.notification_contact_version or not hmac.compare_digest(pref.contact_hash,contact_hash(destination)):
            fail(409,"notification_source_changed")
        fact=latest_fact(db,user.id,context)
        if (fact is None or fact.id!=command.fact_id or fact.source_hash!=command.source_hash or not valid_source(db,user,context,fact,now,lock=True)
                or not qualifies(fact,command.purpose,now)):fail(409,"notification_source_changed")
        prior=db.scalar(select(Outbox.id).where(Outbox.user_id==user.id,Outbox.context==context,
            Outbox.purpose==command.purpose,Outbox.source_hash==fact.source_hash))
        if prior is not None:fail(409,"notification_conflict")
        backlog=db.scalar(select(func.count()).select_from(Outbox).where(Outbox.user_id==user.id,Outbox.context==context,
            Outbox.state.in_(["pending","leased","sending","retry_wait"])))
        if backlog>=100:fail(429,"notification_backlog_limited")
        row=Outbox(id=str(uuid.uuid4()),user_id=user.id,context=context,created_at=naive(now),purpose=command.purpose,
            channel="email",preference_id=pref.id,fact_id=fact.id,source_hash=fact.source_hash,contact_hash=pref.contact_hash,
            contact_version=pref.contact_version,
            request_key=key,request_hash=fingerprint,state="pending",version=1,attempt_count=0,next_attempt_at=naive(now),updated_at=naive(now))
        db.add(row);db.flush();result={"outbox":outbox_dto(row),"replayed":False,"read_required":False}
        commit(db);return result


def list_outbox(expected,context,limit=20,after=None,*,factory=None):
    if type(limit) is not int or not 1<=limit<=50 or (after is not None and (not isinstance(after,str) or not UUID.fullmatch(after))):
        fail(422,"notification_invalid_input")
    with owned(factory) as db:
        user=actor(db,expected,context,authorize=False)
        query=select(Outbox).where(Outbox.user_id==user.id,Outbox.context==context)
        if after:query=query.where(Outbox.id>after)
        rows=db.scalars(query.order_by(Outbox.id).limit(limit+1)).all()
        return {"items":[outbox_dto(r) for r in rows[:limit]],"next_after":rows[limit-1].id if len(rows)>limit else None}


def cancel(expected,context,identifier,command,key,*,factory=None,now=None):
    now=instant(now)
    with owned(factory) as db:
        user=actor(db,expected,context,write=True,authorize=False)
        fingerprint=request_hash(user.id,context,"POST","/api/notificaciones/outbox/"+identifier+"/cancelar",command.model_dump(mode="json"))
        replay=db.scalar(select(Attempt).where(Attempt.user_id==user.id,Attempt.request_key==key))
        if replay is not None:
            if replay.request_hash!=fingerprint:fail(409,"notification_conflict")
            return {"operation_result":{"id":replay.outbox_id},"replayed":True,"read_required":True}
        row=db.scalar(select(Outbox).where(Outbox.id==identifier,Outbox.user_id==user.id,Outbox.context==context).with_for_update())
        if row is None:fail(404,"notification_unavailable")
        if row.version!=command.expected_version or row.state not in {"pending","leased","retry_wait","uncertain"}:
            fail(409,"notification_conflict")
        suppress(db,row,"cancelled_by_subject",now,key,fingerprint);result={"outbox":outbox_dto(row),"replayed":False,"read_required":False}
        commit(db);return result


def exclude(token,*,factory=None,now=None):
    """Bearer permits only disabling its exact current preference, no reads."""
    import re
    now=instant(now);result={"success":True}
    if not isinstance(token,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}",token):return result
    hashed=secret_hash("notification_exclude36:v1",token)
    with owned(factory) as db:
        _begin(db,True)
        if db.get_bind().dialect.name=="postgresql":
            db.execute(text("SELECT set_config('app.notification_exclude_digest',:digest,true)"),{"digest":hashed})
        capability=db.execute(select(Outbox.id,Outbox.user_id,Outbox.preference_id,Outbox.context,Outbox.purpose,Outbox.contact_hash,Outbox.contact_version,
            Outbox.exclude_expires_at).where(Outbox.exclude_hash==hashed,Outbox.exclude_protocol==1,Outbox.exclude_purpose=="notification_exclude")).first()
        if capability is None or aware(capability.exclude_expires_at)<=now:return result
        bind_verified_subject(db,capability.user_id)
        if db.get_bind().dialect.name=="postgresql":
            db.execute(text("SELECT set_config('app.notification_exclude_digest','',true)"))
        user=db.scalar(select(Usuario).options(load_only(Usuario.id,Usuario.activo,Usuario.deleted_at,Usuario.invitation_token,
            Usuario.session_version,Usuario.notification_contact_version,raiseload=True)).where(Usuario.id==capability.user_id).with_for_update(nowait=True))
        # Disable-only remains possible after OFF, never after deletion or an
        # invalid/replaced identity. No activation or new preference is made.
        if (user is None or user.deleted_at is not None or user.invitation_token is not None
                or type(user.session_version) is not int or not 0<=user.session_version<=MAX_VERSION):return result
        prior=latest_preference(db,user.id,capability.context,capability.purpose)
        if (prior is None or prior.id!=capability.preference_id or not prior.enabled
                or prior.contact_version!=user.notification_contact_version or capability.contact_version!=user.notification_contact_version
                or prior.contact_hash!=capability.contact_hash or prior.contact_hash!=contact_hash(email(db,user.id))):return result
        row=Preference(id=str(uuid.uuid4()),user_id=user.id,context=prior.context,created_at=naive(now),purpose=prior.purpose,
            channel="email",version=_next(prior.version),enabled=False,interval_hours=prior.interval_hours,contact_hash=None,
            contact_version=user.notification_contact_version,
            request_key=str(uuid.uuid4()),request_hash=request_hash(user.id,prior.context,"POST","/api/notificaciones/excluir",{"capability":hashed}))
        db.add(row);db.flush()
        pending=db.scalars(select(Outbox).where(Outbox.user_id==user.id,Outbox.context==prior.context,Outbox.purpose==prior.purpose,
            Outbox.state.in_(["pending","leased","retry_wait"])).order_by(Outbox.id).with_for_update()).all()
        for item in pending:suppress(db,item,"preference_changed",now)
        commit(db);return result


def metrics(expected,context,start,through,*,factory=None,now=None):
    from datetime import date,datetime,time
    from zoneinfo import ZoneInfo
    now=instant(now);zone=ZoneInfo("America/Mexico_City")
    today=now.astimezone(zone).date()
    if any(value is not None and type(value) is not date for value in (start,through)):fail(422,"notification_invalid_input")
    start=start or today;through=through or today
    if start>through or through>today or (through-start).days>61:fail(422,"notification_invalid_input")
    lower=naive(datetime.combine(start,time.min,zone));upper=naive(datetime.combine(through+timedelta(days=1),time.min,zone))
    with owned(factory) as db:
        user=actor(db,expected,context,authorize=False)
        counts=dict(db.execute(select(Outbox.state,func.count()).where(Outbox.user_id==user.id,Outbox.context==context,
            Outbox.created_at>=lower,Outbox.created_at<upper).group_by(Outbox.state)).all())
        # Bound the minimum typed projection before bringing values into Python.
        # No provider/contact/body/Session objects are returned or cached.
        rows=db.execute(select(Fact.invoice_id,Fact.resource_id,Fact.version,Fact.paid,Fact.refunded,Fact.period_end,Fact.created_at,Fact.subscription_status)
            .where(Fact.user_id==user.id,Fact.context==context,Fact.created_at<upper).order_by(Fact.version).limit(2001)).all()
        if len(rows)>2000:fail(413,"notification_volume_limit")
        latest={}
        for row in rows:latest[row.invoice_id or row.resource_id]=row
        paid=sorted((r for r in latest.values() if r.paid and not r.refunded and r.period_end is not None and r.subscription_status=="active"),key=lambda r:(r.period_end,r.version))
        advances=0;last_end=None
        for row in paid:
            if last_end is not None and row.period_end>last_end and lower<=row.created_at<upper:advances+=1
            last_end=max(last_end,row.period_end) if last_end else row.period_end
        return {"from":start,"through":through,"timezone":"America/Mexico_City","outbox_states":counts,
            "verified_paid_period_advances":advances,"attribution":"observed_facts_only_no_email_causality"}
