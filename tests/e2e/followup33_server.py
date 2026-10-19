"""Owned UUID PostgreSQL + real auth, loopback only, no providers. No shared schema edits."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import threading
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pg-config',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--stop-file',type=Path,required=True)
parser.add_argument('--port',type=int,default=8795,choices=[8795])
args=parser.parse_args()
cfg=json.loads(args.pg_config.read_text(encoding='utf8'))
from tests.isolation import prepare_environment,block_external_sockets,validate_postgres_test_url
admin_url=validate_postgres_test_url(cfg['METODOBASE_TEST_MIGRATOR_URL'])
app_url=validate_postgres_test_url(cfg['METODOBASE_TEST_POSTGRES_URL'])
admin_parts,app_parts=urlsplit(admin_url),urlsplit(app_url)
assert (admin_parts.hostname,admin_parts.port)==(app_parts.hostname,app_parts.port)==('127.0.0.1',55483)
name='metodobase_test_followup_'+uuid.uuid4().hex[:16]
owned_admin=urlunsplit(admin_parts._replace(path='/'+name))
owned_app=urlunsplit(app_parts._replace(path='/'+name))
for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','PYTEST_XDIST_WORKER'):
    os.environ.pop(key,None)
os.environ['METODOBASE_TEST_DATABASE_URL']=owned_app
temporary=prepare_environment(discard_inherited=True).resolve()
block_external_sockets()
import base64
os.environ['MFA_ENCRYPTION_KEY']=base64.urlsafe_b64encode(os.urandom(32)).decode()
os.environ.update(cfg)
base='http://127.0.0.1:'+str(args.port)
os.environ['BASE_URL']=base;os.environ['CORS_ORIGINS']=base+',http://testserver'
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session,sessionmaker
from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
control=psycopg2.connect(admin_url.replace('postgresql+psycopg2://','postgresql://',1));control.autocommit=True
admin=app_engine=None
with control.cursor() as cursor:cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
try:
    run_migration(owned_admin,'db_bootstrap.py','--revision','head')
    admin=create_engine(owned_admin)
    app_engine=application_engine(owned_admin,admin)
    # The shared integration helper deliberately uses pool=1 for sequential
    # pool-reuse tests. A browser issues concurrent dashboard requests; give
    # this fixture its own bounded pool without changing product settings.
    app_engine.dispose()
    from web.database.tenant_context import configure_tenant_engine
    app_engine=configure_tenant_engine(create_engine(owned_app,pool_size=10,max_overflow=5,pool_timeout=5))
    from datetime import datetime,timedelta,timezone
    from web.auth import hash_password
    from web.database.models import Cliente,PlanGenerado,Usuario,UserRole,Base
    from sqlalchemy import inspect
    from web.database.schema_control import verify_runtime_schema
    from web.database.alembic.history_index_contract_v1 import history_index_signature,expected_history_index
    verify_runtime_schema(admin,expected_revision='20261019_google_subjects')
    with admin.connect() as connection:
        physical_tables=len(inspect(connection).get_table_names())
        history_index=history_index_signature(connection)
    assert physical_tables==36 and len(Base.metadata.tables)==35
    assert history_index==expected_history_index('postgresql')
    with app_engine.connect() as connection:
        flags=connection.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()
        database_nonowner=connection.execute(text('SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()')).scalar_one()
        application_role_restricted_nonowner=tuple(flags)==(False,False,False,False) and database_nonowner is True
        assert application_role_restricted_nonowner is True
        restricted=connection.execute(text("SELECT r.rolsuper,r.rolbypassrls,"
            "current_user=pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity "
            "FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE r.rolname=current_user AND n.nspname='public' AND c.relname='planes_generados'")).one()
    assert tuple(restricted)==(False,False,False,True,True)
    now=datetime.now(timezone.utc)
    with Session(admin) as db:
        for suffix in ['owner','other']:
            db.add(Usuario(id='followup-'+suffix,email='followup-'+suffix+'@example.invalid',nombre='Synthetic '+suffix,
                password_hash=hash_password('Synthetic-Followup-Only-2026!'),tipo='gym',role=UserRole.OWNER,activo=True))
            db.flush()
        for identity,owner,age,end in [('never','owner',None,None),('window','owner',40,None),
                ('date','owner',1,now.replace(tzinfo=None)-timedelta(days=1)),('unknown','owner',1,None),('foreign','other',None,None)]:
            db.add(Cliente(id_cliente='followup-client-'+identity,gym_id='followup-'+owner,nombre='Synthetic <span> '+identity,
                fecha_fin_suscripcion=end,edad=30,sexo='M',peso_kg=75,estatura_cm=175,nivel_actividad='moderada',objetivo='mantenimiento'))
            db.flush()
            if age is not None:
                row=PlanGenerado(id_cliente='followup-client-'+identity,gym_id='followup-'+owner,fecha_generacion=now-timedelta(days=age))
                db.add(row);db.flush()
                if identity=='unknown':row.fecha_generacion=None
        db.commit()
        revision=db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    from web.database import engine as database
    database._engine=app_engine;database._SessionLocal=sessionmaker(bind=app_engine,autoflush=False)
    from web.main_web import create_app
    names=['api/app.py','web/main_web.py','web/routes/followup.py','web/database/followup_repository.py',
        'web/services/followup_policy.py','web/services/followup_service.py','web/templates/dashboard.html',
        'web/static/js/api.js','web/static/js/main.js','web/static/js/dashboard-seguimiento.js','web/auth.py',
        'web/auth_deps.py','web/services/permissions.py','web/database/models.py','web/database/tenant_context.py',
        'web/database/tenant_policy.py','web/database/engine.py','web/middleware/security_headers.py','tests/isolation.py',
        'web/database/schema_control.py','web/database/alembic/history_index_contract_v1.py',
        'config/constantes.py','tests/e2e/followup33_server.py','tests/e2e/dashboard_followup33_browser.cjs',
        'requirements_web-windows.lock','requirements-test-windows.lock','tests/e2e/package.json','tests/e2e/package-lock.json']
    args.report.parent.mkdir(parents=True,exist_ok=True)
    from tests.ci_google33.physical import physical_contract
    global_witness=physical_contract(app_engine,expected_pool=10)
    report={'physical_witness':global_witness,'fixture':'r23-followup-real-pg31','pid':os.getpid(),'port':args.port,'database':name,
        'runtime_revision':revision,'revision_method':'SELECT alembic_version after db_bootstrap --revision head',
        'model_tables':len(Base.metadata.tables),'model_tables_method':'ORM metadata count, not a migration claim',
        'actual_tables':physical_tables,'history_order_index':history_index,'application_role_restricted_nonowner':application_role_restricted_nonowner,
        'providers':'disabled; outbound sockets guarded; fixture synthetic only',
        'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}}
    args.report.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    import uvicorn
    server=uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=args.port,log_level='warning',access_log=False))
    def stop():
        while not args.stop_file.exists():time.sleep(.2)
        server.should_exit=True
    threading.Thread(target=stop,daemon=True).start()
    print('Own R23 fixture ready; PID '+str(os.getpid())+'; revision '+revision,flush=True)
    server.run()
finally:
    if app_engine:app_engine.dispose()
    if admin:admin.dispose()
    with control.cursor() as cursor:
        assert name.startswith('metodobase_test_followup_')
        cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    control.close()
