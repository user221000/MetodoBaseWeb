"""R11 contracts on isolated persistence and a captured email transport only."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def team_case(monkeypatch):
    import base64
    import uuid
    from web import auth
    from web.database import engine as engine_module
    from web.database.engine import get_db
    from web.database.models import Base, Subscription, Usuario, UserRole
    from web.routes import team
    from web.services import email_service
    from web import settings

    engine = create_engine('sqlite://', poolclass=StaticPool,
                           connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(engine_module, '_engine', engine)
    monkeypatch.setattr(engine_module, '_SessionLocal', factory)
    monkeypatch.setattr(auth, '_get_session', factory)
    monkeypatch.setattr(auth, 'SECRET_KEY', 'synthetic-team-only-signing-key-at-least-32-characters')
    configuration = settings.get_settings()
    monkeypatch.setattr(configuration, 'BASE_URL', 'http://127.0.0.1:8765')
    monkeypatch.setattr(configuration, 'RESEND_API_KEY', '')
    monkeypatch.setattr(configuration, 'MFA_ENCRYPTION_KEY', base64.urlsafe_b64encode(b'synthetic-mfa-contract-key-32byte!'[:32]).decode())
    captured = []
    monkeypatch.setattr(email_service, '_send', lambda to, subject, html, attachments=None: captured.append({'to':to, 'subject':subject, 'html':html}) or False)
    principal = {'id':'team-owner','email':'owner@example.invalid','nombre':'Owner','tipo':'gym','role':'owner','team_gym_id':None}
    with factory() as db:
        db.add(Usuario(id=principal['id'], email=principal['email'], nombre='Owner', password_hash=auth.hash_password('SyntheticPassword123!'), tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        db.add(Subscription(gym_id=principal['id'], plan='clinica', status='active', current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.commit()
    def session():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
    app = FastAPI()
    from web.routes import auth as auth_routes, mfa
    from tests.mfa31_contract_client import MfaContractClient
    app.include_router(auth_routes.router, prefix='/api')
    app.include_router(mfa.router, prefix='/api')
    app.include_router(team.router, prefix='/api')
    app.include_router(team.auth_router, prefix='/api')
    app.dependency_overrides[get_db] = session
    number = int(uuid.uuid4().hex[:4], 16)
    with TestClient(app, raise_server_exceptions=False, client=(f'127.2.{number // 256}.{number % 256}', 50000)) as raw:
        client = MfaContractClient(raw, principal, factory, 'SyntheticPassword123!')
        client.authenticate()
        yield client, factory, principal, captured
    engine.dispose()


def invite(case, email='professional@example.invalid', role='nutriologo'):
    client, _, _, _ = case
    response = client.post('/api/gym/team/invite', json={'email':email,'nombre':'Professional','apellido':'Synthetic','role':role})
    assert response.status_code == 200, response.text
    return response.json()


def member(factory, email='professional@example.invalid'):
    from web.database.models import Usuario
    with factory() as db:
        return db.execute(select(Usuario).where(Usuario.email == email)).scalar_one()


def test_invite_uses_absolute_single_token_url_and_does_not_claim_delivery(team_case):
    import hashlib
    client, factory, _, captured = team_case
    result = invite(team_case)
    link = urlsplit(result['invitation_link'])
    assert link.scheme == 'http' and link.netloc == '127.0.0.1:8765'
    assert link.path == '/auth/accept-invite'
    assert not link.query
    token = parse_qs(link.fragment)['token'][0]
    assert len(token) >= 32 and '?' not in token
    assert member(factory).invitation_token == hashlib.sha256(token.encode()).hexdigest()
    assert result['delivery_status'] == 'not_confirmed'
    assert 'enviada' not in result['message'].lower()
    assert result['invitation_link'] in captured[0]['html']
    assert 'token=/auth/' not in captured[0]['html']
    assert client.get('/api/auth/invite-info', params={'token':token}).status_code == 200
    public = client.post('/api/auth/invite-info',json={'token':token})
    assert public.status_code == 200
    assert public.headers['cache-control'] == 'no-store'
    assert public.headers['referrer-policy'] == 'no-referrer'


def test_valid_invite_accepts_once_with_persisted_professional_identity(team_case):
    from web import auth
    client, factory, _, _ = team_case
    token = invite(team_case)['invitation_token']
    info = client.get('/api/auth/invite-info', params={'token':token})
    assert info.status_code == 200, info.text
    assert info.json()['status'] == 'pending' and info.json()['is_expired'] is False
    payload = {'token':token, 'password':'SyntheticPassword123!'}
    accepted = client.post('/api/auth/accept-invite', json=payload)
    assert accepted.status_code == 200, accepted.text
    identity = auth.verificar_token(accepted.json()['access_token'])
    assert identity['role'] == 'nutriologo' and identity['team_gym_id'] == 'team-owner'
    assert member(factory).invitation_token is None
    assert client.post('/api/auth/accept-invite', json=payload).status_code in {400,409}


def test_expired_invitation_is_visible_and_cannot_activate_account(team_case):
    from web.database.models import Usuario
    client, factory, _, _ = team_case
    token = invite(team_case)['invitation_token']
    with factory() as db:
        db.get(Usuario, member(factory).id).invitation_expires = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    info = client.get('/api/auth/invite-info', params={'token':token})
    assert info.status_code == 200, info.text
    assert info.json()['status'] == 'expired'
    assert client.post('/api/auth/accept-invite', json={'token':token,'password':'SyntheticPassword123!'}).status_code == 410
    assert member(factory).activo is False


def test_resend_rotates_token_and_returns_current_shareable_link(team_case):
    client, factory, _, _ = team_case
    old = invite(team_case)['invitation_token']
    response = client.post('/api/gym/team/'+member(factory).id+'/resend-invite')
    assert response.status_code == 200, response.text
    new = response.json()['invitation_token']
    assert new != old and new in response.json()['invitation_link']
    assert client.get('/api/auth/invite-info', params={'token':old}).status_code == 404
    assert client.get('/api/auth/invite-info', params={'token':new}).status_code == 200


def test_revocation_preserves_personal_profile_and_invalidates_team_sessions(team_case):
    from web import auth
    from web.database.models import Usuario, Cliente, UserRole, UserSubscription
    client, factory, _, _ = team_case
    token = invite(team_case)['invitation_token']
    response = client.post('/api/auth/accept-invite', json={'token':token,'password':'SyntheticPassword123!'})
    assert response.status_code == 200, response.text
    pair = response.json(); subject = member(factory).id
    with factory() as db:
        db.add(Cliente(id_cliente='existing-personal-profile', gym_id=subject, nombre='Personal Profile'))
        db.add(UserSubscription(user_id=subject, plan='starter', mes_actual='2026-10'))
        db.commit()
    assert client.delete('/api/gym/team/'+subject).status_code == 200
    with factory() as db:
        user = db.get(Usuario, subject)
        assert user is not None and user.activo is True
        assert user.team_gym_id is None and user.role == UserRole.VIEWER
        assert user.session_version == 1
        assert db.execute(select(Cliente).where(Cliente.gym_id == subject)).scalar_one().id_cliente == 'existing-personal-profile'
        assert db.execute(select(UserSubscription).where(UserSubscription.user_id == subject)).scalar_one().plan == 'starter'
    assert auth.verificar_token(pair['access_token']) is None
    assert auth.verificar_refresh_token(pair['refresh_token']) is None
    personal = auth.verificar_credenciales('professional@example.invalid','SyntheticPassword123!')
    assert personal['team_gym_id'] is None and personal['role'] == 'viewer'


def test_existing_personal_email_never_becomes_a_professional_link(team_case):
    from web.database.models import Usuario, UserRole
    client, factory, _, _ = team_case
    with factory() as db:
        db.add(Usuario(id='independent-person', email='person@example.invalid', nombre='Person', password_hash='unused', tipo='usuario', role=UserRole.VIEWER, activo=True))
        db.commit()
    response = client.post('/api/gym/team/invite', json={'email':'person@example.invalid','nombre':'Person','role':'viewer'})
    assert response.status_code == 409
    with factory() as db:
        assert db.get(Usuario,'independent-person').team_gym_id is None


def test_admin_cannot_rotate_an_admin_invitation(team_case):
    from web import auth
    from web.database.models import Usuario, UserRole
    client, factory, principal, _ = team_case
    invite(team_case, role='admin'); target = member(factory).id
    with factory() as db:
        db.add(Usuario(id='team-admin', email='admin@example.invalid', nombre='Admin', password_hash=auth.hash_password('SyntheticPassword123!'), tipo='usuario', role=UserRole.ADMIN, team_gym_id='team-owner', activo=True))
        db.commit()
    principal.update(id='team-admin', role='admin', tipo='usuario', team_gym_id='team-owner')
    assert client.post('/api/gym/team/'+target+'/resend-invite').status_code == 403


def test_invite_password_follows_registration_minimum(team_case):
    client, factory, _, _ = team_case
    token = invite(team_case)['invitation_token']
    assert client.post('/api/auth/accept-invite', json={'token':token,'password':'short123'}).status_code == 422
    assert member(factory).activo is False


def test_member_list_exposes_current_capabilities_and_invitation_expiry(team_case):
    client, _, _, _ = team_case
    invite(team_case)
    response = client.get('/api/gym/team')
    assert response.status_code == 200
    body = response.json()
    assert body['assignable_roles'] == ['admin','nutriologo','viewer']
    assert body['capabilities']['revoke_preserves_identity'] is True
    pending = next(row for row in body['members'] if row['is_pending'])
    assert pending['invitation_status'] == 'pending' and pending['invitation_expires_at']
    assert pending['can_resend'] is True and pending['can_remove'] is True


def test_stored_digest_is_not_a_bearer_token(team_case):
    client, factory, _, _ = team_case
    invite(team_case)
    digest = member(factory).invitation_token
    assert client.get('/api/auth/invite-info',params={'token':digest}).status_code == 422
    assert client.post('/api/auth/accept-invite',json={'token':digest,'password':'SyntheticPassword123!'}).status_code == 422
    assert member(factory).activo is False


def test_cancel_pending_invitation_never_activates_personal_account(team_case):
    from web.database.models import Usuario
    client, factory, _, _ = team_case
    token = invite(team_case)['invitation_token']; subject = member(factory).id
    assert client.delete('/api/gym/team/'+subject).status_code == 200
    with factory() as db:
        row = db.get(Usuario,subject)
        assert row is not None and row.activo is False and row.team_gym_id is None
    assert client.get('/api/auth/invite-info',params={'token':token}).status_code == 404
    assert client.post('/api/auth/accept-invite',json={'token':token,'password':'SyntheticPassword123!'}).status_code == 400


def test_unicode_password_size_error_does_not_consume_invitation(team_case):
    client, factory, _, _ = team_case
    token = invite(team_case)['invitation_token']
    assert client.post('/api/auth/accept-invite',json={'token':token,'password':'界'*30}).status_code == 422
    assert member(factory).invitation_token is not None


def test_team_email_escapes_untrusted_names_and_url(team_case):
    from web.services.email_service import send_team_invitation
    _, _, _, captured = team_case
    send_team_invitation('synthetic@example.invalid','<img src=x onerror=alert(1)>','<script>gym</script>','<b>role</b>','https://example.invalid/?x=" onclick="alert(1)')
    html = captured[-1]['html']
    assert '<script>' not in html and '<img src=x' not in html and '<b>role</b>' not in html
    assert '&lt;script&gt;' in html and '&quot; onclick=&quot;' in html


def test_parallel_consumers_only_one_can_claim_token(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from web import auth
    from web.database.models import Base, Subscription, Usuario, UserRole
    from web.services import team_invitation_service as service
    engine = create_engine('sqlite:///'+(tmp_path/'team-race.db').as_posix(),connect_args={'check_same_thread':False,'timeout':10})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine,expire_on_commit=False)
    token = 'r'*43
    with factory() as db:
        db.add(Usuario(id='race-owner',email='race-owner@example.invalid',nombre='Owner',password_hash='unused',tipo='gym',role=UserRole.OWNER,activo=True))
        db.commit()
        db.add(Subscription(gym_id='race-owner',plan='clinica',status='active',current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.commit()
        db.add(Usuario(id='race-member',email='race-member@example.invalid',nombre='Member',password_hash='PENDING_INVITATION',tipo='usuario',role=UserRole.VIEWER,team_gym_id='race-owner',activo=False,invitation_token=service.token_digest(token),invitation_expires=datetime.now(timezone.utc)+timedelta(minutes=10),invitation_role=UserRole.VIEWER))
        db.commit()
    barrier = Barrier(2); original = service.find_invitation
    def stale_read(db, value):
        row = original(db,value)
        barrier.wait(timeout=10)
        return row
    monkeypatch.setattr(service,'find_invitation',stale_read)
    def claim(number):
        password = 'Synthetic-Race-Password-'+str(number)
        with factory() as db:
            try:
                service.consume(db,token,password)
                return 200,password
            except HTTPException as error:
                return error.status_code,password
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim,[1,2]))
        assert sorted(status for status,_ in results) == [200,409]
        with factory() as db:
            row = db.get(Usuario,'race-member')
            assert row.invitation_token is None and row.activo is True
            winner = next(password for status,password in results if status==200)
            loser = next(password for status,password in results if status!=200)
            assert auth.verify_password(winner,row.password_hash)
            assert not auth.verify_password(loser,row.password_hash)
    finally:
        engine.dispose()


def test_email_transport_failure_does_not_log_bearer_or_message(monkeypatch, caplog):
    import sys
    from web.services import email_service
    sentinel = 'synthetic-invitation-bearer-and-private-email-body'
    def rejected(_):
        raise RuntimeError(sentinel)
    monkeypatch.setattr(email_service, '_is_configured', lambda: True)
    monkeypatch.setattr(email_service, 'get_settings', lambda: SimpleNamespace(RESEND_API_KEY='synthetic-offline-only'))
    monkeypatch.setitem(sys.modules, 'resend', SimpleNamespace(Emails=SimpleNamespace(send=rejected)))
    assert email_service._send('synthetic@example.invalid', 'Synthetic invitation', sentinel) is False
    assert sentinel not in caplog.text and 'RuntimeError' in caplog.text


def test_detaching_historical_gym_typed_member_never_changes_owner(team_case):
    from web.database.models import Usuario, UserRole
    client, factory, _, _ = team_case
    with factory() as db:
        db.add(Usuario(id='historical-professional',email='historical@example.invalid',nombre='Historical',password_hash='unused',tipo='gym',role=UserRole.VIEWER,team_gym_id='team-owner',activo=True))
        db.commit()
    assert client.delete('/api/gym/team/historical-professional').status_code == 200
    with factory() as db:
        row = db.get(Usuario,'historical-professional')
        assert row.tipo == 'usuario' and row.role == UserRole.VIEWER and row.team_gym_id is None
        owner = db.get(Usuario,'team-owner')
        assert owner.tipo == 'gym' and owner.role == UserRole.OWNER and owner.activo is True


@pytest.mark.parametrize('action',['role','remove','resend'])
def test_team_mutations_never_cross_to_another_gym(team_case, action):
    from web.database.models import Usuario, UserRole, MfaAuthorization
    client, factory, principal, _ = team_case
    with factory() as db:
        db.add(Usuario(id='different-gym',email='different-owner@example.invalid',nombre='Other Owner',password_hash='unused',tipo='gym',role=UserRole.OWNER,activo=True))
        db.commit()
        db.add(Usuario(id='different-member',email='different-member@example.invalid',nombre='Other Member',password_hash='PENDING_INVITATION',tipo='usuario',role=UserRole.VIEWER,team_gym_id='different-gym',activo=False,invitation_token='z'*43,invitation_expires=datetime.now(timezone.utc)+timedelta(hours=1),invitation_role=UserRole.VIEWER))
        db.commit()
    if action=='role': response=client.patch('/api/gym/team/different-member/role',json={'role':'admin'})
    elif action=='remove': response=client.delete('/api/gym/team/different-member')
    else: response=client.post('/api/gym/team/different-member/resend-invite')
    # Current31 authorizes the exact MFA action before the business lookup.
    # Foreign and missing IDs remain indistinguishable at that boundary.
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'mfa_action_forbidden'
    if action=='role': missing=client.patch('/api/gym/team/absent-member/role',json={'role':'admin'})
    elif action=='remove': missing=client.delete('/api/gym/team/absent-member')
    else: missing=client.post('/api/gym/team/absent-member/resend-invite')
    assert missing.status_code == response.status_code and missing.json() == response.json()
    with factory() as db:
        row=db.get(Usuario,'different-member')
        assert row.team_gym_id=='different-gym' and row.role==UserRole.VIEWER and row.invitation_token=='z'*43
        assert db.query(MfaAuthorization).filter_by(user_id=principal['id'],purpose='action').count() == 0


def test_invitation_name_is_scoped_to_persisted_offer_not_input_gym(team_case):
    from web.database.models import GymProfile, Usuario, UserRole
    client, factory, _, _ = team_case
    with factory() as db:
        db.add(Usuario(id='other-profile-gym',email='other-profile@example.invalid',nombre='Other',password_hash='unused',tipo='gym',role=UserRole.OWNER,activo=True))
        db.commit()
        db.add_all([GymProfile(gym_id='team-owner',nombre_negocio='Authorized Invitation Gym'),GymProfile(gym_id='other-profile-gym',nombre_negocio='Different Private Gym')])
        db.commit()
    token=invite(team_case)['invitation_token']
    result=client.post('/api/auth/invite-info',json={'token':token})
    assert result.status_code==200 and result.json()['gym_name']=='Authorized Invitation Gym'
    assert 'Different Private Gym' not in result.text
    assert client.post('/api/auth/invite-info',json={'token':token,'gym_id':'other-profile-gym'}).status_code==422


def test_role_change_between_read_and_claim_cannot_restore_stale_role(team_case, monkeypatch):
    from sqlalchemy import update
    from web.database.models import Usuario, UserRole
    from web.services import team_invitation_service as service
    client, factory, _, _ = team_case
    token=invite(team_case,role='admin')['invitation_token']
    original=service.find_invitation
    def changed_offer(db, bearer):
        row=original(db,bearer)
        with factory() as concurrent:
            concurrent.execute(update(Usuario).where(Usuario.id==row.id).values(role=UserRole.VIEWER,invitation_role=UserRole.VIEWER,session_version=1))
            concurrent.commit()
        return row
    monkeypatch.setattr(service,'find_invitation',changed_offer)
    response=client.post('/api/auth/accept-invite',json={'token':token,'password':'SyntheticPassword123!'})
    assert response.status_code==409
    current=member(factory)
    assert current.role==UserRole.VIEWER and current.activo is False and current.invitation_token is not None


@pytest.mark.parametrize('action', ['role', 'remove'])
@pytest.mark.parametrize('change', ['role', 'team', 'session'])
def test_stale_membership_mutation_rejects_changed_target_without_revoking_new_sessions(team_case, monkeypatch, action, change):
    from sqlalchemy import update
    from web.database.models import RefreshToken, Usuario, UserRole
    from web.routes import team
    client, factory, _, _ = team_case
    with factory() as db:
        db.add(Usuario(id='replacement-owner', email='replacement-owner@example.invalid', nombre='Other owner', password_hash='unused', tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        db.add(Usuario(id='changed-member', email='changed-member@example.invalid', nombre='Changed member', password_hash='unused', tipo='usuario', role=UserRole.VIEWER, team_gym_id='team-owner', activo=True, session_version=0))
        db.commit()
        db.add(RefreshToken(jti='changed-member-refresh', user_id='changed-member', created_at=0, expires_at=9999999999, revoked=False))
        db.commit()
    original = team._target
    changed = {'role': UserRole.ADMIN} if change == 'role' else {'team_gym_id': 'replacement-owner'} if change == 'team' else {'session_version': 1}
    def stale_target(db, actor, user_id):
        observed = original(db, actor, user_id)
        with factory() as concurrent:
            concurrent.execute(update(Usuario).where(Usuario.id == user_id).values(**changed))
            concurrent.commit()
        return observed
    monkeypatch.setattr(team, '_target', stale_target)
    response = client.patch('/api/gym/team/changed-member/role', json={'role':'nutriologo'}) if action == 'role' else client.delete('/api/gym/team/changed-member')
    assert response.status_code == 409
    with factory() as db:
        current = db.get(Usuario, 'changed-member')
        assert current.team_gym_id == changed.get('team_gym_id', 'team-owner')
        assert current.role == changed.get('role', UserRole.VIEWER)
        assert current.session_version == changed.get('session_version', 0)
        assert current.activo is True and current.tipo == 'usuario'
        assert db.get(RefreshToken, 'changed-member-refresh').revoked is False


def set_team_plan(factory, plan, status='active', *, expired=False):
    from web.database.models import Subscription
    with factory() as db:
        db.query(Subscription).filter_by(gym_id='team-owner').delete()
        if plan != 'free':
            end = datetime.now(timezone.utc) + timedelta(days=-1 if expired else 30)
            db.add(Subscription(gym_id='team-owner', plan=plan, status=status, current_period_end=end, trial_end=end if status == 'trialing' else None))
        db.commit()


@pytest.mark.parametrize('plan,status,expired', [
    ('free', 'active', False), ('standard', 'active', False), ('gym_comercial', 'active', False),
    ('clinica', 'active', True), ('clinica', 'canceled', False), ('clinica', 'trialing', False),
])
def test_invitation_requires_effective_multi_user_right_without_creating_account(team_case, plan, status, expired):
    from web.database.models import Usuario
    client, factory, _, captured = team_case
    set_team_plan(factory, plan, status, expired=expired)
    result = client.post('/api/gym/team/invite', json={'email':'blocked@example.invalid', 'nombre':'Blocked', 'role':'viewer'})
    assert result.status_code == 402
    with factory() as db:
        assert db.query(Usuario).filter_by(email='blocked@example.invalid').count() == 0
    assert captured == []
    listing = client.get('/api/gym/team')
    assert listing.status_code == 200
    assert listing.json()['capabilities']['invite'] is False


def test_downgrade_blocks_resend_and_claim_without_consuming_offer(team_case):
    client, factory, _, captured = team_case
    set_team_plan(factory, 'clinica')
    offer = invite(team_case)
    before = member(factory)
    set_team_plan(factory, 'standard')
    assert client.post('/api/gym/team/'+before.id+'/resend-invite').status_code == 402
    result = client.post('/api/auth/accept-invite', json={'token':offer['invitation_token'], 'password':'SyntheticPassword123!'})
    assert result.status_code == 402
    current = member(factory)
    assert current.invitation_token == before.invitation_token and current.activo is False
    assert current.role == before.role and current.session_version == before.session_version
    assert len(captured) == 1
    pending = next(row for row in client.get('/api/gym/team').json()['members'] if row['id'] == before.id)
    assert pending['can_resend'] is False and pending['can_remove'] is True


def test_existing_members_remain_manageable_after_downgrade(team_case):
    client, factory, _, _ = team_case
    set_team_plan(factory, 'clinica')
    offer = invite(team_case)
    assert client.post('/api/auth/accept-invite', json={'token':offer['invitation_token'], 'password':'SyntheticPassword123!'}).status_code == 200
    subject = member(factory).id
    set_team_plan(factory, 'free')
    listing = client.get('/api/gym/team').json()
    assert listing['capabilities']['invite'] is False
    assert next(row for row in listing['members'] if row['id'] == subject)['activo'] is True
    assert client.patch('/api/gym/team/'+subject+'/role', json={'role':'viewer'}).status_code == 200
    assert client.delete('/api/gym/team/'+subject).status_code == 200
    assert member(factory).activo is True and member(factory).team_gym_id is None


def test_invitation_gate_refreshes_cached_subscription_before_issuing(team_case):
    from fastapi import HTTPException
    from web.database.models import Subscription, Usuario, UserRole
    from web.services import team_invitation_service as service
    _, factory, actor, captured = team_case
    with factory() as db:
        cached = db.query(Subscription).filter_by(gym_id='team-owner').one()
        assert cached.plan == 'clinica'
        with factory() as concurrent:
            concurrent.query(Subscription).filter_by(gym_id='team-owner').update({'plan':'standard'})
            concurrent.commit()
        with pytest.raises(HTTPException) as rejected:
            service.issue(db, actor=actor, gym_id='team-owner', email='cached-plan@example.invalid', nombre='Cached plan', apellido='', role=UserRole.VIEWER, base_url='http://127.0.0.1:8767')
        assert rejected.value.status_code == 402
        assert db.query(Usuario).filter_by(email='cached-plan@example.invalid').count() == 0
    assert captured == []
