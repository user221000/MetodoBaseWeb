"""Own SQLite32 web server; TCP driver creates actual invitation lineage.

No auth/limiter override. Controls only parent OFF, a one-shot already committed
ACK loss with real rollback/close, bounded read-only witnesses and own stop.
"""
from pathlib import Path
import argparse,base64,json,os,socket,sys,threading,time,uuid
from datetime import UTC,datetime,timedelta
parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);parser.add_argument('--root',required=True);parser.add_argument('--port',required=True,type=int)
args=parser.parse_args();ROOT=Path(args.root);PHASE=Path(args.phase);sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
temporary=prepare_environment(discard_inherited=True).resolve();block_external_sockets();origin='http://127.0.0.1:'+str(args.port)
with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
os.environ.update(BASE_URL=origin,CORS_ORIGINS=origin+',http://testserver',RESEND_API_KEY='re_synthetic_offline_only',MFA_ENCRYPTION_KEY=base64.urlsafe_b64encode(os.urandom(32)).decode())
from sqlalchemy import func,inspect,select,text
from sqlalchemy.orm import Session,sessionmaker
from web.auth import hash_password
from web.database.engine import get_engine
from web.database.models import Base,Usuario,UserRole,Cliente,Subscription,ProgressConsent,MfaAuthorization,RefreshToken,AuthAuditLog
from web.database.schema_control import verify_runtime_schema
from web.services import email_service
from db_bootstrap import main as bootstrap
engine=get_engine();assert engine.dialect.name=='sqlite' and Path(engine.url.database).is_relative_to(temporary)
assert bootstrap(['--revision','20261019_personal_progress'])==0;verify_runtime_schema(engine,expected_revision='20261019_personal_progress')
ids={key:str(uuid.uuid4()) for key in ('parent','professional','clientA','clientB','clientC')};now=datetime.now(UTC);password='Synthetic-QA-Retirement-2026!'
with Session(engine) as db:
    for kind in ('parent','professional'):
        db.add(Usuario(id=ids[kind],email='qa-retirement-'+kind+'@example.invalid',nombre='Synthetic '+kind,apellido='',tipo='gym',role=UserRole.OWNER,password_hash=hash_password(password),activo=True,session_version=0,fecha_registro=now))
    db.flush()
    for label in ('A','B','C'):db.add(Cliente(id_cliente=ids['client'+label],gym_id=ids['professional'],nombre='Synthetic exact retirement '+label,activo=True))
    for kind in ('parent','professional'):db.add(Subscription(gym_id=ids[kind],plan='clinica',status='active',provider='stripe',max_clientes=0,current_period_start=now-timedelta(days=1),current_period_end=now+timedelta(days=2)))
    db.commit()
def capture(recipient,subject,html,**kwargs):
    with (PHASE/'mail.private.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps({'recipient':recipient,'html':html})+'\n')
    return True
email_service._send=capture;fault={'target':None,'used':False}
class LostOnce(Session):
    def commit(self):
        lose=fault['target'] is not None and not fault['used'] and any(getattr(row,'event_type',None)=='progress_retirement_withdraw' and row.user_id==fault['target'] for row in self.new)
        super().commit()
        if lose:fault['used']=True;raise RuntimeError('QA_PRIVATE_RETIREMENT_LOST_COMMIT_ACK')
from web.database import engine as database
database._SessionLocal=sessionmaker(bind=engine,class_=LostOnce,autoflush=False,expire_on_commit=False)
import uvicorn
from web.main_web import create_app
server=uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=args.port,log_level='warning',access_log=False))
def snapshot(actors):
    result={}
    with Session(engine) as db:
        for label,identifier in actors.items():
            assert label in {'A','B','C'} and str(uuid.UUID(identifier))==identifier
            user=db.get(Usuario,identifier);assert user and user.team_gym_id==ids['parent']
            events=db.scalars(select(ProgressConsent).where(ProgressConsent.user_id==identifier).order_by(ProgressConsent.version)).all()
            result[label]={'role':user.role.value,'tipo':user.tipo,'sv':user.session_version,'active':user.activo,'invitation_null':user.invitation_token is None,
                'parent_active':db.get(Usuario,ids['parent']).activo,'profiles':db.scalar(select(func.count()).select_from(Cliente).where(Cliente.gym_id==identifier)),
                'general_proofs':db.scalar(select(func.count()).select_from(MfaAuthorization).where(MfaAuthorization.user_id==identifier)),
                'refresh':db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id==identifier)),
                'attempts':db.scalar(select(func.count()).select_from(AuthAuditLog).where(AuthAuditLog.user_id==identifier,AuthAuditLog.event_type=='progress_retirement_attempt')),
                'events':[[row.event,row.version] for row in events]}
    return result
def controls():
    number=0
    while not server.should_exit:
        path=PHASE/('control-'+str(number)+'.private.json')
        if not path.exists():time.sleep(.1);continue
        command=json.loads(path.read_bytes());action=command['action'];result={'action':action,'completed':False}
        try:
            if action=='stop':server.should_exit=True
            elif action=='parent-off':
                with Session(engine) as db:db.get(Usuario,ids['parent']).activo=False;db.commit()
            elif action=='lose-withdraw-ack':
                target=command['actor'];assert str(uuid.UUID(target))==target and not fault['used']
                with Session(engine) as db:assert db.get(Usuario,target).team_gym_id==ids['parent']
                fault['target']=target
            elif action=='snapshot':result['snapshot']=snapshot(command['actors']);result['fault_used']=fault['used']
            else:raise ValueError('Unknown own control')
            result['completed']=True
        except Exception as error:result['error_class']=type(error).__name__
        with (PHASE/('control-'+str(number)+'-result.private.json')).open('x',encoding='utf8') as stream:json.dump(result,stream)
        number+=1
threading.Thread(target=controls,daemon=True).start()
with engine.connect() as db:
    marker={'fixture':'qa-retirement32-real-sqlite','origin':origin,'pid':os.getpid(),'port':args.port,'revision':db.scalar(text('SELECT version_num FROM alembic_version')),
        'model_tables':len(Base.metadata.tables),'physical_tables':len(inspect(db).get_table_names()),'ids':ids,'database':str(engine.url.database),'temporary_root':str(temporary)}
with (PHASE/'startup.private.json').open('x',encoding='utf8') as stream:json.dump(marker,stream)
try:server.run()
finally:
    engine.dispose()
    with (PHASE/'closure.private.json').open('x',encoding='utf8') as stream:json.dump({'server_returned':True,'engine_disposed':True,'sqlite_preserved':True,'fault_used':fault['used'],'pid':os.getpid()},stream)
