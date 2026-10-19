"""Owned loopback SQLite32. Real factory/auth; no send/provider or auth override."""
from pathlib import Path
import argparse, json, os, socket, sys, threading, time
from datetime import datetime, timedelta, timezone
import uuid

parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);parser.add_argument('--root',required=True);parser.add_argument('--port',type=int,required=True)
args=parser.parse_args();ROOT=Path(args.root);PHASE=Path(args.phase)
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
temporary=prepare_environment(discard_inherited=True).resolve();block_external_sockets()
base='http://127.0.0.1:'+str(args.port)
with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
os.environ.update(BASE_URL=base,CORS_ORIGINS=base+',http://testserver',RESEND_API_KEY='re_synthetic_offline_only')
from sqlalchemy import inspect,select,text
from sqlalchemy.orm import Session
from web.auth import hash_password
from web.database.engine import get_engine
from web.database.models import Base,Usuario,UserRole,Cliente,Subscription,ClientProgress,PlanGenerado
from web.database.schema_control import verify_runtime_schema
from web.services import email_service
from db_bootstrap import main as bootstrap
engine=get_engine();assert engine.dialect.name=='sqlite' and Path(engine.url.database).is_relative_to(temporary)
assert bootstrap(['--revision','20261019_personal_progress'])==0
verify_runtime_schema(engine,expected_revision='20261019_personal_progress')
ids={key:str(uuid.uuid4()) for key in ('gym','person','other','client','profile','other_profile')}
password='Synthetic-QA-Progress-2026!';now=datetime.now(timezone.utc)
with Session(engine) as db:
    for key in ('gym','person','other'):
        db.add(Usuario(id=ids[key],email='qa-progress-'+key+'@example.invalid',nombre='Synthetic '+key,
            apellido='',password_hash=hash_password(password),tipo='gym' if key=='gym' else 'usuario',
            role=UserRole.OWNER if key=='gym' else UserRole.VIEWER,activo=True,session_version=0,fecha_registro=now))
    db.flush()
    db.add_all([Cliente(id_cliente=ids['client'],gym_id=ids['gym'],nombre='Synthetic professional ficha',activo=True),
        Cliente(id_cliente=ids['profile'],gym_id=ids['person'],nombre='Synthetic explicit personal profile',activo=True),
        Cliente(id_cliente=ids['other_profile'],gym_id=ids['other'],nombre='Synthetic other profile',activo=True)])
    db.flush()
    db.add(Subscription(gym_id=ids['gym'],plan='clinica',status='active',provider='stripe',current_period_start=now-timedelta(days=1),current_period_end=now+timedelta(days=2)))
    db.add(ClientProgress(gym_id=ids['gym'],id_cliente=ids['client'],peso_kg=88.25,notas='QA_PRIVATE_NATIVE_NOTES'))
    plan=PlanGenerado(gym_id=ids['person'],id_cliente=ids['profile'],plan_json=json.dumps({'desayuno':{'alimentos':{'huevo':50}}}))
    db.add(plan);db.commit();ids['plan']=plan.id
def capture(recipient,subject,html,**kwargs):
    with (PHASE/'mail.private.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps({'html':html})+'\n')
    return True
email_service._send=capture
import uvicorn
from web.main_web import create_app
server=uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=args.port,log_level='warning',access_log=False))
def controls():
    number=0
    while not server.should_exit:
        path=PHASE/('control-'+str(number)+'.private.json')
        if not path.exists():time.sleep(.1);continue
        command=json.loads(path.read_bytes());action=command['action']
        result={'index':number,'action':action,'completed':False}
        try:
            if action=='stop':server.should_exit=True
            elif action=='owner-person':
                with Session(engine) as db:
                    actor=db.get(Usuario,ids['person']);actor.role=UserRole.OWNER;actor.session_version+=1;db.commit()
            elif action=='expire-subscription':
                with Session(engine) as db:
                    sub=db.scalar(select(Subscription).where(Subscription.gym_id==ids['gym']));sub.current_period_end=datetime.now(timezone.utc)-timedelta(seconds=1);db.commit()
            else:raise ValueError('Unknown private control action')
            result['completed']=True
        except Exception as error:result['error_class']=type(error).__name__
        with (PHASE/('control-'+str(number)+'-result.private.json')).open('x',encoding='utf8') as stream:json.dump(result,stream)
        number+=1
thread=threading.Thread(target=controls,daemon=True);thread.start()
with engine.connect() as db:
    marker={'fixture':'qa-r25-real-sqlite32','pid':os.getpid(),'port':args.port,'origin':base,
        'revision':db.scalar(text('SELECT version_num FROM alembic_version')),'model_tables':len(Base.metadata.tables),
        'physical_tables':len(inspect(db).get_table_names()),'database':str(engine.url.database),'ids':ids,'temporary_root':str(temporary)}
with (PHASE/'startup.private.json').open('x',encoding='utf8') as stream:json.dump(marker,stream)
try:server.run()
finally:
    engine.dispose()
    with (PHASE/'closure.private.json').open('x',encoding='utf8') as stream:json.dump({'server_returned':True,'engine_disposed':True,'sqlite_preserved':True,'pid':os.getpid()},stream)
