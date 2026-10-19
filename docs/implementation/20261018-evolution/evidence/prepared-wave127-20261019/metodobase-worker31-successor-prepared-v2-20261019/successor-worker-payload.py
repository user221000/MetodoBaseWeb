
from pathlib import Path
import hashlib,json,os
from config.settings import get_settings
from web.database.engine import get_engine
from web.database.schema_control import expected_head,verify_runtime_schema
from web.database.tenant_policy import verify_application_database_role
from sqlalchemy import text
settings=get_settings();assert settings.is_production and settings.ENV=='production' and not settings.SEED_DEMO
worker=dict(part.split(b'=',1) for part in Path('/proc/1/environ').read_bytes().split(b'\0') if b'=' in part)
assert b'MIGRATOR_DATABASE_URL' not in worker and b'DATABASE_URL' in worker
assert worker[b'METODOBASE_ENV']==b'production' and worker[b'PORT']==b'18033'
engine=get_engine();verify_runtime_schema(engine);verify_application_database_role(engine)
with engine.connect() as connection:
 head=connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one();assert head==expected_head()
 role=connection.execute(text('SELECT current_user')).scalar_one()
 flags=connection.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolinherit FROM pg_roles WHERE rolname=current_user')).one();assert not any(flags)
 owner=connection.execute(text('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()')).scalar_one();assert role!=owner
 tables=connection.execute(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r'")).scalar_one()
 rls=[dict(r._mapping) for r in connection.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname"))]
 assert any(r['relforcerowsecurity'] for r in rls)
 contract_blob=Path('/app/web/database/alembic/schema_targets/20261019_mfa_postgresql.json').read_bytes()
 assert hashlib.sha256(contract_blob).hexdigest()=='dbdd3f96beb1bc251b6507d4375c9b6e95aaf1ff5c32d4bc168dc7a35e8cadc9'
 contract=json.loads(contract_blob)
 assert head=='20261019_mfa'
 observed_flags=[[r['relname'],r['relrowsecurity'],r['relforcerowsecurity']] for r in rls if r['relname']!='alembic_version']
 assert observed_flags==contract['tenant_security']['tables']
sources={p.relative_to('/app').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
print(json.dumps({'production_settings_valid':True,'migrator_unset_in_worker_PID1':True,'application_database_role':role,'migration_database_owner':owner,
 'application_role_flags_false':list(flags),'head':head,'expected_head':expected_head(),'public_table_count':tables,'runtime_schema_verified':True,
 'table_RLS_flags':rls,'source_hashes_after_startup':sources,'uid':os.getuid(),'seed_demo':False,'private_store_backend':settings.OBJECT_STORAGE_BACKEND,
 'provider_authentication_or_business_flow_executed':False}))
