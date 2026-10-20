"""Own QA20 control: sparse fields and declared facts are never computed away."""
import importlib
from sqlalchemy.orm import Session
from tests.test_nutrition35_http import followup_db,followup_http
from tests.test_nutrition35_profile_contract import declaration
from web.database.models import Cliente,GymGenerationReservation
from web.services.nutrition_profiles import capture_profile

def test_sparse_edit_preserves_declared_facts_and_does_not_call_macro_builder(followup_http,monkeypatch):
    c=followup_http
    path='/api/clientes/'+c['profile']
    expected=declaration(reported=True)
    assert c['raw'].put(path,json={'restricciones_nutricionales':expected,'alimentos_excluidos':['avena']}).status_code==200
    def forbidden(*args,**kwargs):
        raise AssertionError('profile edit invoked macro builder')
    monkeypatch.setattr(importlib.import_module('api.routes.clientes' if c['factory_name']=='api.app' else 'web.dependencies'),'build_cliente_from_dict',forbidden)
    saved=c['raw'].put(path,json={'peso_kg':76,'restricciones_nutricionales':None,'alimentos_excluidos':None})
    assert saved.status_code==200
    after=c['raw'].get(path)
    assert after.status_code==200
    value=after.json()
    assert value['peso_kg']==76 and value['edad'] is None and value['estatura_cm'] is None and value['objetivo'] is None
    assert value['restricciones_nutricionales']==expected and value['alimentos_excluidos']==['avena']
    with Session(c['admin']) as db:
        row=db.query(Cliente).filter_by(gym_id=c['user'],id_cliente=c['profile']).one()
        assert capture_profile(row).declaration_payload()==expected
        assert db.query(GymGenerationReservation).filter_by(gym_id=c['user']).count()==0
