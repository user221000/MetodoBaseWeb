"""Independent SaaS35 controls; all accounts and declarations are synthetic."""
import copy
import importlib
import json
import uuid

import pytest
from sqlalchemy.orm import Session

from tests.test_nutrition35_http import VALID, followup_db, followup_http, personal35_http
from tests.followup34_http import PASSWORD
from tests.test_nutrition35_profile_contract import declaration
from web.database.models import Cliente, GenerationReservation, GymGenerationReservation, PlanGenerado, StoredObject, Usuario, UserRole, UserSubscription
from web.services.nutrition_profiles import encode_declaration


def _private(response):
    assert 'no-store' in response.headers.get('cache-control', '').lower().split(','), 'private cache directive'
    assert response.headers.get('referrer-policy') == 'no-referrer', 'private referrer policy'


def _put(c, **body):
    return c['raw'].put('/api/clientes/'+c['profile'], json=body)


def _new(c, key=None):
    return c['raw'].post('/api/generar-plan', json={'id_cliente':c['profile'], 'plan_numero':1, 'tipo_plan':'menu_fijo'}, headers={'Idempotency-Key':key or str(uuid.uuid4())})


def _state(c):
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'], id_cliente=c['profile']).one()
        return (row.nutrition_restrictions_json, row.alimentos_excluidos, row.peso_kg,
                db.query(GymGenerationReservation).filter_by(gym_id=c['user']).count(),
                db.query(PlanGenerado).filter_by(gym_id=c['user']).count(),
                db.query(StoredObject).filter_by(gym_id=c['user']).count())


def _individual(c):
    email=uuid.uuid4().hex+'@example.invalid'
    raw=c['raw']
    assert raw.post('/api/auth/registro', json={'email':email,'password':PASSWORD,'nombre':'Synthetic personal control','tipo':'usuario'}).status_code == 200
    response=raw.post('/api/auth/login',json={'email':email,'password':PASSWORD})
    assert response.status_code == 200
    raw.headers['Authorization']='Bearer '+response.json()['token']
    me=raw.get('/api/auth/me')
    assert me.status_code == 200
    return raw, me.json()['id']


def test_foreign_client_and_no_principal_cannot_read_edit_generate_or_export_portfolio(followup_http):
    c=followup_http
    foreign, client_id=str(uuid.uuid4()),str(uuid.uuid4())
    with Session(c['admin']) as db:
        db.add(Usuario(id=foreign,email=uuid.uuid4().hex+'@example.invalid',nombre='Synthetic foreign owner',tipo='gym',role=UserRole.OWNER,password_hash='synthetic'))
        db.flush()
        db.add(Cliente(gym_id=foreign,id_cliente=client_id,nombre='Synthetic foreign client',nutrition_restrictions_json=encode_declaration(declaration(reported=True))))
        db.commit()
    for response in (
        c['raw'].get('/api/clientes/'+client_id),
        c['raw'].put('/api/clientes/'+client_id,json={'restricciones_nutricionales':declaration()}),
        c['raw'].post('/api/generar-plan',json={'id_cliente':client_id,'plan_numero':1,'tipo_plan':'menu_fijo'},headers={'Idempotency-Key':str(uuid.uuid4())}),
    ):
        assert response.status_code in (403,404), 'foreign authority rejected'
        _private(response)
        assert 'allergies' not in response.text, 'no foreign declaration'
    exported=c['raw'].get('/api/usuario/privacidad/exportar')
    assert exported.status_code == 200
    assert exported.json()['profiles']['records'] == [], 'professional portfolio excluded'
    auth=c['raw'].headers.pop('Authorization')
    try:
        anonymous=c['raw'].get('/api/clientes/'+c['profile'])
        assert anonymous.status_code in (401,403)
        _private(anonymous)
    finally:
        c['raw'].headers['Authorization']=auth
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(id_cliente=client_id,gym_id=foreign).one()
        assert row.nutrition_restrictions_json == encode_declaration(declaration(reported=True))
        assert db.query(GymGenerationReservation).filter_by(gym_id=c['user']).count() == 0


def test_closed_input_and_nonfinite_values_are_rejected_without_partial_edit(followup_http):
    c=followup_http
    assert _put(c, **VALID, restricciones_nutricionales=declaration()).status_code == 200
    before=_state(c)
    invalid=[]
    for change in ({'version':True},{'professional_review_requested':0},{'approval':'SYNTHETIC_PRIVATE_SENTINEL'},{'allergies':{'version':1,'status':'reported','foods':['SYNTHETIC_PRIVATE_SENTINEL'],'other_reported':False}}):
        invalid.append({'peso_kg':77,'restricciones_nutricionales':{**declaration(),**change}})
    for raw_number in ('NaN','Infinity','1e309'):
        response=c['raw'].put('/api/clientes/'+c['profile'],content='{"peso_kg":'+raw_number+',"restricciones_nutricionales":'+json.dumps(declaration())+'}',headers={'Content-Type':'application/json'})
        assert response.status_code == 422, 'nonfinite input rejected'
        _private(response)
        assert response.json()['detail']['code'] == 'nutrition_profile_invalid_input'
    for body in invalid:
        response=_put(c,**body)
        assert response.status_code == 422
        assert response.json()['detail']['code'] == 'nutrition_profile_invalid_input'
        assert 'SYNTHETIC_PRIVATE_SENTINEL' not in response.text
        _private(response)
    assert _state(c) == before, 'all invalid edits atomic'


@pytest.mark.parametrize('variant',['duplicate_nested_key','nonfinite_persisted','null_persisted'])
def test_corrupt_persisted_declaration_stops_reads_and_generation_before_quota(followup_http,variant,monkeypatch):
    c=followup_http
    assert _put(c,**VALID).status_code == 200
    raw=encode_declaration(declaration())
    if variant == 'duplicate_nested_key':
        raw=raw.replace('"status":"not_reported"','"status":"reported","status":"not_reported"')
    elif variant == 'nonfinite_persisted':
        raw=raw.replace('"version":1','"version":NaN',1)
    else:
        raw='null'
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        row.nutrition_restrictions_json=raw
        db.commit()
    before=_state(c)
    def no_cpu(*args,**kwargs):
        pytest.fail('corrupt persisted profile reached worker')
    module=importlib.import_module('api.routes.planes' if c['factory_name']=='api.app' else 'web.routes.planes')
    monkeypatch.setattr(module,'_generar_plan_sync',no_cpu)
    for response in (c['raw'].get('/api/clientes/'+c['profile']), _new(c)):
        assert response.status_code == 422
        assert response.json()['detail']['code'] == 'nutrition_restrictions_invalid'
        _private(response)
    assert _state(c) == before


def test_malformed_existing_exclusions_have_same_private_failclosed_read_boundary(followup_http):
    c=followup_http
    assert _put(c,**VALID).status_code == 200
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        row.alimentos_excluidos='["SYNTHETIC_PRIVATE_SENTINEL"'
        db.commit()
    before=_state(c)
    response=c['raw'].get('/api/clientes/'+c['profile'])
    assert response.status_code == 422, 'corrupt exclusions use bounded nutrition domain error'
    _private(response)
    assert 'SYNTHETIC_PRIVATE_SENTINEL' not in response.text
    assert _state(c)==before


def test_completed_retry_remains_exact_after_profile_change_without_new_consumption(followup_http,monkeypatch):
    c=followup_http
    assert _put(c,**VALID,restricciones_nutricionales=declaration()).status_code == 200
    key=str(uuid.uuid4())
    first=_new(c,key)
    assert first.status_code==200, 'real plan/PDF publication'
    plan_id=first.json()['plan_id']
    assert _put(c,restricciones_nutricionales=declaration(review=True)).status_code==200
    before=_state(c)
    assert before[3:] == (1,1,1)
    module=importlib.import_module('api.routes.planes' if c['factory_name']=='api.app' else 'web.routes.planes')
    def forbidden(*args,**kwargs):
        pytest.fail('replay reached worker')
    monkeypatch.setattr(module,'_generar_plan_sync',forbidden)
    replay=_new(c,key)
    assert replay.status_code == 200 and replay.json()==first.json()
    assert replay.json()['plan_id']==plan_id
    denied=_new(c)
    assert denied.status_code==422
    assert denied.json()['detail']['code']=='nutrition_professional_review_required'
    assert _state(c)==before, 'no new spend, object or plan'


def test_worker_invalid_storage_after_reservation_compensates_before_builder(followup_http,monkeypatch):
    c=followup_http
    assert _put(c,**VALID).status_code==200
    module=importlib.import_module('api.routes.planes' if c['factory_name']=='api.app' else 'web.routes.planes')
    original=module._generar_plan_sync
    def changed(*args,**kwargs):
        with Session(c['admin']) as db:
            row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
            row.nutrition_restrictions_json='null'
            db.commit()
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'_generar_plan_sync',changed)
    def forbidden(*args,**kwargs):
        pytest.fail('invalid storage reached CPU builder')
    monkeypatch.setattr(importlib.import_module('web.dependencies'),'build_cliente_from_dict',forbidden)
    response=_new(c)
    assert response.status_code==422
    _private(response)
    with Session(c['admin']) as db:
        reservation=db.query(GymGenerationReservation).filter_by(gym_id=c['user']).one()
        assert reservation.status=='released' and reservation.persisted_at is None and reservation.plan_id is None
        assert db.query(PlanGenerado).filter_by(gym_id=c['user']).count()==0
        assert db.query(StoredObject).filter_by(gym_id=c['user']).count()==0


def test_personal_export_contains_only_own_exact_declaration_and_null_edits_preserve(personal35_http):
    c=personal35_http
    raw,user=_individual(c)
    payload=declaration(reported=True)
    payload['allergies']['foods']=['huevo','huevo']
    assert raw.put('/api/usuario/perfil',json={**VALID,'restricciones_nutricionales':payload}).status_code==200
    expected=copy.deepcopy(payload)
    expected['allergies']['foods']=['huevo']
    assert raw.put('/api/usuario/perfil',json={'peso_kg':76}).status_code==200
    assert raw.put('/api/usuario/perfil',json={'restricciones_nutricionales':None}).status_code==200
    profile=raw.get('/api/usuario/perfil')
    assert profile.status_code==200 and profile.json()['restricciones_nutricionales']==expected
    exported=raw.get('/api/usuario/privacidad/exportar')
    assert exported.status_code==200
    _private(exported)
    rows=exported.json()['profiles']['records']
    assert len(rows)==1
    assert json.loads(rows[0]['nutrition_restrictions_json'])==expected
    assert rows[0]['id_cliente']!=c['profile']
    denied=raw.get('/api/clientes/'+c['profile'])
    assert denied.status_code in (403,404)
    with Session(c['admin']) as db:
        assert db.query(GenerationReservation).filter_by(user_id=user).count()==0
        sub=db.query(UserSubscription).filter_by(user_id=user).one_or_none()
        assert sub is None or sub.planes_usados_mes==0


def test_personal_complete_replay_keeps_old_id_and_new_requests_block(personal35_http,monkeypatch):
    c=personal35_http
    raw,user=_individual(c)
    assert raw.put('/api/usuario/perfil',json={**VALID,'restricciones_nutricionales':declaration()}).status_code==200
    key=str(uuid.uuid4())
    first=raw.post('/api/usuario/generar-plan',headers={'Idempotency-Key':key})
    assert first.status_code==200
    assert raw.put('/api/usuario/perfil',json={'restricciones_nutricionales':declaration(review=True)}).status_code==200
    def forbidden(*args,**kwargs):
        pytest.fail('personal replay reached worker')
    monkeypatch.setattr(importlib.import_module('web.routes.planes'),'_generar_plan_sync',forbidden)
    replay=raw.post('/api/usuario/generar-plan',headers={'Idempotency-Key':key})
    assert replay.status_code==200 and replay.json()==first.json()
    blocked=raw.post('/api/usuario/generar-plan',headers={'Idempotency-Key':str(uuid.uuid4())})
    assert blocked.status_code==422
    _private(blocked)
    with Session(c['admin']) as db:
        reservations=db.query(GenerationReservation).filter_by(user_id=user).all()
        assert len(reservations)==1 and reservations[0].status=='completed'
        assert reservations[0].plan_id==first.json()['plan_id']
        assert db.query(PlanGenerado).filter_by(gym_id=user).count()==1
        assert db.query(UserSubscription).filter_by(user_id=user).one().planes_usados_mes==1
