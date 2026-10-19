"""Complete rejection at stream, source, snapshot and response boundaries."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session
from starlette.requests import Request

from tests.test_personal_diary_persistence import diary_http


def test_stream_stops_before_parsing_or_reading_remaining_chunks(monkeypatch):
    from web.routes import personal_diary as route
    reads, parses = [], []
    chunks = [b' ' * route.MAX_OPERATION_BYTES, b'x', b'must-not-read']
    async def receive():
        index = len(reads)
        reads.append(index)
        return {'type':'http.request','body':chunks[index],'more_body':index < 2}
    class Parser:
        def validate_json(self, raw):
            parses.append(True)
            raise AssertionError('Oversized body reached the parser')
    monkeypatch.setattr(route,'_PATCH',Parser())
    with pytest.raises(HTTPException) as failure:
        asyncio.run(route.operation_body(Request({'type':'http','method':'PATCH','path':'/'}, receive)))
    assert failure.value.status_code == 413
    assert reads == [0,1] and parses == []


@pytest.mark.parametrize('raw', ['x' * (256*1024+1), 'é' * (128*1024+1)], ids=['ascii','utf8'])
def test_plan_bytes_are_bounded_before_json_parse(monkeypatch,raw):
    from web.services import personal_diary_service as service
    from web.personal_diary_schemas import MealSelection
    def forbidden(*args,**kwargs):
        raise AssertionError('Oversized source reached JSON parsing')
    monkeypatch.setattr(service.json,'loads',forbidden)
    with pytest.raises(HTTPException) as failure:
        service.resolve_consumed_meal(SimpleNamespace(id=1,gym_id='subject',deleted_at=None,
            plan_json=raw),'subject','desayuno',MealSelection())
    assert failure.value.status_code == 409


def test_utf8_snapshot_bytes_are_bounded_before_parse(monkeypatch):
    from web.services import personal_diary_persistence as service
    raw = '{"x":"'+'é'*40000+'"}'
    assert len(raw)<65536<len(raw.encode('utf-8'))
    def forbidden(*args,**kwargs):
        raise AssertionError('Oversized snapshot reached JSON parsing')
    monkeypatch.setattr(service.json,'loads',forbidden)
    with pytest.raises(HTTPException) as failure:
        service.decode_meals(raw)
    assert failure.value.status_code == 409


@pytest.mark.parametrize('group', ['options','vegetables'])
def test_source_food_counts_reject_whole_operation(group):
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    food = {'alimento':'huevo','gramos':1,'macros':{'kcal':1,'proteina':1,'carbs':1,'grasa':1}}
    meal = {'proteinas':{'opciones':[food]*(257 if group=='options' else 1)},
        'vegetales':[food]*(33 if group=='vegetables' else 0)}
    plan = SimpleNamespace(id=1,gym_id='subject',deleted_at=None,plan_json=json.dumps({'desayuno':meal}))
    with pytest.raises(HTTPException) as failure:
        resolve_consumed_meal(plan,'subject','desayuno',MealSelection(proteinas=0,include_vegetables=True))
    assert failure.value.status_code == 409


def test_source_escaped_invalid_unicode_requires_review_not_a_failed_save():
    from web.personal_diary_schemas import MealSelection
    from web.services.personal_diary_service import resolve_consumed_meal
    food={'alimento':'huevo','gramos':1,'equivalencia':'\ud800',
        'macros':{'kcal':1,'proteina':1,'carbs':1,'grasa':1}}
    plan=SimpleNamespace(id=1,gym_id='subject',deleted_at=None,
        plan_json=json.dumps({'desayuno':{'proteinas':{'opciones':[food]}}}))
    with pytest.raises(HTTPException) as failure:
        resolve_consumed_meal(plan,'subject','desayuno',MealSelection(proteinas=0))
    assert failure.value.status_code==409
    assert failure.value.detail['code']=='diary_source_unavailable'


def _large_meals():
    food = {'food_id':'f'*200,'grams':1.0,'equivalence':'e'*500,
        'macros':{'kcal':1.0,'protein_g':1.0,'carbs_g':1.0,'fat_g':1.0}}
    meals = {}
    for name in ('desayuno','comida'):
        meals[name] = {'source_plan_id':1,'meal':name,'selections':{'include_vegetables':True},
            'foods':[food]*20,'totals':{'kcal':20.0,'protein_g':20.0,'carbs_g':20.0,'fat_g':20.0},
            'recorded_at':'2026-10-01T00:00:00+00:00','completed':False}
    return json.dumps(meals,separators=(',',':'))


def test_range_and_export_budget_return_complete_days_or_reject(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine = diary_http
    today = local_today()
    encoded = _large_meals()
    assert 30000<len(encoded.encode())<65536
    with Session(engine) as db:
        for index in range(40):
            db.add(PersonalDiaryDay(user_id='diary-person',local_date=today-timedelta(days=index),
                meals_json=encoded,version=1))
        db.commit()
    response = client.get('/api/usuario/diario',headers=tokens['diary-person'],
        params={'start':(today-timedelta(days=39)).isoformat(),'end':today.isoformat()})
    assert response.status_code == 413
    page = client.get('/api/usuario/privacidad/exportar',headers=tokens['diary-person'],params={'limit':50})
    assert page.status_code == 200,page.text
    records = page.json()['personal_diary']['records']
    assert 1<=len(records)<40
    assert page.json()['personal_diary']['next_after']==records[-1]['local_date']
    assert all(row['meals']==json.loads(encoded) for row in records)


def test_corrupt_day_is_not_overwritten_by_water(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine = diary_http
    today = local_today()
    corrupt = '{"desayuno":null}'
    with Session(engine) as db:
        db.add(PersonalDiaryDay(user_id='diary-person',local_date=today,meals_json=corrupt,version=1))
        db.commit()
    response = client.patch('/api/usuario/diario/'+today.isoformat(),headers=tokens['diary-person'],
        json={'operation':'water','expected_version':1,'water_ml':800})
    assert response.status_code == 409
    with Session(engine) as db:
        row = db.query(PersonalDiaryDay).one()
        assert (row.version,row.water_ml,row.meals_json)==(1,0,corrupt)


def test_exhausted_version_preserves_day(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine = diary_http
    today=local_today()
    with Session(engine) as db:
        db.add(PersonalDiaryDay(user_id='diary-person',local_date=today,version=2147483647))
        db.commit()
    response=client.patch('/api/usuario/diario/'+today.isoformat(),headers=tokens['diary-person'],
        json={'operation':'water','expected_version':2147483647,'water_ml':1})
    assert response.status_code==409
    assert response.json()['detail']['code']=='diary_version_exhausted'


def test_ambient_tenant_cannot_be_rebound_to_personal_subject(diary_http):
    from web.database.tenant_context import tenant_scope
    from web.services.personal_diary_persistence import read_diary_day
    from web.services.personal_diary_service import local_today
    _,_,engine=diary_http
    with tenant_scope('diary-other'),Session(engine) as db,pytest.raises(HTTPException) as failure:
        read_diary_day(db,'diary-person',local_today())
    assert failure.value.status_code==403
