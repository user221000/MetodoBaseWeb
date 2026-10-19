"""Recovery28 on migrated UUID PostgreSQL, restricted app role and real locks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import importlib
import multiprocessing
from threading import Event,current_thread
import time
from urllib.parse import urlsplit,parse_qs

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine,event,select,text,update
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session,sessionmaker

from tests.integration_schema_migrations import migration_database,run_migration
from tests.integration_provider_subjects import application_engine

pytestmark=pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
OLD='SyntheticOldPassword123'
NEW='SyntheticNewPassword456'


@pytest.fixture
def recovery_pg(migration_database,monkeypatch):
    from web import auth
    from web.database import engine as database
    from web.database.models import Usuario,UserRole
    from web.database.tenant_context import configure_tenant_engine
    url,admin=migration_database
    run_migration(url,'db_bootstrap.py','--revision','head')
    with Session(admin) as db:
        for identity,kind,role,parent in [('reset-owner','gym',UserRole.OWNER,None),
                ('reset-other','usuario',UserRole.VIEWER,None),
                ('reset-member','gym',UserRole.NUTRIOLOGO,'reset-owner')]:
            db.add(Usuario(id=identity,email=identity+'@example.invalid',nombre='Synthetic',
                password_hash=auth.hash_password(OLD),tipo=kind,role=role,team_gym_id=parent,activo=True))
            db.flush()
        db.commit()
    single=application_engine(url,admin)
    app=configure_tenant_engine(create_engine(single.url,pool_size=4,max_overflow=0))
    single.dispose()
    @event.listens_for(app,'connect')
    def timeout(connection,record):
        with connection.cursor() as cursor: cursor.execute("SET statement_timeout='12000ms'")
        connection.commit()
    monkeypatch.setattr(database,'_engine',app)
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=app,autoflush=False))
    auth.init_auth()
    try: yield admin,app
    finally: app.dispose()


def issue(app,*,identity='reset-owner',now=None):
    from web.services.password_recovery import issue_request
    messages=[]
    issue_request(identity+'@example.invalid','https://recovery.example.invalid',now=now,
        factory=sessionmaker(bind=app),sender=lambda *args:messages.append(args) or True)
    assert len(messages)==1
    return parse_qs(urlsplit(messages[0][2]).fragment)['token'][0]


@pytest.mark.parametrize('factory',['web.main_web','api.app'])
def test_real_http_reset_member_preserves_other_authority_and_pool_blank(recovery_pg,monkeypatch,factory):
    from web import auth
    from web.database.models import Usuario,RefreshToken,AuthAuditLog
    from web.services import email_service
    from web.settings import get_settings
    from web.rate_limiter import _buckets,_bucket_windows
    admin,app=recovery_pg
    monkeypatch.setattr(get_settings(),'BASE_URL','https://recovery.example.invalid')
    monkeypatch.setattr(get_settings(),'RESEND_API_KEY','synthetic-never-dispatched')
    for key in list(_buckets):
        if key.startswith('rl:recovery-v1:'):
            _buckets.pop(key,None); _bucket_windows.pop(key,None)
    messages=[]
    monkeypatch.setattr(email_service,'send_password_reset',lambda *args:messages.append(args) or True)
    monkeypatch.setattr(email_service,'send_password_changed',lambda *args:True)
    application=importlib.import_module(factory).create_app()
    with Session(app) as db:
        own=auth.identity_from_user(db.get(Usuario,'reset-member'),db)
        other=auth.identity_from_user(db.get(Usuario,'reset-other'),db)
    pair,other_pair=auth.crear_token_pair(own),auth.crear_token_pair(other)
    with TestClient(application,raise_server_exceptions=False) as client:
        assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+pair['access_token']}).status_code==200
        response=client.post('/api/auth/password-reset/request',json={'email':' RESET-MEMBER@EXAMPLE.INVALID '})
        assert response.status_code==202,response.text
        deadline=time.monotonic()+5
        while application.state.recovery_dispatcher.pending and time.monotonic()<deadline: time.sleep(.01)
        assert len(messages)==1
        token=parse_qs(urlsplit(messages[0][2]).fragment)['token'][0]
        payload={'token':token,'new_password':NEW,'confirm_password':NEW}
        changed=client.post('/api/auth/password-reset/confirm',json=payload)
        assert changed.status_code==200,changed.text
        assert client.get('/api/auth/me').status_code==401
        assert client.post('/api/auth/password-reset/confirm',json=payload).status_code==400
        deadline=time.monotonic()+5
        while application.state.recovery_dispatcher.pending and time.monotonic()<deadline: time.sleep(.01)
    with Session(admin) as db:
        user=db.get(Usuario,'reset-member')
        assert (user.session_version,user.role.value,user.tipo,user.team_gym_id)==(1,'nutriologo','gym','reset-owner')
        assert user.password_reset_hash is None and auth.verify_password(NEW,user.password_hash)
        assert db.query(RefreshToken).filter_by(user_id=user.id,revoked=False).count()==0
        assert db.query(AuthAuditLog).filter_by(event_type='password_reset_complete').count()==1
    assert auth.verificar_token(pair['access_token']) is None
    assert auth.verificar_refresh_token(pair['refresh_token']) is None
    assert auth.verificar_token(other_pair['access_token'])
    assert auth.verificar_refresh_token(other_pair['refresh_token'])
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
        assert db.scalar(text('SELECT count(*) FROM clientes'))==0


def _consume_process(url,token,start,ready,output):
    from tests.isolation import block_external_sockets,validate_postgres_test_url
    from web.database.tenant_context import configure_tenant_engine
    from web.services.password_recovery import consume
    validate_postgres_test_url(url); block_external_sockets()
    engine=configure_tenant_engine(create_engine(url,pool_size=1,max_overflow=0))
    try:
        ready.put(True)
        assert start.wait(15)
        with Session(engine) as db: consume(db,token,NEW)
        output.put(200)
    except HTTPException as error: output.put(error.status_code)
    except Exception as error: output.put(type(error).__name__)
    finally: engine.dispose()


def test_two_processes_consume_same_bearer_exactly_once(recovery_pg):
    from web.database.models import Usuario,AuthAuditLog
    admin,app=recovery_pg
    token=issue(app)
    context=multiprocessing.get_context('spawn')
    start,ready,output=context.Event(),context.Queue(),context.Queue()
    workers=[context.Process(target=_consume_process,args=(app.url.render_as_string(hide_password=False),
        token,start,ready,output)) for _ in range(2)]
    try:
        for worker in workers: worker.start()
        assert ready.get(timeout=20) and ready.get(timeout=20)
        start.set()
        results=[output.get(timeout=25),output.get(timeout=25)]
        assert sorted(results)==[200,400],results
        with Session(admin) as db:
            assert db.get(Usuario,'reset-owner').session_version==1
            assert db.query(AuthAuditLog).filter_by(event_type='password_reset_complete').count()==1
    finally:
        for worker in workers:
            worker.join(5)
            if worker.is_alive(): worker.terminate(); worker.join(5)
        assert all(worker.exitcode==0 for worker in workers)


@pytest.mark.parametrize('ack_lost',[False,True])
def test_real_commit_rollback_ack_and_refresh_are_atomic(recovery_pg,monkeypatch,caplog,ack_lost):
    from web import auth
    from web.database.models import Usuario,RefreshToken,AuthAuditLog
    from web.services.password_recovery import consume,digest
    admin,app=recovery_pg
    token=issue(app)
    with Session(app) as db: principal=auth.identity_from_user(db.get(Usuario,'reset-owner'),db)
    pair=auth.crear_token_pair(principal)
    with Session(app) as db:
        original=db.commit
        def uncertain():
            if ack_lost: original()
            raise StatementError('private-recovery-sql','private-statement',{'bearer':token,'password':NEW},RuntimeError())
        monkeypatch.setattr(db,'commit',uncertain)
        with pytest.raises(HTTPException) as failure: consume(db,token,NEW)
    assert failure.value.status_code==503 and failure.value.detail['code']=='password_reset_unconfirmed'
    assert all(value not in caplog.text for value in (token,NEW,'private-recovery-sql','private-statement'))
    with Session(admin) as db:
        user=db.get(Usuario,'reset-owner')
        assert user.session_version==int(ack_lost)
        assert auth.verify_password(NEW if ack_lost else OLD,user.password_hash)
        assert user.password_reset_hash==(None if ack_lost else digest(token))
        assert db.query(RefreshToken).filter_by(user_id=user.id,revoked=True).count()==int(ack_lost)
        assert db.query(AuthAuditLog).filter_by(event_type='password_reset_complete').count()==int(ack_lost)
    assert bool(auth.verificar_token(pair['access_token'])) is not ack_lost


@pytest.mark.parametrize('operation',['logout','reuse'])
def test_reset_and_revocation_share_actual_account_lock_without_deadlock(recovery_pg,operation):
    from web import auth
    from web.database.models import Usuario,RefreshToken
    from web.services.password_recovery import consume
    admin,app=recovery_pg
    with Session(app) as db: principal=auth.identity_from_user(db.get(Usuario,'reset-owner'),db)
    old=auth.crear_token_pair(principal)['refresh_token']
    if operation=='reuse': assert auth.rotar_refresh_token(old)
    token=issue(app)
    account_locked,revoker_waiting=Event(),Event()
    def after(connection,cursor,statement,parameters,context,executemany):
        if current_thread().name.startswith('reset-race') and statement.lower().startswith('update usuarios'):
            account_locked.set()
            assert revoker_waiting.wait(8)
    def before(connection,cursor,statement,parameters,context,executemany):
        if current_thread().name.startswith('revoke-race') and statement.lower().startswith('update usuarios'):
            revoker_waiting.set()
    event.listen(app,'after_cursor_execute',after); event.listen(app,'before_cursor_execute',before)
    def reset():
        with Session(app) as db: return consume(db,token,NEW)
    def revoke():
        assert account_locked.wait(8)
        if operation=='reuse': return auth.rotar_refresh_token(old)
        return auth.revocar_refresh_tokens_usuario('reset-owner')
    try:
        with ThreadPoolExecutor(max_workers=1,thread_name_prefix='reset-race') as resets, \
                ThreadPoolExecutor(max_workers=1,thread_name_prefix='revoke-race') as revokers:
            first=resets.submit(reset); second=revokers.submit(revoke)
            assert first.result(timeout=18)==('reset-owner@example.invalid','Synthetic')
            assert second.result(timeout=18) is None
    finally:
        event.remove(app,'after_cursor_execute',after); event.remove(app,'before_cursor_execute',before)
    assert account_locked.is_set() and revoker_waiting.is_set()
    with Session(admin) as db:
        user=db.get(Usuario,'reset-owner')
        assert user.session_version==2 and auth.verify_password(NEW,user.password_hash)
        assert db.query(RefreshToken).filter_by(user_id=user.id,revoked=False).count()==0


def test_refresh_pair_issued_late_with_old_version_is_not_valid(recovery_pg,monkeypatch):
    from web import auth
    from web.database.models import Usuario
    from web.services.password_recovery import consume
    admin,app=recovery_pg
    with Session(app) as db: principal=auth.identity_from_user(db.get(Usuario,'reset-owner'),db)
    old=auth.crear_token_pair(principal)['refresh_token']
    token=issue(app)
    original=auth.crear_token_pair
    def after_last_identity_check(snapshot,*args,**kwargs):
        with Session(app) as db: consume(db,token,NEW)
        return original(snapshot,*args,**kwargs)
    monkeypatch.setattr(auth,'crear_token_pair',after_last_identity_check)
    pair=auth.rotar_refresh_token(old)
    assert pair and auth.verificar_token(pair['access_token']) is None
    assert auth.verificar_refresh_token(pair['refresh_token']) is None


@pytest.mark.parametrize('zone',['UTC','America/Mexico_City'])
def test_expiry_offset_and_postlock_revalidation(recovery_pg,monkeypatch,zone):
    from web.database.models import Usuario
    from web.services import password_recovery as recovery
    admin,app=recovery_pg
    base=datetime(2026,10,19,12,tzinfo=timezone(timedelta(hours=5,minutes=30)))
    token=issue(app,now=base)
    with app.connect() as db:
        db.execute(text("SELECT set_config('TimeZone',:zone,false)"),{'zone':zone}); db.commit()
    with Session(admin) as db:
        assert db.get(Usuario,'reset-owner').password_reset_expires_at==datetime(2026,10,19,7)
    moments=iter([base+timedelta(minutes=29),base+timedelta(minutes=30)])
    monkeypatch.setattr(recovery,'clock',lambda now=None:next(moments).astimezone(timezone.utc))
    with Session(app) as db,pytest.raises(HTTPException) as failure: recovery.consume(db,token,NEW)
    assert failure.value.status_code==400
    with Session(admin) as db:
        assert db.get(Usuario,'reset-owner').session_version==0


def test_subject_mismatch_and_reissue_between_preview_and_lock_are_denied(recovery_pg):
    from web.database.models import Usuario
    from web.database.tenant_context import tenant_scope
    from web.services.password_recovery import consume,digest
    admin,app=recovery_pg
    token=issue(app)
    with tenant_scope('reset-other'),Session(app) as db,pytest.raises(HTTPException) as denied:
        consume(db,token,NEW)
    assert denied.value.status_code==400
    replacement='z'*43
    changed=[]
    def intervene(connection,cursor,statement,parameters,context,executemany):
        if statement.lower().startswith('update usuarios') and not changed:
            changed.append(True)
            with admin.begin() as other:
                other.execute(update(Usuario).where(Usuario.id=='reset-owner').values(password_reset_hash=digest(replacement)))
    event.listen(app,'before_cursor_execute',intervene)
    try:
        with Session(app) as db,pytest.raises(HTTPException) as denied: consume(db,token,NEW)
    finally: event.remove(app,'before_cursor_execute',intervene)
    assert denied.value.status_code==400 and changed
    with Session(admin) as db:
        assert db.get(Usuario,'reset-owner').session_version==0
        assert db.get(Usuario,'reset-owner').password_reset_hash==digest(replacement)
