"""Own self-reported measurements; explicit sources, truthful dates and CAS.

The service owns one root transaction. A scalar DTO is captured before COMMIT
but never returned before its ACK. Ambiguous outcomes are visible, not retried.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import base64
import json
import logging

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from web.database.models import ClientProgress, Cliente, Usuario, UserRole
from web.personal_progress_schemas import MAX_VERSION, uuid_text
from web.services import client_link_context as identity
from web.services.personal_diary_service import local_today

logger=logging.getLogger(__name__)
MAX_RESPONSE_BYTES=256*1024
MAX_PAGE=100


def fail(status,code,**extra):
    raise HTTPException(status,{"code":code,"message":"Consulta el estado autorizado antes de continuar.",**extra})


def bounded(value):
    try:encoded=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")
    except (TypeError,ValueError,OverflowError,UnicodeError):fail(409,"progress_source_requires_review")
    if len(encoded)>MAX_RESPONSE_BYTES:fail(413,"progress_volume_limit")
    return value


@contextmanager
def operation(db):
    if db.in_transaction() or db.in_nested_transaction():fail(503,"progress_transaction_unavailable")
    db.info["progress_commit_attempted"]=False
    try:yield
    except Exception as error:
        try:db.rollback()
        except Exception as rollback_error:
            logger.error("Progress rollback class=%s",type(rollback_error).__name__)
            fail(503,"progress_unconfirmed")
        if db.info.get("progress_commit_attempted"):fail(503,"progress_unconfirmed")
        if isinstance(error,HTTPException):
            if isinstance(error.detail,dict) and str(error.detail.get("code","")).startswith("member_"):
                raise HTTPException(error.status_code,{"code":error.detail["code"].replace("member_","progress_",1),"message":"Consulta el estado autorizado antes de continuar."}) from None
            raise
        state=getattr(getattr(error,"orig",None),"pgcode",None)
        if state=="55P03":fail(409,"progress_busy")
        if isinstance(error,IntegrityError):fail(409,"progress_version_conflict")
        logger.error("Progress operation class=%s",type(error).__name__)
        fail(503,"progress_unconfirmed")


def commit(db):
    db.info["progress_commit_attempted"]=True
    db.commit()


def personal(db,principal,*,write=False,gyms=(),eligible=True):
    actor=identity.recipient_scope(db,principal)
    if actor.role==UserRole.OWNER:fail(403,"progress_personal_space_required")
    actor,_=identity.lock_contexts(db,principal,actor,set(gyms),write=write,require_eligible_gym=eligible)
    return actor


def retirement_actor(db,principal,*,write=False):
    """Only own immutable consent events, including an account now OWNER.

    This does not assert a personal space or load a profile/professional source.
    Ambiguous OWNER authority cannot create measurements or a new grant.
    """
    subject,expected=identity._claims(principal)
    identity.bind_scope(db,subject)
    if write and db.get_bind().dialect.name=="sqlite":
        db.execute(update(Usuario).where(Usuario.id==subject).values(id=Usuario.id).execution_options(synchronize_session=False))
    query=select(Usuario).where(Usuario.id==subject).execution_options(populate_existing=True)
    if db.get_bind().dialect.name=="postgresql":query=query.with_for_update(read=not write,nowait=True)
    actor=db.scalar(query)
    if (actor is None or not actor.activo or actor.deleted_at is not None or actor.invitation_token is not None
            or actor.role not in set(UserRole) or type(actor.session_version) is not int
            or not 0<=actor.session_version<=MAX_VERSION or actor.session_version!=expected):
        fail(401,"progress_identity_unavailable")
    return actor


def profile(db,subject,profile_id,*,active=True,lock=True):
    query=select(Cliente).where(Cliente.gym_id==subject,Cliente.id_cliente==profile_id,Cliente.deleted_at.is_(None))
    if active:query=query.where(Cliente.activo.is_(True))
    if lock:query=query.with_for_update(read=True)
    row=db.scalar(query.execution_options(populate_existing=True))
    if row is None:fail(404,"progress_source_unavailable")
    return row


def checked_version(actual,expected):
    if actual!=expected:fail(409,"progress_version_conflict",current_version=actual)
    if actual>=MAX_VERSION:fail(409,"progress_version_overflow")


def instant(db,now=None):return identity.clock(db,now)


def period(start=None,end=None,*,now=None):
    today=local_today(now)
    if (start is None)!=(end is None):fail(422,"progress_invalid_input")
    if start is None:start,end=today-timedelta(days=29),today
    if type(start) is not date or type(end) is not date or not 0<=(end-start).days<62 or end>today:fail(422,"progress_invalid_input")
    return start,end


def page_size(limit):
    if type(limit) is not int or not 1<=limit<=MAX_PAGE:fail(422,"progress_invalid_input")
    return limit


def measurement_dto(row,*,categories=None):
    from web.personal_progress_schemas import MeasurementValues
    values={"peso_kg":row.peso_kg,"grasa_corporal_pct":row.grasa_corporal_pct,"masa_magra_kg":row.masa_magra_kg}
    if row.source_kind=="self_reported":
        try:MeasurementValues.model_validate(values)
        except ValueError:fail(409,"progress_source_requires_review")
    if categories is not None:
        values={key:value for key,value in values.items() if categories[key]}
    return {"record_key":row.record_key,"legacy_id":row.id if row.source_kind=="legacy_unverified" else None,
        "version":row.version,"source_profile_id":row.id_cliente,"source_kind":row.source_kind,
        "measured_on":row.measured_on.isoformat() if row.measured_on else None,
        "legacy_recording_timestamp":identity.utc(row.fecha) if row.source_kind=="legacy_unverified" else None,
        "recorded_at":identity.utc(row.recorded_at),"updated_at":identity.utc(row.updated_at),
        "withdrawn_at":identity.utc(row.withdrawn_at),"values":values,
        "units":{"peso_kg":"kg","grasa_corporal_pct":"percent","masa_magra_kg":"kg"},
        "verification":"self_reported" if row.source_kind=="self_reported" else "legacy_requires_review"}


def read_context(db,principal,*,limit=100,after=None):
    page_size(limit)
    with operation(db):
        actor=personal(db,principal)
        query=select(Cliente.id_cliente,Cliente.nombre,Cliente.activo).where(Cliente.gym_id==actor.id,Cliente.deleted_at.is_(None))
        if after is not None:
            if not isinstance(after,str) or not 1<=len(after)<=36:fail(422,"progress_invalid_input")
            query=query.where(Cliente.id_cliente>after)
        rows=db.execute(query.order_by(Cliente.id_cliente).limit(limit+1)).all()
        items=[]
        for row in rows[:limit]:
            try:uuid_text(row.id_cliente);valid=True
            except ValueError:valid=False
            items.append({"id":row.id_cliente,"display_name":row.nombre,"active":bool(row.activo),"can_record":valid and bool(row.activo)})
        return bounded({"today":local_today().isoformat(),"timezone":"America/Mexico_City","profiles":{"items":items,"next_after":rows[limit-1].id_cliente if len(rows)>limit else None},
            "capabilities":{"record_measurements":True,"manage_consent":True,"share_reciprocally":False},"source_profile_required":True})


def _row(db,subject,key,*,lock=False):
    query=select(ClientProgress).join(Cliente,Cliente.id_cliente==ClientProgress.id_cliente).where(
        ClientProgress.gym_id==subject,Cliente.gym_id==subject,Cliente.deleted_at.is_(None),
        ClientProgress.record_key==key,ClientProgress.source_kind=="self_reported")
    if lock:query=query.with_for_update(of=ClientProgress)
    return db.scalar(query.execution_options(populate_existing=True))


def read_measurement(db,principal,key):
    uuid_text(key)
    with operation(db):
        actor=personal(db,principal);row=_row(db,actor.id,key)
        if row is None:fail(404,"progress_source_unavailable")
        return bounded(measurement_dto(row))


def write_measurement(db,principal,key,body,*,now=None):
    uuid_text(key)
    with operation(db):
        actor=personal(db,principal,write=True);stamp=instant(db,now)
        if body.measured_on>local_today(stamp):fail(422,"progress_invalid_input")
        profile(db,actor.id,body.source_profile_id)
        row=_row(db,actor.id,key,lock=True)
        checked_version(row.version if row else 0,body.expected_version)
        if row is not None and (row.withdrawn_at is not None or row.id_cliente!=body.source_profile_id):fail(409,"progress_scope_changed")
        if row is None:
            row=ClientProgress(record_key=key,gym_id=actor.id,id_cliente=body.source_profile_id,source_kind="self_reported",
                recorded_by_id=actor.id,recorded_at=stamp,updated_at=stamp,fecha=stamp,notas="",version=1)
            db.add(row)
        else:row.version+=1;row.updated_at=stamp
        row.measured_on=body.measured_on
        for name,value in body.values.model_dump().items():setattr(row,name,value)
        db.flush();db.refresh(row);result=bounded(measurement_dto(row));commit(db);return result


def withdraw_measurement(db,principal,key,body,*,now=None):
    uuid_text(key)
    with operation(db):
        actor=personal(db,principal,write=True)
        row=_row(db,actor.id,key,lock=True)
        if row is None:fail(404,"progress_source_unavailable")
        checked_version(row.version,body.expected_version)
        if row.withdrawn_at is not None:fail(409,"progress_scope_changed")
        row.version+=1;row.updated_at=instant(db,now);row.withdrawn_at=row.updated_at
        db.flush();db.refresh(row);result=bounded(measurement_dto(row));commit(db);return result


def list_measurements(db,principal,profile_id,*,start=None,end=None,limit=100,cursor=None,now=None):
    uuid_text(profile_id);page_size(limit);start,end=period(start,end,now=now)
    with operation(db):
        actor=personal(db,principal);profile(db,actor.id,profile_id,active=False)
        query=select(ClientProgress).join(Cliente,Cliente.id_cliente==ClientProgress.id_cliente).where(
            ClientProgress.gym_id==actor.id,Cliente.gym_id==actor.id,Cliente.deleted_at.is_(None),ClientProgress.id_cliente==profile_id,
            ClientProgress.source_kind=="self_reported",ClientProgress.withdrawn_at.is_(None),ClientProgress.measured_on>=start,ClientProgress.measured_on<=end)
        scope=[profile_id,start.isoformat(),end.isoformat()]
        if cursor:
            try:
                if not isinstance(cursor,str) or len(cursor)>512:raise ValueError()
                payload=json.loads(base64.urlsafe_b64decode(cursor+"="*(-len(cursor)%4)))
                if payload[:3]!=scope or len(payload)!=5:raise ValueError()
                day=date.fromisoformat(payload[3]);key=uuid_text(payload[4])
            except (ValueError,TypeError,KeyError):fail(409,"progress_scope_changed")
            query=query.where((ClientProgress.measured_on>day)|((ClientProgress.measured_on==day)&(ClientProgress.record_key>key)))
        rows=db.scalars(query.order_by(ClientProgress.measured_on,ClientProgress.record_key).limit(limit+1)).all()
        next_after=None
        if len(rows)>limit:
            last=rows[limit-1];payload=scope+[last.measured_on.isoformat(),last.record_key]
            next_after=base64.urlsafe_b64encode(json.dumps(payload,separators=(",",":")).encode()).decode().rstrip("=")
        return bounded({"items":[measurement_dto(row) for row in rows[:limit]],"next_after":next_after,"from_date":start.isoformat(),"through_date":end.isoformat(),"timezone":"America/Mexico_City"})
