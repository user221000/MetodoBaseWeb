"""Canonical29 shared services on owned migrated SQLite and restricted PG."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import json
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import event,select
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database,run_migration
from tests.integration_provider_subjects import application_engine
from web.client_link_schemas import InvitationAccept,InvitationIssue,PlanPublication
from web.database.models import Cliente,ClientAccountLink,ClientLinkInvitation,PlanGenerado,StoredObject,Usuario,UserRole
from web.database.tenant_context import configure_tenant_engine,tenant_scope
from web.services import client_link_invitations as invitations,client_link_plans as plans
from web.storage.objects import describe
from web.storage.runtime import get_object_store

ORIGIN='https://member.example.invalid'


@pytest.fixture(scope='module',params=['sqlite','postgresql'])
def link_db(request,tmp_path_factory):
    generator=migration_database.__wrapped__(SimpleNamespace(param=request.param),tmp_path_factory.mktemp('r12-services'))
    url,admin=next(generator)
    app=None
    try:
        run_migration(url,'db_bootstrap.py','--revision','20261019_client_account_links')
        if admin.dialect.name=='sqlite':
            @event.listens_for(admin,'connect')
            def foreign_keys(connection,record):connection.execute('PRAGMA foreign_keys=ON')
            admin.dispose()
        app=configure_tenant_engine(application_engine(url,admin))
        yield admin,app
    finally:
        if app is not None and app is not admin:app.dispose()
        generator.close()


@pytest.fixture
def case(link_db):
    admin,app=link_db
    ids={key:str(uuid.uuid4()) for key in ('gym','othergym','person','other','client','otherclient')}
    email='member-'+ids['person']+'@example.invalid'
    with Session(admin) as db:
        for identity,kind,role in [(ids['gym'],'gym',UserRole.OWNER),(ids['othergym'],'gym',UserRole.OWNER),
                (ids['person'],'usuario',UserRole.VIEWER),(ids['other'],'usuario',UserRole.VIEWER)]:
            db.add(Usuario(id=identity,email=email if identity==ids['person'] else identity+'@example.invalid',
                password_hash='synthetic',nombre='Synthetic',tipo=kind,role=role,session_version=0,activo=True))
        db.flush()
        for client,gym in [(ids['client'],ids['gym']),(ids['otherclient'],ids['othergym'])]:
            db.add(Cliente(id_cliente=client,gym_id=gym,nombre='Synthetic client',activo=True))
        db.commit()
    return dict(ids,admin=admin,app=app,email=email)


def principal(identity):return {'id':identity,'session_version':0}


@contextmanager
def session(case,who):
    with tenant_scope(case[who]),Session(case['app']) as db:yield db


def issue(case,recipient=None,key=None):
    with session(case,'gym') as db:
        result,message=invitations.issue_invitation(db,principal(case['gym']),case['client'],
            InvitationIssue(recipient_email=recipient or case['email'],request_key=key or str(uuid.uuid4())),ORIGIN)
    token=parse_qs(urlsplit(message.url).fragment)['token'][0]
    return result,token


def accept(case,issued,token,who='person'):
    with session(case,who) as db:
        return invitations.accept_invitation(db,principal(case[who]),InvitationAccept(token=token,expected_version=issued['version'],confirm=True))


def source(case,*,pdf=True,marker='old'):
    content=b'%PDF-1.7\nsynthetic-'+marker.encode()
    descriptor=describe(case['gym'],'plan_pdf',content,'application/pdf') if pdf else None
    if descriptor:get_object_store().put(descriptor,content,owner_id=case['gym'])
    with Session(case['admin']) as db:
        if descriptor:
            db.add(StoredObject(id=descriptor.id,gym_id=case['gym'],key=descriptor.key,kind='plan_pdf',
                byte_size=descriptor.byte_size,sha256=descriptor.sha256,content_type=descriptor.content_type,storage_backend='local',status='ready'))
            db.flush()
        raw=json.dumps({meal:{'kcal_objetivo':100,'kcal_real':100,'alimentos':{marker:50}} for meal in ('desayuno','almuerzo','comida','cena')})
        row=PlanGenerado(gym_id=case['gym'],id_cliente=case['client'],pdf_object_id=descriptor.id if descriptor else None,plan_json=raw)
        db.add(row);db.commit();identity=row.id
    return identity,descriptor,content


def publish(case,link,plan_id,*,current=0,observed_id=None):
    with session(case,'gym') as db:
        return plans.publish_plan(db,principal(case['gym']),case['client'],link['link_id'],
            PlanPublication(plan_id=plan_id,expected_link_version=link['version'],expected_publication_version=current,
                expected_publication_id=observed_id))


def assert_failure(code,function,*args,**kwargs):
    with pytest.raises(HTTPException) as denied:function(*args,**kwargs)
    assert denied.value.status_code==code,denied.value.detail
    return denied.value


def test_issue_before_registration_accepts_exact_new_account_without_personal_adoption(case):
    email='not-registered-'+uuid.uuid4().hex+'@example.invalid'
    issued,token=issue(case,email)
    assert issued['delivery_status']=='not_confirmed'
    new=str(uuid.uuid4());case['new']=new
    with Session(case['admin']) as db:
        db.add(Usuario(id=new,email=email,password_hash='synthetic',nombre='New',tipo='usuario',role=UserRole.VIEWER));db.commit()
    accepted=accept(case,issued,token,'new')
    assert accepted['status']=='active' and accepted['version']==2
    with Session(case['admin']) as db:
        user=db.get(Usuario,new)
        assert user.role==UserRole.VIEWER and user.team_gym_id is None and user.session_version==0
        assert db.scalars(select(Cliente).where(Cliente.gym_id==new)).all()==[]
        assert db.get(Cliente,db.scalar(select(Cliente.id).where(Cliente.id_cliente==case['client']))).gym_id==case['gym']


def test_wrong_account_purpose_and_consumed_replay_do_not_disclose_context(case):
    issued,token=issue(case)
    with session(case,'other') as db:
        failure=assert_failure(404,invitations.inspect_invitation,db,principal(case['other']),token)
        assert set(failure.detail)=={'code','message'}
    with session(case,'person') as db:assert_failure(404,invitations.inspect_invitation,db,principal(case['person']),'X'*43)
    accept(case,issued,token)
    with session(case,'person') as db:
        assert invitations.inspect_invitation(db,principal(case['person']),token)['status']=='consumed'
    assert_failure(409,accept,case,issued,token)


def test_request_key_replay_and_rotation_do_not_resend_or_retarget(case):
    key=str(uuid.uuid4());issued,old=issue(case,key=key)
    with session(case,'gym') as db:
        replay,message=invitations.issue_invitation(db,principal(case['gym']),case['client'],
            InvitationIssue(recipient_email=case['email'],request_key=key),ORIGIN)
        assert replay==issued and message is None
    with session(case,'gym') as db:
        assert_failure(409,invitations.issue_invitation,db,principal(case['gym']),case['client'],
            InvitationIssue(recipient_email='different@example.invalid',request_key=key),ORIGIN)
    with session(case,'gym') as db:
        rotated,message=invitations.resend_invitation(db,principal(case['gym']),case['client'],issued['invitation_id'],1,ORIGIN)
    assert rotated['version']==2 and rotated['link_version']==1
    new=parse_qs(urlsplit(message.url).fragment)['token'][0]
    with session(case,'person') as db:assert_failure(404,invitations.inspect_invitation,db,principal(case['person']),old)
    with session(case,'person') as db:
        info=invitations.inspect_invitation(db,principal(case['person']),new)
        assert info['version']==2 and info['can_accept'] is True
    accept(case,rotated,new)


def test_expired_invitation_and_version_conflict_leave_no_assignment(case):
    issued,token=issue(case)
    with session(case,'person') as db:
        assert_failure(409,invitations.accept_invitation,db,principal(case['person']),InvitationAccept(token=token,expected_version=2,confirm=True))
    with session(case,'person') as db:
        assert_failure(410,invitations.accept_invitation,db,principal(case['person']),InvitationAccept(token=token,expected_version=1,confirm=True),
            now=datetime.now(timezone.utc)+timedelta(days=8))
    with Session(case['admin']) as db:
        link=db.get(ClientAccountLink,issued['link_id']);invitation=db.get(ClientLinkInvitation,issued['invitation_id'])
        assert link.status=='pending' and link.user_id is None and invitation.status=='pending'


def test_publication_exact_pdf_replacement_and_no_general_source_access(case):
    issued,token=issue(case);link=accept(case,issued,token)
    old,descriptor,content=source(case)
    publication=publish(case,link,old)
    with session(case,'person') as db:
        result=plans.read_member_plan(db,principal(case['person']),link['link_id'])
        assert result['publication']['source_plan_id']==old
        assert result['publication']['plan']['desayuno']['alimentos']=={'old':50}
    with session(case,'person') as db:
        assert plans.read_member_pdf(db,principal(case['person']),link['link_id'],publication['publication_id'])==content
    with session(case,'other') as db:assert_failure(404,plans.read_member_plan,db,principal(case['other']),link['link_id'])
    if case['app'].dialect.name=='postgresql':
        with session(case,'person') as db:
            assert db.get(PlanGenerado,old) is None and db.get(StoredObject,descriptor.id) is None
    new,_,newcontent=source(case,marker='new')
    replacement=publish(case,link,new,current=publication['version'],observed_id=publication['publication_id'])
    with session(case,'person') as db:assert_failure(404,plans.read_member_pdf,db,principal(case['person']),link['link_id'],publication['publication_id'])
    with session(case,'person') as db:
        assert plans.read_member_pdf(db,principal(case['person']),link['link_id'],replacement['publication_id'])==newcontent


def test_legacy_menu_without_pdf_is_explicit_and_source_change_withdraws(case):
    issued,token=issue(case);link=accept(case,issued,token)
    identity,_,_=source(case,pdf=False)
    published=publish(case,link,identity)
    assert published['download_published_pdf'] is False and published['pdf_unavailable_reason']=='legacy_requires_review'
    with session(case,'person') as db:
        result=plans.read_member_plan(db,principal(case['person']),link['link_id'])
        assert result['publication']['pdf_url'] is None and result['capabilities']['download_published_pdf'] is False
    with tenant_scope(case['gym']),Session(case['app']) as db:
        row=db.get(PlanGenerado,identity);row.deleted_at=datetime.now(timezone.utc);db.commit()
    with session(case,'person') as db:assert plans.read_member_plan(db,principal(case['person']),link['link_id'])['publication'] is None


def test_recipient_can_only_revoke_own_link_even_when_source_owner_inactive(case):
    issued,token=issue(case);link=accept(case,issued,token)
    with Session(case['admin']) as db:db.get(Usuario,case['gym']).activo=False;db.commit()
    with session(case,'person') as db:assert_failure(404,plans.read_member_plan,db,principal(case['person']),link['link_id'])
    with session(case,'other') as db:assert_failure(404,plans.revoke_member_link,db,principal(case['other']),link['link_id'],2)
    with session(case,'person') as db:
        result=plans.revoke_member_link(db,principal(case['person']),link['link_id'],2)
        assert result['status']=='revoked' and result['version']==3
    with Session(case['admin']) as db:db.get(Usuario,case['gym']).activo=True;db.commit()
    with session(case,'person') as db:assert plans.list_member_links(db,principal(case['person']))['items']==[]


@pytest.mark.parametrize('same_gym',[False,True])
def test_legitimate_owner_recipient_never_uses_own_gym_branch_to_read_someone_elses_link(case,same_gym):
    with Session(case['admin']) as db:
        user=db.get(Usuario,case['person']);user.tipo='gym';user.role=UserRole.OWNER;db.commit()
    if same_gym:
        case=dict(case,gym=case['person'])
        with Session(case['admin']) as db:
            client=Cliente(gym_id=case['gym'],id_cliente=str(uuid.uuid4()),nombre='Own context',activo=True)
            db.add(client);db.commit();case['client']=client.id_cliente
    issued,token=issue(case);link=accept(case,issued,token)
    second=dict(case,gym=case['person'],client=str(uuid.uuid4()),email=case['other']+'@example.invalid',person=case['other'])
    with Session(case['admin']) as db:
        db.add(Cliente(gym_id=second['gym'],id_cliente=second['client'],nombre='Another recipient',activo=True));db.commit()
    others,proof=issue(second);accept(second,others,proof)
    with session(case,'person') as db:
        own=plans.list_member_links(db,principal(case['person']))
        assert [item['link_id'] for item in own['items']]==[link['link_id']]
    with session(case,'person') as db:assert_failure(404,plans.read_member_plan,db,principal(case['person']),others['link_id'])
    with session(case,'person') as db:
        from web.services.privacy_export import export_personal_data
        exported=export_personal_data(db,case['person'])
        assert exported['scope']['personal_space'] is False
        assert [item['id'] for item in exported['member_links']['records']]==[link['link_id']]
        for name in ('profiles','plans','measurements','purchases','generation_requests','personal_diary'):
            assert exported[name]['records']==[]


def test_ambiguous_owner_cannot_adopt_member_context_or_export_portfolio(case):
    with Session(case['admin']) as db:
        db.get(Usuario,case['person']).role=UserRole.OWNER
        db.add(Cliente(gym_id=case['person'],id_cliente=str(uuid.uuid4()),nombre='Private portfolio',activo=True));db.commit()
    issued,token=issue(case)
    with session(case,'person') as db:
        failure=assert_failure(409,invitations.inspect_invitation,db,principal(case['person']),token)
        assert failure.detail['code']=='member_context_requires_review'
    with session(case,'person') as db:
        from web.services.privacy_export import export_personal_data
        exported=export_personal_data(db,case['person'])
        assert exported['scope']['personal_space'] is False and exported['member_links']['records']==[]
        assert exported['profiles']['records']==[] and exported['plans']['records']==[]
    with Session(case['admin']) as db:assert db.get(ClientAccountLink,issued['link_id']).status=='pending'


def test_member_export_keyset_and_budget_never_expand_to_portfolio_or_invitation(case):
    from web.services.privacy_export import export_personal_data
    from web.services.client_link_export import export_member_links
    first,token=issue(case);accept(case,first,token)
    other=dict(case,gym=case['othergym'],client=case['otherclient'])
    second,proof=issue(other);accept(other,second,proof)
    seen=[];after=None
    for _ in range(3):
        with session(case,'person') as db:
            result=export_personal_data(db,case['person'],limit=1,cursors={'member_link':after})
        assert result['profiles']['records']==[] and result['plans']['records']==[]
        page=result['member_links'];seen.extend(row['id'] for row in page['records'])
        assert all(set(row)=={'id','status','version','gym_name','client_display_name','accepted_at','publication'} for row in page['records'])
        after=page['next_after']
        if after is None:break
    assert seen==sorted([first['link_id'],second['link_id']]) and len(set(seen))==2
    with session(case,'person') as db:
        actor=db.get(Usuario,case['person'])
        assert_failure(413,export_member_links,db,actor,limit=100,maximum_bytes=256)


@pytest.mark.parametrize('role,can_issue,can_publish',[(UserRole.ADMIN,True,True),(UserRole.NUTRIOLOGO,False,True),(UserRole.VIEWER,False,False)])
def test_professional_roles_are_reloaded_and_new_recipient_link_gives_no_professional_grant(case,role,can_issue,can_publish):
    issued,token=issue(case);link=accept(case,issued,token)
    identity,_,_=source(case,pdf=False)
    with Session(case['admin']) as db:
        user=db.get(Usuario,case['other']);user.team_gym_id=case['gym'];user.role=role;db.commit()
    with tenant_scope(case['gym']),Session(case['app']) as db:
        if can_publish:
            result=plans.publish_plan(db,principal(case['other']),case['client'],link['link_id'],
                PlanPublication(plan_id=identity,expected_link_version=2,expected_publication_version=0,expected_publication_id=None))
            assert result['source_plan_id']==identity
        else:
            assert_failure(403,plans.publish_plan,db,principal(case['other']),case['client'],link['link_id'],
                PlanPublication(plan_id=identity,expected_link_version=2,expected_publication_version=0,expected_publication_id=None))
    with tenant_scope(case['gym']),Session(case['app']) as db:
        if can_issue:
            # Permission is admitted, but a current link on this exact client
            # still rejects a duplicate association at the unique constraint.
            assert_failure(409,invitations.issue_invitation,db,principal(case['other']),case['client'],
                InvitationIssue(recipient_email=case['email'],request_key=str(uuid.uuid4())),ORIGIN)
        else:
            assert_failure(403,invitations.issue_invitation,db,principal(case['other']),case['client'],
                InvitationIssue(recipient_email=case['email'],request_key=str(uuid.uuid4())),ORIGIN)


@pytest.mark.parametrize('after_commit',[False,True])
def test_uncertain_commit_is_visible_and_never_returns_a_send_packet(case,after_commit):
    class FailingSession(Session):
        def commit(self):
            if after_commit:super().commit()
            raise RuntimeError('synthetic private details never exposed')
    with tenant_scope(case['gym']),FailingSession(case['app']) as db:
        failure=assert_failure(503,invitations.issue_invitation,db,principal(case['gym']),case['client'],
            InvitationIssue(recipient_email=case['email'],request_key='uncertain'),ORIGIN)
        assert failure.detail['code']=='member_link_reconciliation_required'
    with Session(case['admin']) as db:
        rows=db.scalars(select(ClientAccountLink).where(ClientAccountLink.client_id==case['client'])).all()
        assert len(rows)==int(after_commit)
        if rows:assert rows[0].status=='pending' and rows[0].user_id is None
