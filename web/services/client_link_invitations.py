"""Explicit recipient invitations; account existence is never consulted at issue."""
from datetime import timedelta,timezone
import hashlib
import json
import secrets
from urllib.parse import urlencode

from sqlalchemy import or_,select,update

from web.database.models import Cliente,ClientAccountLink,ClientLinkInvitation,GymProfile,UserRole
from web.services.client_link_context import (
    audit,bounded,clock,commit,digest,fail,install_proof,lock_context,operation,
    professional_scope,recipient_scope,require_professional_after_lock,unavailable,utc,version,
)
from web.services.client_link_mail import InvitationMessage

ISSUERS={UserRole.OWNER,UserRole.ADMIN}
READERS={*ISSUERS,UserRole.NUTRIOLOGO}
INVITATION_LIFETIME=timedelta(days=7)


def _client(db,gym,client_id,*,active=True):
    query=select(Cliente).where(Cliente.gym_id==gym,Cliente.id_cliente==client_id,Cliente.deleted_at.is_(None))
    if active:query=query.where(Cliente.activo.is_(True))
    client=db.scalar(query.with_for_update().execution_options(populate_existing=True))
    if client is None:unavailable()
    return client


def _link(db,gym,client_id,identity,*,read=False):
    row=db.scalar(select(ClientAccountLink).where(ClientAccountLink.id==identity,ClientAccountLink.gym_id==gym,
        ClientAccountLink.client_id==client_id).with_for_update(read=read).execution_options(populate_existing=True))
    if row is None:unavailable()
    return row


def _public(invitation,link):
    return bounded({'invitation_id':invitation.id,'link_id':link.id,'status':invitation.status,
        'link_status':link.status,'version':invitation.version,'link_version':link.version,
        'expires_at':utc(invitation.expires_at),'delivery_status':'not_confirmed'})


def _request_hash(gym,client_id,email):
    raw=json.dumps({'purpose':'client-account-issue-v1','gym':gym,'client':client_id,'recipient':email},
        ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _message(origin,token,recipient,gym_name):
    return InvitationMessage(recipient,gym_name,origin+'/auth/accept-client-link#'+urlencode({'token':token}))


def issue_invitation(db,principal,client_id,data,origin,*,now=None):
    with operation(db):
        actor,gym=professional_scope(db,principal,ISSUERS)
        actor,owner=lock_context(db,principal,actor,gym,write=True)
        require_professional_after_lock(actor,gym,ISSUERS)
        client=_client(db,gym,client_id)
        payload_hash=_request_hash(gym,client_id,data.recipient_email)
        existing=db.scalar(select(ClientLinkInvitation).where(ClientLinkInvitation.gym_id==gym,
            ClientLinkInvitation.request_key==data.request_key))
        if existing is not None:
            if existing.payload_hash!=payload_hash or existing.client_id!=client_id:
                fail(409,'member_request_key_conflict','La clave ya corresponde a otra solicitud.')
            link=_link(db,gym,client_id,existing.link_id)
            return _public(existing,link),None
        profile=db.scalar(select(GymProfile).where(GymProfile.gym_id==gym))
        gym_name=(profile.nombre_negocio if profile is not None else None) or owner.nombre
        if (not isinstance(gym_name,str) or not 1<=len(gym_name)<=255
                or not isinstance(client.nombre,str) or not 1<=len(client.nombre)<=200):
            fail(409,'member_state_requires_review','El contexto requiere una revision autorizada.')
        instant=clock(db,now)
        link=ClientAccountLink(gym_id=gym,client_id=client_id,status='pending',version=1,
            gym_name=gym_name,client_display_name=client.nombre,created_at=instant,updated_at=instant)
        db.add(link);db.flush()
        token=secrets.token_urlsafe(32)
        invitation=ClientLinkInvitation(gym_id=gym,client_id=client_id,link_id=link.id,
            recipient_email=data.recipient_email,token_hash=digest(token),expires_at=instant+INVITATION_LIFETIME,
            status='pending',issued_by=actor.id,version=1,request_key=data.request_key,payload_hash=payload_hash,
            created_at=instant,updated_at=instant)
        db.add(invitation);db.flush()
        public=_public(invitation,link)
        message=_message(origin,token,data.recipient_email,gym_name)
        audit(db,actor,'issue',link.id)
        commit(db)
        return public,message


def resend_invitation(db,principal,client_id,invitation_id,expected_version,origin,*,now=None):
    with operation(db):
        actor,gym=professional_scope(db,principal,ISSUERS)
        actor,_=lock_context(db,principal,actor,gym,write=True)
        require_professional_after_lock(actor,gym,ISSUERS)
        _client(db,gym,client_id)
        candidate=db.scalar(select(ClientLinkInvitation).where(ClientLinkInvitation.id==invitation_id,
            ClientLinkInvitation.gym_id==gym,ClientLinkInvitation.client_id==client_id))
        if candidate is None:unavailable('invitation')
        link=_link(db,gym,client_id,candidate.link_id)
        invitation=db.scalar(select(ClientLinkInvitation).where(ClientLinkInvitation.id==invitation_id,
            ClientLinkInvitation.gym_id==gym,ClientLinkInvitation.client_id==client_id,
            ClientLinkInvitation.link_id==link.id).with_for_update().execution_options(populate_existing=True))
        if invitation is None or invitation.status!='pending' or link.status!='pending':unavailable('invitation')
        version(invitation.version,expected_version)
        instant=clock(db,now);token=secrets.token_urlsafe(32)
        invitation.token_hash=digest(token);invitation.expires_at=instant+INVITATION_LIFETIME
        invitation.version+=1;invitation.updated_at=instant
        db.flush()
        public=_public(invitation,link)
        message=_message(origin,token,invitation.recipient_email,link.gym_name)
        audit(db,actor,'rotate',link.id)
        commit(db)
        return public,message


def _recipient_invitation(db,actor,hashed,*,lock=False):
    query=select(ClientLinkInvitation).where(ClientLinkInvitation.token_hash==hashed,
        ClientLinkInvitation.recipient_email==actor.email,
        or_(ClientLinkInvitation.status!='consumed',ClientLinkInvitation.consumed_by==actor.id))
    if lock:query=query.with_for_update()
    invitation=db.scalar(query.execution_options(populate_existing=True))
    if invitation is None:unavailable('invitation')
    return invitation


def _verified_invitation(db,principal,token,*,write):
    actor=recipient_scope(db,principal);hashed=install_proof(db,actor,token)
    initial=_recipient_invitation(db,actor,hashed)
    initial_gym,initial_client,initial_link=initial.gym_id,initial.client_id,initial.link_id
    actor,_=lock_context(db,principal,actor,initial_gym,write=write)
    # Re-read exact hash/email after all account locks, without accepting Gscope
    # as recipient authority when actor.id is also the professional gym ID.
    current=_recipient_invitation(db,actor,hashed)
    if (current.gym_id,current.client_id,current.link_id)!=(initial_gym,initial_client,initial_link):unavailable('invitation')
    link=_link(db,initial_gym,initial_client,initial_link,read=not write)
    invitation=_recipient_invitation(db,actor,hashed,lock=write)
    if invitation.link_id!=link.id:unavailable('invitation')
    return actor,invitation,link,hashed


def inspect_invitation(db,principal,token,*,now=None):
    with operation(db):
        _,invitation,link,_=_verified_invitation(db,principal,token,write=False)
        instant=clock(db,now)
        expires=invitation.expires_at.replace(tzinfo=timezone.utc) if invitation.expires_at.tzinfo is None else invitation.expires_at.astimezone(timezone.utc)
        state='expired' if invitation.status=='pending' and expires<=instant else invitation.status
        return bounded({'status':state,'version':invitation.version,'expires_at':utc(invitation.expires_at),
            'link_id':link.id,'context':{'kind':'gym_member','gym_name':link.gym_name,'client_display_name':link.client_display_name},
            'can_accept':state=='pending' and link.status=='pending'})


def accept_invitation(db,principal,data,*,now=None):
    with operation(db):
        if data.confirm is not True:fail(422,'member_invalid_input','Confirma expresamente la vinculacion.')
        actor,invitation,link,hashed=_verified_invitation(db,principal,data.token,write=True)
        if invitation.status=='consumed':fail(409,'member_invitation_consumed','Esta invitacion ya fue utilizada.')
        if invitation.status!='pending' or link.status!='pending':unavailable('invitation')
        version(invitation.version,data.expected_version);version(link.version,link.version)
        instant=clock(db,now)
        expires=invitation.expires_at.replace(tzinfo=timezone.utc) if invitation.expires_at.tzinfo is None else invitation.expires_at.astimezone(timezone.utc)
        if expires<=instant:fail(410,'member_invitation_expired','La invitacion vencio. Solicita un reenvio al gimnasio.')
        used=db.execute(update(ClientLinkInvitation).where(ClientLinkInvitation.id==invitation.id,
            ClientLinkInvitation.gym_id==invitation.gym_id,ClientLinkInvitation.client_id==link.client_id,
            ClientLinkInvitation.link_id==link.id,ClientLinkInvitation.token_hash==hashed,
            ClientLinkInvitation.recipient_email==actor.email,ClientLinkInvitation.status=='pending',
            ClientLinkInvitation.version==data.expected_version,ClientLinkInvitation.expires_at>instant)
            .values(status='consumed',consumed_by=actor.id,consumed_at=instant,version=data.expected_version+1,updated_at=instant)
            .returning(ClientLinkInvitation.id,ClientLinkInvitation.consumed_at)
            .execution_options(synchronize_session=False)).one_or_none()
        if used is None:fail(409,'member_version_conflict','La invitacion cambio. Vuelve a consultarla.')
        updated=db.execute(update(ClientAccountLink).where(ClientAccountLink.id==link.id,ClientAccountLink.gym_id==invitation.gym_id,
            ClientAccountLink.client_id==invitation.client_id,ClientAccountLink.status=='pending',ClientAccountLink.user_id.is_(None),
            ClientAccountLink.version==link.version).values(status='active',user_id=actor.id,accepted_at=used.consumed_at,
                version=link.version+1,updated_at=instant).returning(ClientAccountLink.id)
            .execution_options(synchronize_session=False)).scalar_one_or_none()
        if updated is None:fail(409,'member_version_conflict','El vinculo cambio. Vuelve a consultarlo.')
        owned=db.scalar(select(ClientAccountLink).where(ClientAccountLink.id==updated,ClientAccountLink.user_id==actor.id,
            ClientAccountLink.status=='active').execution_options(populate_existing=True))
        if owned is None:unavailable()
        public=bounded({'link_id':owned.id,'status':owned.status,'version':owned.version,
            'context':{'kind':'gym_member','gym_name':owned.gym_name,'client_display_name':owned.client_display_name}})
        from web.services.product_facts import link_accepted
        link_accepted(db, owned)
        audit(db,actor,'accept',owned.id)
        commit(db)
        return public
