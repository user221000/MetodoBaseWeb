from pathlib import Path
import contextlib,datetime,hashlib,importlib,io,json,logging,os,re,subprocess,sys,traceback
from unittest.mock import patch
from urllib.parse import urlsplit,urlunsplit

sys.dont_write_bytecode=True
HERE=Path(__file__).parent;ROOT=Path('F:/mb-follow-sec');sys.path.insert(0,str(ROOT))
from tests.isolation import prepare_environment,block_external_sockets
DATA=prepare_environment(discard_inherited=True);block_external_sockets()
from sqlalchemy import create_engine,event,text
from sqlalchemy.orm import Session,sessionmaker
from fastapi.testclient import TestClient
from web.database import engine as database
from web.database.models import Base,Usuario,UserRole,Cliente,PlanGenerado,StoredObject,GymGenerationReservation
from web.auth import crear_access_token,identity_from_user,init_auth
from web.database.tenant_context import tenant_scope
init_auth()
UTC=datetime.timezone.utc;NOW=datetime.datetime.now(UTC);PATH='/api/estadisticas/seguimiento'
RESULTS=[];CLOSURE=[]
def require(v,msg='independent criterion failed'):
    if not v:raise AssertionError(msg)
def record(label,fn):
    try:fn();RESULTS.append({'name':label,'passed':True})
    except Exception as error:
        # Detailed synthetic stack goes to private RAW; connection URLs are never printed.
        (HERE/(re.sub('[^a-zA-Z0-9_-]','_',label)+'.trace')).write_text(traceback.format_exc(),encoding='utf8')
        RESULTS.append({'name':label,'passed':False,'error_class':type(error).__name__})
    print(json.dumps(RESULTS[-1]),flush=True)
def clean(engine):
    with engine.begin() as c:
        for table in reversed(Base.metadata.sorted_tables):c.execute(table.delete())
def seed(engine):
    with Session(engine) as db:
        for name,role,team,kind in [('A',UserRole.OWNER,None,'gym'),('B',UserRole.OWNER,None,'gym'),('ADMIN',UserRole.ADMIN,'A','usuario'),('VIEWER',UserRole.VIEWER,'A','usuario'),('AMBIGUOUS',UserRole.OWNER,None,'usuario')]:
            db.add(Usuario(id=name,email=name+'@example.invalid',nombre='Synthetic',password_hash='unused',role=role,tipo=kind,team_gym_id=team,activo=True));db.flush()
        for name,gym,active,deleted in [('a-empty','A',True,False),('a-soft-plan','A',True,False),('a-recent','A',True,False),('a-inactive','A',False,False),('a-deleted','A',True,True),('b-private','B',True,False)]:
            db.add(Cliente(id_cliente=name,gym_id=gym,nombre='PRIVATE_FOREIGN_CLIENT' if gym=='B' else 'SYNTHETIC_OWN',email='PRIVATE_EMAIL@example.invalid',notas='PRIVATE_NOTES',activo=active,deleted_at=NOW if deleted else None,fecha_fin_suscripcion=NOW.replace(tzinfo=None)-datetime.timedelta(days=1) if name=='a-recent' else None));db.flush()
        obj=StoredObject(id='d'*32,gym_id='A',kind='gym_logo',key='PRIVATE_OBJECT_KEY',content_type='application/pdf',byte_size=10,sha256='e'*64,storage_backend='local',status='ready');db.add(obj);db.flush()
        live=PlanGenerado(gym_id='A',id_cliente='a-recent',fecha_generacion=NOW-datetime.timedelta(days=1),plan_json='PRIVATE_PLAN_JSON',ruta_pdf='PRIVATE_LOCAL_PATH',pdf_object_id=obj.id);db.add(live);db.flush()
        for client,gym,deleted in [('a-soft-plan','A',True),('a-inactive','A',False),('a-deleted','A',False),('a-empty','B',False),('b-private','A',False)]:
            db.add(PlanGenerado(gym_id=gym,id_cliente=client,fecha_generacion=NOW-datetime.timedelta(days=1),deleted_at=NOW if deleted else None,plan_json='PRIVATE_PLAN_JSON'))
        db.add(GymGenerationReservation(gym_id='B',client_id='a-recent',request_key='PRIVATE_REQUEST_KEY',request_hash='f'*64,period=NOW.strftime('%Y-%m'),local_date=NOW.date(),timezone='America/Mexico_City',catalog_plan='free',status='completed',persisted_at=NOW,plan_id=live.id,result_json='PRIVATE_RESULT'))
        db.commit()
def headers(engine,name,override=None):
    with Session(engine) as db:
        user=identity_from_user(db.get(Usuario,name),db);require(user is not None)
        if override:user={**user,**override}
        return {'Authorization':'Bearer '+crear_access_token(user)}
@contextlib.contextmanager
def application(factory,engine):
    with patch.object(database,'_engine',engine),patch.object(database,'_SessionLocal',sessionmaker(bind=engine,autoflush=False)):
        with TestClient(importlib.import_module(factory).create_app(),raise_server_exceptions=False) as client:yield client
@contextlib.contextmanager
def observe(engine):
    statements=[]
    def cb(conn,cursor,sql,params,context,many):statements.append(sql)
    event.listen(engine,'before_cursor_execute',cb)
    try:yield statements
    finally:event.remove(engine,'before_cursor_execute',cb)
def no_dml(statements):
    require(not any(re.match(r'\s*(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE)\b',s,re.I) for s in statements),'HTTP read or rejected method executed DML/DDL')
def business(statements):return [s for s in statements if ' AS priority' in s or ' AS plans_saved' in s]
def facts(client,engine):
    with observe(engine) as statements:r=client.get(PATH+'?gym_id=B&id_cliente=b-private&limit=100',headers=headers(engine,'ADMIN'))
    require(r.status_code==200,'facts status');body=r.json()
    require([x['id_cliente'] for x in body['items']]==['a-empty','a-soft-plan','a-recent'],'double-owner or soft-delete scope')
    require([x['causes'] for x in body['items']]==[['no_saved_plan'],['no_saved_plan'],['membership_date_passed']])
    require(body['metrics']=={'plans_saved':1,'generation_operations_completed':0,'pdf_metadata_ready':0},'foreign ledger or wrong-kind object contributed')
    require(set(body)=={'as_of','window_start','window_days','items','limit','has_more','metrics','payment_evidence','responsibility','sources','capabilities'})
    require(all(set(x)=={'id_cliente','nombre','causes','priority','last_plan_at','elapsed_days','membership_end','responsible','next_step'} for x in body['items']))
    require('PRIVATE_' not in r.text,'private projected data escaped DTO')
    require(r.headers['Cache-Control']=='no-store' and r.headers['Referrer-Policy']=='no-referrer')
    queries=business(statements);require(len(queries)==2)
    require(all(x not in '\n'.join(queries) for x in ['plan_json','ruta_pdf','request_key','email','notas']))
    no_dml(statements)
def forged(client,engine):
    forged_headers=headers(engine,'VIEWER',{'role':'owner','tipo':'gym','team_gym_id':'B'})
    with observe(engine) as statements:r=client.get(PATH,headers=forged_headers)
    require(r.status_code in (401,403),'persisted viewer got forged privilege');require('items' not in r.json());require(not business(statements));no_dml(statements)
def ambiguous(client,engine):
    forged_headers=headers(engine,'AMBIGUOUS',{'tipo':'gym','role':'owner'})
    with observe(engine) as statements:r=client.get(PATH,headers=forged_headers)
    require(r.status_code in (401,403),'ambiguous personal OWNER adopted portfolio');require(not business(statements));no_dml(statements)
def methods(client,engine):
    auth=headers(engine,'A')
    with observe(engine) as statements:
        for method in ['POST','PUT','PATCH','DELETE']:require(client.request(method,PATH,headers=auth,json={'gym_id':'B'}).status_code==405,method+' mounted mutable path')
    require(not business(statements));no_dml(statements)
def sql_failure(client,engine):
    from sqlalchemy.exc import OperationalError
    import web.routes.followup as route
    stream=io.StringIO();handler=logging.StreamHandler(stream);logger=logging.getLogger(route.__name__);logger.addHandler(handler)
    try:
        with patch.object(route,'get_followup',side_effect=OperationalError('PRIVATE_SQL_STATEMENT',{'email':'PRIVATE_SQL_PARAM'},RuntimeError('PRIVATE_DRIVER_TEXT'))):
            r=client.get(PATH,headers=headers(engine,'A'))
        require(r.status_code==503 and r.json()=={'detail':{'code':'followup_unavailable','message':'No fue posible consultar el seguimiento. Vuelve a intentar.'}})
        require('PRIVATE_' not in r.text+stream.getvalue());require('OperationalError' in stream.getvalue())
        require(r.headers['Cache-Control']=='no-store' and r.headers['Referrer-Policy']=='no-referrer')
    finally:logger.removeHandler(handler)
def revocation(client,engine,admin):
    old=headers(engine,'ADMIN')
    with Session(admin) as db:
        user=db.get(Usuario,'ADMIN');user.team_gym_id=None;user.role=UserRole.VIEWER;user.session_version+=1;db.commit()
    with observe(engine) as statements:r=client.get(PATH,headers=old)
    require(r.status_code==401,'old membership token survived');require(not business(statements));no_dml(statements)

if __name__=='__main__':
    sqlite=create_engine('sqlite:///'+(DATA/'own-review.db').as_posix(),connect_args={'check_same_thread':False});Base.metadata.create_all(sqlite)
    for factory in ['web.main_web','api.app']:
        for name,body in [('facts and strict projected scopes',facts),('forged JWT authority',forged),('ambiguous personal OWNER',ambiguous),('all mutable methods denied',methods),('SQL exception privacy',sql_failure),('persisted membership revoked',lambda c,e:revocation(c,e,e))]:
            def case(f=factory,fn=body):
                clean(sqlite);seed(sqlite)
                with application(f,sqlite) as client:fn(client,sqlite)
            record(factory+' SQLite '+name,case)
    sqlite.dispose()
    # Profiles remain private and are loaded only after the ordinary test scrub.
    profile=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes());os.environ.update(profile)
    from tests.integration_schema_migrations import run_migration
    from tests.integration_provider_subjects import application_engine
    import psycopg2
    from psycopg2 import sql
    registry_path=HERE/'owned-databases.json';registry=json.loads(registry_path.read_bytes())
    admin_url=profile['METODOBASE_TEST_MIGRATOR_URL'];parsed=urlsplit(admin_url);require(parsed.hostname in ['localhost','127.0.0.1'] and parsed.port==55483)
    control=psycopg2.connect(admin_url.replace('postgresql+psycopg2://','postgresql://',1));control.autocommit=True
    for entry in registry['entries']:
        admin=None;app=None
        try:
            name=entry['database'];require(re.fullmatch(r'metodobase_test_r23_security_[a-f0-9]{12}',name) is not None)
            with control.cursor() as c:c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            entry['created']=True;registry_path.write_text(json.dumps(registry,indent=2)+'\n')
            url=urlunsplit(parsed._replace(path='/'+name));admin=create_engine(url)
            # Bootstrap stdout/stderr retained privately, not emitted to the review console.
            migration=run_migration(url,'db_bootstrap.py','--revision','head')
            (HERE/(name+'.migration.stdout')).write_text(migration.stdout,encoding='utf8');(HERE/(name+'.migration.stderr')).write_text(migration.stderr,encoding='utf8')
            seed(admin);app=application_engine(url,admin)
            def pg_case():
                with app.connect() as c:
                    flags=c.execute(text('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user')).one();require(tuple(flags)==(False,False))
                    require(c.execute(text("SELECT count(*) FROM pg_class WHERE relname IN ('clientes','planes_generados') AND relnamespace='public'::regnamespace AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)")).scalar_one()==0)
                    require(c.execute(text("SELECT count(*) FROM pg_class WHERE relname IN ('clientes','planes_generados') AND relnamespace='public'::regnamespace AND relrowsecurity AND relforcerowsecurity")).scalar_one()==2)
                with application(entry['factory'],app) as client:
                    facts(client,app);forged(client,app);ambiguous(client,app);methods(client,app);sql_failure(client,app);revocation(client,app,admin)
                with Session(app) as db:require(db.query(Cliente).count()==0,'public pool reused prior tenant')
                with tenant_scope('B'),Session(app) as db:require([x.id_cliente for x in db.query(Cliente).all()]==['b-private'],'foreign pool scope mismatch')
                CLOSURE.append({'factory':entry['factory'],'database':name,'restricted_nonowner':True,'force_rls':True,'public_pool_empty':True,'other_tenant_explicit':True})
            record(entry['factory']+' PG restricted HTTP scope and pool cleanup',pg_case)
        except Exception as error:
            (HERE/(entry['database']+'.setup.trace')).write_text(traceback.format_exc(),encoding='utf8');RESULTS.append({'name':entry['factory']+' PG setup','passed':False,'error_class':type(error).__name__});print(json.dumps(RESULTS[-1]),flush=True)
        finally:
            if app is not None:app.dispose()
            if admin is not None:admin.dispose()
            if entry['created']:
                with control.cursor() as c:
                    c.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(entry['database'])))
                    c.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(entry['database'],));require(c.fetchone()[0]==0)
                entry['closed']=True;registry_path.write_text(json.dumps(registry,indent=2)+'\n')
    control.close()
    result={'scope':'Independent HTTP/SQLite and two own migrated PG UUID databases, restricted app role; no browser/providers','total':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'results':RESULTS,'pg_properties':CLOSURE,'owned_database_closure':registry,'source_root':str(ROOT),'synthetic_data_root':str(DATA)}
    out=HERE/'http-results.json';require(not out.exists());out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'total':result['total'],'passed':result['passed'],'owned_db_closed':all(e['closed'] for e in registry['entries'])}),flush=True)
    sys.exit(0 if result['total']==result['passed'] else 1)
