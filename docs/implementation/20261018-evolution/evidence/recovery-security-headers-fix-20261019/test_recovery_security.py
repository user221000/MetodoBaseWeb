"""Independent R16/schema28 HTTP/SQLite privacy and state-transition canaries."""
import asyncio,importlib,json,time,uuid
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from urllib.parse import urlsplit,parse_qs
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event,update,select
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy.exc import StatementError
from starlette.requests import Request

OLD='IndependentOldPassword123';NEW='IndependentNewPassword456'
A='security-recovery-A';B='security-recovery-B';M='security-recovery-member'
EMAIL='independent-private-a@example.invalid'

@pytest.fixture(scope='session')
def engine():
 from web.database.engine import get_engine
 from web.database.models import Base
 from web import auth
 engine=get_engine();Base.metadata.create_all(engine);auth.init_auth()
 yield engine
 engine.dispose()

@pytest.fixture(scope='session')
def old_hash():
 from web.auth import hash_password
 return hash_password(OLD)

@pytest.fixture(autouse=True)
def clean(engine):
 from web.database.models import Base
 from web.rate_limiter import _buckets,_bucket_windows
 from web.database.tenant_context import current_tenant
 assert not current_tenant.get()
 with engine.begin() as c:
  for table in reversed(Base.metadata.sorted_tables):c.execute(table.delete())
 _buckets.clear();_bucket_windows.clear()
 yield
 assert not current_tenant.get()

@pytest.fixture
def seeded(engine,old_hash):
 from web.database.models import Usuario,UserRole,Cliente,RefreshToken
 with Session(engine) as db:
  db.add(Usuario(id=A,email=EMAIL,nombre='Independent <private-name>',password_hash=old_hash,tipo='gym',role=UserRole.OWNER,session_version=4));db.flush()
  db.add(Usuario(id=B,email='independent-private-b@example.invalid',nombre='Independent B',password_hash=old_hash,tipo='usuario',role=UserRole.VIEWER,session_version=9))
  db.add(Usuario(id=M,email='independent-member@example.invalid',nombre='Independent Member',password_hash=old_hash,tipo='gym',role=UserRole.NUTRIOLOGO,team_gym_id=A,session_version=2))
  db.add(Cliente(id_cliente='independent-private-client',gym_id=A,nombre='Independent Client'))
  for subject in [A,B,M]:db.add(RefreshToken(jti=str(uuid.uuid4()),user_id=subject,created_at=time.time(),expires_at=time.time()+1000,revoked=False))
  db.commit()
 return engine

@pytest.fixture(params=['web.main_web','api.app'])
def case(request,seeded,monkeypatch):
 from web.settings import get_settings
 from web.services import email_service
 settings=get_settings();monkeypatch.setattr(settings,'BASE_URL','https://independent-recovery.example.invalid');monkeypatch.setattr(settings,'RESEND_API_KEY','synthetic-only-not-provider-key')
 def forbidden(*args,**kwargs):raise AssertionError('No real SDK dispatch permitted')
 monkeypatch.setattr(email_service,'_send',forbidden)
 mails=[];notices=[]
 monkeypatch.setattr(email_service,'send_password_reset',lambda *args:mails.append(args) or True)
 monkeypatch.setattr(email_service,'send_password_changed',lambda *args:notices.append(args) or True)
 app=importlib.import_module(request.param).create_app()
 with TestClient(app,raise_server_exceptions=False) as client:
  result=SimpleNamespace(client=client,app=app,engine=seeded,mails=mails,notices=notices,factory=request.param,settings=settings)
  yield result;idle(result)

def idle(case):
 deadline=time.monotonic()+5
 while case.app.state.recovery_dispatcher.pending and time.monotonic()<deadline:time.sleep(.005)
 assert case.app.state.recovery_dispatcher.pending==0

def issue(case,email=EMAIL):
 response=case.client.post('/api/auth/password-reset/request',json={'email':email})
 assert response.status_code==202;idle(case)
 link=case.mails[-1][2];parsed=urlsplit(link)
 assert parsed.scheme=='https' and parsed.netloc=='independent-recovery.example.invalid' and not parsed.query
 token=parse_qs(parsed.fragment)['token'][0];assert len(token)==43
 return token

def confirm(case,token,**extra):
 return case.client.post('/api/auth/password-reset/confirm',json={'token':token,'new_password':NEW,'confirm_password':NEW,**extra})

def privacy(response):
 assert response.headers['cache-control']=='no-store';assert response.headers['referrer-policy']=='no-referrer'

def snapshot(engine,subject=A):
 from web.database.models import Usuario,RefreshToken,AuthAuditLog
 with Session(engine) as db:
  u=db.get(Usuario,subject)
  return {'hash':u.password_hash,'sv':u.session_version,'role':u.role.value,'tipo':u.tipo,'team':u.team_gym_id,'active':u.activo,'reset':u.password_reset_hash,'expiry':u.password_reset_expires_at,'reset_sv':u.password_reset_session_version,'live_rt':db.query(RefreshToken).filter_by(user_id=subject,revoked=False).count(),'events':db.query(AuthAuditLog).filter_by(user_id=subject).count()}

def test_host_poison_scanner_and_get_do_not_consume_or_supply_origin(case,caplog):
 token=issue(case);before=snapshot(case.engine)
 page=case.client.get('/auth/reset-password',headers={'Host':'attacker.example.invalid','X-Forwarded-Host':'attacker.example.invalid','X-Forwarded-Proto':'http'})
 assert page.status_code==200;privacy(page);assert token not in page.text
 assert snapshot(case.engine)==before
 rejected=case.client.get('/api/auth/password-reset/confirm',params={'token':'synthetic-scanner-token'})
 assert rejected.status_code==405;assert snapshot(case.engine)==before
 response=confirm(case,token);assert response.status_code==200;privacy(response)
 assert set(response.json())=={'code','message'};assert token not in response.text+caplog.text

def test_additional_authority_fields_rejected_without_consuming_or_touching_other_subject(case):
 token=issue(case);before=snapshot(case.engine);other=snapshot(case.engine,B)
 response=confirm(case,token,user_id=B,role='owner',team_gym_id=A,email='intruder@example.invalid')
 assert response.status_code==422;privacy(response);assert snapshot(case.engine)==before;assert snapshot(case.engine,B)==other
 assert confirm(case,token).status_code==200;assert snapshot(case.engine,B)==other

@pytest.mark.parametrize('mode',['no_redis','redis_down'])
def test_production_recovery_fail_closed_even_with_general_limiter_disabled(case,monkeypatch,mode):
 from web import rate_limiter_redis
 token=issue(case);before=snapshot(case.engine)
 monkeypatch.setattr(case.settings,'is_production',True)
 monkeypatch.setattr(case.settings,'REDIS_URL','' if mode=='no_redis' else 'redis://127.0.0.1:56379/15')
 calls=[]
 async def broken():calls.append(True);raise RuntimeError('independent-private-redis-outage')
 monkeypatch.setattr(rate_limiter_redis,'_get_redis',broken)
 requested=case.client.post('/api/auth/password-reset/request',json={'email':EMAIL})
 changed=confirm(case,token)
 assert requested.status_code==changed.status_code==503;privacy(requested);privacy(changed)
 assert snapshot(case.engine)==before
 assert len(case.mails)==1;assert bool(calls)==(mode=='redis_down')

def test_bad_json_and_bounded_input_errors_do_not_echo_credential_or_input(case):
 token=issue(case);before=snapshot(case.engine)
 for body,content_type,status in [(b'{"token":"independent-private-invalid"','application/json',422),(b'x'*4097,'application/json',413),(b'independent-private-invalid','text/plain',415),(json.dumps({'email':EMAIL,'extra':'independent-private-invalid'}).encode(),'application/json',422)]:
  response=case.client.post('/api/auth/password-reset/request',content=body,headers={'Content-Type':content_type})
  assert response.status_code==status;privacy(response);assert 'independent-private-invalid' not in response.text
 assert snapshot(case.engine)==before;assert len(case.mails)==1

def test_local_token_limit_and_request_limit_are_separate_and_normalize_account(case):
 # Confirm invalid bearers do not spend request admission, and request aliases share one account budget.
 for _ in range(10):assert confirm(case,'z'*43).status_code==400
 assert confirm(case,'z'*43).status_code==429
 for email in [EMAIL,' '+EMAIL.upper()+' ',EMAIL]:
  response=case.client.post('/api/auth/password-reset/request',json={'email':email});assert response.status_code==202
 rejected=case.client.post('/api/auth/password-reset/request',json={'email':EMAIL});assert rejected.status_code==429
 assert int(rejected.headers['retry-after'])>0;privacy(rejected);idle(case)

def test_lost_commit_ack_cannot_report_success_or_undo_all_committed_effects(case,monkeypatch,caplog):
 from web.database.models import AuthAuditLog
 from web.auth import verify_password
 token=issue(case);other=snapshot(case.engine,B);original=Session.commit
 def commit(db):
  consuming=any(isinstance(x,AuthAuditLog) and x.event_type=='password_reset_complete' for x in db.new)
  result=original(db)
  if consuming:raise StatementError('independent-private-message','independent-private-SQL',{'secret':token,'password':NEW},RuntimeError('independent-private-inner'))
  return result
 monkeypatch.setattr(Session,'commit',commit)
 response=confirm(case,token);assert response.status_code==503;privacy(response)
 assert response.json()['detail']['code']=='password_reset_unconfirmed'
 after=snapshot(case.engine);assert after['sv']==5 and after['reset'] is None and after['live_rt']==0;assert verify_password(NEW,after['hash'])
 assert snapshot(case.engine,B)==other;assert not case.notices
 assert all(x not in response.text+caplog.text for x in [token,NEW,'independent-private-message','independent-private-SQL','independent-private-inner'])

@pytest.mark.parametrize('change',['revoked_parent','role_owner','deleted_parent'])
def test_changed_membership_or_parent_is_revalidated_when_consuming(case,change):
 from web.database.models import Usuario,UserRole
 token=issue(case,'independent-member@example.invalid');before=snapshot(case.engine,M)
 with Session(case.engine) as db:
  if change=='revoked_parent':db.get(Usuario,A).activo=False
  elif change=='deleted_parent':db.get(Usuario,A).deleted_at=datetime.now(timezone.utc)
  else:db.get(Usuario,M).role=UserRole.OWNER
  db.commit()
 response=confirm(case,token);assert response.status_code==400;privacy(response)
 after=snapshot(case.engine,M);assert after['hash']==before['hash'] and after['sv']==before['sv'] and after['live_rt']==before['live_rt'];assert after['reset']==before['reset']

def test_typed_authority_preserved_and_recovery_metadata_never_exported(case,caplog):
 from web import auth
 from web.database.models import Usuario
 token=issue(case);before=snapshot(case.engine)
 assert confirm(case,token).status_code==200;idle(case)
 after=snapshot(case.engine)
 for key in ['role','tipo','team','active']:assert after[key]==before[key]
 # OWNER recovery grants no personal authority. Inspect a personal subject's
 # export with live reset state, through the real existing route instead.
 personal_token=issue(case,'independent-private-b@example.invalid')
 with Session(case.engine) as db:principal=auth.identity_from_user(db.get(Usuario,B),db)
 access=auth.crear_access_token(principal)
 export=case.client.get('/api/usuario/privacidad/exportar',headers={'Authorization':'Bearer '+access})
 assert export.status_code==200
 assert all(name not in export.text for name in ['password_reset_hash','password_reset_session_version','password_reset_expires_at',token,personal_token])
 from web.services.password_recovery import recovery_status
 text=json.dumps(recovery_status());assert token not in text and EMAIL not in text and NEW not in text
 assert all(value not in caplog.text for value in [token,NEW,EMAIL])

@pytest.mark.parametrize('kind',['inactive','pending','missing'])
def test_public_admission_does_not_enumerate_ineligible_accounts_or_activate_them(case,kind):
 from web.database.models import Usuario
 with Session(case.engine) as db:
  if kind!='missing':
   row=db.get(Usuario,B);row.activo=False
   if kind=='pending':row.invitation_token='f'*64
   db.commit()
 address='missing-independent@example.invalid' if kind=='missing' else 'independent-private-b@example.invalid'
 unknown=case.client.post('/api/auth/password-reset/request',json={'email':address})
 known=case.client.post('/api/auth/password-reset/request',json={'email':EMAIL})
 assert unknown.status_code==known.status_code==202;assert unknown.content==known.content;privacy(unknown);idle(case)
 assert len(case.mails)==1 and case.mails[0][0]==EMAIL
 if kind!='missing':assert snapshot(case.engine,B)['active'] is False and snapshot(case.engine,B)['reset'] is None

@pytest.mark.parametrize('mutation',['digest','version','inactive'])
def test_consume_reloads_same_subject_after_prelock_intervention(seeded,mutation):
 from web.database.models import Usuario
 from web.services import password_recovery as recovery
 mails=[];recovery.issue_request(EMAIL,'https://independent-recovery.example.invalid',factory=sessionmaker(bind=seeded),sender=lambda *args:mails.append(args) or True)
 token=parse_qs(urlsplit(mails[0][2]).fragment)['token'][0];before=snapshot(seeded);fired=[]
 def intervene(connection,cursor,statement,parameters,context,executemany):
  if statement.lower().startswith('update usuarios') and not fired:
   fired.append(True)
   changes={'password_reset_hash':recovery.digest('q'*43)} if mutation=='digest' else {'session_version':5} if mutation=='version' else {'activo':False}
   with seeded.begin() as other:other.execute(update(Usuario).where(Usuario.id==A).values(**changes))
 event.listen(seeded,'before_cursor_execute',intervene)
 try:
  with Session(seeded) as db,pytest.raises(HTTPException) as failure:recovery.consume(db,token,NEW)
 finally:event.remove(seeded,'before_cursor_execute',intervene)
 assert fired and failure.value.status_code==400
 after=snapshot(seeded);assert after['hash']==before['hash'] and after['live_rt']==before['live_rt'];assert after['events']==before['events']

def test_issue_reloads_email_after_account_lock_and_sends_nothing_if_it_changed(seeded):
 from web.database.models import Usuario
 from web.services import password_recovery as recovery
 fired=[];mails=[]
 def intervene(connection,cursor,statement,parameters,context,executemany):
  if statement.lower().startswith('update usuarios') and not fired:
   fired.append(True)
   with seeded.begin() as other:other.execute(update(Usuario).where(Usuario.id==A).values(email='replacement-independent@example.invalid'))
 event.listen(seeded,'before_cursor_execute',intervene)
 try:recovery.issue_request(EMAIL,'https://independent-recovery.example.invalid',factory=sessionmaker(bind=seeded),sender=lambda *args:mails.append(args) or True)
 finally:event.remove(seeded,'before_cursor_execute',intervene)
 assert fired and not mails;assert snapshot(seeded)['reset'] is None

def test_issue_transport_runs_after_session_close_and_digest_commit(seeded):
 from web.services import password_recovery as recovery
 from web.database.models import Usuario,AuthAuditLog
 states=[]
 class Tracked(Session):
  def close(self):states.append('closed');return super().close()
 def sender(email,name,link):
  assert states==['closed']
  token=parse_qs(urlsplit(link).fragment)['token'][0]
  with Session(seeded) as db:
   assert db.get(Usuario,A).password_reset_hash==recovery.digest(token)
   audit=db.scalar(select(AuthAuditLog).where(AuthAuditLog.user_id==A))
   assert audit.event_metadata=={'channel':'email_link'} and token not in json.dumps(audit.event_metadata)
  return True
 recovery.issue_request(EMAIL,'https://independent-recovery.example.invalid',factory=sessionmaker(bind=seeded,class_=Tracked),sender=sender)
 assert states==['closed'] and snapshot(seeded)['reset'] is not None

def test_explicit_ambient_subject_is_rejected_without_changing_either_account(seeded):
 from web.services import password_recovery as recovery
 from web.database.tenant_context import tenant_scope
 mails=[];recovery.issue_request(EMAIL,'https://independent-recovery.example.invalid',factory=sessionmaker(bind=seeded),sender=lambda *args:mails.append(args) or True)
 token=parse_qs(urlsplit(mails[0][2]).fragment)['token'][0];before=snapshot(seeded);other=snapshot(seeded,B)
 with tenant_scope(B),Session(seeded) as db,pytest.raises(HTTPException) as failure:recovery.consume(db,token,NEW)
 assert failure.value.status_code==400;assert snapshot(seeded)==before and snapshot(seeded,B)==other

def test_stream_overflow_never_reads_the_following_chunk_or_parser(monkeypatch):
 from web.routes import password_recovery as routes
 calls=[]
 class Parser:
  def validate_json(self,*args):raise AssertionError('Oversized credential body reached parser')
 monkeypatch.setattr(routes,'TypeAdapter',lambda *args:Parser())
 async def receive():
  calls.append(True)
  if len(calls)>1:raise AssertionError('Read beyond first already oversized credential chunk')
  return {'type':'http.request','body':b'x'*4097,'more_body':True}
 request=Request({'type':'http','method':'POST','path':'/','headers':[(b'content-type',b'application/json')]},receive)
 with pytest.raises(HTTPException) as failure:asyncio.run(routes.bounded_body(routes.RecoveryConfirm)(request))
 assert failure.value.status_code==413 and len(calls)==1
