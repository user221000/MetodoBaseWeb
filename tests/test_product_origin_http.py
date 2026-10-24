"""Both real factories on38; no mail/provider transport outside local doubles."""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from tests import integration_client_link_http as original
from tests import product38_fixtures as f
from web.database.models import ProductAnalyticsFact as Fact
from web.database.repository import registrar_plan

origin38_engine = f.origin38_engine
link_db = f.link_db
case = f.case
http = original.http


def declaration(case, value, version):
    return case['client_http'].post('/api/analytics/procedencia', params={'context': 'gym', 'client': case['client']},
        headers=case['headers']['gym'], json={'origin': value, 'expected_version': version})


def test_provenance_http_strict_shape_foreign_and_cas_without_private_reflection(http):
    assert declaration(http, 'demo', 0).status_code == 200
    replay = declaration(http, 'customer', 0)
    assert replay.status_code == 409
    raw = http['client_http']
    assert raw.get('/api/analytics/procedencia', params={'context': 'gym', 'client': http['otherclient']},
                   headers=http['headers']['gym']).status_code == 404
    for body in ({'origin': 'demo', 'expected_version': True},
                 {'origin': 'customer', 'expected_version': 1, 'email': 'secret@example.invalid'},
                 {'origin': 'arbitrary-private-marker', 'expected_version': 1}):
        response = raw.post('/api/analytics/procedencia', params={'context': 'gym', 'client': http['client']},
                            headers=http['headers']['gym'], json=body)
        assert response.status_code == 422 and 'secret@example.invalid' not in response.text and 'arbitrary-private-marker' not in response.text
    value = raw.get('/api/analytics/producto/v2', params={'context': 'gym'}, headers=http['headers']['gym'])
    assert value.status_code == 200 and value.json()['baseline']['status'] == 'not_observed'
    assert http['client'] not in value.text and http['gym'] not in value.text


def test_real_accept_publish_and_first_complete_response_are_durable_idempotent(http):
    raw = http['client_http']
    assert declaration(http, 'demo', 0).status_code == 200
    issued, token = original.issued(http)
    accepted = raw.post('/api/usuario/vinculaciones/aceptar', headers=http['headers']['person'],
        json={'token': token, 'expected_version': issued['version'], 'confirm': True})
    assert accepted.status_code == 200
    link = accepted.json()['link_id']
    plan_json = json.dumps({meal: {'kcal_objetivo': 100, 'kcal_real': 100, 'alimentos': {'synthetic': 50}}
                           for meal in ('desayuno', 'almuerzo', 'comida', 'cena')})
    with Session(http['app']) as db:
        plan = registrar_plan(db, http['gym'], http['client'], {'plan_json': plan_json}, return_id=True)
        db.commit()
    assert declaration(http, 'customer', 1).status_code == 200
    published = raw.post('/api/clientes/'+http['client']+'/vinculacion/'+link+'/publicaciones', headers=http['headers']['gym'],
        json={'plan_id': plan, 'expected_link_version': accepted.json()['version'], 'expected_publication_version': 0, 'expected_publication_id': None})
    assert published.status_code == 200, published.text
    publication = published.json()['publication_id']
    # Foreign access is denied and never creates an observed consultation.
    denied = raw.get('/api/usuario/vinculos/'+link+'/plan', headers=http['headers']['other'])
    assert denied.status_code == 404
    for _ in range(2):
        served = raw.get('/api/usuario/vinculos/'+link+'/plan', headers=http['headers']['person'])
        assert served.status_code == 200 and served.json()['publication']['id'] == publication
    with Session(http['admin']) as db:
        facts = db.scalars(select(Fact).where(Fact.owner_id == http['gym'])).all()
        observed = [row for row in facts if row.event_type == 'assigned_plan_http200']
        assert len(observed) == 1 and observed[0].origin == 'demo'
        assert [row.origin for row in facts if row.event_type == 'plan_assignment_published'] == ['demo']
        assert [row.origin for row in facts if row.event_type == 'client_link_accepted'] == ['demo']
    withdrawn = raw.request('DELETE', '/api/clientes/'+http['client']+'/vinculacion/'+link+'/publicaciones/'+publication,
        headers=http['headers']['gym'], json={'expected_version': published.json()['version']})
    assert withdrawn.status_code == 200
    empty = raw.get('/api/usuario/vinculos/'+link+'/plan', headers=http['headers']['person'])
    assert empty.status_code == 200 and empty.json()['publication'] is None
    with Session(http['admin']) as db:
        assert db.query(Fact).filter_by(owner_id=http['gym'], event_type='assigned_plan_http200').count() == 1
        assert db.scalar(select(Fact.origin).where(Fact.owner_id == http['gym'], Fact.event_type == 'plan_assignment_withdrawn')) == 'demo'


def test_v2_read_is_no_write_and_personal_origin_does_not_mark_gym(http):
    raw = http['client_http']
    changed = raw.post('/api/analytics/procedencia', params={'context': 'personal'}, headers=http['headers']['person'],
                      json={'origin': 'demo', 'expected_version': 0})
    assert changed.status_code == 200
    queries = []
    from sqlalchemy import event
    def observe(_c, _cursor, sql, _params, _ctx, _many): queries.append(sql.lower().lstrip())
    event.listen(http['app'], 'before_cursor_execute', observe)
    try:
        response = raw.get('/api/analytics/producto/v2', params={'context': 'personal'}, headers=http['headers']['person'])
    finally:
        event.remove(http['app'], 'before_cursor_execute', observe)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert not any(sql.split()[0] in ('insert', 'update', 'delete', 'create', 'alter') for sql in queries)
    owner = raw.get('/api/analytics/procedencia', params={'context': 'gym', 'client': http['client']}, headers=http['headers']['gym'])
    assert owner.json()['origin'] == 'unknown'
