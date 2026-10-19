"""Independent R14 privacy/integrity canaries; real HTTP and persisted subjects."""
from datetime import datetime, timedelta, timezone
import json

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from tests.test_personal_diary_persistence import diary_http, meal_patch, seed_plan


@pytest.mark.parametrize('source', ['foreign','mixed','deleted_plan','deleted_client'])
def test_even_empty_selection_requires_both_live_source_owners(diary_http, source):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine=diary_http
    plan=seed_plan(engine,owner='diary-other' if source=='foreign' else 'diary-person',
        client_owner='diary-other' if source=='mixed' else None,
        plan_deleted=source=='deleted_plan',client_deleted=source=='deleted_client')
    payload=meal_patch(plan,0)
    payload['selections']={}
    response=client.patch('/api/usuario/diario/'+local_today().isoformat(),headers=tokens['diary-person'],json=payload)
    assert response.status_code==404
    with Session(engine) as db:
        assert db.query(PersonalDiaryDay).count()==0


def test_snapshot_survives_source_reassignment_without_authorizing_new_consumption(diary_http):
    from web.database.models import PlanGenerado
    from web.services.personal_diary_service import local_today
    client,tokens,engine=diary_http
    plan=seed_plan(engine)
    url='/api/usuario/diario/'+local_today().isoformat()
    headers=tokens['diary-person']
    saved=client.patch(url,headers=headers,json=meal_patch(plan,0))
    assert saved.status_code==200
    before=saved.json()
    with Session(engine) as db:
        db.get(PlanGenerado,plan).gym_id='diary-other'
        db.commit()
    assert client.get(url,headers=headers).json()==before
    completed=client.patch(url,headers=headers,json={'operation':'completion','expected_version':1,'meal':'desayuno','completed':True})
    assert completed.status_code==200
    expected={**before['meals']['desayuno'],'completed':True}
    assert completed.json()['meals']['desayuno']==expected
    denied=client.patch(url,headers=headers,json=meal_patch(plan,2,'comida'))
    assert denied.status_code==404
    unchanged=client.get(url,headers=headers).json()
    assert unchanged['version']==2 and unchanged['meals']=={'desayuno':expected}
    exported=client.get('/api/usuario/privacidad/exportar',headers=headers).json()
    assert exported['plans']['records']==[]
    assert exported['personal_diary']['records'][0]['meals']==unchanged['meals']


def test_lost_commit_ack_requires_reread_and_stale_retry_cannot_duplicate(diary_http,monkeypatch,caplog):
    from web.services.personal_diary_service import local_today
    client,tokens,_=diary_http
    url='/api/usuario/diario/'+local_today().isoformat()
    headers=tokens['diary-person']
    original=Session.commit
    marker='synthetic-diary-ack-private-marker'
    def lost_ack(db):
        original(db)
        raise StatementError(marker,'SELECT private_diary_note',{'note':marker},RuntimeError(marker))
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',lost_ack)
        failed=client.patch(url,headers=headers,json={'operation':'water','expected_version':0,'water_ml':1750})
    assert failed.status_code==503
    assert marker not in failed.text+caplog.text and 'SELECT private_diary_note' not in caplog.text
    retry=client.patch(url,headers=headers,json={'operation':'water','expected_version':0,'water_ml':900})
    assert retry.status_code==409 and retry.json()['detail']['current_version']==1
    read=client.get(url,headers=headers).json()
    assert (read['version'],read['water_ml'])==(1,1750)
    export=client.get('/api/usuario/privacidad/exportar',headers=headers).json()['personal_diary']['records']
    assert len(export)==1 and (export[0]['version'],export[0]['water_ml'])==(1,1750)
    assert client.get(url,headers=tokens['diary-other']).json()['version']==0


def test_rollback_failure_is_unconfirmed_and_never_logs_statement_values(diary_http,monkeypatch,caplog):
    from web.services.personal_diary_service import local_today
    client,tokens,_=diary_http
    marker='synthetic-diary-rollback-private-marker'
    original_rollback=Session.rollback
    def failed_commit(db):
        raise StatementError(marker,'INSERT private_diary_snapshot',{'foods':marker},RuntimeError(marker))
    def failed_rollback(db):
        original_rollback(db)
        raise RuntimeError(marker)
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',failed_commit)
        patch.setattr(Session,'rollback',failed_rollback)
        response=client.patch('/api/usuario/diario/'+local_today().isoformat(),headers=tokens['diary-person'],
            json={'operation':'water','expected_version':0,'water_ml':333})
    assert response.status_code==503
    assert response.json()['detail']['code']=='diary_save_unconfirmed'
    assert marker not in response.text+caplog.text
    assert 'INSERT private_diary_snapshot' not in caplog.text
    read=client.get('/api/usuario/diario/'+local_today().isoformat(),headers=tokens['diary-person']).json()
    assert read['version']==0


def test_rejected_mass_assignment_does_not_persist_any_day(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine=diary_http
    url='/api/usuario/diario/'+local_today().isoformat()
    for field,value in [('user_id','diary-other'),('meals',{}),('created_at','2026-01-01'),('version',99),('timezone','UTC')]:
        response=client.patch(url,headers=tokens['diary-person'],json={'operation':'water','expected_version':0,'water_ml':500,field:value})
        assert response.status_code==422
    with Session(engine) as db:
        assert db.query(PersonalDiaryDay).count()==0


def test_diary_date_cursor_does_not_select_another_subject(diary_http):
    from web.services.personal_diary_service import local_today
    client,tokens,_=diary_http
    today=local_today()
    for actor,water in [('diary-person',345),('diary-other',987)]:
        for offset in (0,1):
            response=client.patch('/api/usuario/diario/'+(today-timedelta(days=offset)).isoformat(),headers=tokens[actor],
                json={'operation':'water','expected_version':0,'water_ml':water})
            assert response.status_code==200
    response=client.get('/api/usuario/privacidad/exportar',headers=tokens['diary-person'],params={
        'after_diary':(today-timedelta(days=1)).isoformat(),'limit':1,'user_id':'diary-other','gym_id':'diary-other'})
    assert response.status_code==200
    records=response.json()['personal_diary']['records']
    assert len(records)==1 and records[0]['water_ml']==345 and records[0]['local_date']==today.isoformat()
    assert response.json()['personal_diary']['next_after'] is None
    assert client.get('/api/usuario/privacidad/exportar',headers=tokens['diary-person'],params={'after_diary':'2026-02-30'}).status_code==422


def test_stored_duplicate_snapshot_members_are_not_exported_or_overwritten(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine=diary_http
    day=local_today()
    raw='{"desayuno":{},"desayuno":{}}'
    with Session(engine) as db:
        db.add(PersonalDiaryDay(user_id='diary-person',local_date=day,meals_json=raw,version=1))
        db.commit()
    headers=tokens['diary-person']
    assert client.get('/api/usuario/diario/'+day.isoformat(),headers=headers).status_code==409
    assert client.get('/api/usuario/privacidad/exportar',headers=headers).status_code==409
    assert client.patch('/api/usuario/diario/'+day.isoformat(),headers=headers,
        json={'operation':'water','expected_version':1,'water_ml':900}).status_code==409
    with Session(engine) as db:
        row=db.scalars(select(PersonalDiaryDay)).one()
        assert row.meals_json==raw and (row.version,row.water_ml)==(1,0)


def test_actual_http_body_limit_preserves_day_and_accepts_exact_boundary(diary_http):
    from web.routes.personal_diary import MAX_OPERATION_BYTES
    from web.services.personal_diary_service import local_today
    client,tokens,_=diary_http
    url='/api/usuario/diario/'+local_today().isoformat()
    headers={**tokens['diary-person'],'Content-Type':'application/json'}
    saved=client.patch(url,headers=headers,json={'operation':'water','expected_version':0,'water_ml':400})
    assert saved.status_code==200
    body=json.dumps({'operation':'water','expected_version':1,'water_ml':800}).encode()
    excessive=body+b' '*(MAX_OPERATION_BYTES+1-len(body))
    rejected=client.patch(url,headers=headers,content=excessive)
    assert rejected.status_code==413
    assert client.get(url,headers=headers).json()==saved.json()
    exact=body+b' '*(MAX_OPERATION_BYTES-len(body))
    accepted=client.patch(url,headers=headers,content=exact)
    assert accepted.status_code==200
    assert (accepted.json()['version'],accepted.json()['water_ml'])==(2,800)


def test_utf8_storage_within_sql_character_check_still_rejects_full_byte_overflow(diary_http):
    from web.database.models import PersonalDiaryDay
    from web.services.personal_diary_service import local_today
    client,tokens,engine=diary_http
    day=local_today()
    food={'food_id':'🍎'*200,'grams':1,'equivalence':'🍎'*500,
        'macros':{'kcal':1,'protein_g':1,'carbs_g':1,'fat_g':1}}
    raw=json.dumps({'desayuno':{'source_plan_id':1,'meal':'desayuno','selections':{'include_vegetables':True},
        'foods':[food]*24,'totals':{'kcal':24,'protein_g':24,'carbs_g':24,'fat_g':24},
        'recorded_at':'2026-10-19T12:00:00+00:00','completed':False}},ensure_ascii=False)
    assert len(raw)<65536<len(raw.encode('utf8'))
    with Session(engine) as db:
        db.add(PersonalDiaryDay(user_id='diary-person',local_date=day,meals_json=raw,version=1))
        db.commit()
    headers=tokens['diary-person']
    assert client.get('/api/usuario/diario/'+day.isoformat(),headers=headers).status_code==409
    assert client.get('/api/usuario/privacidad/exportar',headers=headers).status_code==409
    rejected=client.patch('/api/usuario/diario/'+day.isoformat(),headers=headers,
        json={'operation':'water','expected_version':1,'water_ml':900})
    assert rejected.status_code==409
    with Session(engine) as db:
        row=db.scalars(select(PersonalDiaryDay)).one()
        assert row.meals_json==raw and (row.version,row.water_ml)==(1,0)


def test_stream_does_not_trust_small_content_length_or_consume_following_chunks(monkeypatch):
    import asyncio
    from starlette.requests import Request
    from fastapi import HTTPException
    from web.routes import personal_diary as route
    consumed=[]
    async def receive():
        consumed.append(True)
        assert len(consumed)==1,'Excessive stream must not be read again'
        return {'type':'http.request','body':b' '*(route.MAX_OPERATION_BYTES+1),'more_body':True}
    class ForbiddenParser:
        def validate_json(self,raw):
            raise AssertionError('Excessive body must not reach DTO parsing')
    monkeypatch.setattr(route,'_PATCH',ForbiddenParser())
    request=Request({'type':'http','method':'PATCH','path':'/','headers':[(b'content-length',b'1')]},receive)
    with pytest.raises(HTTPException) as denied:
        asyncio.run(route.operation_body(request))
    assert denied.value.status_code==413 and consumed==[True]


def test_real_membership_revocation_preserves_personal_diary_and_removes_portfolio(diary_http,request):
    from web.auth import hash_password
    from web.database.models import Usuario,UserRole,PlanGenerado
    from web.services.personal_diary_service import local_today
    client,tokens,engine=diary_http
    password='SyntheticDiaryMembershipOnly123!'
    with Session(engine) as db:
        member=db.get(Usuario,'diary-member')
        member.password_hash=hash_password(password)
        assert member.session_version==0
        db.commit()
    portfolio_plan=seed_plan(engine,owner='diary-owner')
    personal_plan=seed_plan(engine,owner='diary-member')
    with Session(engine) as db:
        portfolio_profile=db.get(PlanGenerado,portfolio_plan).id_cliente
        personal_profile=db.get(PlanGenerado,personal_plan).id_cliente
    old_headers=tokens['diary-member']
    # The existing standalone API reserves client adapters for OWNER; SaaS
    # permits the professional role. Diary/export are personal in both.
    web=request.node.callspec.params['diary_http']=='web.main_web'
    assert client.get('/api/clientes/'+portfolio_profile,headers=old_headers).status_code==(200 if web else 403)
    url='/api/usuario/diario/'+local_today().isoformat()
    water=client.patch(url,headers=old_headers,json={'operation':'water','expected_version':0,'water_ml':650})
    assert water.status_code==200
    meal=client.patch(url,headers=old_headers,json=meal_patch(personal_plan,1))
    assert meal.status_code==200
    before=meal.json()
    revoked=client.delete('/api/gym/team/diary-member',headers=tokens['diary-owner'])
    assert revoked.status_code==200
    assert revoked.json()['status']=='revoked'
    assert client.get(url,headers=old_headers).status_code==401
    with Session(engine) as db:
        member=db.get(Usuario,'diary-member')
        assert member.activo and member.deleted_at is None
        assert member.session_version==1
        assert member.team_gym_id is None and member.role==UserRole.VIEWER and member.tipo=='usuario'
    login=client.post('/api/auth/login',json={'email':'diary-member@example.invalid','password':password})
    assert login.status_code==200
    current={'Authorization':'Bearer '+login.json()['token']}
    assert login.json()['role']=='viewer' and login.json()['team_gym_id'] is None
    assert client.get(url,headers=current).json()==before
    exported=client.get('/api/usuario/privacidad/exportar',headers=current)
    assert exported.status_code==200
    data=exported.json()
    assert data['scope']['personal_space'] is True and data['scope']['professional_membership'] is False
    assert data['personal_diary']['records'][0]['meals']==before['meals']
    assert data['personal_diary']['records'][0]['water_ml']==650
    assert [row['id'] for row in data['plans']['records']]==[personal_plan]
    assert [row['id_cliente'] for row in data['profiles']['records']]==[personal_profile]
    assert client.get('/api/clientes/'+portfolio_profile,headers=current).status_code in {403,404}
    assert client.get('/api/clientes/'+personal_profile,headers=current).status_code==(200 if web else 403)
    assert client.get('/api/clientes/'+portfolio_profile,headers=tokens['diary-owner']).status_code==200
