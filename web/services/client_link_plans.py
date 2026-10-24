"""Explicit professional publications and account-scoped member capabilities."""
from datetime import timezone
import hashlib

from sqlalchemy import and_,select
from sqlalchemy.orm import aliased

from web.database.models import (
    Cliente,ClientAccountLink,ClientLinkInvitation,ClientPlanPublication,
    PlanGenerado,StoredObject,UserRole,Usuario,
)
from web.services.client_link_context import (
    audit,bounded,clock,commit,fail,lock_context,lock_contexts,operation,
    professional_scope,recipient_scope,require_professional_after_lock,unavailable,utc,version,
)
from web.services.client_link_invitations import ISSUERS,READERS,_client,_link
from web.services.client_link_projection import ProjectionUnavailable,project_source,read_projection
from web.storage.objects import ObjectDescriptor,ObjectUnavailable,authorize,verify
from web.storage.runtime import get_object_store,storage_configuration

PUBLISHERS={UserRole.OWNER,UserRole.ADMIN,UserRole.NUTRIOLOGO}


def member_link_query(actor_id):
    """The explicit recipient filter is mandatory even for a professional OWNER."""
    owner=aliased(Usuario)
    return select(ClientAccountLink).join(owner,owner.id==ClientAccountLink.gym_id).where(
        ClientAccountLink.user_id==actor_id,ClientAccountLink.status=='active',
        owner.tipo=='gym',owner.role==UserRole.OWNER,owner.team_gym_id.is_(None),owner.activo.is_(True),
        owner.deleted_at.is_(None),owner.invitation_token.is_(None))


def _owned_link(db,actor_id,identity,*,write=False):
    query=member_link_query(actor_id).where(ClientAccountLink.id==identity)
    row=db.scalar(query.with_for_update(read=not write,of=ClientAccountLink).execution_options(populate_existing=True))
    if row is None:unavailable()
    return row


def _read_context(db,principal,identity,*,write=False):
    actor=recipient_scope(db,principal)
    candidate=db.scalar(member_link_query(actor.id).where(ClientAccountLink.id==identity))
    if candidate is None:unavailable()
    actor,_=lock_context(db,principal,actor,candidate.gym_id,write=write)
    link=_owned_link(db,actor.id,identity,write=write)
    return actor,link


def _publication(db,link,identity=None,*,read=True):
    query=select(ClientPlanPublication).where(ClientPlanPublication.gym_id==link.gym_id,
        ClientPlanPublication.client_id==link.client_id,ClientPlanPublication.link_id==link.id,
        ClientPlanPublication.status=='published')
    if identity is not None:query=query.where(ClientPlanPublication.id==identity)
    return db.scalar(query.with_for_update(read=read).execution_options(populate_existing=True))


def _context_dto(link):
    return {'kind':'gym_member','link_id':link.id,'gym_name':link.gym_name,
        'client_display_name':link.client_display_name}


def _capabilities(publication=None,actor=None):
    from web.services.personal_diary_persistence import personal_space_supported
    return {'read_published_plan':True,'download_published_pdf':bool(publication and publication.source_object_id),
        'record_personal_consumption':bool(publication and actor and personal_space_supported(actor)),
        'share_personal_diary':False,'read_shared_progress':False,'manage_clients':False,'manage_team':False}


def list_member_links(db,principal,*,limit=100,after=None):
    if type(limit) is not int or not 1<=limit<=100:fail(422,'member_invalid_page','Revisa la pagina solicitada.')
    with operation(db):
        actor=recipient_scope(db,principal)
        query=member_link_query(actor.id)
        if after is not None:query=query.where(ClientAccountLink.id>after)
        query=query.order_by(ClientAccountLink.id).limit(limit+1)
        candidates=db.scalars(query).all()
        actor,owners=lock_contexts(db,principal,actor,{row.gym_id for row in candidates},write=False)
        rows=db.scalars(query.with_for_update(read=True,of=ClientAccountLink).execution_options(populate_existing=True)).all()
        if any(row.gym_id not in owners for row in rows):fail(409,'member_context_changed','La pertenencia cambio. Vuelve a consultar.')
        has_more=len(rows)>limit;rows=rows[:limit]
        return bounded({'items':[{'context':_context_dto(row),'link_id':row.id,'status':row.status,'version':row.version,
            'capabilities':{'read_published_plan':True,'revoke_link':True,'share_personal_diary':False,'read_shared_progress':False,'manage_clients':False,'manage_team':False}}
            for row in rows],'next_after':rows[-1].id if has_more else None})


def read_member_plan(db,principal,link_id):
    with operation(db):
        actor,link=_read_context(db,principal,link_id)
        publication=_publication(db,link)
        dto=None
        if publication is not None:
            try:content=read_projection(publication.plan_json,publication.plan_sha256)
            except ProjectionUnavailable:fail(409,'member_publication_requires_review','La publicacion requiere una revision autorizada.')
            dto={'id':publication.id,'version':publication.publication_version,'source_plan_id':publication.source_plan_id,
                'published_at':utc(publication.published_at),'plan_schema_version':publication.schema_version,
                'plan':content['plan'],'meta':content['meta'],
                'pdf_url':('/api/usuario/vinculos/'+link.id+'/publicaciones/'+publication.id+'/pdf') if publication.source_object_id else None}
            if publication.source_object_id is None:dto['pdf_unavailable_reason']='legacy_requires_review'
        return bounded({'context':_context_dto(link),'link':{'status':link.status,'version':link.version},
            'capabilities':_capabilities(publication,actor),'publication':dto})


def consumption_source(db,principal,data):
    """Lock exactly the accepted current recipient/publication for a diary write.

    The diary service owns the fresh transaction and COMMIT. Account locks use
    the same total order as R12 before link/publication locks. No professional
    profile or raw Plan is read/written: the triple source FKs and validated
    immutable projection are the publication authority, not a guessed owner.
    """
    _,link=_read_context(db,principal,data.link_id,write=True)
    version(link.version,data.expected_link_version)
    publication=_publication(db,link,data.publication_id,read=False)
    if publication is None:unavailable('publication')
    version(publication.publication_version,data.expected_publication_version)
    try:content=read_projection(publication.plan_json,publication.plan_sha256)
    except ProjectionUnavailable:fail(409,'member_publication_requires_review','La publicacion requiere una revision autorizada.')
    return {'source_plan_id':publication.source_plan_id,'plan':content['plan'],
        'source_context':{'kind':'publication','link_id':link.id,'publication_id':publication.id,
            'link_version':link.version,'publication_version':publication.publication_version,'published_at':utc(publication.published_at)}}


def read_member_pdf(db,principal,link_id,publication_id):
    with operation(db):
        _,link=_read_context(db,principal,link_id)
        publication=_publication(db,link,publication_id)
        if publication is None or publication.source_object_id is None:unavailable('publication')
        try:
            from web.settings import get_settings
            if publication.storage_backend!=storage_configuration(get_settings()).backend:raise ObjectUnavailable('Backend unavailable')
            descriptor=ObjectDescriptor(publication.source_object_id,publication.gym_id,'plan_pdf',publication.object_key,
                publication.content_type,publication.byte_size,publication.sha256)
            authorize(descriptor,publication.gym_id)
            if descriptor.content_type!='application/pdf':raise ObjectUnavailable('Kind unavailable')
            content=get_object_store().read(descriptor,owner_id=publication.gym_id)
            verify(descriptor,content)
            if not content.startswith(b'%PDF-'):raise ObjectUnavailable('Content unavailable')
            return content
        except (ObjectUnavailable,OSError,ValueError,TypeError):unavailable('publication')


def revoke_member_link(db,principal,link_id,expected_version,*,now=None):
    with operation(db):
        actor=recipient_scope(db,principal)
        own=select(ClientAccountLink).where(ClientAccountLink.id==link_id,
            ClientAccountLink.user_id==actor.id,ClientAccountLink.status=='active')
        candidate=db.scalar(own)
        if candidate is None:unavailable()
        actor,_=lock_context(db,principal,actor,candidate.gym_id,write=True,require_eligible_gym=False)
        link=db.scalar(own.with_for_update().execution_options(populate_existing=True))
        if link is None:unavailable()
        version(link.version,expected_version)
        instant=clock(db,now)
        link.status='revoked';link.version+=1;link.revoked_at=instant;link.updated_at=instant
        db.flush()
        # Recipient revocation relies on the active-link predicate. It never
        # gains UPDATE on publications, impersonates the gym, or changes SV.
        public=bounded({'link_id':link.id,'status':'revoked','version':link.version})
        audit(db,actor,'recipient_revoke',link.id)
        commit(db)
        return public


def publish_plan(db,principal,client_id,link_id,data,*,now=None):
    with operation(db):
        actor,gym=professional_scope(db,principal,PUBLISHERS)
        actor,_=lock_context(db,principal,actor,gym,write=True)
        require_professional_after_lock(actor,gym,PUBLISHERS)
        _client(db,gym,client_id)
        link=_link(db,gym,client_id,link_id)
        if link.status not in {'pending','active'}:unavailable()
        version(link.version,data.expected_link_version)
        source=db.scalar(select(PlanGenerado).join(Cliente,and_(Cliente.gym_id==PlanGenerado.gym_id,
            Cliente.id_cliente==PlanGenerado.id_cliente)).where(PlanGenerado.id==data.plan_id,PlanGenerado.gym_id==gym,
                PlanGenerado.id_cliente==client_id,PlanGenerado.deleted_at.is_(None),Cliente.gym_id==gym,
                Cliente.id_cliente==client_id,Cliente.activo.is_(True),Cliente.deleted_at.is_(None))
            .with_for_update(read=True,of=PlanGenerado).execution_options(populate_existing=True))
        if source is None:fail(409,'member_source_unavailable','No fue posible verificar ese plan autorizado.')
        try:
            raw=project_source(source)
            descriptor=None
            if source.pdf_object_id is not None:
                from web.settings import get_settings
                row=db.scalar(select(StoredObject).where(StoredObject.id==source.pdf_object_id,StoredObject.gym_id==gym)
                    .with_for_update(read=True).execution_options(populate_existing=True))
                if (row is None or row.status!='ready' or row.kind!='plan_pdf'
                        or row.storage_backend!=storage_configuration(get_settings()).backend):raise ObjectUnavailable('Object unavailable')
                descriptor=ObjectDescriptor(row.id,row.gym_id,row.kind,row.key,row.content_type,row.byte_size,row.sha256)
                authorize(descriptor,gym)
        except (ProjectionUnavailable,ObjectUnavailable,ValueError,TypeError):
            fail(409,'member_source_unavailable','No fue posible verificar ese plan autorizado.')
        current=_publication(db,link,read=False)
        actual=current.publication_version if current is not None else 0
        actual_id=current.id if current is not None else None
        if actual!=data.expected_publication_version or actual_id!=data.expected_publication_id:
            fail(409,'member_version_conflict','La publicacion cambio. Vuelve a consultarla.')
        instant=clock(db,now)
        if current is not None:
            version(current.publication_version,data.expected_publication_version)
            current.status='withdrawn';current.publication_version+=1;current.withdrawn_at=instant
            db.flush()
            from web.services.product_facts import assignment_withdrawn
            assignment_withdrawn(db, current)
        publication=ClientPlanPublication(gym_id=gym,client_id=client_id,link_id=link.id,source_plan_id=source.id,
            schema_version=1,publication_version=1,status='published',published_by=actor.id,published_at=instant,
            plan_json=raw,plan_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
            source_object_id=descriptor.id if descriptor else None,object_key=descriptor.key if descriptor else None,
            content_type=descriptor.content_type if descriptor else None,byte_size=descriptor.byte_size if descriptor else None,
            sha256=descriptor.sha256 if descriptor else None,storage_backend=row.storage_backend if descriptor else None)
        db.add(publication);db.flush()
        # PostgreSQL canonizes JSON/hash/time in the trigger. Re-read that exact
        # row under the same owned transaction before exposing its DTO.
        publication=db.scalar(select(ClientPlanPublication).where(ClientPlanPublication.id==publication.id,
            ClientPlanPublication.gym_id==gym,ClientPlanPublication.client_id==client_id,
            ClientPlanPublication.link_id==link.id).execution_options(populate_existing=True))
        public=bounded({'publication_id':publication.id,'version':publication.publication_version,'link_id':link.id,
            'link_version':link.version,'source_plan_id':source.id,'published_at':utc(publication.published_at),
            'download_published_pdf':publication.source_object_id is not None})
        if publication.source_object_id is None:public['pdf_unavailable_reason']='legacy_requires_review'
        from web.services.product_facts import assignment_published
        assignment_published(db, publication)
        audit(db,actor,'publish',publication.id)
        commit(db)
        return public


def withdraw_plan(db,principal,client_id,link_id,publication_id,expected_version,*,now=None):
    with operation(db):
        actor,gym=professional_scope(db,principal,PUBLISHERS)
        actor,_=lock_context(db,principal,actor,gym,write=True)
        require_professional_after_lock(actor,gym,PUBLISHERS)
        _client(db,gym,client_id,active=False)
        link=_link(db,gym,client_id,link_id)
        publication=_publication(db,link,publication_id,read=False)
        if publication is None:unavailable('publication')
        version(publication.publication_version,expected_version)
        publication.status='withdrawn';publication.publication_version+=1;publication.withdrawn_at=clock(db,now)
        db.flush()
        public=bounded({'publication_id':publication.id,'status':'withdrawn','version':publication.publication_version})
        from web.services.product_facts import assignment_withdrawn
        assignment_withdrawn(db, publication)
        audit(db,actor,'withdraw',publication.id)
        commit(db)
        return public


def revoke_professional_link(db,principal,client_id,link_id,expected_version,*,now=None):
    with operation(db):
        actor,gym=professional_scope(db,principal,ISSUERS)
        actor,_=lock_context(db,principal,actor,gym,write=True)
        require_professional_after_lock(actor,gym,ISSUERS)
        _client(db,gym,client_id,active=False)
        link=_link(db,gym,client_id,link_id)
        if link.status not in {'pending','active'}:unavailable()
        version(link.version,expected_version)
        invitation=db.scalar(select(ClientLinkInvitation).where(ClientLinkInvitation.link_id==link.id,
            ClientLinkInvitation.gym_id==gym,ClientLinkInvitation.client_id==client_id).with_for_update())
        publication=_publication(db,link,read=False)
        instant=clock(db,now)
        link.status='revoked';link.version+=1;link.revoked_at=instant;link.updated_at=instant
        if invitation is not None and invitation.status=='pending':
            version(invitation.version,invitation.version)
            invitation.status='revoked';invitation.version+=1;invitation.revoked_at=instant;invitation.updated_at=instant
        if publication is not None:
            version(publication.publication_version,publication.publication_version)
            publication.status='withdrawn';publication.publication_version+=1;publication.withdrawn_at=instant
        db.flush()
        if publication is not None:
            from web.services.product_facts import assignment_withdrawn
            assignment_withdrawn(db, publication)
        public=bounded({'link_id':link.id,'status':'revoked','version':link.version})
        audit(db,actor,'professional_revoke',link.id)
        commit(db)
        return public


def professional_link_state(db,principal,client_id,*,limit=100,after=None):
    if type(limit) is not int or not 1<=limit<=100:fail(422,'member_invalid_page','Revisa la pagina solicitada.')
    with operation(db):
        actor,gym=professional_scope(db,principal,READERS)
        actor,_=lock_context(db,principal,actor,gym,write=False)
        require_professional_after_lock(actor,gym,READERS)
        client=db.scalar(select(Cliente).where(Cliente.gym_id==gym,Cliente.id_cliente==client_id,Cliente.deleted_at.is_(None)))
        if client is None:unavailable()
        query=select(ClientAccountLink,ClientLinkInvitation.id.label('invitation_id'),
            ClientLinkInvitation.status.label('invitation_status'),ClientLinkInvitation.version.label('invitation_version'),
            ClientLinkInvitation.expires_at,ClientPlanPublication.id.label('publication_id'),
            ClientPlanPublication.publication_version,ClientPlanPublication.source_plan_id,ClientPlanPublication.published_at,
            ClientPlanPublication.source_object_id.is_not(None).label('has_pdf')).outerjoin(ClientLinkInvitation,and_(ClientLinkInvitation.link_id==ClientAccountLink.id,
                ClientLinkInvitation.gym_id==ClientAccountLink.gym_id,ClientLinkInvitation.client_id==ClientAccountLink.client_id))
        query=query.outerjoin(ClientPlanPublication,and_(ClientPlanPublication.link_id==ClientAccountLink.id,
            ClientPlanPublication.gym_id==ClientAccountLink.gym_id,ClientPlanPublication.client_id==ClientAccountLink.client_id,
            ClientPlanPublication.status=='published'))
        query=query.where(ClientAccountLink.gym_id==gym,ClientAccountLink.client_id==client_id)
        if after is not None:query=query.where(ClientAccountLink.id>after)
        rows=db.execute(query.order_by(ClientAccountLink.id).limit(limit+1)).all()
        has_more=len(rows)>limit;rows=rows[:limit]
        instant=clock(db)
        def invitation_state(row):
            expires=row.expires_at
            if expires is not None:
                expires=expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires.astimezone(timezone.utc)
            return 'expired' if row.invitation_status=='pending' and expires is not None and expires<=instant else row.invitation_status
        return bounded({'client_id':client_id,'capabilities':{'issue_invitation':actor.role in ISSUERS and bool(client.activo),
            'rotate_invitation':actor.role in ISSUERS and bool(client.activo),'revoke_link':actor.role in ISSUERS,
            'publish_plan':actor.role in PUBLISHERS and bool(client.activo),'withdraw_publication':actor.role in PUBLISHERS},
            'items':[{'link_id':row[0].id,'status':row[0].status,'version':row[0].version,
            'accepted_at':utc(row[0].accepted_at),'revoked_at':utc(row[0].revoked_at),
            'invitation_id':row.invitation_id,'invitation_status':invitation_state(row),
            'invitation_version':row.invitation_version,'expires_at':utc(row.expires_at),
            'publication':{'id':row.publication_id,'version':row.publication_version,'source_plan_id':row.source_plan_id,
                'published_at':utc(row.published_at),'download_published_pdf':bool(row.has_pdf)} if row.publication_id else None} for row in rows],
            'next_after':rows[-1][0].id if has_more else None})
