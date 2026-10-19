"""Direct SQL adversarial publication checks on actual restricted-role head29."""
from copy import deepcopy
import hashlib
import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration_client_link_canonical_postgres import (
    CA,GA,UA,lab,clean_lab,issue,accept,publish,tx,
)


def projection(lab):
    with tx(lab,GA) as db:
        return db.scalar(text('SELECT public.r12_project_plan(p)::text FROM planes_generados p WHERE id=:id'),{'id':lab['plans'][CA]})


def raw_insert(db,lab,issued,payload,*,sha=None):
    descriptor=lab['objects'][CA]
    return db.execute(text("""INSERT INTO client_plan_publications(id,gym_id,client_id,link_id,source_plan_id,
        source_object_id,object_key,content_type,byte_size,sha256,storage_backend,plan_json,plan_sha256,published_by,status)
        VALUES(:id,:gym,:client,:link,:plan,:object,:key,'application/pdf',:size,:sha,'local',:payload,:plan_sha,:gym,'published')
        RETURNING id,plan_json,plan_sha256"""),{'id':str(uuid.uuid4()),'gym':GA,'client':CA,'link':issued['link'],
        'plan':lab['plans'][CA],'object':descriptor.id,'key':descriptor.key,'size':descriptor.byte_size,
        'sha':descriptor.sha256,'payload':payload,'plan_sha':sha or hashlib.sha256(payload.encode()).hexdigest()}).one()


@pytest.mark.parametrize('change',['meal','meta','extra','sha','empty'])
def test_direct_sql_rejects_forged_projection_even_with_correct_plan_and_object(lab,change):
    issued=issue(lab);accept(lab,issued)
    payload=projection(lab)
    value=json.loads(payload)
    if change=='meal': value['plan']['desayuno']['alimentos']['synthetic-food']=999
    elif change=='meta': value['meta']['kcal_real']=999
    elif change=='extra': value['private_note']='must-never-be-projected'
    elif change=='empty': value['plan']={}
    payload=json.dumps(value,ensure_ascii=False)
    with tx(lab,GA) as db:
        with pytest.raises(DBAPIError) as denied: raw_insert(db,lab,issued,payload,sha='0'*64 if change=='sha' else None)
        assert denied.value.orig.pgcode=='23514'
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT count(*) FROM client_plan_publications'))==0


@pytest.mark.parametrize('invalid',[
    'not-json',
    '{"desayuno":{},"desayuno":{},"almuerzo":{},"comida":{},"cena":{}}',
    '{"desayuno":{},"almuerzo":{},"comida":{},"cena":{}}',
    '{"desayuno":true,"almuerzo":{},"comida":{},"cena":{}}',
    '{"note":"'+('x'*262144)+'"}',
],ids=['non-json','duplicate','empty-schema','boolean','oversize'])
def test_invalid_source_schema_fails_inside_insert_guard_not_only_python_adapter(lab,invalid):
    issued=issue(lab);accept(lab,issued)
    valid_payload=projection(lab)
    with lab['admin'].begin() as db:
        original=db.scalar(text('SELECT plan_json FROM planes_generados WHERE id=:id'),{'id':lab['plans'][CA]})
        db.execute(text('UPDATE planes_generados SET plan_json=:raw WHERE id=:id'),{'raw':invalid,'id':lab['plans'][CA]})
    try:
        with tx(lab,GA) as db:
            with pytest.raises(DBAPIError) as denied: raw_insert(db,lab,issued,valid_payload)
            assert denied.value.orig.pgcode=='23514'
    finally:
        with lab['admin'].begin() as db:
            db.execute(text('UPDATE planes_generados SET plan_json=:raw WHERE id=:id'),{'raw':original,'id':lab['plans'][CA]})


@pytest.mark.parametrize('mode',['fixed','options'])
def test_complete_four_meal_source_publishes_exact_menu_meta_and_sha(lab,mode):
    issued=issue(lab);accept(lab,issued)
    with lab['admin'].begin() as db:
        original=db.scalar(text('SELECT plan_json FROM planes_generados WHERE id=:id'),{'id':lab['plans'][CA]})
        if mode=='options':
            option={'alimento':'synthetic-food','gramos':50,'equivalencia':'synthetic',
                'macros':{'kcal':100,'proteina':10,'carbs':10,'grasa':1}}
            menu={name:{'kcal_objetivo':400,'tipo_plan':'opciones',
                **{group:{'cantidad_objetivo':20,'opciones':[deepcopy(option)]} for group in ('proteinas','carbohidratos','grasas')},
                'vegetales':[{'alimento':'synthetic-vegetable','gramos':50}]} for name in ('desayuno','almuerzo','comida','cena')}
            db.execute(text('UPDATE planes_generados SET plan_json=:raw WHERE id=:id'),{'raw':json.dumps(menu,ensure_ascii=False),'id':lab['plans'][CA]})
    try:
        with tx(lab,GA) as db:
            raw=db.scalar(text('SELECT public.r12_project_plan(p)::text FROM planes_generados p WHERE id=:id'),{'id':lab['plans'][CA]})
            result=raw_insert(db,lab,issued,raw)
            assert json.loads(result.plan_json)==json.loads(raw)
            assert result.plan_sha256==hashlib.sha256(result.plan_json.encode()).hexdigest()
            assert set(json.loads(result.plan_json)['plan'])=={'desayuno','almuerzo','comida','cena'}
            assert set(json.loads(result.plan_json)['meta'])=={'tmb','get_total','kcal_objetivo','kcal_real','proteina_g','carbs_g','grasa_g','objetivo','nivel_actividad','tipo_plan'}
            db.commit()
        with tx(lab,UA) as db:
            assert db.scalar(text('SELECT id FROM client_plan_publications WHERE id=:id'),{'id':result.id})==result.id
    finally:
        with lab['admin'].begin() as db:
            # Returning the source to its fixture state explicitly withdraws
            # the options snapshot; it never resurrects a previous projection.
            db.execute(text('UPDATE planes_generados SET plan_json=:raw WHERE id=:id'),{'raw':original,'id':lab['plans'][CA]})


def test_real_engine_hook_clears_proof_without_laboratory_listener(lab):
    from sqlalchemy import create_engine
    from web.database.tenant_context import configure_tenant_engine,tenant_scope
    issued=issue(lab)
    app=configure_tenant_engine(create_engine(lab['app'].url,pool_size=1,max_overflow=0,hide_parameters=True))
    try:
        with tx(lab,UA,issued['token'],engine=app) as db:
            pid=db.scalar(text('SELECT pg_backend_pid()'))
            assert db.scalar(text('SELECT count(*) FROM client_link_invitations'))==1
            db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,false)"),
                {'hash':db.scalar(text('SELECT token_hash FROM client_link_invitations'))})
            db.commit()
        with tenant_scope(UA),app.connect() as db:
            assert db.scalar(text('SELECT pg_backend_pid()'))==pid
            assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
            assert db.scalar(text('SELECT count(*) FROM client_link_invitations'))==0
    finally: app.dispose()


def test_direct_sql_volume_guard_precedes_json_parsing(lab):
    issued=issue(lab);accept(lab,issued)
    with tx(lab,GA) as db:
        with pytest.raises(DBAPIError) as denied:raw_insert(db,lab,issued,'['*262145)
        assert denied.value.orig.pgcode=='23514'
        assert denied.value.orig.diag.message_primary=='R12 projection volume unavailable'
