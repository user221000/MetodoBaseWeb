"""New explicit SQLite35 fixture for bounded R31 error diagnosis, no PG/RLS claim."""
from pathlib import Path
import base64
from datetime import datetime,timedelta,timezone
import hashlib,json,os,socket,sys,threading
from types import SimpleNamespace

ROOT=Path('F:/mb-qa-browser31-20261020')
P=Path(__file__).resolve().parent/'private'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))

def main():
    for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL',
                'METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','PYTEST_XDIST_WORKER','MFA_ENCRYPTION_KEY'):
        os.environ.pop(key,None)
    os.environ['TEMP']=os.environ['TMP']=str(P)
    from tests.isolation import prepare_environment,block_external_sockets
    temporary=prepare_environment(discard_inherited=True).resolve();block_external_sockets()
    base='http://127.0.0.1:8802'
    with socket.socket() as probe:probe.bind(('127.0.0.1',8802))
    os.environ.update({'BASE_URL':base,'CORS_ORIGINS':base+',http://testserver',
                      'MFA_ENCRYPTION_KEY':base64.urlsafe_b64encode(os.urandom(32)).decode()})
    from sqlalchemy import inspect,text
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import Base,Usuario,UserRole,Subscription
    from web.database.schema_control import expected_head,verify_runtime_schema
    from web.database.alembic.history_index_contract_v1 import history_index_signature,expected_history_index
    from tests.followup34_owned import process_birth
    engine=get_engine()
    assert engine.dialect.name=='sqlite' and Path(engine.url.database).resolve().is_relative_to(temporary)
    from db_bootstrap import main as bootstrap
    assert bootstrap(['--revision','20261020_nutrition_profile'])==0
    verify_runtime_schema(engine)
    with engine.connect() as db:
        head=db.scalar(text('SELECT version_num FROM alembic_version'))
        tables=len(inspect(db).get_table_names());index=history_index_signature(db)
    assert expected_head()==head=='20261020_nutrition_profile'
    assert len(Base.metadata.tables)==37 and tables==38 and index==expected_history_index('sqlite')
    from web.auth import hash_password
    now=datetime.now(timezone.utc);hashed=hash_password('Synthetic-MFA-UI-Password-2026!')
    with Session(engine) as db:
        for name in ('owner','other'):
            db.add(Usuario(id='synthetic-mfa-ui-'+name,email='mfa-ui-'+name+'@example.invalid',nombre='Synthetic '+name,
                apellido='',password_hash=hashed,tipo='gym',role=UserRole.OWNER,activo=True,session_version=0,fecha_registro=now))
        db.flush();db.add(Subscription(gym_id='synthetic-mfa-ui-owner',plan='clinica',status='active',provider='stripe',
            stripe_customer_id='cus_synthetic_mfa_ui',current_period_end=now+timedelta(days=30)));db.commit()
    import stripe
    from web.services import email_service,stripe_service
    email_service._send=lambda *_args,**_kwargs:False
    stripe_service._init_stripe=lambda:True
    stripe.billing_portal.Session.create=lambda **_kwargs:SimpleNamespace(url='https://billing.stripe.com/synthetic-no-provider')
    origins={}
    for name,module in list(sys.modules.items()):
        if name.split('.')[0] in {'web','api','core','tests','config','src','scripts'} and getattr(module,'__file__',None):
            path=Path(module.__file__).resolve();assert path.is_relative_to(ROOT);origins[name]=path.relative_to(ROOT).as_posix()
    assert Path(sys.modules[Base.__module__].__file__).resolve().is_relative_to(ROOT)
    startup={'fixture':'mfa-browser35-SQLite-diagnostic','dialect':'sqlite','origin':base,'pid':os.getpid(),'birth':process_birth(),
        'expected_runtime_revision':expected_head(),'actual_alembic_revision':head,'metadata_table_count':37,'physical_table_count':tables,
        'history_order_index':index,'no_PG_or_RLS_claim':True,'module_origins':origins,'canonical_Base_origin':str(Path(sys.modules[Base.__module__].__file__).resolve()),
        'providers':'no-send mail and synthetic Stripe SDK response only; external sockets blocked',
        'fixture_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (P/'startup.json').write_text(json.dumps(startup,indent=2),encoding='utf-8');print(json.dumps(startup),flush=True)
    import uvicorn
    from web.main_web import create_app
    server=uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=8802,log_level='warning',access_log=False))
    done=threading.Event()
    def watch_stop():
        while not done.wait(.1):
            if (P/'stop').exists():server.should_exit=True;return
    watcher=threading.Thread(target=watch_stop,daemon=True);watcher.start()
    try:server.run()
    finally:
        done.set();watcher.join(timeout=2);assert not watcher.is_alive();engine.dispose()
        after={}
        for name,module in list(sys.modules.items()):
            if name.split('.')[0] in {'web','api','core','tests','config','src','scripts'} and getattr(module,'__file__',None):
                path=Path(module.__file__).resolve();assert path.is_relative_to(ROOT);after[name]=path.relative_to(ROOT).as_posix()
        (P/'module-origins-after.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
        (P/'close.json').write_text(json.dumps({'normal_server_exit':True,'dialect':'sqlite','PG_connections':0}),encoding='utf-8')

if __name__=='__main__':main()
