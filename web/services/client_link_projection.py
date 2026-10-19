"""Known source menu projection, with no nutrient recalculation or hidden fields."""
import hashlib
import json
import math

MAX_BYTES=256*1024
MEALS=('desayuno','almuerzo','comida','cena')
MACRO_GROUPS=('proteinas','carbohidratos','grasas')
META_NUMBERS=('tmb','get_total','kcal_objetivo','kcal_real','proteina_g','carbs_g','grasa_g')
META_TEXT=('objetivo','nivel_actividad','tipo_plan')


class ProjectionUnavailable(ValueError):
    pass


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ProjectionUnavailable('Duplicate object member')
        result[key]=value
    return result


def _reject_constant(_):
    raise ProjectionUnavailable('Nonfinite JSON constant')


def decode(raw):
    if not isinstance(raw,str) or len(raw)>MAX_BYTES:
        raise ProjectionUnavailable('Source volume unavailable')
    try:
        if len(raw.encode('utf-8'))>MAX_BYTES:raise ProjectionUnavailable('Source volume unavailable')
        value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=_reject_constant)
        _depth(value,0)
        return value
    except (ValueError,TypeError,RecursionError,UnicodeError,OverflowError):
        raise ProjectionUnavailable('Source content unavailable') from None


def _depth(value,level):
    if level>12:raise ProjectionUnavailable('Source depth unavailable')
    if isinstance(value,dict):
        for child in value.values():_depth(child,level+1)
    elif isinstance(value,list):
        for child in value:_depth(child,level+1)


def _keys(value,allowed,required=None):
    if not isinstance(value,dict) or set(value)-set(allowed) or set(required or ())-set(value):
        raise ProjectionUnavailable('Source schema unavailable')


def _number(value,*,positive=False):
    if type(value) not in {int,float} or not 0<=value<=10**12 or not math.isfinite(value) or (positive and value==0):
        raise ProjectionUnavailable('Source number unavailable')


def _food(value):
    _keys(value,{'alimento','gramos','equivalencia','macros'},{'alimento','gramos'})
    if not isinstance(value['alimento'],str) or not 1<=len(value['alimento'])<=200:
        raise ProjectionUnavailable('Source food unavailable')
    _number(value['gramos'],positive=True)
    if 'equivalencia' in value and (not isinstance(value['equivalencia'],str) or len(value['equivalencia'])>500):
        raise ProjectionUnavailable('Source equivalence unavailable')
    if 'macros' in value:
        _keys(value['macros'],{'kcal','proteina','carbs','grasa'})
        for number in value['macros'].values():_number(number)


def validate_menu(value):
    _keys(value,MEALS,MEALS)
    for name in MEALS:
        meal=value[name]
        if isinstance(meal,dict) and meal.get('tipo_plan')=='opciones':
            keys={'kcal_objetivo','tipo_plan','vegetales',*MACRO_GROUPS}
            _keys(meal,keys,keys);_number(meal['kcal_objetivo'])
            count=0
            for category in MACRO_GROUPS:
                block=meal[category];_keys(block,{'cantidad_objetivo','opciones'},{'cantidad_objetivo','opciones'})
                _number(block['cantidad_objetivo'])
                options=block['opciones']
                if not isinstance(options,list) or len(options)>256:raise ProjectionUnavailable('Source options unavailable')
                count+=len(options)
                for option in options:_food(option)
            vegetables=meal['vegetales']
            if not isinstance(vegetables,list) or len(vegetables)>32:raise ProjectionUnavailable('Source vegetables unavailable')
            count+=len(vegetables)
            for vegetable in vegetables:_food(vegetable)
            if count==0:raise ProjectionUnavailable('Source meal empty')
        else:
            keys={'kcal_objetivo','kcal_real','alimentos'}
            _keys(meal,keys,keys);_number(meal['kcal_objetivo']);_number(meal['kcal_real'])
            foods=meal['alimentos']
            if not isinstance(foods,dict) or not 1<=len(foods)<=256:raise ProjectionUnavailable('Source foods unavailable')
            for food,grams in foods.items():
                if not isinstance(food,str) or not 1<=len(food)<=200:raise ProjectionUnavailable('Source food unavailable')
                _number(grams,positive=True)
    return value


def project_source(plan):
    menu=validate_menu(decode(plan.plan_json))
    metadata={}
    for name in META_NUMBERS:
        value=getattr(plan,name)
        if value is not None:_number(value)
        metadata[name]=value
    for name in META_TEXT:
        value=getattr(plan,name)
        if value is not None and (not isinstance(value,str) or len(value)>30):raise ProjectionUnavailable('Source metadata unavailable')
        metadata[name]=value
    return serialize({'plan':menu,'meta':metadata})


def serialize(value):
    try:
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))
        if len(raw.encode('utf-8'))>MAX_BYTES:raise ProjectionUnavailable('Projection volume unavailable')
        return raw
    except (TypeError,ValueError,OverflowError,UnicodeError):
        raise ProjectionUnavailable('Projection content unavailable') from None


def read_projection(raw,expected_sha):
    value=decode(raw)
    if (not isinstance(expected_sha,str) or len(expected_sha)!=64
            or hashlib.sha256(raw.encode('utf-8')).hexdigest()!=expected_sha):
        raise ProjectionUnavailable('Projection integrity unavailable')
    _keys(value,{'plan','meta'},{'plan','meta'});validate_menu(value['plan'])
    _keys(value['meta'],{*META_NUMBERS,*META_TEXT},{*META_NUMBERS,*META_TEXT})
    for name in META_NUMBERS:
        if value['meta'][name] is not None:_number(value['meta'][name])
    for name in META_TEXT:
        item=value['meta'][name]
        if item is not None and (not isinstance(item,str) or len(item)>30):raise ProjectionUnavailable('Projection metadata unavailable')
    return value
