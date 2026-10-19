"""Populated revision29 additions; no edits or retargeting of historical restore."""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_provider_subjects import application_engine
from web.client_link_schemas import InvitationAccept,InvitationIssue,PlanPublication
from web.database.models import Cliente,ClientAccountLink,ClientLinkInvitation,ClientPlanPublication,PlanGenerado,StoredObject,Usuario,UserRole
from web.database.tenant_context import tenant_scope
from web.services import client_link_invitations as invitations,client_link_plans as plans
from web.services.client_link_projection import read_projection
from web.storage.local import LocalObjectStore
from web.storage.objects import describe


def _principal(identity):return {'id':identity,'session_version':0}


def populate_links29(source_url,admin,objects):
    ids={key:str(uuid.uuid4()) for key in ('gym_a','gym_b','recipient','other','pending_user')}
    clients={key:str(uuid.uuid4()) for key in ('active','pending','revoked','external','owner_self','other_recipient')}
    with Session(admin) as db:
        for key,identity in ids.items():
            owner=key.startswith('gym_')
            db.add(Usuario(id=identity,email=identity+'@example.invalid',password_hash='synthetic-r12-restore',
                nombre='Synthetic R12 restore',tipo='gym' if owner else 'usuario',role=UserRole.OWNER if owner else UserRole.VIEWER))
        db.flush()
        for label,identity in clients.items():
            db.add(Cliente(gym_id=ids['gym_b'] if label=='external' else ids['gym_a'],id_cliente=identity,nombre='Synthetic '+label,activo=True))
        db.commit()
    app=application_engine(source_url,admin)
    store=LocalObjectStore(objects);tokens=[];links={};publications={};documents={}
    def issue(label,recipient):
        gym=ids['gym_b'] if label=='external' else ids['gym_a']
        with tenant_scope(gym),Session(app) as db:
            result,message=invitations.issue_invitation(db,_principal(gym),clients[label],
                InvitationIssue(recipient_email=ids[recipient]+'@example.invalid',request_key='restore29-'+label),
                'https://restore.example.invalid')
        proof=parse_qs(urlsplit(message.url).fragment)['token'][0];tokens.append(proof)
        links[label]={'gym':gym,'recipient':ids[recipient],'link':result['link_id'],'invitation':result['invitation_id'],'token':proof,'version':1}
        return links[label]
    def accept(label):
        link=links[label]
        with tenant_scope(link['recipient']),Session(app) as db:
            result=invitations.accept_invitation(db,_principal(link['recipient']),InvitationAccept(token=link['token'],expected_version=1,confirm=True))
        link['version']=result['version']
    def publish(label,marker,expected=0,observed_id=None):
        link=links[label];content=b'%PDF-1.7\nrestore29 '+marker.encode()+b'\n%%EOF'
        descriptor=describe(link['gym'],'plan_pdf',content,'application/pdf')
        store.put(descriptor,content,owner_id=link['gym'])
        with Session(admin) as db:
            db.add(StoredObject(id=descriptor.id,gym_id=link['gym'],kind='plan_pdf',key=descriptor.key,
                content_type=descriptor.content_type,byte_size=descriptor.byte_size,sha256=descriptor.sha256,storage_backend='local',status='ready'))
            db.flush()
            raw=json.dumps({meal:{'kcal_objetivo':100,'kcal_real':100,'alimentos':{marker:50}}
                for meal in ('desayuno','almuerzo','comida','cena')})
            plan=PlanGenerado(gym_id=link['gym'],id_cliente=clients[label],pdf_object_id=descriptor.id,plan_json=raw)
            db.add(plan);db.commit();plan_id=plan.id
        with tenant_scope(link['gym']),Session(app) as db:
            publication=plans.publish_plan(db,_principal(link['gym']),clients[label],link['link'],
                PlanPublication(plan_id=plan_id,expected_link_version=link['version'],expected_publication_version=expected,
                    expected_publication_id=observed_id))
        documents[publication['publication_id']]={'bytes_sha256':hashlib.sha256(content).hexdigest(),'content':content,'key':descriptor.key,'object_id':descriptor.id,'plan_id':plan_id}
        publications[marker]=publication['publication_id']
        return publication
    try:
        issue('pending','pending_user')
        for label,recipient in [('active','recipient'),('revoked','other'),('external','gym_a'),('owner_self','gym_a')]:
            issue(label,recipient);accept(label)
        old=publish('active','withdrawn-old')
        publish('active','current-active',1,old['publication_id'])
        publish('revoked','withdrawn-revoked')
        with tenant_scope(ids['gym_a']),Session(app) as db:
            result=plans.revoke_professional_link(db,_principal(ids['gym_a']),clients['revoked'],links['revoked']['link'],2)
            assert result['status']=='revoked'
        publish('external','current-external-owner')
        publish('owner_self','current-own-owner')
        issue('other_recipient','other');accept('other_recipient')
    finally:app.dispose()
    with Session(admin) as db:
        assert db.query(ClientAccountLink).count()==6 and db.query(ClientLinkInvitation).count()==6
        assert db.query(ClientPlanPublication).filter_by(status='published').count()==3
        assert db.query(ClientPlanPublication).filter_by(status='withdrawn').count()==2
    return {'ids':ids,'clients':clients,'links':links,'publications':publications,'documents':documents,'tokens':tokens}


def verify_restored_links29(admin,app,restored_objects,expected,monkeypatch):
    from web.settings import get_settings
    from web.database.alembic.member_link_security_v1 import member_link_security_signature
    from web.database.member_link_policy_v1 import MEMBER_LINK_TABLES
    ids=expected['ids'];links=expected['links'];documents=expected['documents']
    with app.connect() as db:
        assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one())==(False,False,False,False)
        assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND pg_has_role(current_user,relowner,'MEMBER'))"))
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
        assert db.scalar(text('SELECT count(*) FROM client_account_links'))==0
        assert db.scalar(text('SELECT count(*) FROM client_plan_publications'))==0
    with admin.connect() as db:
        signature=member_link_security_signature(db)
        assert signature['functions'] and all(row[3] is False and row[4]==['search_path=pg_catalog'] for row in signature['functions'])
        assert all(row[1] and row[2] for row in db.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname=ANY(:tables)"),{'tables':sorted(MEMBER_LINK_TABLES)}))
        assert db.scalar(text("SELECT condeferrable AND condeferred FROM pg_constraint WHERE conname='fk_client_invitation_consumption'")) is True
    settings=get_settings()
    with monkeypatch.context() as scoped:
        # Reconstruct from restored private files. No original adapter instance,
        # SQL source Plan access, or original descriptor object is used to read.
        scoped.setattr(settings,'OBJECT_STORAGE_LOCAL_ROOT',str(Path(restored_objects)))
        scoped.setattr(settings,'OBJECT_STORAGE_BACKEND','local')
        for label,marker in [('active','current-active'),('external','current-external-owner'),('owner_self','current-own-owner')]:
            link=links[label];identity=expected['publications'][marker]
            with tenant_scope(link['recipient']),Session(app) as db:
                result=plans.read_member_plan(db,_principal(link['recipient']),link['link'])
                assert result['publication']['id']==identity
                assert result['publication']['plan']['desayuno']['alimentos']=={marker:50}
            with tenant_scope(link['recipient']),Session(app) as db:
                content=plans.read_member_pdf(db,_principal(link['recipient']),link['link'],identity)
                assert content==documents[identity]['content']
                assert hashlib.sha256(content).hexdigest()==documents[identity]['bytes_sha256']
            with Session(admin) as db:
                row=db.get(ClientPlanPublication,identity)
                assert row.source_plan_id==documents[identity]['plan_id'] and row.source_object_id==documents[identity]['object_id']
                assert row.object_key==documents[identity]['key'] and row.sha256==documents[identity]['bytes_sha256']
                assert read_projection(row.plan_json,row.plan_sha256)['plan']==result['publication']['plan']
        for label,who in [('active',ids['other']),('other_recipient',ids['gym_a']),('revoked',ids['other']),('pending',ids['pending_user'])]:
            with tenant_scope(who),Session(app) as db,pytest.raises(HTTPException) as denied:
                plans.read_member_plan(db,_principal(who),links[label]['link'])
            assert denied.value.status_code==404
        with tenant_scope(ids['gym_a']),Session(app) as db:
            listed=plans.list_member_links(db,_principal(ids['gym_a']))
            assert {row['link_id'] for row in listed['items']}=={links['external']['link'],links['owner_self']['link']}
        for marker in ('withdrawn-old','withdrawn-revoked'):
            label='active' if marker=='withdrawn-old' else 'revoked';link=links[label]
            with tenant_scope(link['recipient']),Session(app) as db,pytest.raises(HTTPException) as denied:
                plans.read_member_pdf(db,_principal(link['recipient']),link['link'],expected['publications'][marker])
            assert denied.value.status_code==404
    # A restored pending proof cannot commit only half the acceptance. This is
    # actual UPDATE/RETURNING followed by COMMIT under FORCE and the app role.
    pending=links['pending']
    from web.services.client_link_context import digest
    with tenant_scope(pending['recipient']),Session(app) as db:
        db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),{'hash':digest(pending['token'])})
        row=db.execute(text("UPDATE client_link_invitations SET status='consumed',consumed_by=:actor,version=version+1 WHERE id=:id RETURNING id"),{'actor':pending['recipient'],'id':pending['invitation']}).one()
        assert row.id==pending['invitation']
        with pytest.raises(DBAPIError):db.commit()
        db.rollback()
    with Session(admin) as db:
        invitation=db.get(ClientLinkInvitation,pending['invitation']);link=db.get(ClientAccountLink,pending['link'])
        assert invitation.status=='pending' and invitation.consumed_by is None and link.status=='pending' and link.user_id is None
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
        assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
    return {'links':6,'invitations':6,'pending':1,'active':4,'revoked':1,'current_publications':3,'withdrawn_publications':2,
        'private_pdf_objects':5,'exact_pdf_after_reconstructed_adapter':True,'recipient_owner_self_and_external':True,
        'same_gym_other_recipient_denied':True,'deferred_half_consumption_commit_rejected':True,
        'business_rows_unchanged_by_checks':True,'real_app_role_no_bypass_or_ddl_owner':True}
