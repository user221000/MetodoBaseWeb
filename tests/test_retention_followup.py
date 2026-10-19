"""R23: real factories, persisted identities and bounded, read-only facts."""
from datetime import datetime, timedelta, timezone
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

PATH = '/api/estadisticas/seguimiento'


@pytest.fixture(params=['web.main_web', 'api.app'])
def followup(request, test_gym_user):
    from web.database.engine import get_engine
    with TestClient(importlib.import_module(request.param).create_app(), raise_server_exceptions=False) as client:
        yield client, get_engine(), test_gym_user


def read(case, **params):
    return case[0].get(PATH, headers=case[2]['auth_headers'], params=params)


def test_empty_is_confirmed_and_does_not_invent_payments_or_assignments(followup):
    response = read(followup)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['items'] == [] and body['has_more'] is False
    assert body['payment_evidence'] == 'unavailable'
    assert body['metrics']['plans_saved'] == 0
    assert body['responsibility'] == 'not_recorded'


def seed(case, *, identity='followup-client', age=None, end=None, null_plan=False):
    from web.database.models import Cliente, PlanGenerado
    with Session(case[1]) as db:
        db.add(Cliente(gym_id=case[2]['id'], id_cliente=identity, nombre='Synthetic '+identity,
                       email='never-in-dto@example.invalid', notas='PRIVATE-NOTES',
                       fecha_fin_suscripcion=end))
        db.flush()
        if age is not None or null_plan:
            plan = PlanGenerado(gym_id=case[2]['id'], id_cliente=identity,
                fecha_generacion=datetime.now(timezone.utc)-timedelta(days=age or 0), plan_json='PRIVATE-PLAN')
            db.add(plan); db.flush()
            if null_plan:
                plan.fecha_generacion = None
        db.commit()


def test_saved_plan_and_recorded_membership_are_separate_facts(followup):
    seed(followup, age=1, end=datetime.now()-timedelta(days=2))
    response = read(followup)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['items'][0]['causes'] == ['membership_date_passed']
    assert body['items'][0]['responsible'] is None
    assert body['metrics']['plans_saved'] == 1
    assert body['metrics']['generation_operations_completed'] == 0
    assert body['metrics']['pdf_metadata_ready'] == 0
    assert all(value not in response.text for value in ['never-in-dto', 'PRIVATE-NOTES', 'PRIVATE-PLAN', 'ruta_pdf', 'request_key'])


def test_priority_ties_and_null_dates_have_a_stable_explicit_order(followup):
    seed(followup, identity='a-never')
    seed(followup, identity='b-never')
    seed(followup, identity='c-outside', age=31)
    seed(followup, identity='d-unknown', null_plan=True)
    seed(followup, identity='e-date', age=1, end=datetime.now()-timedelta(days=1))
    seed(followup, identity='f-recent', age=1)
    body = read(followup).json()
    assert [row['id_cliente'] for row in body['items']] == ['a-never','b-never','c-outside','d-unknown','e-date']
    assert [row['priority'] for row in body['items']] == [1,1,2,3,4]
    assert body['items'][3]['causes'] == ['plan_date_missing']
    assert body['items'][3]['last_plan_at'] is None
    assert body['metrics']['plans_saved'] == 2  # NULL and outside-window records are not invented as current.
    assert body['window_days'] == 30


@pytest.mark.parametrize('value', ['0','101','true','1.5','x'])
def test_invalid_limits_fail_before_read(followup, value, monkeypatch):
    import web.routes.followup as route
    monkeypatch.setattr(route, 'get_followup', lambda *args: pytest.fail('must not read'))
    assert read(followup, limit=value).status_code == 422


def test_limit_plus_one_is_sql_bounded_and_get_never_writes(followup):
    from web.database.models import Cliente
    with Session(followup[1]) as db:
        db.add_all([Cliente(id_cliente=f'bounded-{i:03d}',gym_id=followup[2]['id'],nombre='Synthetic') for i in range(103)])
        db.commit()
    statements = []
    def observe(conn, cursor, statement, parameters, context, many):
        statements.append((statement, parameters))
    event.listen(followup[1], 'before_cursor_execute', observe)
    try:
        first = read(followup).json()
        maximum = read(followup, limit=100).json()
    finally:
        event.remove(followup[1], 'before_cursor_execute', observe)
    assert len(first['items']) == 50 and first['has_more'] is True
    assert len(maximum['items']) == 100 and maximum['has_more'] is True
    assert not [s for s,_ in statements if s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','ALTER'))]
    queries = [(s,p) for s,p in statements if 'AS priority' in s]
    assert len(queries) == 2
    assert queries[0][1][-2:] == (51,0) and queries[1][1][-2:] == (101,0)
    assert all('plan_json' not in s and 'ruta_pdf' not in s and 'email' not in s for s,_ in queries)


def test_double_owner_deleted_and_inactive_rows_do_not_contribute(followup):
    from web.database.models import Cliente, PlanGenerado, Usuario, UserRole
    seed(followup, identity='own')
    seed(followup, identity='deleted', age=1)
    seed(followup, identity='inactive', age=1)
    with Session(followup[1]) as db:
        db.add(Usuario(id='foreign-owner',email='foreign@example.invalid',password_hash='unused',nombre='Foreign',tipo='gym',role=UserRole.OWNER))
        db.flush()
        db.add(Cliente(id_cliente='foreign-client',gym_id='foreign-owner',nombre='PRIVATE-FOREIGN'))
        db.flush()
        db.add_all([
            PlanGenerado(id_cliente='own',gym_id='foreign-owner'),
            PlanGenerado(id_cliente='foreign-client',gym_id=followup[2]['id']),
            PlanGenerado(id_cliente='foreign-client',gym_id='foreign-owner'),
        ])
        db.query(Cliente).filter_by(id_cliente='deleted').one().deleted_at=datetime.now(timezone.utc)
        db.query(Cliente).filter_by(id_cliente='inactive').one().activo=False
        db.commit()
    response = read(followup)
    body = response.json()
    assert [row['id_cliente'] for row in body['items']] == ['own']
    assert body['items'][0]['causes'] == ['no_saved_plan']
    assert body['metrics']['plans_saved'] == 0
    assert 'PRIVATE-FOREIGN' not in response.text


def test_metrics_count_persisted_completed_and_ready_states_separately(followup):
    from web.database.models import GymGenerationReservation, PlanGenerado, StoredObject
    seed(followup, age=1)
    now=datetime.now(timezone.utc)
    with Session(followup[1]) as db:
        plan=db.query(PlanGenerado).one()
        db.add(GymGenerationReservation(gym_id=followup[2]['id'],client_id='followup-client',request_key='synthetic-only',
            request_hash='a'*64,period=now.strftime('%Y-%m'),local_date=now.date(),timezone='America/Mexico_City',
            catalog_plan='free',status='completed',persisted_at=now,plan_id=plan.id,result_json='{}'))
        obj=StoredObject(id='b'*32,gym_id=followup[2]['id'],kind='plan_pdf',key='synthetic-pdf',
            content_type='application/pdf',byte_size=10,sha256='c'*64,storage_backend='local',status='pending')
        db.add(obj);db.flush();plan.pdf_object_id=obj.id;db.commit()
    assert read(followup).json()['metrics'] == {'plans_saved':1,'generation_operations_completed':1,'pdf_metadata_ready':0}
    with Session(followup[1]) as db:
        db.get(StoredObject,'b'*32).status='ready';db.commit()
    assert read(followup).json()['metrics']['pdf_metadata_ready'] == 1
    # This is descriptor state only: no file/object bytes are read or claimed delivered.


def test_real_recorded_date_update_changes_followup_but_does_not_claim_payment(followup):
    seed(followup, age=1, end=datetime.now()-timedelta(days=1))
    assert read(followup).json()['items'][0]['causes'] == ['membership_date_passed']
    # Shared repository mutation is reached through the real web client adapter;
    # API factory's independent CRUD has a different contract, not silently composed.
    from web.main_web import create_app
    with TestClient(create_app(),raise_server_exceptions=False) as web:
        result=web.put('/api/clientes/followup-client',headers=followup[2]['auth_headers'],
            json={'fecha_fin_suscripcion':(datetime.now()+timedelta(days=10)).isoformat()})
        assert result.status_code==200, result.text
    body=read(followup).json()
    assert body['items'] == [] and body['payment_evidence']=='unavailable'


@pytest.mark.parametrize('role', ['owner','admin','nutriologo','viewer'])
def test_rbac_uses_persisted_identity_and_member_revocation(followup, role):
    from web.auth import crear_access_token, identity_from_user
    from web.database.models import Usuario, UserRole
    with Session(followup[1]) as db:
        member=Usuario(id='member',email='member@example.invalid',nombre='Synthetic',password_hash='unused',
            tipo='gym' if role=='owner' else 'usuario',role=UserRole(role),
            team_gym_id=None if role=='owner' else followup[2]['id'])
        db.add(member);db.commit()
        headers={'Authorization':'Bearer '+crear_access_token(identity_from_user(member,db))}
    response=followup[0].get(PATH,headers=headers)
    assert response.status_code==(200 if role in ('owner','admin') else 403)
    if role!='owner':
        with Session(followup[1]) as db:
            user=db.get(Usuario,'member');user.team_gym_id=None;user.role=UserRole.VIEWER;user.session_version+=1;db.commit()
        assert followup[0].get(PATH,headers=headers).status_code==401


def test_auth_ambiguous_owner_and_failure_do_not_return_false_empty(followup, monkeypatch, caplog):
    from web.auth import crear_access_token, identity_from_user
    from web.database.models import Usuario, UserRole
    assert followup[0].get(PATH).status_code==401
    with Session(followup[1]) as db:
        user=Usuario(id='ambiguous',email='ambiguous@example.invalid',nombre='Synthetic',password_hash='unused',tipo='usuario',role=UserRole.OWNER)
        db.add(user);db.commit();headers={'Authorization':'Bearer '+crear_access_token(identity_from_user(user,db))}
    assert followup[0].get(PATH,headers=headers).status_code==403
    import web.routes.followup as route
    def fail(*args): raise RuntimeError('PRIVATE-SQL-PARAMETERS')
    monkeypatch.setattr(route,'get_followup',fail)
    response=read(followup)
    assert response.status_code==503 and response.json()['detail']['code']=='followup_unavailable'
    assert 'PRIVATE-SQL' not in response.text+caplog.text and 'items' not in response.json()
    assert response.headers['Referrer-Policy']=='no-referrer'


def test_new_route_is_composed_exactly_once_and_preserves_adjacent_routes(followup):
    from web.routes.followup import router
    # Current FastAPI composes _IncludedRouter lazily instead of expanding
    # paths onto app.routes. Count its original router rather than a false zero.
    assert sum(getattr(route,'original_router',None) is router for route in followup[0].app.routes)==1
    assert set(followup[0].app.openapi()['paths'][PATH])=={'get'}
    assert followup[0].post(PATH,headers=followup[2]['auth_headers']).status_code==405
    assert followup[0].get(PATH+'-other',headers=followup[2]['auth_headers']).status_code==404


def test_dashboard_mount_renders_the_actual_component_without_jinja_css_collision(followup):
    response=followup[0].get('/dashboard')
    assert response.status_code==200
    assert 'id="followup-section"' in response.text
    assert 'dashboard-seguimiento.js' in response.text
    assert 'Pagos: no disponibles' in response.text
