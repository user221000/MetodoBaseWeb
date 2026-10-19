"""Exact-link, append-only consent and minimal live professional projections.

No reciprocal portfolio permission, blanket diary access or clinical inference.
"""
from datetime import date
import uuid

from sqlalchemy import func, select

from web.database.models import ClientAccountLink, Cliente, ProgressConsent, Subscription, Usuario, UserRole
from web.personal_progress_schemas import uuid_text
from web.services import client_link_context as identity
from web.services import personal_progress as own

READERS={UserRole.OWNER,UserRole.ADMIN,UserRole.NUTRIOLOGO}
_SCOPE=("link_id","gym_id","client_id","user_id","link_version","protocol","source_profile_id",
    "share_weight","share_body_fat","share_lean_mass","share_completion","from_date","through_date")


def latest(db,link_id,*,user_id=None,lock=False):
    query=select(ProgressConsent).where(ProgressConsent.link_id==link_id)
    if user_id is not None:query=query.where(ProgressConsent.user_id==user_id)
    query=query.order_by(ProgressConsent.version.desc()).limit(1)
    if lock:query=query.with_for_update(read=True)
    return db.scalar(query.execution_options(populate_existing=True))


def consent_dto(row):
    if row is None:return None
    return {"id":row.id,"version":row.version,"event":row.event,"protocol":row.protocol,"link_version":row.link_version,
        "source_profile_id":row.source_profile_id,"categories":{"weight":row.share_weight,"body_fat":row.share_body_fat,
            "lean_mass":row.share_lean_mass,"completion":row.share_completion},
        "from_date":row.from_date.isoformat(),"through_date":row.through_date.isoformat() if row.through_date else None,
        "ongoing":row.through_date is None,"created_at":identity.utc(row.created_at)}


def _cas(row,expected_id,expected_version):
    if (row.id if row else None)!=expected_id:own.fail(409,"progress_version_conflict")
    own.checked_version(row.version if row else 0,expected_version)


def _own_link(db,actor_id,link_id,*,lock=False):
    query=select(ClientAccountLink).where(ClientAccountLink.id==link_id,ClientAccountLink.user_id==actor_id)
    if lock:query=query.with_for_update(read=True)
    row=db.scalar(query.execution_options(populate_existing=True))
    if row is None:own.fail(404,"progress_consent_unavailable")
    return row


def _effective(db,row,link):
    if row is None or row.event!="grant" or link is None or link.status!="active" or link.version!=row.link_version:return False
    if not identity.canonical_gym(db.get(Usuario,row.gym_id,populate_existing=True)):return False
    if row.source_profile_id is not None:
        return bool(db.scalar(select(Cliente.id).where(Cliente.gym_id==row.user_id,Cliente.id_cliente==row.source_profile_id,
            Cliente.activo.is_(True),Cliente.deleted_at.is_(None))))
    return True


def read_own_consent(db,principal,link_id):
    uuid_text(link_id)
    with own.operation(db):
        actor=own.retirement_actor(db,principal)
        row=latest(db,link_id,user_id=actor.id)
        if actor.role==UserRole.OWNER:
            if row is None:own.fail(404,"progress_consent_unavailable")
            return own.bounded({"link_id":link_id,"consent":consent_dto(row),"version":row.version,
                "effective":None,"scope":"own_consent_metadata_only","capabilities":{"withdraw":row.event=="grant","grant":False}})
        # A retained own event remains discoverable without a live source link.
        link=db.scalar(select(ClientAccountLink).where(ClientAccountLink.id==link_id,ClientAccountLink.user_id==actor.id))
        if row is None and link is None:own.fail(404,"progress_consent_unavailable")
        return own.bounded({"link_id":link_id,"consent":consent_dto(row),"version":row.version if row else 0,
            "effective":_effective(db,row,link),"capabilities":{"withdraw":bool(row and row.event=="grant"),
                "grant":bool(link and link.status=="active" and identity.canonical_gym(db.get(Usuario,link.gym_id)))}})


def list_own_consents(db,principal,*,limit=100,after=None):
    own.page_size(limit)
    if after is not None:uuid_text(after)
    with own.operation(db):
        actor=own.retirement_actor(db,principal)
        maximum=select(ProgressConsent.link_id,func.max(ProgressConsent.version).label("version")).where(
            ProgressConsent.user_id==actor.id).group_by(ProgressConsent.link_id).subquery()
        query=select(ProgressConsent).join(maximum,(ProgressConsent.link_id==maximum.c.link_id)&(ProgressConsent.version==maximum.c.version)).where(ProgressConsent.user_id==actor.id)
        if after is not None:query=query.where(ProgressConsent.link_id>after)
        rows=db.scalars(query.order_by(ProgressConsent.link_id).limit(limit+1)).all()
        return own.bounded({"items":[{"link_id":row.link_id,"consent":consent_dto(row),
            "capabilities":{"withdraw":row.event=="grant"}} for row in rows[:limit]],
            "next_after":rows[limit-1].link_id if len(rows)>limit else None})


def grant_consent(db,principal,link_id,body,*,now=None):
    uuid_text(link_id)
    with own.operation(db):
        actor=identity.recipient_scope(db,principal);candidate=_own_link(db,actor.id,link_id)
        actor=own.personal(db,principal,write=True,gyms={candidate.gym_id})
        if body.source_profile_id is not None:own.profile(db,actor.id,body.source_profile_id)
        link=_own_link(db,actor.id,link_id,lock=True)
        if link.status!="active" or link.version!=body.expected_link_version:own.fail(409,"progress_scope_changed")
        prior=latest(db,link_id,user_id=actor.id,lock=True);_cas(prior,body.expected_consent_id,body.expected_version)
        categories=body.categories
        row=ProgressConsent(id=str(uuid.uuid4()),link_id=link.id,gym_id=link.gym_id,client_id=link.client_id,user_id=actor.id,
            version=body.expected_version+1,link_version=link.version,event="grant",protocol=body.protocol,
            source_profile_id=body.source_profile_id,share_weight=categories.weight,share_body_fat=categories.body_fat,
            share_lean_mass=categories.lean_mass,share_completion=categories.completion,from_date=body.from_date,
            through_date=body.through_date,created_at=own.instant(db,now))
        db.add(row);db.flush();db.refresh(row)
        result=own.bounded({"link_id":link.id,"consent":consent_dto(row),"version":row.version,"effective":True,
            "capabilities":{"withdraw":True,"grant":True}})
        own.commit(db);return result


def withdraw_consent(db,principal,link_id,body,*,now=None):
    uuid_text(link_id)
    with own.operation(db):
        actor=own.retirement_actor(db,principal,write=True)
        prior=latest(db,link_id,user_id=actor.id,lock=True)
        if prior is None:own.fail(404,"progress_consent_unavailable")
        _cas(prior,body.expected_consent_id,body.expected_version)
        if prior.event!="grant":own.fail(409,"progress_scope_changed")
        row=ProgressConsent(id=str(uuid.uuid4()),version=prior.version+1,event="withdraw",created_at=own.instant(db,now),
            **{name:getattr(prior,name) for name in _SCOPE})
        db.add(row);db.flush();db.refresh(row)
        result=own.bounded({"link_id":link_id,"consent":consent_dto(row),"version":row.version,"effective":False,
            "capabilities":{"withdraw":False,"grant":False}})
        own.commit(db);return result


def professional_context(db,principal,client_id,link_id=None):
    """All accounts first, including recipient's canonical parent, no late User lock."""
    actor,gym=identity.professional_scope(db,principal,READERS)
    candidate=None;recipient=None
    if link_id is not None:
        candidate=db.scalar(select(ClientAccountLink).where(ClientAccountLink.id==link_id,
            ClientAccountLink.gym_id==gym,ClientAccountLink.client_id==client_id,ClientAccountLink.status=="active"))
        if candidate is None or candidate.user_id is None:own.fail(404,"progress_source_unavailable")
        recipient=db.get(Usuario,candidate.user_id)
    ids={gym}
    if recipient is not None:
        ids.add(recipient.id)
        if recipient.team_gym_id:ids.add(recipient.team_gym_id)
    actor,participants=identity.lock_contexts(db,principal,actor,ids,write=False,require_eligible_gym=False)
    identity.require_professional_after_lock(actor,gym,READERS)
    if not identity.canonical_gym(participants[gym]):own.fail(404,"progress_source_unavailable")
    if recipient is not None:
        recipient=participants[recipient.id]
        if recipient.team_gym_id and recipient.team_gym_id not in participants:own.fail(409,"progress_scope_changed")
        if not identity.valid_actor(recipient,participants.get(recipient.team_gym_id)) or recipient.role==UserRole.OWNER:
            own.fail(404,"progress_source_unavailable")
    # The published catalog is the existing entitlement, not a new price/right.
    from core.plan_catalog import get_plan_catalog
    from core.subscription_policy import gym_subscription_is_current
    subscription=db.scalar(select(Subscription).where(Subscription.gym_id==gym).with_for_update(read=True).execution_options(populate_existing=True))
    if (subscription is None or not gym_subscription_is_current(plan=subscription.plan,status=subscription.status,
            period_end=subscription.current_period_end,trial_end=subscription.trial_end)
            or not get_plan_catalog("web").get(subscription.plan,{}).get("progresion_clientes",False)):
        own.fail(402,"progress_plan_required")
    client=own.profile(db,gym,client_id)
    link=None
    if link_id is not None:
        link=db.scalar(select(ClientAccountLink).where(ClientAccountLink.id==link_id,ClientAccountLink.gym_id==gym,
            ClientAccountLink.client_id==client.id_cliente,ClientAccountLink.user_id==recipient.id,ClientAccountLink.status=="active")
            .with_for_update(read=True).execution_options(populate_existing=True))
        if link is None:own.fail(404,"progress_source_unavailable")
    return actor,gym,link


def read_professional_consent(db,principal,client_id,link_id):
    with own.operation(db):
        _,_,link=professional_context(db,principal,client_id,link_id)
        row=latest(db,link.id,lock=True)
        return own.bounded({"link_id":link.id,"link_version":link.version,"consent":consent_dto(row),
            "today":own.local_today().isoformat(),"timezone":"America/Mexico_City",
            "capabilities":{"read_shared_progress":bool(row and row.event=="grant" and row.link_version==link.version)}})


def authorized_consent(db,link,expected_id,expected_version,expected_link,start,end):
    row=latest(db,link.id,lock=True)
    if (row is None or row.event!="grant" or row.id!=expected_id or row.version!=expected_version
            or row.link_version!=link.version or link.version!=expected_link or row.user_id!=link.user_id
            or row.gym_id!=link.gym_id or row.client_id!=link.client_id):own.fail(409,"progress_scope_changed")
    if start<row.from_date or row.through_date is not None and end>row.through_date:own.fail(409,"progress_scope_changed")
    return row
