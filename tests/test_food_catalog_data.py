"""Reject corrupt catalog data before selecting foods or publishing a menu."""
from copy import deepcopy

import pytest

from core.food_catalog import FoodCatalog, FoodRestrictionError


def source():
    foods={name:{'proteina':1,'carbs':2,'grasa':3,'kcal':39,'meal_idx':[0,1,2,3]}
           for name in ('p','c','g','v')}
    return foods,{'proteina':['p'],'carbs':['c'],'grasa':['g'],'verdura':['v']}


@pytest.mark.parametrize('field',['proteina','carbs','grasa','kcal'])
@pytest.mark.parametrize('bad',[None,'1',True,-1,float('nan'),float('inf'),float('-inf')])
def test_invalid_nutrient_is_rejected_without_exposing_values(field,bad):
    foods,categories=source()
    foods['p'][field]=bad
    with pytest.raises(FoodRestrictionError) as error:
        FoodCatalog.from_data(foods,categories)
    assert error.value.code=='food_restriction_unavailable'
    assert 'proteina' not in str(error.value)
    assert 'nan' not in str(error.value).lower()


@pytest.mark.parametrize('field',['proteina','carbs','grasa','kcal','meal_idx'])
def test_missing_required_field_is_rejected(field):
    foods,categories=source()
    del foods['p'][field]
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories)


@pytest.mark.parametrize('bad',[None,[],[4],[-1],[True],[1.0],'0123',{'meal':0},[0,'1']])
def test_invalid_meal_declaration_is_rejected(bad):
    foods,categories=source()
    foods['p']['meal_idx']=bad
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories)


@pytest.mark.parametrize('category',['proteina','custom_legume'])
def test_category_cannot_silently_drop_unknown_food(category):
    foods,categories=source()
    categories.setdefault(category,[]).append('private-missing-food-id')
    with pytest.raises(FoodRestrictionError) as error:
        FoodCatalog.from_data(foods,categories)
    assert 'private-missing-food-id' not in str(error.value)


@pytest.mark.parametrize('bad',[None,'p',{'p':True},[None],[['p']]])
def test_invalid_category_members_are_stable_domain_errors(bad):
    foods,categories=source()
    categories['proteina']=bad
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories)


@pytest.mark.parametrize('direct',[False,True])
def test_direct_constructor_cannot_bypass_data_validation(direct):
    foods,categories=source()
    foods['p']['kcal']=float('nan')
    with pytest.raises(FoodRestrictionError):
        (FoodCatalog if direct else FoodCatalog.from_data)(foods,categories)


def test_corrupt_excluded_row_is_not_hidden_before_validation():
    foods,categories=source()
    foods['unused']={'proteina':-1,'carbs':1,'grasa':1,'kcal':1,'meal_idx':[0]}
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories,['unused'])


def test_custom_categories_multigroup_food_unicode_and_metadata_are_preserved():
    foods,categories=source()
    foods['requesón']={**foods['p'],'meal_idx':(0,3),'source':{'url':'https://example.invalid/food','tags':['raw-source-label']}}
    categories['proteina'].append('requesón')
    categories['custom_legume']=['requesón','c']
    before=deepcopy((foods,categories))
    catalog=FoodCatalog.from_data(foods,categories)
    assert catalog.categorias['custom_legume']==('requesón','c')
    assert 'requesón' in catalog.categorias['proteina']
    assert catalog.alimentos['requesón']['meal_idx']==(0,3)
    assert catalog.alimentos['requesón']['source']['tags']==('raw-source-label',)
    assert (foods,categories)==before
    with pytest.raises(TypeError):
        catalog.alimentos['requesón']['kcal']=0


def test_valid_direct_constructor_owns_an_immutable_snapshot():
    foods,categories=source()
    catalog=FoodCatalog(foods,categories)
    foods['p']['kcal']=100
    categories['proteina'].clear()
    assert catalog.alimentos['p']['kcal']==39
    assert catalog.categorias['proteina']==('p',)


def test_zero_and_finite_nutrients_do_not_impose_an_arbitrary_energy_formula():
    foods,categories=source()
    foods['p'].update(proteina=0,carbs=0,grasa=0,kcal=1.0)
    assert FoodCatalog.from_data(foods,categories).alimentos['p']['kcal']==1.0


def test_runtime_seed_values_and_identifiers_are_accepted_unchanged():
    from src.alimentos_seed_runtime import ALIMENTOS_BASE_SEED, CATEGORIAS_SEED
    before=deepcopy(ALIMENTOS_BASE_SEED)
    catalog=FoodCatalog.from_data(ALIMENTOS_BASE_SEED,CATEGORIAS_SEED)
    assert set(catalog.alimentos)==set(before)
    for name,values in before.items():
        assert dict(catalog.alimentos[name])=={**values,'meal_idx':tuple(values['meal_idx'])}
    assert ALIMENTOS_BASE_SEED==before


def test_exclusions_still_remove_foods_and_fail_on_empty_required_category():
    foods,categories=source()
    foods['extra']={**foods['p']}
    categories['proteina'].append('extra')
    catalog=FoodCatalog.from_data(foods,categories,['p'])
    assert catalog.categorias['proteina']==('extra',)
    assert catalog.excluidos==frozenset({'p'})
    assert 'p' not in catalog.alimentos
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(foods,categories,['p','extra'])
