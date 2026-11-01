"""Source attribution and automatic eligibility survive load/fallback/reload."""
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.food_catalog import FoodCatalog, FoodRestrictionError, validate_catalog_data
from src.alimentos_catalogo_usda import load_usda_catalog


def small_catalog():
    foods={name:{'proteina':1,'carbs':2,'grasa':3,'kcal':39,'meal_idx':[0,1,2,3]}
           for name in ('p','c','g','v')}
    return foods,{'proteina':['p'],'carbs':['c'],'grasa':['g'],'verdura':['v']}


@pytest.fixture
def owned_base_loader(monkeypatch):
    # Snapshot only pure runtime seeds. All DB/branding adapters below are
    # isolated fakes; executing the real base module never opens a database.
    from src import alimentos_seed_runtime as runtime

    full={name:deepcopy(getattr(runtime,name)) for name in
          ('ALIMENTOS_BASE_SEED','CATEGORIAS_SEED','LIMITES_ALIMENTOS_SEED','EQUIVALENCIAS_PRACTICAS_SEED')}
    usda=load_usda_catalog()
    true_id=next(k for k,v in usda['metadata'].items() if v['auto_generation'])
    false_id=next(k for k,v in usda['metadata'].items() if not v['auto_generation'])

    def load(*,fail=False,use_full=False):
        foods,categories=small_catalog()
        foods['proteina_suero']={'proteina':25,'carbs':8,'grasa':6,'kcal':400,'meal_idx':[0]}
        categories['proteina'].append('proteina_suero')
        for key in (true_id,false_id):
            foods[key]=deepcopy(usda['foods'][key])
            categories.setdefault(usda['metadata'][key]['categoria'],[]).append(key)
        seeds=full if use_full else {'ALIMENTOS_BASE_SEED':foods,'CATEGORIAS_SEED':categories,
                                     'LIMITES_ALIMENTOS_SEED':{},'EQUIVALENCIAS_PRACTICAS_SEED':{}}
        holder={'fail':fail,'payload':{'alimentos_base':deepcopy(seeds['ALIMENTOS_BASE_SEED']),
                'categorias':deepcopy(seeds['CATEGORIAS_SEED']),
                'limites_alimentos':deepcopy(seeds['LIMITES_ALIMENTOS_SEED']),
                'equivalencias_practicas':deepcopy(seeds['EQUIVALENCIAS_PRACTICAS_SEED'])}}

        def read():
            if holder['fail']:
                raise RuntimeError('owned synthetic unavailable catalog')
            return deepcopy(holder['payload'])

        monkeypatch.setitem(sys.modules,'src.alimentos_seed_runtime',SimpleNamespace(**seeds))
        monkeypatch.setitem(sys.modules,'src.alimentos_sqlite',SimpleNamespace(
            inicializar_db_si_es_necesario=Mock(),cargar_datos=read))
        monkeypatch.setitem(sys.modules,'core.branding',SimpleNamespace(branding=SimpleNamespace(get=lambda *args:[])))
        monkeypatch.setitem(sys.modules,'utils.logger',SimpleNamespace(logger=Mock()))
        monkeypatch.delitem(sys.modules,'config.catalogo_alimentos',raising=False)
        file=Path(__file__).resolve().parents[1]/'src'/'alimentos_base.py'
        spec=importlib.util.spec_from_file_location('owned_food_base',file)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module,holder,seeds,true_id,false_id

    return load


@pytest.mark.parametrize('flag',[None,0,1,'false',[],{}])
def test_automatic_flag_is_only_a_bool(flag):
    foods,categories=small_catalog()
    foods['p']['auto_generation']=flag
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories)


def test_false_automatic_flag_does_not_become_a_personal_exclusion():
    foods,categories=small_catalog()
    foods['blocked']={**foods['p'],'auto_generation':False}
    categories['proteina'].append('blocked')
    catalog=FoodCatalog.from_data(foods,categories)
    assert 'blocked' not in catalog.alimentos
    assert 'blocked' not in catalog.categorias['proteina']
    assert catalog.excluidos==frozenset()
    explicit=FoodCatalog.from_data(foods,categories,['blocked'])
    assert explicit.excluidos==frozenset({'blocked'})


@pytest.mark.parametrize('plan',[{'desayuno':{'alimentos':{'blocked':10}}},
                                {'cena':{'opciones':[{'alimento':'blocked','gramos':10}]}}])
def test_final_validation_cannot_be_bypassed_by_direct_constructor(plan):
    foods,categories=small_catalog()
    foods['blocked']={**foods['p'],'auto_generation':False}
    catalog=FoodCatalog(foods,categories)
    with pytest.raises(FoodRestrictionError):
        catalog.validate_plan(plan)
    assert catalog.require_candidates(['blocked','p'])==['p']


def test_all_automatic_proteins_unavailable_fails_without_restoring_them():
    foods,categories=small_catalog()
    foods['p']['auto_generation']=False
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories)


def test_public_data_validator_accepts_single_food_without_generation_groups():
    foods,_=small_catalog()
    validate_catalog_data({'p':foods['p']},{'custom':['p']})


@pytest.mark.parametrize('fail',[False,True])
def test_sqlite_and_fallback_have_same_current_provenance_without_seed_mutation(owned_base_loader,fail):
    module,holder,seeds,true_id,false_id=owned_base_loader(fail=fail)
    original=holder['payload']['alimentos_base']
    for key,row in original.items():
        for field in ('proteina','carbs','grasa','kcal','meal_idx'):
            assert module.ALIMENTOS_BASE[key][field]==row[field]
    reference=module.ALIMENTOS_BASE[true_id]
    assert reference['source']['provider']=='USDA FoodData Central'
    assert reference['estado'] and reference['porcion_base_g']==100
    assert reference['auto_generation'] is True
    assert module.ALIMENTOS_BASE[false_id]['auto_generation'] is False
    assert module.ALIMENTOS_BASE['proteina_suero']['provenance_status']=='legacy_review_required'
    assert module.ALIMENTOS_BASE['proteina_suero']['review_reason']=='energy_inconsistency'
    assert module.ALIMENTOS_BASE['proteina_suero']['auto_generation'] is False
    assert seeds['ALIMENTOS_BASE_SEED']==original
    assert 'source' not in seeds['ALIMENTOS_BASE_SEED'][true_id]


def test_customized_nutrients_do_not_keep_old_usda_attribution(owned_base_loader):
    module,_,_,true_id,_=owned_base_loader()
    old=deepcopy(module.ALIMENTOS_BASE)
    old[true_id]['proteina']+=1
    result=module._enriquecer_alimentos(old)[true_id]
    assert result['proteina']==old[true_id]['proteina']
    assert result['source'] is None and result['provenance_status']=='customized'
    assert result['auto_generation'] is False
    for field in ('estado','nutrients_source','energy_diagnostic','editorial'):
        assert field not in result


@pytest.mark.parametrize('changes',[{'proteina':26},{'carbs':9},{'grasa':7},{'kcal':401},
                                    {'proteina':34,'carbs':10,'grasa':1}])
def test_only_exact_legacy_whey_profile_is_quarantined(owned_base_loader,changes):
    module,_,_,_,_=owned_base_loader()
    foods=deepcopy(module.ALIMENTOS_BASE)
    foods['proteina_suero'].update(changes)
    result=module._enriquecer_alimentos(foods)['proteina_suero']
    assert all(result[key]==value for key,value in changes.items())
    assert 'auto_generation' not in result
    assert 'provenance_status' not in result


def test_metadata_cannot_replace_persisted_nutrients_or_meal_indices(owned_base_loader,monkeypatch):
    from src import alimentos_catalogo_usda as loader

    module,holder,_,_,_=owned_base_loader()
    monkeypatch.setattr(loader,'metadata_by_id',lambda foods:{'p':{'kcal':999,'meal_idx':[99],'source':None}})
    enriched=module._enriquecer_alimentos(holder['payload']['alimentos_base'])
    assert enriched['p']['kcal']==39 and enriched['p']['meal_idx']==[0,1,2,3]


def test_reload_refreshes_already_imported_catalog_lists_in_place(owned_base_loader,monkeypatch):
    module,holder,_,_,_=owned_base_loader()
    monkeypatch.setitem(sys.modules,'src.alimentos_base',module)
    file=Path(__file__).resolve().parents[1]/'config'/'catalogo_alimentos.py'
    spec=importlib.util.spec_from_file_location('owned_food_categories',file)
    catalog=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    monkeypatch.setitem(sys.modules,'config.catalogo_alimentos',catalog)
    old_reference=catalog.PROTEINAS
    holder['payload']['alimentos_base']['new_custom']={**holder['payload']['alimentos_base']['p']}
    holder['payload']['categorias']['proteina'].append('new_custom')
    assert module.recargar_desde_db() is True
    assert catalog.PROTEINAS is old_reference
    assert 'new_custom' in old_reference


def test_failed_reload_preserves_the_whole_previous_snapshot(owned_base_loader,monkeypatch):
    module,holder,_,_,_=owned_base_loader()
    before=deepcopy((module.ALIMENTOS_BASE,module.CATEGORIAS,module.LIMITES_ALIMENTOS,module.EQUIVALENCIAS_PRACTICAS))
    refresh=Mock()
    monkeypatch.setitem(sys.modules,'config.catalogo_alimentos',SimpleNamespace(refrescar_catalogo=refresh))
    holder['fail']=True
    assert module.recargar_desde_db() is False
    assert (module.ALIMENTOS_BASE,module.CATEGORIAS,module.LIMITES_ALIMENTOS,module.EQUIVALENCIAS_PRACTICAS)==before
    refresh.assert_not_called()


def test_reload_reattributes_current_rows_and_drops_previous_source_flags(owned_base_loader):
    module,holder,_,true_id,_=owned_base_loader()
    holder['payload']['alimentos_base'][true_id]['proteina']+=1
    holder['payload']['alimentos_base']['proteina_suero']['proteina']=26
    assert module.recargar_desde_db() is True
    current=module.ALIMENTOS_BASE[true_id]
    assert current['source'] is None and current['provenance_status']=='customized'
    assert current['auto_generation'] is False
    assert 'nutrients_source' not in current
    assert 'auto_generation' not in module.ALIMENTOS_BASE['proteina_suero']


def test_full_runtime_keeps171_values_but_only161_automatic_foods(owned_base_loader):
    module,_,seeds,_,_=owned_base_loader(use_full=True)
    assert len(module.ALIMENTOS_BASE)==171
    catalog=FoodCatalog.from_data(module.ALIMENTOS_BASE,module.CATEGORIAS)
    assert len(catalog.alimentos)==161
    assert catalog.excluidos==frozenset()
    assert len([x for x in module.ALIMENTOS_BASE.values() if x.get('auto_generation') is False])==10
    for key,row in seeds['ALIMENTOS_BASE_SEED'].items():
        assert all(module.ALIMENTOS_BASE[key][field]==row[field] for field in ('proteina','carbs','grasa','kcal'))
