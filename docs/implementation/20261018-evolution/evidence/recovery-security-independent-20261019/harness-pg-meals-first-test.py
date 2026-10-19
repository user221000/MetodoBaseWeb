"""Independent reverse-order lock canaries, migrated28 and restricted RLS role."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date,datetime,timezone
from threading import Event,current_thread
from urllib.parse import urlsplit,urlunsplit,parse_qs
import json,os,re,subprocess,sys,time,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine,event,text,update,select
from sqlalchemy.orm import Session,sessionmaker

R=Path(__file__).parent;AUTHOR=Path('F:/MetodoBaseWeb-recovery-20261019')
OLD='IndependentOldPassword123';NEW='IndependentNewPassword456'
A='pg-sec-recovery-owner';B='pg-sec-recovery-other';M='pg-sec-recovery-member'

@pytest.fixture(scope='session')
def pg():
 import psycopg2
 from psycopg2 import sql
 from tests.isolation import validate_postgres_test_url
 from tests.integration_provider_subjects import application_engine
 from web.database.tenant_context import configure_tenant_engine
 from web.database.tenant_policy import verify_application_database_role
 control=os.environ['METODOBASE_TEST_MIGRATOR_URL'];validate_postgres_test_url(control)
 parsed=urlsplit(control);assert parsed.hostname=='127.0.0.1' and parsed.port==55483
 name='metodobase_test_recovery_sec_'+uuid.uuid4().hex
 assert re.fullmatch(r'metodobase_test_recovery_sec_[0-9a-f]{32}',name)
 record={'database':name,'port':55483,'events':['planned_owned_uuid'],'connection_urls_recorded':False};record_path=R/'owned-database.json'
 def record_event(message):record['events'].append(message);record_path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
 record_event('before_create')
 admin=psycopg2.connect(control.replace('postgresql+psycopg2://','postgresql://',1));admin.autocommit=True
 created=False;engine=None;app=None
 try:
  with admin.cursor() as cur:cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
  created=True;record_event('created')
  target=urlunsplit(parsed._replace(path='/'+name));engine=create_engine(target)
  environment=dict(os.environ,DATABASE_URL=target,METODOBASE_TEST_DATABASE_URL='')
  result=subprocess.run([sys.executable,'-X','utf8','db_bootstrap.py','--revision','head'],cwd=AUTHOR,env=environment,capture_output=True,text=True)
  assert result.returncode==0,'Owned migration failed; subprocess text retained privately without connection parameters'
  (R/'pg-migration.log').write_text(result.stdout+result.stderr,encoding='utf8');record_event('migrated28')
  single=application_engine(target,engine)
  app=configure_tenant_engine(create_engine(single.url,pool_size=4,max_overflow=0));single.dispose();verify_application_database_role(app)
  @event.listens_for(app,'connect')
  def timeouts(connection,record):
   with connection.cursor() as cur:cur.execute("SET statement_timeout='12000ms'")
   connection.commit()
  yield engine,app
 finally:
  if app is not None:app.dispose()
  if engine is not None:engine.dispose()
  if created:
   assert re.fullmatch(r'metodobase_test_recovery_sec_[0-9a-f]{32}',name)
   record_event('before_drop_exact_owned')
   with admin.cursor() as cur:
    cur.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    cur.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(name,));assert cur.fetchone()[0]==0
   record_event('dropped_and_absence_verified')
  admin.close()

@pytest.fixture
def seeded_pg(pg,monkeypatch):
 from web import auth
 from web.database import engine as database
 from web.database.models import Base,Usuario,UserRole,Cliente,RefreshToken,PersonalDiaryDay
 admin,app=pg
 with admin.begin() as c:
  for table in reversed(Base.metadata.sorted_tables):c.execute(table.delete())
 old=auth.hash_password(OLD)
 with Session(admin) as db:
  db.add(Usuario(id=A,email=A+'@example.invalid',nombre='Synthetic',tipo='gym',role=UserRole.OWNER,password_hash=old,session_version=0));db.flush()
  db.add(Usuario(id=B,email=B+'@example.invalid',nombre='Synthetic B',tipo='usuario',role=UserRole.VIEWER,password_hash=old,session_version=7))
  db.add(Usuario(id=M,email=M+'@example.invalid',nombre='Synthetic Member',tipo='gym',role=UserRole.NUTRIOLOGO,team_gym_id=A,password_hash=old,session_version=2));db.flush()
  for subject in [A,B]:db.add(Cliente(id_cliente='client-'+subject,gym_id=subject,nombre='Synthetic private client'))
  for subject in [A,B,M]:db.add(RefreshToken(jti=str(uuid.uuid4()),user_id=subject,created_at=time.time(),expires_at=time.time()+1000,revoked=False))
  db.add(PersonalDiaryDay(id=str(uuid.uuid4()),user_id=M,local_date=date(2026,10,19),timezone='America/Mexico_City',water_ml=925,version=1,meals_json={}))
  db.commit()
 monkeypatch.setattr(database,'_engine',app);monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=app,autoflush=False));auth.init_auth()
 return admin,app

def issue(app,identity=A):
 from web.services.password_recovery import issue_request
 mails=[];issue_request(identity+'@example.invalid','https://independent-recovery.example.invalid',factory=sessionmaker(bind=app),sender=lambda *args:mails.append(args) or True)
 assert len(mails)==1
 return parse_qs(urlsplit(mails[0][2]).fragment)['token'][0]

def state(admin,identity=A):
 from web.database.models import Usuario,RefreshToken,AuthAuditLog
 with Session(admin) as db:
  u=db.get(Usuario,identity)
  return {'sv':u.session_version,'hash':u.password_hash,'reset':u.password_reset_hash,'reset_sv':u.password_reset_session_version,'role':u.role.value,'team':u.team_gym_id,'tipo':u.tipo,'live_rt':db.query(RefreshToken).filter_by(user_id=identity,revoked=False).count(),'completions':db.query(AuthAuditLog).filter_by(user_id=identity,event_type='password_reset_complete').count()}

@contextmanager
def first_revoker_holds_user_lock(app,worker_prefix):
 locked,waiter=Event(),Event()
 def after(connection,cursor,statement,parameters,context,executemany):
  if current_thread().name.startswith('independent-revoker') and statement.lower().startswith('update usuarios') and not locked.is_set():
   locked.set();assert waiter.wait(8),'Waiter never reached account lock'
 def before(connection,cursor,statement,parameters,context,executemany):
  if current_thread().name.startswith(worker_prefix) and statement.lower().startswith('update usuarios'):waiter.set()
 event.listen(app,'after_cursor_execute',after);event.listen(app,'before_cursor_execute',before)
 try:yield locked,waiter
 finally:event.remove(app,'after_cursor_execute',after);event.remove(app,'before_cursor_execute',before)

@pytest.mark.parametrize('operation',['logout','reuse'])
def test_revocation_winning_account_lock_prevents_old_reset_in_reverse_order(seeded_pg,operation):
 from web import auth
 from web.database.models import Usuario
 from web.services.password_recovery import consume
 admin,app=seeded_pg
 with Session(app) as db:principal=auth.identity_from_user(db.get(Usuario,A),db)
 old=auth.crear_token_pair(principal)['refresh_token']
 if operation=='reuse':assert auth.rotar_refresh_token(old)
 token=issue(app);other=state(admin,B)
 def revoke():
  return auth.revocar_refresh_tokens_usuario(A) if operation=='logout' else auth.rotar_refresh_token(old)
 def reset():
  with Session(app) as db:
   try:consume(db,token,NEW);return 200
   except HTTPException as error:return error.status_code
 with first_revoker_holds_user_lock(app,'independent-reset') as (locked,waiter):
  with ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-revoker') as first,ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-reset') as second:
   one=first.submit(revoke);assert locked.wait(5);two=second.submit(reset)
   assert one.result(timeout=18) is None;assert two.result(timeout=18)==400
  assert waiter.is_set()
 after=state(admin);assert after['sv']==1 and after['live_rt']==0 and after['reset_sv']==0 and after['completions']==0
 assert auth.verify_password(OLD,after['hash']);assert state(admin,B)==other

def test_issuance_waiting_for_logout_reloads_current_sv_and_does_not_send_stale_bearer(seeded_pg):
 from web import auth
 from web.services.password_recovery import consume
 admin,app=seeded_pg
 with first_revoker_holds_user_lock(app,'independent-issuer') as (locked,waiter):
  with ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-revoker') as first,ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-issuer') as second:
   one=first.submit(auth.revocar_refresh_tokens_usuario,A);assert locked.wait(5);two=second.submit(issue,app)
   assert one.result(timeout=18) is None;token=two.result(timeout=18)
  assert waiter.is_set()
 assert state(admin)['sv']==state(admin)['reset_sv']==1
 with Session(app) as db:consume(db,token,NEW)
 after=state(admin);assert after['sv']==2 and after['reset'] is None and after['completions']==1;assert auth.verify_password(NEW,after['hash'])

def test_real_membership_revocation_winning_lock_rejects_old_link_but_preserves_personal_identity(seeded_pg):
 from web import auth
 from web.database.models import Usuario,PersonalDiaryDay
 from web.services.password_recovery import consume
 from web.services.team_invitation_service import revoke_membership
 admin,app=seeded_pg
 token=issue(app,M)
 def revoke():
  with Session(app) as db:
   actor=auth.identity_from_user(db.get(Usuario,A),db)
   return revoke_membership(db,actor,db.get(Usuario,M))
 def reset():
  with Session(app) as db:
   try:consume(db,token,NEW);return 200
   except HTTPException as error:return error.status_code
 with first_revoker_holds_user_lock(app,'independent-reset') as (locked,waiter):
  with ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-revoker') as first,ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-reset') as second:
   one=first.submit(revoke);assert locked.wait(5);two=second.submit(reset)
   assert one.result(timeout=18) is None;assert two.result(timeout=18)==400
  assert waiter.is_set()
 after=state(admin,M);assert (after['sv'],after['role'],after['tipo'],after['team'])==(3,'viewer','usuario',None)
 fresh=issue(app,M)
 with Session(app) as db:consume(db,fresh,NEW)
 with Session(admin) as db:assert db.scalar(select(PersonalDiaryDay.water_ml).where(PersonalDiaryDay.user_id==M))==925
 assert state(admin,M)['sv']==4 and auth.verify_password(NEW,state(admin,M)['hash'])

def test_new_authority_fields_do_not_expand_rls_or_persist_subject_in_connection_pool(seeded_pg):
 from web.database.tenant_context import bind_verified_subject
 from web.database.models import Cliente
 from web.database.alembic.security_contract_v1 import tenant_security_signature
 from web.services.password_recovery import consume
 admin,app=seeded_pg
 target=json.loads((AUTHOR/'web/database/alembic/schema_targets/20261019_personal_diary_postgresql.json').read_text())
 with admin.connect() as db:assert tenant_security_signature(db)==target['tenant_security']
 with app.connect() as db:
  flags=db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()
  assert tuple(flags)==(False,False,False,False);assert db.scalar(text('SELECT count(*) FROM clientes'))==0
 token=issue(app)
 with Session(app) as db:consume(db,token,NEW)
 with app.connect() as db:
  assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
  assert db.scalar(text('SELECT count(*) FROM clientes'))==0
 with Session(app) as db:
  bind_verified_subject(db,A);assert db.query(Cliente).count()==1
  with pytest.raises(ValueError):bind_verified_subject(db,B)
 with app.connect() as db:assert db.scalar(text('SELECT count(*) FROM clientes'))==0
