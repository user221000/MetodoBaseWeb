"""Canonical revision29 adaptation of the frozen35 mechanism criteria.

Only a UUID database returned by the existing owned migration fixture is used.
Real revision28 sources and a real NOSUPERUSER/NOBYPASSRLS/nonowner role execute
the full reviewed actor/proof predicates in the real revision29 migration.
Only table/fixture/extra required columns were adapted; original35 stays frozen.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import secrets
from threading import Barrier, Event
from types import SimpleNamespace
import time
import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine
from web.database.tenant_context import configure_tenant_engine, tenant_scope

GA = 'a0000000-0000-0000-0000-000000000001'
GB = 'b0000000-0000-0000-0000-000000000002'
UA = '10000000-0000-0000-0000-000000000003'
UB = '20000000-0000-0000-0000-000000000004'
TEAM = '30000000-0000-0000-0000-000000000005'
CA, CA2, CB = 'r12-client-a', 'r12-client-a2', 'r12-client-b'


def digest(token):
    return hashlib.sha256(('client-account-invite-v1:' + token).encode('ascii')).hexdigest()


def clear_proof(connection):
    connection.execute(text("SELECT set_config('app.client_invitation_digest','',true)"))


def make_app(url, *, size=1):
    app = configure_tenant_engine(create_engine(url, pool_size=size, max_overflow=0, hide_parameters=True))
    event.listen(app, 'begin', clear_proof)
    return app


@pytest.fixture(scope='module')
def lab(tmp_path_factory):
    from web.database.models import Usuario, UserRole, Cliente, PlanGenerado, StoredObject, Subscription
    from web.storage.objects import describe
    from web.database.schema_control import verify_runtime_schema

    owner = migration_database.__wrapped__(SimpleNamespace(param='postgresql'), tmp_path_factory.mktemp('r12-lab'))
    url, admin = next(owner)
    app = None
    try:
        run_migration(url, 'db_bootstrap.py', '--revision', '20261019_client_account_links')
        verify_runtime_schema(admin, expected_revision='20261019_client_account_links')
        objects, plans = {}, {}
        with Session(admin) as db:
            for identity, kind, role, parent in [(GA,'gym',UserRole.OWNER,None),(GB,'gym',UserRole.OWNER,None),
                    (UA,'usuario',UserRole.VIEWER,None),(UB,'usuario',UserRole.VIEWER,None),
                    (TEAM,'usuario',UserRole.NUTRIOLOGO,GA)]:
                db.add(Usuario(id=identity,email=identity+'@example.invalid',password_hash='synthetic-only',
                    nombre='Synthetic',tipo=kind,role=role,team_gym_id=parent,activo=True))
            db.flush()
            db.add(Subscription(gym_id=GA,plan='clinica',status='active'))
            for client, gym in [(CA,GA),(CA2,GA),(CB,GB)]:
                db.add(Cliente(id_cliente=client,gym_id=gym,nombre='Synthetic',activo=True))
                descriptor=describe(gym,'plan_pdf',b'%PDF-1.7\nsynthetic-'+client.encode(),'application/pdf')
                objects[client]=descriptor
                db.add(StoredObject(id=descriptor.id,gym_id=gym,kind=descriptor.kind,key=descriptor.key,
                    content_type=descriptor.content_type,byte_size=descriptor.byte_size,sha256=descriptor.sha256,
                    storage_backend='local',status='ready'))
                db.flush()
                plan=PlanGenerado(gym_id=gym,id_cliente=client,pdf_object_id=descriptor.id,plan_json=json.dumps({meal:{'kcal_objetivo':100,'kcal_real':100,'alimentos':{'synthetic-food':50}} for meal in ('desayuno','almuerzo','comida','cena')}))
                db.add(plan);db.flush();plans[client]=plan.id
            db.commit()
        base_app=application_engine(url,admin)
        app=make_app(base_app.url,size=4)
        base_app.dispose()
        yield {'admin':admin,'app':app,'objects':objects,'plans':plans}
    finally:
        if app is not None: app.dispose()
        owner.close()


@pytest.fixture(autouse=True)
def clean_lab(lab):
    with lab['admin'].begin() as db:
        db.exec_driver_sql('TRUNCATE public.client_plan_publications,public.client_link_invitations,public.client_account_links')
        db.execute(text('UPDATE public.clientes SET activo=true,deleted_at=NULL'))
        db.execute(text('UPDATE public.stored_objects SET status=\'ready\''))
        db.execute(text('UPDATE public.planes_generados SET deleted_at=NULL'))
        db.execute(text('UPDATE public.usuarios SET activo=true,session_version=0'))


@contextmanager
def tx(lab, actor, token=None, *, engine=None):
    with tenant_scope(actor), (engine or lab['app']).connect() as db:
        db.execute(text("SELECT set_config('statement_timeout','6000',true)"))
        if token:
            db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),{'hash':digest(token)})
        try:
            yield db
        finally:
            db.rollback()


def issue(lab, *, gym=GA, client=CA, recipient=UA, expires='1 day'):
    token=secrets.token_urlsafe(32)
    link, invitation=str(uuid.uuid4()),str(uuid.uuid4())
    with tx(lab,gym) as db:
        db.execute(text('SELECT id FROM public.usuarios WHERE id=:id FOR UPDATE NOWAIT'),{'id':gym})
        db.execute(text('SELECT id FROM public.clientes WHERE gym_id=:gym AND id_cliente=:client FOR UPDATE'),{'gym':gym,'client':client})
        assert db.execute(text("INSERT INTO public.client_account_links(id,gym_id,client_id,status,gym_name,client_display_name) VALUES(:id,:gym,:client,'pending','Synthetic gym','Synthetic client') RETURNING id"),
            {'id':link,'gym':gym,'client':client}).scalar_one()==link
        db.execute(text("INSERT INTO public.client_link_invitations(id,link_id,gym_id,client_id,recipient_email,token_hash,expires_at,status,issued_by,request_key,payload_hash) VALUES(:id,:link,:gym,:client,:email,:hash,(clock_timestamp() AT TIME ZONE 'UTC')+CAST(:expiry AS interval),'pending',:gym,:id,:hash)"),
            {'id':invitation,'link':link,'gym':gym,'client':client,'email':recipient+'@example.invalid','hash':digest(token),'expiry':expires})
        db.commit()
    return {'link':link,'invitation':invitation,'token':token,'actor':recipient,'gym':gym,'client':client}


def consume_steps(db, issued, *, activate=True):
    for identity in sorted(set([issued['gym'],issued['actor']])):
        user=db.execute(text('SELECT id,session_version FROM public.usuarios WHERE id=:id FOR UPDATE NOWAIT'),{'id':identity}).one()
        if identity==issued['actor'] and user.session_version!=0:
            raise ValueError('R12 stale session')
    assert db.execute(text('SELECT id FROM public.client_account_links WHERE id=:id FOR UPDATE'),{'id':issued['link']}).scalar_one()==issued['link']
    used=db.execute(text("UPDATE public.client_link_invitations SET status='consumed',consumed_by=:actor,version=version+1 WHERE id=:id AND status='pending' RETURNING id,consumed_at"),
        {'id':issued['invitation'],'actor':issued['actor']}).one()
    assert db.execute(text("SELECT status FROM public.client_link_invitations WHERE id=:id"),{'id':used.id}).scalar_one()=='consumed'
    if activate:
        activated=db.execute(text("UPDATE public.client_account_links SET status='active',user_id=:actor,accepted_at=:at,version=version+1 WHERE id=:id AND status='pending' RETURNING id,user_id"),
            {'actor':issued['actor'],'at':used.consumed_at,'id':issued['link']}).one()
        assert activated.user_id==issued['actor']
    return used


def accept(lab, issued):
    with tx(lab,issued['actor'],issued['token']) as db:
        consume_steps(db,issued)
        db.commit()


def publish(lab, issued, *, source_client=None, descriptor_client=None, connection=None, payload_transform=None):
    source=source_client or issued['client']
    descriptor=lab['objects'][descriptor_client or source]
    values={'id':str(uuid.uuid4()),'gym':issued['gym'],'client':issued['client'],'link':issued['link'],
        'plan':lab['plans'][source],'object':descriptor.id,'key':descriptor.key,'content_type':descriptor.content_type,
        'size':descriptor.byte_size,'sha':descriptor.sha256}
    sql=text("""INSERT INTO public.client_plan_publications(id,gym_id,client_id,link_id,source_plan_id,source_object_id,object_key,content_type,byte_size,sha256,storage_backend,plan_json,plan_sha256,published_by,status)
      VALUES(:id,:gym,:client,:link,:plan,:object,:key,:content_type,:size,:sha,'local',:payload,:plan_sha,:gym,'published') RETURNING id""")
    def insert(db):
        payload=db.scalar(text('SELECT public.r12_project_plan(p)::text FROM public.planes_generados p WHERE id=:id'),{'id':values['plan']})
        if payload_transform: payload=payload_transform(payload)
        values.update(payload=payload,plan_sha=hashlib.sha256(payload.encode('utf-8')).hexdigest())
        return db.execute(sql,values).scalar_one()
    if connection is not None: return insert(connection)
    with tx(lab,issued['gym']) as db:
        identity=insert(db);db.commit();return identity


def test_real_role_force_and_missing_context(lab):
    with lab['app'].connect() as db:
        assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one())==(False,False,False,False)
        assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND pg_has_role(current_user,relowner,'MEMBER'))"))
        assert db.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relname IN ('client_account_links','client_link_invitations','client_plan_publications')")).all()==[(True,True)]*3
        for table in ['client_account_links','client_link_invitations','client_plan_publications']:
            assert db.scalar(text('SELECT count(*) FROM public.'+table))==0


def test_returning_consumed_then_active_commits_one_exact_subject(lab):
    issued=issue(lab)
    accept(lab,issued)
    with lab['admin'].connect() as db:
        assert db.execute(text('SELECT i.status,i.consumed_by,l.status,l.user_id,i.consumed_at=l.accepted_at FROM public.client_link_invitations i JOIN public.client_account_links l ON l.id=i.link_id')).one()==('consumed',UA,'active',UA,True)


@pytest.mark.parametrize('lock',['FOR SHARE','FOR UPDATE'])
def test_recipient_can_lock_publication_but_cannot_write(lab,lock):
    issued=issue(lab);accept(lab,issued);publication=publish(lab,issued)
    with tx(lab,UA) as db:
        assert db.execute(text('SELECT id FROM public.client_plan_publications WHERE id=:id '+lock),{'id':publication}).scalar_one()==publication
    with tx(lab,UA) as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE public.client_plan_publications SET status='withdrawn',publication_version=publication_version+1 WHERE id=:id"),{'id':publication})
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT status FROM public.client_plan_publications'))=='published'


@pytest.mark.parametrize('failure',['incomplete','proof_removed'])
def test_deferred_pair_and_proof_reject_partial_commit(lab,failure):
    issued=issue(lab)
    with tx(lab,UA,issued['token']) as db:
        consume_steps(db,issued,activate=failure!='incomplete')
        if failure=='proof_removed': db.execute(text("SELECT set_config('app.client_invitation_digest','',true)"))
        with pytest.raises(DBAPIError): db.commit()
    with lab['admin'].connect() as db:
        assert db.execute(text('SELECT i.status,l.status FROM public.client_link_invitations i JOIN public.client_account_links l ON l.id=i.link_id')).one()==('pending','pending')


def test_gym_branch_cannot_consume_on_behalf_of_recipient(lab):
    issued=issue(lab)
    with tx(lab,GA) as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE public.client_link_invitations SET status='consumed',consumed_by=:actor,version=version+1 WHERE id=:id"),{'actor':UA,'id':issued['invitation']})


@pytest.mark.parametrize('descriptor_client',[CA2,CB])
def test_direct_insert_cannot_replace_exact_plan_object(lab,descriptor_client):
    issued=issue(lab);accept(lab,issued)
    with pytest.raises(DBAPIError):publish(lab,issued,descriptor_client=descriptor_client)
    with lab['admin'].connect() as db: assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications'))==0


def test_invalidation_sees_publication_committed_while_waiting_for_object(lab):
    issued=issue(lab);accept(lab,issued)
    started,finished=Event(),Event()
    def mutate():
        with tx(lab,GA) as db:
            started.set()
            db.execute(text("UPDATE public.stored_objects SET status='pending' WHERE id=:id"),{'id':lab['objects'][CA].id})
            db.commit();finished.set()
    with tx(lab,GA) as publisher, ThreadPoolExecutor(max_workers=1) as executor:
        publisher.execute(text('SELECT id FROM public.stored_objects WHERE id=:id FOR SHARE'),{'id':lab['objects'][CA].id})
        future=executor.submit(mutate)
        assert started.wait(2)
        publication=publish(lab,issued,connection=publisher)
        assert not finished.is_set()
        publisher.commit()
        future.result(timeout=8)
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT status FROM public.client_plan_publications WHERE id=:id'),{'id':publication})=='withdrawn'


def test_object_mutation_wins_then_old_descriptor_is_rejected(lab):
    issued=issue(lab);accept(lab,issued)
    with tx(lab,GA) as db:
        db.execute(text("UPDATE public.stored_objects SET status='pending' WHERE id=:id"),{'id':lab['objects'][CA].id});db.commit()
    with pytest.raises(DBAPIError):publish(lab,issued)


@pytest.mark.parametrize('isolation',['REPEATABLE READ','SERIALIZABLE'])
def test_non_rc_invalidation_denied_without_visible_publication(lab,isolation):
    with tenant_scope(GA), lab['app'].connect().execution_options(isolation_level=isolation) as db:
        with pytest.raises(DBAPIError) as rejected:
            db.execute(text("UPDATE public.stored_objects SET status='pending' WHERE id=:id"),{'id':lab['objects'][CA].id})
        assert rejected.value.orig.pgcode=='25000'


def test_nowait_user_total_order_conflicts_instead_of_cycle_with_legacy_r11(lab):
    # R11 holds gym->Subscription before trying the lower-ID nonowner target.
    def r12_attempt():
        with tx(lab,TEAM) as r12:
            r12.execute(text('SELECT id FROM public.usuarios WHERE id=:id FOR UPDATE NOWAIT'),{'id':TEAM})
            with pytest.raises(DBAPIError) as busy:
                r12.execute(text('SELECT id FROM public.usuarios WHERE id=:id FOR UPDATE NOWAIT'),{'id':GA})
            assert busy.value.orig.pgcode=='55P03'
            r12.rollback()
    with tx(lab,GA) as r11, ThreadPoolExecutor(max_workers=1) as executor:
        r11.execute(text('SELECT id FROM public.usuarios WHERE id=:id FOR UPDATE'),{'id':GA})
        r11.execute(text('SELECT id FROM public.subscriptions WHERE gym_id=:gym FOR UPDATE'),{'gym':GA})
        executor.submit(r12_attempt).result(timeout=4)
        assert r11.execute(text('SELECT id FROM public.usuarios WHERE id=:id FOR UPDATE NOWAIT'),{'id':TEAM}).scalar_one()==TEAM


def test_client_invalidation_remains_durable_if_owner_temporarily_inactive(lab):
    """Source triggers cannot depend on the owner's current login eligibility.

    A previously authorized maintenance transaction still has source RLS scope;
    the committed client invalidation must not disappear on owner reactivation.
    """
    issued=issue(lab);accept(lab,issued);publish(lab,issued)
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:id'),{'id':GA})
    with tx(lab,GA) as db:
        db.execute(text('UPDATE public.clientes SET activo=false WHERE id_cliente=:id'),{'id':CA});db.commit()
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=true WHERE id=:id'),{'id':GA})
        assert db.scalar(text('SELECT status FROM public.client_account_links'))=='revoked'
        assert db.scalar(text('SELECT status FROM public.client_plan_publications'))=='withdrawn'


@pytest.mark.parametrize('operation',['new_link','new_invitation','rotate','consume','publish'])
def test_inactive_owner_scope_cannot_grant_or_rotate(lab,operation):
    issued=issue(lab)
    if operation=='publish': accept(lab,issued)
    if operation=='new_invitation':
        with tx(lab,GA) as db:
            extra=str(uuid.uuid4())
            db.execute(text("INSERT INTO public.client_account_links(id,gym_id,client_id,status,gym_name,client_display_name) VALUES(:id,:gym,:client,'pending','Synthetic gym','Synthetic client')"),
                {'id':extra,'gym':GA,'client':CA2});db.commit()
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:id'),{'id':GA})
    with pytest.raises(DBAPIError):
        if operation=='new_link': issue(lab,client=CA2)
        elif operation=='consume': accept(lab,issued)
        elif operation=='publish': publish(lab,issued)
        else:
            with tx(lab,GA) as db:
                if operation=='rotate':
                    db.execute(text("UPDATE public.client_link_invitations SET token_hash=:hash,expires_at=expires_at+interval '1 day',version=version+1 WHERE id=:id"),
                        {'hash':digest(secrets.token_urlsafe(32)),'id':issued['invitation']})
                else:
                    db.execute(text("INSERT INTO public.client_link_invitations(id,link_id,gym_id,client_id,recipient_email,token_hash,expires_at,status,issued_by,request_key,payload_hash) VALUES(:id,:link,:gym,:client,:email,:hash,(clock_timestamp() AT TIME ZONE 'UTC')+interval '1 day','pending',:gym,:id,:hash)"),
                        {'id':str(uuid.uuid4()),'link':extra,'gym':GA,'client':CA2,'email':UB+'@example.invalid','hash':digest(secrets.token_urlsafe(32))})
                db.commit()
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications'))==0
        assert db.scalar(text("SELECT count(*) FROM public.client_link_invitations WHERE status='consumed'"))==int(operation=='publish')
        assert db.scalar(text('SELECT token_hash FROM public.client_link_invitations WHERE id=:id'),{'id':issued['invitation']})==digest(issued['token'])


def test_inactive_owner_scope_can_revoke_pending_and_withdraw_published(lab):
    pending=issue(lab)
    active=issue(lab,client=CA2,recipient=UB);accept(lab,active)
    published=publish(lab,active)
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:id'),{'id':GA})
    with tx(lab,GA) as db:
        assert db.execute(text("UPDATE public.client_account_links SET status='revoked',version=version+1 WHERE id=:id RETURNING id"),{'id':pending['link']}).scalar_one()==pending['link']
        assert db.execute(text("UPDATE public.client_link_invitations SET status='revoked',version=version+1 WHERE id=:id RETURNING id"),{'id':pending['invitation']}).scalar_one()==pending['invitation']
        assert db.execute(text("UPDATE public.client_plan_publications SET status='withdrawn',publication_version=publication_version+1 WHERE id=:id RETURNING id"),{'id':published}).scalar_one()==published
        db.commit()
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=true WHERE id=:id'),{'id':GA})
    with tx(lab,UA,pending['token']) as db:
        assert db.scalar(text("SELECT status FROM public.client_link_invitations WHERE id=:id"),{'id':pending['invitation']})=='revoked'
    with tx(lab,UB) as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications WHERE id=:id'),{'id':published})==0


def test_proof_is_purpose_bound_and_does_not_survive_pool_reuse(lab):
    issued=issue(lab)
    single=make_app(lab['app'].url,size=1)
    try:
        with tx(lab,UA,engine=single) as db:
            # A plain token hash from a different purpose confers no authority.
            db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),
                {'hash':hashlib.sha256(issued['token'].encode('ascii')).hexdigest()})
            assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations'))==0
            db.rollback()
        with tx(lab,UA,issued['token'],engine=single) as db:
            pid=db.scalar(text('SELECT pg_backend_pid()'))
            assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations'))==1
            # Simulate a pre-existing session setting: every begin must mask it.
            db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,false)"),{'hash':digest(issued['token'])})
            db.commit()
        with tx(lab,UB,engine=single) as db:
            assert db.scalar(text('SELECT pg_backend_pid()'))==pid
            assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
            assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations'))==0
        with tx(lab,UA,engine=single) as db:
            assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
            assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations'))==0
    finally: single.dispose()


def test_rollback_to_before_proof_removes_the_capability(lab):
    issued=issue(lab)
    with tx(lab,UA) as db:
        db.exec_driver_sql('SAVEPOINT before_proof')
        db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),{'hash':digest(issued['token'])})
        assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations'))==1
        db.exec_driver_sql('ROLLBACK TO SAVEPOINT before_proof')
        assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
        assert db.execute(text("UPDATE public.client_link_invitations SET status='consumed',consumed_by=:actor,version=version+1 WHERE id=:id RETURNING id"),
            {'actor':UA,'id':issued['invitation']}).all()==[]
        db.commit()
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT status FROM public.client_link_invitations'))=='pending'


def test_expiry_is_checked_after_waiting_for_the_invitation_lock(lab):
    issued=issue(lab,expires='1.2 seconds')
    ready=Event();state={}
    def waiting_consumer():
        with tx(lab,UA,issued['token']) as db:
            state['pid']=db.scalar(text('SELECT pg_backend_pid()'));ready.set()
            with pytest.raises(DBAPIError) as rejected: consume_steps(db,issued)
            assert rejected.value.orig.pgcode=='42501'
    with lab['admin'].begin() as blocker, ThreadPoolExecutor(max_workers=1) as executor:
        blocker.execute(text('SELECT id FROM public.client_link_invitations WHERE id=:id FOR UPDATE'),{'id':issued['invitation']})
        future=executor.submit(waiting_consumer);assert ready.wait(2)
        deadline=time.monotonic()+2
        while not blocker.scalar(text('SELECT cardinality(pg_blocking_pids(:pid))>0'),{'pid':state['pid']}):
            assert time.monotonic()<deadline
            time.sleep(.01)
        assert blocker.scalar(text("SELECT expires_at>clock_timestamp() AT TIME ZONE 'UTC' FROM public.client_link_invitations WHERE id=:id"),{'id':issued['invitation']})
        blocker.execute(text('SELECT pg_sleep(1.25)'))
        blocker.commit();future.result(timeout=5)
    with lab['admin'].connect() as db:
        assert db.execute(text('SELECT i.status,l.status FROM public.client_link_invitations i JOIN public.client_account_links l ON l.id=i.link_id')).one()==('pending','pending')


def test_consumption_before_expiry_can_commit_after_expiry(lab):
    issued=issue(lab,expires='0.5 seconds')
    with tx(lab,UA,issued['token']) as db:
        consume_steps(db,issued)
        db.execute(text('SELECT pg_sleep(0.55)'))
        db.commit()
    with lab['admin'].connect() as db:
        assert db.scalar(text("SELECT status='consumed' AND consumed_at<expires_at AND expires_at<clock_timestamp() AT TIME ZONE 'UTC' FROM public.client_link_invitations"))


def test_owner_recipient_must_filter_own_links_even_when_gym_scope_is_visible(lab):
    professional=issue(lab);accept(lab,professional);own_publication=publish(lab,professional)
    received=issue(lab,gym=GB,client=CB,recipient=GA);accept(lab,received);received_publication=publish(lab,received)
    with tx(lab,GA) as db:
        # RLS legitimately permits both professional A and recipient A in B.
        assert set(db.scalars(text('SELECT id FROM public.client_plan_publications')))=={own_publication,received_publication}
        result=db.scalars(text("SELECT p.id FROM public.client_plan_publications p JOIN public.client_account_links l ON l.id=p.link_id AND l.gym_id=p.gym_id AND l.client_id=p.client_id WHERE l.user_id=:actor AND l.status='active' AND p.status='published'"),{'actor':GA}).all()
        assert result==[received_publication]


def test_owner_own_gym_acceptance_still_requires_exact_proof(lab):
    issued=issue(lab,recipient=GA)
    with tx(lab,GA) as db:
        with pytest.raises(DBAPIError): consume_steps(db,issued)
    accept(lab,issued)
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT user_id FROM public.client_account_links'))==GA


def test_ambiguous_personal_owner_cannot_consume_invitation(lab):
    issued=issue(lab)
    with lab['admin'].begin() as db:
        db.execute(text("UPDATE public.usuarios SET role='OWNER' WHERE id=:id"),{'id':UA})
    try:
        with tx(lab,UA,issued['token']) as db:
            assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations'))==0
    finally:
        with lab['admin'].begin() as db:
            db.execute(text("UPDATE public.usuarios SET role='VIEWER' WHERE id=:id"),{'id':UA})


@pytest.mark.parametrize('source',['client','plan','object'])
def test_source_delete_is_restricted_and_does_not_publish_partial_withdrawal(lab,source):
    issued=issue(lab);accept(lab,issued);published=publish(lab,issued)
    sql,values={
        'client':('DELETE FROM public.clientes WHERE id_cliente=:id',{'id':CA}),
        'plan':('DELETE FROM public.planes_generados WHERE id=:id',{'id':lab['plans'][CA]}),
        'object':('DELETE FROM public.stored_objects WHERE id=:id',{'id':lab['objects'][CA].id}),
    }[source]
    with tx(lab,GA) as db:
        with pytest.raises(DBAPIError) as restricted: db.execute(text(sql),values)
        assert restricted.value.orig.pgcode=='23503'
    with tx(lab,UA) as db:
        assert db.scalar(text('SELECT id FROM public.client_plan_publications WHERE id=:id'),{'id':published})==published


def test_rr_readonly_inventory_and_noninvalidating_client_updates_remain_allowed(lab):
    with tenant_scope(GA),lab['app'].connect().execution_options(isolation_level='REPEATABLE READ') as db:
        db.exec_driver_sql('SET TRANSACTION READ ONLY')
        assert db.scalar(text('SELECT count(*) FROM public.clientes'))==2
    with tenant_scope(GA),lab['app'].connect().execution_options(isolation_level='REPEATABLE READ') as db:
        assert db.execute(text('UPDATE public.clientes SET activo=activo WHERE id_cliente=:id RETURNING id_cliente'),{'id':CA}).scalar_one()==CA
        db.rollback()


def test_cross_owner_acceptance_uses_total_order_and_never_deadlocks(lab):
    invited_a=issue(lab,gym=GB,client=CB,recipient=GA)
    invited_b=issue(lab,gym=GA,client=CA,recipient=GB)
    barrier=Barrier(2)
    def contender(issued):
        with tx(lab,issued['actor'],issued['token']) as db:
            barrier.wait(timeout=3)
            try:
                consume_steps(db,issued);db.commit();return 'accepted'
            except DBAPIError as conflict:
                assert conflict.orig.pgcode=='55P03'
                db.rollback();return 'busy'
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(contender,issued) for issued in (invited_a,invited_b)]
        outcomes=[future.result(timeout=7) for future in futures]
    assert 'accepted' in outcomes
    with lab['admin'].connect() as db:
        assert db.scalar(text("SELECT count(*) FROM public.client_link_invitations i JOIN public.client_account_links l ON l.id=i.link_id WHERE (i.status='consumed') IS DISTINCT FROM (l.status='active')"))==0
        assert db.execute(text('SELECT tipo,role,team_gym_id FROM public.usuarios WHERE id IN (:a,:b) ORDER BY id'),{'a':GA,'b':GB}).all()==[('gym','OWNER',None)]*2


@pytest.mark.parametrize('operation',['logout','reset'])
def test_account_revocation_waits_after_acceptance_then_invalidates_stale_session(lab,monkeypatch,operation):
    from web import auth
    from web.services import password_recovery
    issued=issue(lab)
    reset_token=secrets.token_urlsafe(32)
    with lab['admin'].begin() as db:
        db.execute(text("UPDATE public.usuarios SET password_reset_hash=:hash,password_reset_session_version=0,password_reset_expires_at=(clock_timestamp() AT TIME ZONE 'UTC')+interval '10 minutes' WHERE id=:id"),
            {'hash':password_recovery.digest(reset_token),'id':UA})
        db.execute(text("INSERT INTO public.refresh_tokens(jti,user_id,expires_at,revoked,created_at) VALUES(:jti,:user,:expires,false,:created)"),
            {'jti':str(uuid.uuid4()),'user':UA,'expires':time.time()+600,'created':time.time()})
    ready=Event();state={}
    def factory():
        db=Session(lab['app'])
        state['pid']=db.scalar(text('SELECT pg_backend_pid()'));ready.set()
        return db
    monkeypatch.setattr(auth,'_get_session',factory)
    def revoke():
        if operation=='logout': auth.revocar_refresh_tokens_usuario(UA)
        else:
            with factory() as db: password_recovery.consume(db,reset_token,'SyntheticStrongPassword-2026!')
    with tx(lab,UA,issued['token']) as accepter, ThreadPoolExecutor(max_workers=1) as executor:
        consume_steps(accepter,issued)
        future=executor.submit(revoke);assert ready.wait(2)
        with lab['admin'].connect() as observer:
            deadline=time.monotonic()+4
            while not observer.scalar(text('SELECT cardinality(pg_blocking_pids(:pid))>0'),{'pid':state['pid']}):
                assert time.monotonic()<deadline
                time.sleep(.01)
        accepter.commit();future.result(timeout=7)
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT session_version FROM public.usuarios WHERE id=:id'),{'id':UA})==1
        assert db.scalar(text('SELECT bool_and(revoked) FROM public.refresh_tokens WHERE user_id=:id'),{'id':UA}) is True
        assert db.scalar(text('SELECT status FROM public.client_account_links'))=='active'
    # A subsequent operation must revalidate the persisted version under lock.
    another=issue(lab,gym=GB,client=CB)
    with tx(lab,UA,another['token']) as db:
        with pytest.raises(ValueError,match='stale session'): consume_steps(db,another)
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT status FROM public.client_link_invitations WHERE id=:id'),{'id':another['invitation']})=='pending'
