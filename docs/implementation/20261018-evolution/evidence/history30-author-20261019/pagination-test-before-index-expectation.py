"""Personal history pages through both real factories and persisted auth, offline SQLite."""
from datetime import datetime
import importlib

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.fixture(params=['web.main_web', 'api.app'])
def history_http(request):
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Cliente, Usuario, UserRole
    app = importlib.import_module(request.param).create_app()
    engine = get_engine()
    pairs = {}
    with Session(engine) as db:
        for subject in ('history-person', 'history-other'):
            user = Usuario(id=subject, email=subject+'@example.invalid', password_hash='synthetic-unused',
                nombre='Synthetic', tipo='usuario', role=UserRole.VIEWER, activo=True)
            db.add(user)
            db.flush()
            db.add(Cliente(id_cliente=subject+'-profile', gym_id=subject, nombre='Synthetic'))
            db.commit()
            pairs[subject] = {'Authorization':'Bearer '+crear_access_token(identity_from_user(user, db))}
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/auth/me', headers=pairs['history-person']).json()['role'] == 'viewer'
        yield client, engine, pairs


def plans(engine, count, *, subject='history-person', profile=None, stamp=datetime(2026, 1, 2, 3, 4, 5)):
    from web.database.models import PlanGenerado
    with Session(engine) as db:
        rows = [PlanGenerado(gym_id=subject, id_cliente=profile or subject+'-profile',
            fecha_generacion=stamp, kcal_objetivo=1000+i) for i in range(count)]
        db.add_all(rows)
        db.flush()
        ids = [row.id for row in rows]
        if stamp is None:
            db.query(PlanGenerado).filter(PlanGenerado.id.in_(ids)).update({PlanGenerado.fecha_generacion:None}, synchronize_session=False)
        db.commit()
        return ids


def get(case, **params):
    return case[0].get('/api/usuario/historial', headers=case[2]['history-person'], params=params)


def test_default_history_is_bounded_to_50_from_1000_persisted_results(history_http):
    ids = plans(history_http[1], 1000)
    response = get(history_http)
    assert response.status_code == 200, response.text
    assert len(response.json()['planes']) == 50
    assert [p['id'] for p in response.json()['planes']] == list(reversed(ids))[:50]
    assert isinstance(response.json()['next_cursor'], str)


def test_ties_and_null_dates_are_complete_stable_and_exhaustible(history_http):
    newest = plans(history_http[1], 5)
    older = plans(history_http[1], 3, stamp=datetime(2025, 1, 1))
    undated = plans(history_http[1], 5, stamp=None)
    seen, cursor = [], None
    for _ in range(10):
        page = get(history_http, **({'limit':3, 'cursor':cursor} if cursor else {'limit':3}))
        assert page.status_code == 200, page.text
        body = page.json()
        seen += [row['id'] for row in body['planes']]
        cursor = body['next_cursor']
        if cursor is None:
            break
    assert cursor is None
    assert seen == newest[::-1]+older[::-1]+undated[::-1]
    assert len(seen) == len(set(seen)) == 13


def test_deletes_and_newer_inserts_between_pages_do_not_shift_the_position(history_http):
    from web.database.models import PlanGenerado
    ids = plans(history_http[1], 7)
    first = get(history_http, limit=3).json()
    # Delete the cursor row itself and another unseen row; the signed position is not a row lookup.
    with Session(history_http[1]) as db:
        for identity in (ids[4], ids[1]):
            db.get(PlanGenerado, identity).deleted_at = datetime(2026, 1, 3)
        db.commit()
    inserted = plans(history_http[1], 1, stamp=datetime(2027, 1, 1))[0]
    second = get(history_http, limit=3, cursor=first['next_cursor']).json()
    assert [p['id'] for p in second['planes']] == [ids[3], ids[2], ids[0]]
    assert second['next_cursor'] is None
    assert get(history_http).json()['planes'][0]['id'] == inserted


@pytest.mark.parametrize('limit', [1, 200])
def test_explicit_limits_remain_bounded(history_http, limit):
    plans(history_http[1], 205)
    body = get(history_http, limit=limit).json()
    assert len(body['planes']) == limit
    assert body['next_cursor']


@pytest.mark.parametrize('value', ['0', '201', '-1', 'true', '1.5', 'x'])
def test_invalid_limits_reject_without_materializing_a_page(history_http, value):
    assert get(history_http, limit=value).status_code == 422


@pytest.mark.parametrize('value', ['', 'not-a-cursor', 'x'*181, 'e30.sig', '<synthetic-private-marker>'])
def test_malformed_cursor_is_generic_and_never_echoed(history_http, value):
    response = get(history_http, cursor=value)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'history_cursor_invalid'
    if value:
        assert value not in response.text


def test_cursor_is_account_profile_bound_and_key_rotation_has_no_fallback(history_http, monkeypatch):
    from web.settings import get_settings
    plans(history_http[1], 2)
    cursor = get(history_http, limit=1).json()['next_cursor']
    foreign = history_http[0].get('/api/usuario/historial', headers=history_http[2]['history-other'], params={'cursor':cursor})
    assert foreign.status_code == 422
    monkeypatch.setattr(get_settings(), 'SECRET_KEY', 'synthetic-rotated-key-only')
    assert get(history_http, cursor=cursor).status_code == 422
    assert get(history_http).status_code == 200


def test_double_owner_soft_delete_and_existing_profile_boundary_are_preserved(history_http):
    from web.database.models import Cliente, PlanGenerado
    own = plans(history_http[1], 1)[0]
    plans(history_http[1], 1, subject='history-other')
    plans(history_http[1], 1, profile='history-other-profile')
    plans(history_http[1], 1, subject='history-other', profile='history-person-profile')
    deleted = plans(history_http[1], 1)[0]
    with Session(history_http[1]) as db:
        db.get(PlanGenerado, deleted).deleted_at = datetime(2026, 1, 3)
        db.query(Cliente).filter_by(id_cliente='history-person-profile').one().activo = False
        db.commit()
    assert [row['id'] for row in get(history_http).json()['planes']] == [own]
    with Session(history_http[1]) as db:
        db.query(Cliente).filter_by(id_cliente='history-person-profile').one().deleted_at = datetime(2026, 1, 3)
        db.add(Cliente(id_cliente='history-later-profile', gym_id='history-person', nombre='Synthetic'))
        db.commit()
    plans(history_http[1], 1, profile='history-later-profile')
    assert get(history_http).json() == {'planes':[], 'next_cursor':None}


def test_empty_history_and_missing_profile_remain_readonly_without_auto_creation(history_http):
    from web.database.models import Cliente
    assert get(history_http).json() == {'planes':[], 'next_cursor':None}
    with Session(history_http[1]) as db:
        db.query(Cliente).filter_by(gym_id='history-person').delete()
        db.commit()
    assert get(history_http).json() == {'planes':[], 'next_cursor':None}
    assert get(history_http,cursor='synthetic.invalid').status_code == 422
    with Session(history_http[1]) as db:
        assert db.query(Cliente).filter_by(gym_id='history-person').count() == 0


def test_auth_and_revoked_member_never_adopt_the_professional_portfolio(history_http):
    from web.auth import crear_access_token, identity_from_user
    from web.database.models import Cliente, Usuario, UserRole
    with Session(history_http[1]) as db:
        owner = Usuario(id='history-team', email='history-team@example.invalid', nombre='Synthetic', password_hash='unused', tipo='gym', role=UserRole.OWNER)
        db.add(owner); db.flush()
        member = db.get(Usuario, 'history-person')
        member.tipo = 'gym'; member.team_gym_id = owner.id
        db.add(Cliente(id_cliente='history-team-profile',gym_id=owner.id,nombre='Synthetic'))
        db.commit()
        token = {'Authorization':'Bearer '+crear_access_token(identity_from_user(member, db))}
        owner_token = {'Authorization':'Bearer '+crear_access_token(identity_from_user(owner, db))}
    own = plans(history_http[1], 2)
    plans(history_http[1], 1, subject='history-team')
    path = '/api/usuario/historial'
    assert history_http[0].get(path).status_code == 401
    assert history_http[0].get(path,headers=owner_token).status_code == 403
    response = history_http[0].get(path,headers=token,params={'limit':1})
    assert response.status_code == 200
    assert response.json()['planes'][0]['id'] == own[-1]
    with Session(history_http[1]) as db:
        member = db.get(Usuario,'history-person')
        member.tipo = 'usuario'; member.team_gym_id = None; member.session_version += 1
        db.commit()
        current = {'Authorization':'Bearer '+crear_access_token(identity_from_user(member,db))}
    assert history_http[0].get(path,headers=token,params={'cursor':response.json()['next_cursor']}).status_code == 401
    assert [row['id'] for row in history_http[0].get(path,headers=current).json()['planes']] == own[::-1]


def test_query_is_readonly_limit_plus_one_without_count_or_plan_json(history_http):
    statements, writes = [], []
    plans(history_http[1], 1000)
    def observed(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','ALTER')):
            writes.append(statement)
        if 'FROM planes_generados JOIN clientes' in statement:
            statements.append((statement, parameters))
    event.listen(history_http[1], 'before_cursor_execute', observed)
    try:
        response = get(history_http)
    finally:
        event.remove(history_http[1], 'before_cursor_execute', observed)
    assert response.status_code == 200 and len(response.json()['planes']) == 50
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert writes == [] and len(statements) == 1
    statement, parameters = statements[0]
    assert 'LIMIT' in statement and 51 in parameters
    assert 'COUNT(' not in statement.upper() and 'plan_json' not in statement
    with history_http[1].connect() as connection:
        explain = [list(row) for row in connection.exec_driver_sql('EXPLAIN QUERY PLAN '+statement, parameters)]
    assert any('ix_planes_gym_fecha' in str(row) for row in explain), explain
    _write_explain_if_requested(history_http[0].app.title, {
        'scope':'SQLite read-only EXPLAIN of 51 summary candidates from 1000 rows; no PostgreSQL performance claim',
        'sql':statement,'parameters':list(parameters),'plan':explain})


def _write_explain_if_requested(title, data):
    """No default writes. Explicit new outputs must stay in a caller-owned Temp directory."""
    import json
    import os
    from pathlib import Path
    import tempfile
    configured = os.environ.get('METODOBASE_HISTORY_EXPLAIN_OUTPUT')
    if not configured:
        return
    directory = Path(configured)
    temporary = Path(tempfile.gettempdir()).resolve()
    resolved = directory.resolve()
    if not directory.is_absolute() or resolved == temporary or not resolved.is_relative_to(temporary):
        raise ValueError('EXPLAIN output requires an explicit isolated Temp subdirectory')
    resolved.mkdir(parents=True, exist_ok=True)
    with (resolved/('explain-'+title.replace(' ','_')+'.json')).open('x', encoding='utf8') as output:
        output.write(json.dumps(data,indent=2)+'\n')


def test_each_factory_has_one_history_get_operation_and_no_added_personal_mutations(history_http):
    # The pinned FastAPI version stores included routers lazily; inspect effective paths.
    from fastapi.routing import _iter_routes_with_context
    routes = [route for route, context in _iter_routes_with_context(history_http[0].app.routes)
        if (context.path if context else getattr(route,'path',None)) == '/api/usuario/historial']
    assert len(routes) == 1 and routes[0].methods == {'GET'}
    schema = history_http[0].get('/openapi.json').json()
    operations = [operation['operationId'] for methods in schema['paths'].values() for method,operation in methods.items() if method in {'get','post','put','patch','delete'}]
    assert len(operations) == len(set(operations))
    assert history_http[0].post('/api/usuario/historial',headers=history_http[2]['history-person']).status_code == 405
