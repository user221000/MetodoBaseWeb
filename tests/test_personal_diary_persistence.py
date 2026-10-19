"""Personal diary HTTP persistence with canonical auth and isolated SQLite."""
from datetime import datetime, timedelta, timezone
import importlib
import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


@pytest.fixture(params=['web.main_web', 'api.app'])
def diary_http(request):
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    application = importlib.import_module(request.param).create_app()
    tokens = {}
    with Session(get_engine()) as db:
        for identity, kind, role, parent in [
            ('diary-owner', 'gym', UserRole.OWNER, None),
            ('diary-person', 'usuario', UserRole.VIEWER, None),
            ('diary-other', 'usuario', UserRole.VIEWER, None),
            ('diary-member', 'gym', UserRole.NUTRIOLOGO, 'diary-owner'),
            ('diary-legacy-owner', 'usuario', UserRole.OWNER, None),
        ]:
            user = Usuario(id=identity, email=identity+'@example.invalid', password_hash='synthetic',
                nombre='Synthetic', tipo=kind, role=role, team_gym_id=parent, activo=True)
            db.add(user)
            db.flush()
        db.commit()
        for identity in ('diary-owner', 'diary-person', 'diary-other', 'diary-member', 'diary-legacy-owner'):
            tokens[identity] = {'Authorization':'Bearer '+crear_access_token(identity_from_user(db.get(Usuario, identity), db))}
    with TestClient(application, raise_server_exceptions=False) as client:
        assert client.get('/api/auth/me', headers=tokens['diary-person']).status_code == 200
        yield client, tokens, get_engine()


def test_missing_diary_day_is_virtual_and_readonly(diary_http):
    from sqlalchemy import event
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client, tokens, engine = diary_http
    day = local_today().isoformat()
    actions, commits = [], []
    def observed(connection, cursor, statement, parameters, context, executemany):
        actions.append(statement.split(None,1)[0].upper())
    def committed(session):
        commits.append(True)
    event.listen(engine, 'before_cursor_execute', observed)
    event.listen(Session, 'after_commit', committed)
    try:
        response = client.get('/api/usuario/diario/'+day, headers=tokens['diary-person'])
    finally:
        event.remove(engine, 'before_cursor_execute', observed)
        event.remove(Session, 'after_commit', committed)
    assert response.status_code == 200, response.text
    assert response.json() == {'local_date':day, 'timezone':'America/Mexico_City', 'today':day,
        'version':0, 'water_ml':0, 'meals':{}, 'created_at':None, 'updated_at':None,
        'totals':{'kcal':0,'protein_g':0,'carbs_g':0,'fat_g':0}}
    assert response.headers['cache-control'] == 'no-store'
    assert commits == [] and not set(actions).intersection({'INSERT','UPDATE','DELETE','CREATE','ALTER'})
    with Session(engine) as db:
        assert db.query(PersonalDiaryDay).count() == 0
    calendar = client.get('/api/usuario/diario',headers=tokens['diary-person'])
    assert calendar.status_code==200
    assert calendar.json()['days']==[response.json()]
    assert calendar.json()['today']==day
    assert client.get('/api/usuario/diario',headers=tokens['diary-person'],params={'start':day}).status_code==422


def test_water_persists_across_requests_and_stale_update_conflicts(diary_http):
    from sqlalchemy import event
    from web.services.personal_diary_service import local_today
    client, tokens, _ = diary_http
    url = '/api/usuario/diario/'+(local_today()-timedelta(days=1)).isoformat()
    commits = []
    def committed(session):
        commits.append(True)
    event.listen(Session, 'after_commit', committed)
    try:
        first = client.patch(url, headers=tokens['diary-person'], json={
            'operation':'water', 'expected_version':0, 'water_ml':1250})
    finally:
        event.remove(Session, 'after_commit', committed)
    assert first.status_code == 200, first.text
    assert first.json()['version'] == 1 and first.json()['water_ml'] == 1250
    assert commits == [True]
    stored = client.get(url, headers=tokens['diary-person'])
    assert stored.status_code == 200 and stored.json() == first.json()
    stale = client.patch(url, headers=tokens['diary-person'], json={
        'operation':'water', 'expected_version':0, 'water_ml':500})
    assert stale.status_code == 409
    assert client.get(url, headers=tokens['diary-person']).json() == first.json()


def seed_plan(engine, *, owner='diary-person', client_owner=None, client_deleted=False, plan_deleted=False, active=True):
    from web.database.models import Cliente, PlanGenerado
    import uuid
    with Session(engine) as db:
        profile = Cliente(id_cliente=str(uuid.uuid4()), gym_id=client_owner or owner, nombre='Synthetic',
            activo=active, deleted_at=datetime.now(timezone.utc) if client_deleted else None)
        db.add(profile)
        db.flush()
        meal = {'proteinas':{'opciones':[{'alimento':'huevo','gramos':100,'equivalencia':'2 piezas',
            'macros':{'kcal':140,'proteina':12,'carbs':1,'grasa':10}}]}, 'vegetales':[]}
        row = PlanGenerado(gym_id=owner, id_cliente=profile.id_cliente,
            plan_json=json.dumps({name:meal for name in ('desayuno','almuerzo','comida','cena')}),
            deleted_at=datetime.now(timezone.utc) if plan_deleted else None)
        db.add(row)
        db.commit()
        return row.id


def meal_patch(plan, version, meal='desayuno'):
    return {'operation':'meal','expected_version':version,'meal':meal,
        'source_plan_id':plan,'selections':{'proteinas':0}}


def test_meals_are_independent_immutable_snapshots_and_completion_requires_one(diary_http):
    from sqlalchemy import text
    from web.services.personal_diary_service import local_today
    client, tokens, engine = diary_http
    url = '/api/usuario/diario/'+local_today().isoformat()
    headers = tokens['diary-person']
    assert client.patch(url, headers=headers, json={'operation':'completion','expected_version':0,
        'meal':'desayuno','completed':True}).status_code == 409
    plan1, plan2 = seed_plan(engine), seed_plan(engine)
    first = client.patch(url, headers=headers, json=meal_patch(plan1,0)).json()
    assert first['meals']['desayuno']['source_plan_id'] == plan1
    completed = client.patch(url, headers=headers, json={'operation':'completion','expected_version':1,
        'meal':'desayuno','completed':True}).json()
    assert completed['totals']==first['totals']=={'kcal':140,'protein_g':12,'carbs_g':1,'fat_g':10}
    water = client.patch(url, headers=headers, json={'operation':'water','expected_version':2,'water_ml':750}).json()
    other_meal = client.patch(url, headers=headers, json=meal_patch(plan2,3,'comida')).json()
    assert other_meal['meals']['desayuno'] == completed['meals']['desayuno']
    assert other_meal['water_ml'] == water['water_ml'] == 750
    assert other_meal['totals']=={'kcal':280,'protein_g':24,'carbs_g':2,'fat_g':20}
    replaced = client.patch(url, headers=headers, json=meal_patch(plan2,4)).json()
    assert replaced['meals']['desayuno']['completed'] is False
    assert replaced['meals']['comida'] == other_meal['meals']['comida']
    with engine.begin() as db:
        db.execute(text('DELETE FROM planes_generados WHERE id=:id'), {'id':plan2})
    assert client.get(url, headers=headers).json() == replaced
    assert replaced['version'] == 5


@pytest.mark.parametrize('source', ['foreign','mixed','client_deleted','plan_deleted','inactive'])
def test_new_snapshot_requires_plan_and_client_live_and_owned(diary_http, source):
    from web.services.personal_diary_service import local_today
    client, tokens, engine = diary_http
    plan = seed_plan(engine, owner='diary-other' if source=='foreign' else 'diary-person',
        client_owner='diary-other' if source=='mixed' else None,
        client_deleted=source=='client_deleted', plan_deleted=source=='plan_deleted', active=source!='inactive')
    response = client.patch('/api/usuario/diario/'+local_today().isoformat(), headers=tokens['diary-person'],
        json=meal_patch(plan,0))
    assert response.status_code == (200 if source=='inactive' else 404), response.text


@pytest.mark.parametrize('identity', ['diary-person','diary-member'])
def test_personal_identities_share_no_portfolio_or_other_account(diary_http, identity):
    from web.services.personal_diary_service import local_today
    client, tokens, _ = diary_http
    url = '/api/usuario/diario/'+local_today().isoformat()
    saved = client.patch(url, headers=tokens[identity], json={'operation':'water','expected_version':0,'water_ml':1800})
    assert saved.status_code == 200, saved.text
    assert client.get(url, headers=tokens['diary-other']).json()['version'] == 0
    assert client.get(url, headers=tokens['diary-owner']).status_code == 403
    exported = client.get('/api/usuario/privacidad/exportar', headers=tokens[identity])
    assert exported.status_code == 200, exported.text
    assert exported.json()['scope']['personal_space'] is True
    assert [row['water_ml'] for row in exported.json()['personal_diary']['records']] == [1800]
    assert client.get('/api/usuario/privacidad/exportar', headers=tokens['diary-owner']).json()['personal_diary']['records'] == []


def test_ambiguous_personal_owner_never_adopts_portfolio(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client, tokens, engine = diary_http
    # A personal persisted type does not establish that this OWNER's plans
    # belong to a personal profile. Keep all existing authorities unchanged.
    seed_plan(engine, owner='diary-legacy-owner')
    seed_plan(engine, owner='diary-legacy-owner', client_owner='diary-other')
    url = '/api/usuario/diario/'+local_today().isoformat()
    for response in (client.get(url,headers=tokens['diary-legacy-owner']),
            client.patch(url,headers=tokens['diary-legacy-owner'],json={
                'operation':'water','expected_version':0,'water_ml':100})):
        assert response.status_code == 409
        assert response.json()['detail']['code'] == 'diary_context_requires_review'
    exported = client.get('/api/usuario/privacidad/exportar',headers=tokens['diary-legacy-owner'])
    assert exported.json()['scope']['personal_space'] is False
    assert exported.json()['profiles']['records'] == []
    assert exported.json()['personal_diary']['records'] == []
    with Session(engine) as db:
        assert db.query(PersonalDiaryDay).count() == 0


@pytest.mark.parametrize('change', ['inactive','deleted','revoked','role_owner'])
def test_persisted_identity_changes_take_effect(diary_http, change):
    from web.database.models import Usuario, UserRole
    from web.services.personal_diary_service import local_today
    client, tokens, engine = diary_http
    with Session(engine) as db:
        user = db.get(Usuario,'diary-member')
        if change == 'inactive': user.activo = False
        elif change == 'deleted': user.deleted_at = datetime.now(timezone.utc)
        elif change == 'revoked': user.session_version += 1
        else: user.role = UserRole.OWNER
        db.commit()
    assert client.get('/api/usuario/diario/'+local_today().isoformat(), headers=tokens['diary-member']).status_code in {401,403}


def test_registration_creates_viewer_and_its_own_persisted_diary(diary_http, monkeypatch):
    from web.database.models import Usuario, UserRole
    from web.services import email_service
    from web.services.personal_diary_service import local_today
    client, _, engine = diary_http
    monkeypatch.setattr(email_service, 'send_welcome', lambda *args: False)
    registered = client.post('/api/auth/registro', json={'email':'new-diary@example.invalid',
        'nombre':'Synthetic', 'password':'SyntheticDiaryPassword123', 'tipo':'usuario'})
    assert registered.status_code == 200, registered.text
    token = {'Authorization':'Bearer '+registered.json()['token']}
    me = client.get('/api/auth/me', headers=token)
    assert me.status_code == 200
    with Session(engine) as db:
        assert db.get(Usuario,me.json()['id']).role == UserRole.VIEWER
    assert client.patch('/api/usuario/diario/'+local_today().isoformat(), headers=token,
        json={'operation':'water','expected_version':0,'water_ml':500}).status_code == 200


@pytest.mark.parametrize('operation', [
    {'operation':'water','expected_version':0,'water_ml':20001},
    {'operation':'water','expected_version':0,'water_ml':100,'user_id':'diary-other'},
    {'operation':'water','expected_version':0,'water_ml':100,'gym_id':'diary-owner'},
    {'operation':'meal','expected_version':0,'source_plan_id':2147483648,'meal':'desayuno','selections':{}},
    {'operation':'meal','expected_version':0,'source_plan_id':1,'meal':'desayuno','selections':{},'foods':[]},
])
def test_http_rejects_mass_assignment_and_invalid_values(diary_http, operation):
    from web.services.personal_diary_service import local_today
    client, tokens, _ = diary_http
    response = client.patch('/api/usuario/diario/'+local_today().isoformat(), headers=tokens['diary-person'], json=operation)
    assert response.status_code == 422


def test_dates_and_calendar_are_strict_and_bounded(diary_http):
    from web.services.personal_diary_service import local_today
    client, tokens, _ = diary_http
    today = local_today()
    headers = tokens['diary-person']
    assert client.get('/api/usuario/diario/2032-2-1', headers=headers).status_code == 422
    future = client.patch('/api/usuario/diario/'+(today+timedelta(days=1)).isoformat(), headers=headers,
        json={'operation':'water','expected_version':0,'water_ml':100})
    assert future.status_code == 422
    assert client.get('/api/usuario/diario', headers=headers,
        params={'start':(today-timedelta(days=62)).isoformat(),'end':today.isoformat()}).status_code == 422
    response = client.get('/api/usuario/diario', headers=headers,
        params={'start':(today-timedelta(days=61)).isoformat(),'end':today.isoformat()})
    assert response.status_code == 200
    assert len(response.json()['days']) == 62 and all(day['version']==0 for day in response.json()['days'])


@pytest.mark.parametrize('after_commit', [False, True])
def test_failed_or_unacknowledged_commit_never_reports_saved(diary_http, monkeypatch, caplog, after_commit):
    from sqlalchemy.exc import StatementError
    from web.services.personal_diary_service import local_today
    client, tokens, _ = diary_http
    url = '/api/usuario/diario/'+local_today().isoformat()
    original = Session.commit
    private = 'synthetic-sensitive-sql-parameter'
    def failed(db):
        if after_commit:
            original(db)
        raise StatementError('Synthetic failure','UPDATE private SET note=:note',{'note':private},RuntimeError(private))
    with monkeypatch.context() as patcher:
        patcher.setattr(Session,'commit',failed)
        response = client.patch(url, headers=tokens['diary-person'], json={'operation':'water','expected_version':0,'water_ml':999})
    assert response.status_code == 503
    assert private not in response.text+caplog.text
    read = client.get(url, headers=tokens['diary-person']).json()
    assert read['version'] == (1 if after_commit else 0)
    assert read['water_ml'] == (999 if after_commit else 0)


def test_export_diary_keyset_is_owned_ordered_and_complete(diary_http):
    from web.services.personal_diary_service import local_today
    client, tokens, _ = diary_http
    today = local_today()
    expected = []
    for offset in (3,2,1):
        day = (today-timedelta(days=offset)).isoformat()
        expected.append(day)
        assert client.patch('/api/usuario/diario/'+day, headers=tokens['diary-person'],
            json={'operation':'water','expected_version':0,'water_ml':offset*100}).status_code == 200
    seen, after = [], None
    for _ in range(3):
        params = {'limit':1}
        if after is not None: params['after_diary'] = after
        response = client.get('/api/usuario/privacidad/exportar', headers=tokens['diary-person'], params=params)
        assert response.status_code == 200, response.text
        page = response.json()['personal_diary']
        seen.extend(row['local_date'] for row in page['records'])
        after = page['next_after']
    assert seen == expected and after is None
