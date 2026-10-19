"""Populated32 measurements and exact-link consent, preserving all31 fixtures."""
from datetime import datetime,timedelta,timezone
import json
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_provider_subjects import application_engine
from web.database.models import Cliente,ClientProgress,PersonalDiaryDay,Subscription,ProgressConsent
from web.database.tenant_context import tenant_scope
from web.personal_diary_schemas import MealSelection
from web.personal_progress_schemas import MeasurementWrite,ConsentGrant,ConsentWithdraw
from web.services import personal_progress as own,progress_share as sharing,progress_readers as readers
from web.services.personal_diary_service import local_today,resolve_consumed_meal


def principal(identity):return {'id':identity,'session_version':0}


def populate_progress32(source_url,admin,links):
    today=local_today();now=datetime.now(timezone.utc);ids=links['ids']
    profiles={name:str(uuid.uuid4()) for name in ('recipient','other')}
    records={name:str(uuid.uuid4()) for name in profiles}
    with Session(admin) as db:
        for name,key in profiles.items():db.add(Cliente(id_cliente=key,gym_id=ids[name],nombre='Synthetic32 explicit own source',activo=True))
        db.add(Subscription(gym_id=ids['gym_a'],plan='clinica',status='active',provider='stripe',max_clientes=0,
            current_period_start=now-timedelta(days=1),current_period_end=now+timedelta(days=2)))
        db.commit()
        # Legacy timestamp is deliberately different and remains unverified.
        legacy=ClientProgress(gym_id=ids['gym_a'],id_cliente=links['clients']['active'],peso_kg=68,
            fecha=datetime(2020,2,3,4,5,6),notas='Synthetic legacy private text excluded from projections')
        db.add(legacy);db.commit();legacy_id=legacy.id
        plan=SimpleNamespace(id=99999,gym_id=ids['recipient'],deleted_at=None,plan_json=json.dumps({'desayuno':{'alimentos':{'huevo':50}}}))
        meal={**resolve_consumed_meal(plan,ids['recipient'],'desayuno',MealSelection(include_fixed_menu=True),now=now),'completed':True}
        db.add(PersonalDiaryDay(user_id=ids['recipient'],local_date=today,water_ml=750,version=1,meals_json=json.dumps({'desayuno':meal}),created_at=now,updated_at=now));db.commit()
    app=application_engine(source_url,admin)
    expected={'profiles':profiles,'records':records,'today':today,'legacy_id':legacy_id,'consents':{},'links':{}}
    try:
        for name in profiles:
            with tenant_scope(ids[name]),Session(app) as db:
                saved=own.write_measurement(db,principal(ids[name]),records[name],MeasurementWrite(expected_version=0,
                    source_profile_id=profiles[name],measured_on=today,values={'peso_kg':71.5 if name=='recipient' else 83,'grasa_corporal_pct':21}))
            assert saved['source_kind']=='self_reported' and saved['version']==1
        for name,label in [('recipient','active'),('other','other_recipient')]:
            link=links['links'][label];expected['links'][name]=link
            with tenant_scope(ids[name]),Session(app) as db:
                granted=sharing.grant_consent(db,principal(ids[name]),link['link'],ConsentGrant(expected_consent_id=None,
                    expected_version=0,expected_link_version=link['version'],event='grant',protocol='progress_share_v1',
                    source_profile_id=profiles[name],categories={'weight':True,'body_fat':False,'lean_mass':False,'completion':True},
                    from_date=today,through_date=None,ongoing=True))
            first=granted['consent']
            if name=='recipient':
                with tenant_scope(ids[name]),Session(app) as db:
                    replaced=sharing.grant_consent(db,principal(ids[name]),link['link'],ConsentGrant(expected_consent_id=first['id'],
                        expected_version=1,expected_link_version=link['version'],event='grant',protocol='progress_share_v1',
                        source_profile_id=profiles[name],categories={'weight':True,'body_fat':False,'lean_mass':False,'completion':True},
                        from_date=today,through_date=today,ongoing=False))
                expected['consents'][name]=replaced['consent']
            else:
                with tenant_scope(ids[name]),Session(app) as db:
                    removed=sharing.withdraw_consent(db,principal(ids[name]),link['link'],ConsentWithdraw(expected_consent_id=first['id'],expected_version=1))
                expected['consents'][name]=removed['consent']
        with Session(admin) as db:
            assert db.scalar(select(ClientProgress).where(ClientProgress.id==legacy_id)).source_kind=='legacy_unverified'
            assert db.scalar(select(ClientProgress).where(ClientProgress.id==legacy_id)).measured_on is None
            assert db.query(ProgressConsent).count()==4
    finally:app.dispose()
    return expected


def verify_restored_progress32(admin,app,links,expected):
    from web.database.progress_policy import signature
    ids=links['ids'];today=expected['today'];active=expected['links']['recipient'];consent=expected['consents']['recipient']
    with admin.connect() as db:
        physical=signature(db)
        assert len(physical['functions'])==4 and all(not row[3] and row[4]==['search_path=pg_catalog'] for row in physical['functions'])
        assert db.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='progress_consents'")).one()==(True,True)
    with app.connect() as db:
        assert db.scalar(text('SELECT count(*) FROM progress_consents'))==0
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
    with tenant_scope(ids['recipient']),Session(app) as db:
        assert {row.user_id for row in db.scalars(select(ProgressConsent))}=={ids['recipient']}
        own_rows=db.scalars(select(ClientProgress).where(ClientProgress.record_key.is_not(None))).all()
        assert [row.record_key for row in own_rows]==[expected['records']['recipient']]
    with tenant_scope(ids['gym_a']),Session(app) as db:
        legacy=db.get(ClientProgress,expected['legacy_id'])
        assert legacy.source_kind=='legacy_unverified' and legacy.measured_on is None and legacy.recorded_by_id is None and legacy.recorded_at is None
        db.rollback()
        result=readers.shared_projection(db,principal(ids['gym_a']),active['client'] if 'client' in active else links['clients']['active'],active['link'],
            expected_id=consent['id'],expected_version=2,expected_link=active['version'],start=today,end=today)
        assert result['measurements']['items'][0]['record_key']==expected['records']['recipient']
        assert result['measurements']['items'][0]['values']=={'peso_kg':71.5}
        assert result['completion']['items']==[{'local_date':today.isoformat(),'registered_snapshots':1,'completed_snapshots':1,'ratio':1.0,'status':'observed'}]
        assert 'notas' not in json.dumps(result) and 'grasa_corporal_pct' not in json.dumps(result)
    with tenant_scope(ids['gym_b']),Session(app) as db,pytest.raises(HTTPException) as denied:
        readers.shared_projection(db,principal(ids['gym_b']),links['clients']['active'],active['link'],expected_id=consent['id'],expected_version=2,expected_link=2,start=today,end=today)
    assert denied.value.status_code==404
    withdrawn=expected['links']['other'];old=expected['consents']['other']
    with tenant_scope(ids['gym_a']),Session(app) as db,pytest.raises(HTTPException) as denied:
        readers.shared_projection(db,principal(ids['gym_a']),links['clients']['other_recipient'],withdrawn['link'],expected_id=old['id'],expected_version=2,expected_link=2,start=today,end=today)
    assert denied.value.status_code==409
    with tenant_scope(ids['recipient']),Session(app) as db:
        with pytest.raises(DBAPIError):db.execute(text("UPDATE progress_consents SET version=99 WHERE id=:id"),{'id':consent['id']})
        db.rollback()
    with tenant_scope(ids['recipient']),Session(app) as db:
        deleted=db.execute(text("DELETE FROM progress_consents WHERE id=:id"),{'id':consent['id']})
        assert deleted.rowcount==0
        assert db.scalar(select(ProgressConsent.id).where(ProgressConsent.id==consent['id']))==consent['id']
        db.rollback()
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
        assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==''
        assert db.scalar(text("SELECT current_setting('app.mfa_actor',true)"))==''
    return {'measurements_self_reported':2,'legacy_measurements_unverified':1,'consent_append_events':4,
        'current_grant':1,'withdrawn_latest':1,'selected_values_only':True,'sql_counts_only':True,'cross_gym_denied':True,
        'forbidden_update_delete':True,'no_session_capability_residue':True}
