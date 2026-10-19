"""Own R24 loopback runtime31; actual auth, worker, objects, publication and diary.

Migrates only a newly allocated PostgreSQL UUID. No privileged HTTP test
endpoint. Invitation delivery has a no-send boundary double with a committed
database witness; its fragment is written only to a private Temp channel.
"""
import sys
sys.dont_write_bytecode=True
import argparse,atexit,hashlib,json,os,re,threading,time,uuid
from datetime import datetime,timedelta,timezone
from html import unescape
from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--private',required=True);parser.add_argument('--config',required=True);args=parser.parse_args()
    import tempfile
    private=Path(args.private).resolve()
    assert private.is_dir() and private.is_relative_to(Path(tempfile.gettempdir()).resolve())
    from tests.isolation import prepare_environment,block_external_sockets
    for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','PYTEST_XDIST_WORKER'):
        os.environ.pop(key,None)
    own=prepare_environment(discard_inherited=True).resolve();block_external_sockets()
    import base64
    os.environ['MFA_ENCRYPTION_KEY']=base64.urlsafe_b64encode(os.urandom(32)).decode()
    origin='http://127.0.0.1:8800';os.environ.update(BASE_URL=origin,CORS_ORIGINS=origin)
    configuration=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    from tests.isolation import validate_postgres_test_url
    for name in ('METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN'):os.environ[name]=configuration[name]
    for name in ('METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL'):validate_postgres_test_url(os.environ[name])
    from tests.integration_schema_migrations import run_migration,migration_database
    from tests.integration_provider_subjects import application_engine
    from types import SimpleNamespace
    generator=migration_database.__wrapped__(SimpleNamespace(param='postgresql'),own)
    url,admin=next(generator);restricted=None;server=None;thread=None;closed=False
    resource={'owned_database':admin.url.database,'port':8800,'pid':os.getpid()}
    (private/'resource.json').write_text(json.dumps(resource,indent=2),encoding='utf8')
    def cleanup():
        nonlocal closed
        if closed:return
        if server is not None:server.should_exit=True
        if thread is not None:thread.join(10)
        if restricted is not None:restricted.dispose()
        generator.close();closed=True
        import psycopg2
        with psycopg2.connect(os.environ['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as control,control.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(resource['owned_database'],));assert cursor.fetchone()[0]==0
        resource['owned_database_absent_after']=True
        (private/'resource.json').write_text(json.dumps(resource,indent=2),encoding='utf8')
    atexit.register(cleanup)
    run_migration(url,'db_bootstrap.py','--revision','20261019_google_subjects')
    bootstrap=application_engine(url,admin);restricted_url=bootstrap.url.render_as_string(hide_password=False);bootstrap.dispose()
    os.environ['DATABASE_URL']=restricted_url
    from sqlalchemy import select,text
    from sqlalchemy.orm import Session
    from web.database import engine as database
    database._engine=None;database._SessionLocal=None
    from web.database.models import Base,Usuario,UserRole,Subscription,ClientLinkInvitation
    from web.database.schema_control import verify_runtime_schema,expected_head
    from web.database.tenant_context import current_tenant
    from web.services import email_service
    from web.settings import get_settings
    engine=database.get_engine();restricted=engine
    assert engine.dialect.name=='postgresql' and engine.url.database==resource['owned_database']
    verify_runtime_schema(engine,require_revision=True)
    with engine.connect() as connection:
        revision=connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
        flags=connection.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()
        database_nonowner=connection.execute(text('SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()')).scalar_one()
        application_role_restricted_nonowner=tuple(flags)==(False,False,False,False) and database_nonowner is True
        assert application_role_restricted_nonowner is True
        assert connection.execute(text("SELECT count(*) FROM pg_class WHERE relname IN ('personal_diary_days','client_account_links','client_plan_publications') AND relrowsecurity AND relforcerowsecurity")).scalar_one()==3
    resource.update(role_super=False,role_bypass=False,app_database_owner=False,force_rls_families=3,runtime_revision=revision)
    assert revision==expected_head()=='20261019_google_subjects'
    settings=get_settings();settings.RESEND_API_KEY='synthetic-no-send';mail=[];mail_lock=threading.Lock()
    def no_send(recipient,subject,html,**_kwargs):
        if '/auth/accept-client-link#token=' not in html:return True
        assert current_tenant.get()==''
        found=re.search(re.escape(origin)+r'/auth/accept-client-link#token=([A-Za-z0-9_-]{43})',unescape(html));assert found
        with Session(admin) as db:
            invitation=db.scalar(select(ClientLinkInvitation).where(ClientLinkInvitation.recipient_email==recipient,ClientLinkInvitation.status=='pending').order_by(ClientLinkInvitation.created_at.desc()))
            assert invitation is not None;link_id=invitation.link_id
        with mail_lock:
            mail.append({'recipient':recipient,'url':found.group(0),'link_id':link_id,'committed_pending':True,'empty_tenant':True})
            (private/'mail.private.json').write_text(json.dumps(mail),encoding='utf8')
        return True
    email_service._send=no_send
    from web.main_web import create_app
    import uvicorn
    server=uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=8800,log_level='warning'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    for _ in range(200):
        if server.started:break
        if not thread.is_alive():raise RuntimeError('Own R24 server failed')
        time.sleep(.05)
    assert server.started
    opener=build_opener(ProxyHandler({}));password='Synthetic-R24-Password-2026!';pairs={}
    def call(path,payload=None,token=None,method='POST',key=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        if key:headers['Idempotency-Key']=key
        request=Request(origin+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers,method=method)
        with opener.open(request,timeout=120) as response:
            assert response.status in (200,201,202);return json.load(response)
    profile={'edad':30,'peso_kg':75,'estatura_cm':175,'sexo':'M','objetivo':'mantenimiento','nivel_actividad':'moderada'}
    identities={}
    for name in ('person','other','gym'):
        pairs[name]=call('/api/auth/registro',{'email':'r24-'+name+'@example.invalid','password':password,'nombre':'Synthetic R24 '+name,'tipo':'gym' if name=='gym' else 'usuario'})
        me=call('/api/auth/me',token=pairs[name]['token'],method='GET');identities[name]={'id':me['id'],'role':me['role'],'tipo':me['tipo'],'team_gym_id':me.get('team_gym_id')}
        if name!='gym':
            assert me['role']=='viewer' and me['tipo']=='usuario'
            call('/api/usuario/perfil',profile,pairs[name]['token'],'PUT')
        with Session(admin) as db:
            db.add(Subscription(gym_id=me['id'],plan='clinica' if name=='gym' else 'pro_usuario',status='active',current_period_end=datetime.now(timezone.utc)+timedelta(days=30)));db.commit()
    client=call('/api/clientes',{'nombre':'Synthetic published source',**profile},pairs['gym']['token'])
    client_id=client.get('id_cliente') or client.get('cliente',{}).get('id_cliente');assert client_id
    plan=call('/api/generar-plan',{'id_cliente':client_id,'plan_numero':1,'tipo_plan':'opciones'},pairs['gym']['token'],key=str(uuid.uuid4()))
    assert isinstance(plan['plan_id'],int)
    (private/'fixture.private.json').write_text(json.dumps({'origin':origin,'password':password,'pairs':pairs,'identities':identities,'client_id':client_id,'professional_plan_id':plan['plan_id']}),encoding='utf8')
    names=sorted({str(p.relative_to(ROOT)).replace('\\','/') for folder in ('web','api','core','src','config') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.js','.html','.css') and '__pycache__' not in p.parts})
    names+=['requirements_web.lock','requirements_web-windows.lock','requirements-test.lock','requirements-test-windows.lock','tests/e2e/daily_plan33_server.py']
    hashes=lambda:{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    assert len(Base.metadata.tables)==35 and len(__import__('sqlalchemy').inspect(engine).get_table_names())==36
    from tests.ci_google33.physical import physical_contract
    global_witness=physical_contract(engine,expected_pool=20)
    before=hashes();startup={'physical_witness':global_witness,'fixture':'r24-daily-plan31','pid':os.getpid(),'origin':origin,'runtime_revision':revision,'model_tables':len(Base.metadata.tables),'actual_tables':len(__import__('sqlalchemy').inspect(engine).get_table_names()),
        'application_role_restricted_nonowner':application_role_restricted_nonowner,
        'preparation':'actual Alembic31 on own UUID PostgreSQL restricted runtime role, real HTTP registrations/worker, synthetic persisted subscriptions only, no-send email boundary',
        'external_sockets':'blocked before product imports; not an OS sandbox','sources':before}
    (private/'startup.json').write_text(json.dumps(startup,indent=2),encoding='utf8');print(json.dumps({'fixture':startup['fixture'],'pid':os.getpid(),'origin':origin,'runtime_revision':revision,'source_count':len(before)}),flush=True)
    try:
        while thread.is_alive() and not (private/'stop').exists():time.sleep(.2)
    finally:
        server.should_exit=True;thread.join(10);assert not thread.is_alive()
        after=hashes();(private/'close.json').write_text(json.dumps({'pid':os.getpid(),'server_thread_closed':True,'source_before':before,'source_after':after,'sources_stable':before==after},indent=2),encoding='utf8')
        cleanup()


if __name__=='__main__':main()
