"""Independent restricted-role negatives, outside frozen product/tests."""
from contextlib import nullcontext
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import json,os,uuid

import pytest
from sqlalchemy import create_engine,event,text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
from tests.integration_client_link_canonical_postgres import (
    GA,GB,UA,UB,TEAM,CA,CA2,CB,digest,issue,accept,publish,consume_steps,tx,
)
from tests.isolation import validate_postgres_test_url
from web.database.tenant_context import configure_tenant_engine,tenant_scope

HERE=Path(__file__).parent
OBS=[]

def observed(case,**values):
    OBS.append({'case':case,**values})
    (HERE/'observations.json').write_text(json.dumps(OBS,indent=2)+'\n',encoding='utf8')

@pytest.fixture(scope='module')
def lab():
    import psycopg2
    from psycopg2 import sql
    from web.database.models import Usuario,UserRole,Cliente,PlanGenerado,StoredObject
    from web.storage.objects import describe
    migrator=os.environ['METODOBASE_TEST_MIGRATOR_URL']
    validate_postgres_test_url(migrator)
    parts=urlsplit(migrator)
    assert parts.hostname in {'127.0.0.1','localhost'} and parts.port==55483
    name='metodobase_test_sec_r12_'+uuid.uuid4().hex
    registry=HERE/'owned-database.json'
    assert not registry.exists()
    registry.write_text(json.dumps({'owned_name':name,'created':False,'dropped':False})+'\n')
    control=psycopg2.connect(migrator.replace('postgresql+psycopg2://','postgresql://',1))
    control.autocommit=True
    with control.cursor() as cursor:cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    registry.write_text(json.dumps({'owned_name':name,'created':True,'dropped':False})+'\n')
    url=urlunsplit(parts._replace(path='/'+name))
    admin=create_engine(url,hide_parameters=True)
    app=None
    try:
        run_migration(url,'db_bootstrap.py','--revision','20261019_client_account_links')
        objects,plans={},{}
        with Session(admin) as db:
            for identity,kind,role,parent in [(GA,'gym',UserRole.OWNER,None),(GB,'gym',UserRole.OWNER,None),
                (UA,'usuario',UserRole.VIEWER,None),(UB,'usuario',UserRole.VIEWER,None),(TEAM,'usuario',UserRole.NUTRIOLOGO,GA)]:
                db.add(Usuario(id=identity,email=identity+'@example.invalid',password_hash='synthetic-only',nombre='Synthetic',
                    tipo=kind,role=role,team_gym_id=parent,activo=True))
            db.flush()
            for client,gym in [(CA,GA),(CA2,GA),(CB,GB)]:
                db.add(Cliente(id_cliente=client,gym_id=gym,nombre='Synthetic',activo=True))
                obj=describe(gym,'plan_pdf',b'%PDF-1.7\nindependent-synthetic-'+client.encode(),'application/pdf')
                objects[client]=obj
                db.add(StoredObject(id=obj.id,gym_id=gym,kind=obj.kind,key=obj.key,content_type=obj.content_type,
                    byte_size=obj.byte_size,sha256=obj.sha256,storage_backend='local',status='ready'))
                db.flush()
                plan=PlanGenerado(gym_id=gym,id_cliente=client,pdf_object_id=obj.id,plan_json=json.dumps({m:{
                    'kcal_objetivo':100,'kcal_real':100,'alimentos':{'independent-synthetic-food':50}}
                    for m in ('desayuno','almuerzo','comida','cena')}))
                db.add(plan);db.flush();plans[client]=plan.id
            db.commit()
        granted=application_engine(url,admin)
        app=configure_tenant_engine(create_engine(granted.url,pool_size=1,max_overflow=0,hide_parameters=True))
        granted.dispose()
        # No author make_app()/clear_proof event: only the real product hook.
        with app.connect() as db:
            assert db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()==(False,False,False,False)
            assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND pg_has_role(current_user,relowner,'MEMBER'))"))
        yield {'admin':admin,'app':app,'objects':objects,'plans':plans}
    finally:
        if app is not None:app.dispose()
        admin.dispose()
        owned=json.loads(registry.read_text())
        assert owned['owned_name']==name and name.startswith('metodobase_test_sec_r12_') and len(name.rsplit('_',1)[1])==32
        with control.cursor() as cursor:cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        registry.write_text(json.dumps({'owned_name':name,'created':True,'dropped':True})+'\n')
        control.close()

@pytest.fixture(autouse=True)
def clean(lab):
    with lab['admin'].begin() as db:
        db.exec_driver_sql('TRUNCATE client_plan_publications,client_link_invitations,client_account_links')
        db.execute(text('UPDATE clientes SET activo=true,deleted_at=NULL'))
        db.execute(text("UPDATE stored_objects SET status='ready'"))
        db.execute(text('UPDATE planes_generados SET deleted_at=NULL'))
        db.execute(text('UPDATE usuarios SET activo=true,deleted_at=NULL,session_version=0,invitation_token=NULL'))
        db.execute(text("UPDATE usuarios SET tipo='gym',role='OWNER',team_gym_id=NULL WHERE id IN (:a,:b)"),{'a':GA,'b':GB})
        db.execute(text("UPDATE usuarios SET tipo='usuario',role='VIEWER',team_gym_id=NULL WHERE id IN (:a,:b)"),{'a':UA,'b':UB})
        db.execute(text("UPDATE usuarios SET tipo='usuario',role='NUTRIOLOGO',team_gym_id=:gym WHERE id=:id"),{'gym':GA,'id':TEAM})

@pytest.mark.parametrize('mutation',['resource_owner','actor_parent'])
def test_noncanonical_owner_parent_cannot_keep_recipient_publication(lab,mutation):
    recipient=UA if mutation=='resource_owner' else TEAM
    issued=issue(lab,gym=GA if mutation=='resource_owner' else GB,client=CA if mutation=='resource_owner' else CB,recipient=recipient)
    accept(lab,issued);publication=publish(lab,issued)
    with tx(lab,recipient) as db:
        assert db.scalar(text('SELECT count(*) FROM client_plan_publications WHERE id=:id'),{'id':publication})==1
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE usuarios SET team_gym_id=:parent WHERE id=:id'),{'parent':GB,'id':GA})
    with tx(lab,recipient) as db:
        assert db.scalar(text('SELECT public.r12_canonical_gym(:id)'),{'id':GA}) is False
        visible=db.scalar(text('SELECT count(*) FROM client_plan_publications WHERE id=:id'),{'id':publication})
        observed('noncanonical_'+mutation,canonical_owner=False,recipient_visible_publications=visible)
        assert visible==0,'recipient must fail closed for a noncanonical resource owner or professional parent'

@pytest.mark.parametrize('proof',['empty','wrong_purpose','valid'])
def test_owner_own_acceptance_commit_requires_current_purpose(lab,proof):
    issued=issue(lab,recipient=GA)
    with tx(lab,GA,issued['token']) as db:
        consume_steps(db,issued)
        if proof=='empty':db.execute(text("SELECT set_config('app.client_invitation_digest','',true)"))
        elif proof=='wrong_purpose':
            import hashlib
            db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),{'hash':hashlib.sha256(issued['token'].encode()).hexdigest()})
        if proof=='valid':
            db.commit()
        else:
            with pytest.raises(DBAPIError):db.commit()
    with lab['admin'].connect() as db:
        states=db.execute(text('SELECT i.status,l.status FROM client_link_invitations i JOIN client_account_links l ON l.id=i.link_id')).one()
        assert states==(('consumed','active') if proof=='valid' else ('pending','pending'))

@pytest.mark.parametrize('api',['connection','session'])
@pytest.mark.parametrize('ending',['commit','rollback','error'])
def test_real_begin_hook_masks_pool_session_purpose(lab,api,ending):
    issued=issue(lab)
    # Install a genuinely session-level value through DBAPI without an engine begin hook.
    raw=lab['app'].raw_connection()
    try:
        with raw.cursor() as c:c.execute("SELECT set_config('app.client_invitation_digest',%s,false)",(digest(issued['token']),))
        raw.commit()
    finally:raw.close()
    with tenant_scope(UA):
        first=lab['app'].connect() if api=='connection' else Session(lab['app'])
        try:
            pid=first.scalar(text('SELECT pg_backend_pid()'))
            assert first.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
            assert first.scalar(text('SELECT count(*) FROM client_link_invitations'))==0
            first.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),{'hash':digest(issued['token'])})
            assert first.scalar(text('SELECT count(*) FROM client_link_invitations'))==1
            if ending=='commit':first.commit()
            elif ending=='rollback':first.rollback()
            else:
                with pytest.raises(DBAPIError):first.execute(text('SELECT 1/0'))
                first.rollback()
        finally:first.close()
    for actor in [UB,UA,None]:
        scope=tenant_scope(actor) if actor else nullcontext()
        with scope:
            second=lab['app'].connect() if api=='connection' else Session(lab['app'])
            try:
                assert second.scalar(text('SELECT pg_backend_pid()'))==pid
                assert second.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
                assert second.scalar(text('SELECT count(*) FROM client_link_invitations'))==0
            finally:second.close()

@pytest.mark.parametrize('api',['connection','session'])
def test_purpose_begin_install_failure_blocks_business_query(lab,api):
    issued=issue(lab)
    own=configure_tenant_engine(create_engine(lab['app'].url,pool_size=1,max_overflow=0,hide_parameters=True))
    seen=[]
    def intercept(conn,cursor,statement,parameters,context,executemany):
        if 'client_link_invitations' in statement:seen.append('business')
        if "set_config('app.client_invitation_digest'" in statement:raise RuntimeError('synthetic-purpose-install-failed')
    event.listen(own,'before_cursor_execute',intercept)
    try:
        with tenant_scope(UA):
            resource=own.connect() if api=='connection' else Session(own)
            try:
                with pytest.raises(RuntimeError,match='synthetic-purpose-install-failed'):
                    resource.scalar(text('SELECT count(*) FROM client_link_invitations'))
                assert seen==[]
            finally:resource.close()
    finally:
        event.remove(own,'before_cursor_execute',intercept);own.dispose()

@pytest.mark.parametrize('attempt',['noop','withdraw','metadata','move_gym','move_plan','delete'])
def test_reader_locks_never_allow_business_dml(lab,attempt):
    issued=issue(lab);accept(lab,issued);published=publish(lab,issued)
    with tx(lab,UA) as db:
        assert db.scalar(text('SELECT id FROM client_plan_publications WHERE id=:id FOR NO KEY UPDATE'),{'id':published})==published
    statement={
        'noop':'UPDATE client_plan_publications SET status=status WHERE id=:id',
        'withdraw':"WITH changed AS (UPDATE client_plan_publications SET status='withdrawn',publication_version=publication_version+1 WHERE id=:id RETURNING id) SELECT id FROM changed",
        'metadata':"UPDATE client_plan_publications SET published_at=published_at+interval '1 second' WHERE id=:id",
        'move_gym':'UPDATE client_plan_publications SET gym_id=:actor WHERE id=:id',
        'move_plan':'UPDATE client_plan_publications SET source_plan_id=:plan WHERE id=:id',
        'delete':'DELETE FROM client_plan_publications WHERE id=:id RETURNING id',
    }[attempt]
    with tx(lab,UA) as db:
        try:
            result=db.execute(text(statement),{'id':published,'actor':UA,'plan':lab['plans'][CA2]})
            assert attempt=='delete' and result.all()==[]
        except DBAPIError as denied:
            assert denied.orig.pgcode in {'23514','42501'}
        else:assert attempt=='delete'
    with lab['admin'].connect() as db:
        assert db.scalar(text("SELECT count(*) FROM client_plan_publications WHERE id=:id AND status='published' AND publication_version=1"),{'id':published})==1

def test_deferred_fk_forced_early_aborts_full_transaction(lab):
    issued=issue(lab)
    with tx(lab,UA,issued['token']) as db:
        consume_steps(db,issued,activate=False)
        with pytest.raises(DBAPIError) as denied:db.exec_driver_sql('SET CONSTRAINTS fk_client_invitation_consumption IMMEDIATE')
        assert denied.value.orig.pgcode=='23503'
        with pytest.raises(DBAPIError) as aborted:db.exec_driver_sql('SELECT 1')
        assert aborted.value.orig.pgcode=='25P02'
    with lab['admin'].connect() as db:
        assert db.execute(text('SELECT i.status,l.status FROM client_link_invitations i JOIN client_account_links l ON l.id=i.link_id')).one()==('pending','pending')

def test_recipient_future_revocation_does_not_need_old_bearer(lab):
    issued=issue(lab);accept(lab,issued);published=publish(lab,issued)
    with tx(lab,UA) as db:
        assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
        assert db.execute(text("UPDATE client_account_links SET status='revoked',version=version+1 WHERE id=:id RETURNING id"),{'id':issued['link']}).scalar_one()==issued['link']
        db.commit()
    with tx(lab,UA) as db:
        assert db.scalar(text('SELECT count(*) FROM client_plan_publications WHERE id=:id'),{'id':published})==0
    with lab['admin'].connect() as db:
        assert db.execute(text('SELECT i.status,i.consumed_by=l.user_id,i.consumed_at=l.accepted_at FROM client_link_invitations i JOIN client_account_links l ON l.id=i.link_id')).one()==('consumed',True,True)
