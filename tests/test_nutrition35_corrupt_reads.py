"""Strict nutrition35 serialization of corrupt legacy exclusions, both factories."""
import uuid

import pytest
from sqlalchemy.orm import Session

from tests.test_nutrition35_http import VALID, followup_db, followup_http
from tests.test_nutrition35_profile_contract import declaration
from web.database.models import Cliente, GymGenerationReservation, PlanGenerado, StoredObject


def _private(response):
    assert 'no-store' in {item.strip().lower() for item in response.headers.get('cache-control','').split(',')}
    assert response.headers.get('referrer-policy')=='no-referrer'
    assert 'SYNTHETIC_PRIVATE_SENTINEL' not in response.text


@pytest.mark.parametrize('corrupt', ['["SYNTHETIC_PRIVATE_SENTINEL"','{','{"unexpected":"SYNTHETIC_PRIVATE_SENTINEL"}'],
                         ids=['truncated-array','truncated-object','wrong-shape'])
def test_corrupt_exclusions_fail_privately_on_generation_detail_and_list_without_spend(followup_http,corrupt):
    c=followup_http
    path='/api/clientes/'+c['profile']
    assert c['raw'].put(path,json=VALID).status_code==200
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        row.alimentos_excluidos=corrupt
        db.commit()
    # Test the already fail-closed generation boundary before exercising reads.
    for response in (
        c['raw'].post('/api/generar-plan',json={'id_cliente':c['profile'],'plan_numero':1,'tipo_plan':'menu_fijo'},headers={'Idempotency-Key':str(uuid.uuid4())}),
        c['raw'].get(path),
        c['raw'].get('/api/clientes'),
    ):
        assert response.status_code==422
        assert response.json()['detail']['code']=='nutrition_restrictions_invalid'
        _private(response)
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        assert row.alimentos_excluidos==corrupt and row.nutrition_restrictions_json is None
        assert db.query(GymGenerationReservation).filter_by(gym_id=c['user']).count()==0
        assert db.query(PlanGenerado).filter_by(gym_id=c['user']).count()==0
        assert db.query(StoredObject).filter_by(gym_id=c['user']).count()==0


def test_valid_exclusion_order_and_unknown_declaration_remain_exact_after_serialization(followup_http):
    c=followup_http
    path='/api/clientes/'+c['profile']
    foods=['huevo','avena']
    assert c['raw'].put(path,json={**VALID,'alimentos_excluidos':foods}).status_code==200
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        before=(row.alimentos_excluidos,row.nutrition_restrictions_json)
    detail=c['raw'].get(path)
    listing=c['raw'].get('/api/clientes')
    assert detail.status_code==listing.status_code==200
    item=next(row for row in listing.json()['clientes'] if row['id_cliente']==c['profile'])
    for value in (detail.json(),item):
        assert value['alimentos_excluidos']==foods
        assert value['restricciones_nutricionales']==declaration()
    _private(detail);_private(listing)
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        assert (row.alimentos_excluidos,row.nutrition_restrictions_json)==before
