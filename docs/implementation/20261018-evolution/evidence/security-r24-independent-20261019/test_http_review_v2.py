"""Independent R24 synthetic HTTP negatives, both real factories, SQLite only."""
from pathlib import Path
from types import SimpleNamespace
import copy,json
import pytest
from sqlalchemy import event,select
from sqlalchemy.orm import Session
from tests.integration_schema_migrations import migration_database,run_migration
from tests.integration_provider_subjects import application_engine
from tests.integration_client_link_services import case,source
from tests.integration_client_link_http import http
from tests.test_publication_diary_consumption import prepare_publication
from web.database.tenant_context import configure_tenant_engine
from web.database.models import Usuario,ClientPlanPublication,PersonalDiaryDay,PlanGenerado,Cliente

ROOT=Path('F:/mb-r24-sec')
@pytest.fixture(scope='module')
def link_db(tmp_path_factory):
    own=tmp_path_factory.mktemp('r24-security-sqlite')
    gen=migration_database.__wrapped__(SimpleNamespace(param='sqlite'),own)
    url,admin=next(gen);app=None
    try:
        run_migration(url,'db_bootstrap.py','--revision','head')
        @event.listens_for(admin,'connect')
        def foreign_keys(conn,record):conn.execute('PRAGMA foreign_keys=ON')
        admin.dispose();app=configure_tenant_engine(application_engine(url,admin));yield admin,app
    finally:
        if app is not None and app is not admin:app.dispose()
        gen.close()
        (Path(__file__).parent/'sqlite-resource.json').write_text(json.dumps({'engine_disposed':True,'only_sqlite':True,'database_filename':own.name+'/migration.db','source_root':str(ROOT)}),'utf-8')

def current(http,day):
    response=http['client_http'].get(day,headers=http['headers']['person']);assert response.status_code==200
    return response.json()
def empty(http,day):
    value=current(http,day);assert value['version']==0 and value['meals']=={}
def own_rows(http):
    with Session(http['admin']) as db:
        return {'plans':[(p.id,p.gym_id,p.id_cliente,p.plan_json) for p in db.scalars(select(PlanGenerado).where(PlanGenerado.gym_id==http['gym']))],
            'clients':[(c.id_cliente,c.gym_id,c.nombre) for c in db.scalars(select(Cliente).where(Cliente.gym_id==http['gym']))]}

def test_replacement_with_same_publication_version_still_rejects_obsolete_identity(http):
    day,body=prepare_publication(http);client=http['client_http']
    replacement,_,_=source(http,marker='huevo',pdf=False)
    reply=client.post('/api/clientes/'+http['client']+'/vinculacion/'+body['link_id']+'/publicaciones',headers=http['headers']['gym'],
        json={'plan_id':replacement,'expected_link_version':2,'expected_publication_version':1,'expected_publication_id':body['publication_id']})
    assert reply.status_code==200
    assert reply.json()['version']==body['expected_publication_version']==1
    assert reply.json()['publication_id']!=body['publication_id']
    response=client.patch(day,headers=http['headers']['person'],json=body)
    assert response.status_code==404;empty(http,day)
    latest={**body,'publication_id':reply.json()['publication_id']}
    previous=own_rows(http);saved=client.patch(day,headers=http['headers']['person'],json=latest)
    assert saved.status_code==200 and saved.json()['version']==1
    assert own_rows(http)==previous
    assert saved.json()['meals']['desayuno']['source_context']['publication_id']==latest['publication_id']

def test_persisted_source_owner_parent_invalidates_consumption_despite_stale_browser_capability(http):
    day,body=prepare_publication(http)
    with Session(http['admin']) as db:
        owner=db.get(Usuario,http['gym']);owner.team_gym_id=http['othergym'];db.commit()
    response=http['client_http'].patch(day,headers=http['headers']['person'],json=body)
    assert response.status_code==404;empty(http,day)

def test_session_revocation_after_source_read_rejects_old_bearer_before_diary_mutation(http):
    day,body=prepare_publication(http)
    with Session(http['admin']) as db:
        actor=db.get(Usuario,http['person']);actor.session_version+=1;db.commit()
    response=http['client_http'].patch(day,headers=http['headers']['person'],json=body)
    assert response.status_code==401
    with Session(http['admin']) as db:assert db.scalar(select(PersonalDiaryDay).where(PersonalDiaryDay.user_id==http['person'])) is None

def test_projection_digest_tamper_rejects_whole_write_and_does_not_emit_content(http,monkeypatch):
    day,body=prepare_publication(http)
    # The real SQLite immutable trigger correctly blocks UPDATE. Inject only
    # a corrupt loaded-value seam after the actual authorized locked reader;
    # do not disable DDL guards or rewrite any table to prepare this probe.
    from web.services import client_link_plans
    actual=client_link_plans._publication
    def corrupt(db,link,*args,**kwargs):
        pub=actual(db,link,*args,**kwargs)
        if pub is None:return None
        fields=('id','publication_version','source_plan_id','published_at','plan_json','plan_sha256')
        values={key:getattr(pub,key) for key in fields};values['plan_json']=values['plan_json'].replace('50','51',1)
        return SimpleNamespace(**values)
    monkeypatch.setattr(client_link_plans,'_publication',corrupt)
    response=http['client_http'].patch(day,headers=http['headers']['person'],json=body)
    assert response.status_code==409 and response.json()['detail']['code']=='member_publication_requires_review'
    assert 'plan_json' not in response.text and 'alimentos' not in response.text;empty(http,day)

def test_snapshot_export_is_minimal_and_removal_after_revocation_needs_no_professional_source(http,monkeypatch):
    from web.services import client_link_plans
    day,body=prepare_publication(http);client=http['client_http']
    saved=client.patch(day,headers=http['headers']['person'],json=body);assert saved.status_code==200
    snapshot=saved.json()['meals']['desayuno'];context=snapshot['source_context']
    assert set(context)=={'kind','link_id','publication_id','link_version','publication_version','published_at'}
    assert set(snapshot)=={'source_plan_id','meal','selections','foods','totals','recorded_at','completed','source_context'}
    water=client.patch(day,headers=http['headers']['person'],json={'operation':'water','expected_version':1,'water_ml':725});assert water.status_code==200
    revoked=client.request('DELETE','/api/usuario/vinculos/'+body['link_id'],headers=http['headers']['person'],json={'expected_version':2});assert revoked.status_code==200
    exported=client.get('/api/usuario/privacidad/exportar',headers=http['headers']['person']);assert exported.status_code==200
    rows=exported.json()['personal_diary']['records'];assert len(rows)==1 and rows[0]['meals']['desayuno']==snapshot
    assert client.get('/api/usuario/privacidad/exportar',headers=http['headers']['other']).json()['personal_diary']['records']==[]
    def forbidden(*a,**k):raise AssertionError('Removal tried professional source access')
    monkeypatch.setattr(client_link_plans,'consumption_source',forbidden)
    removed=client.patch(day,headers=http['headers']['person'],json={'operation':'remove_meal','expected_version':2,'meal':'desayuno'})
    assert removed.status_code==200
    assert removed.json()['meals']=={} and removed.json()['water_ml']==725 and removed.json()['version']==3
    assert current(http,day)==removed.json()

def test_precommit_failure_rolls_back_and_logs_only_technical_class(http,monkeypatch,caplog):
    day,body=prepare_publication(http);original=Session.commit;marker='SYNTHETIC_SQL_VAR_TOKEN_EMAIL@example.invalid'
    def fail(db):
        if any(isinstance(row,PersonalDiaryDay) and row.user_id==http['person'] for row in db.identity_map.values()):raise RuntimeError(marker)
        return original(db)
    monkeypatch.setattr(Session,'commit',fail)
    response=http['client_http'].patch(day,headers=http['headers']['person'],json=body)
    assert response.status_code==503 and response.json()['detail']['code']=='diary_save_unconfirmed'
    assert marker not in caplog.text and marker not in response.text
    assert 'Diary save failed class=RuntimeError' in caplog.text
    empty(http,day)

def test_diary_cas_checks_before_replacing_another_personal_snapshot(http):
    day,body=prepare_publication(http);client=http['client_http']
    first=client.patch(day,headers=http['headers']['person'],json=body);assert first.status_code==200
    stale={**body,'meal':'cena'}
    response=client.patch(day,headers=http['headers']['person'],json=stale)
    assert response.status_code==409 and response.json()['detail']['code']=='diary_version_conflict'
    assert current(http,day)==first.json()

def test_duplicate_click_server_cas_has_exactly_one_confirmed_personal_change(http):
    day,body=prepare_publication(http);client=http['client_http'];before=own_rows(http)
    first=client.patch(day,headers=http['headers']['person'],json=body);assert first.status_code==200
    again=client.patch(day,headers=http['headers']['person'],json=copy.deepcopy(body));assert again.status_code==409
    assert current(http,day)==first.json() and own_rows(http)==before

def test_actual_sqlite_guard_blocks_publication_projection_update(http):
    from sqlalchemy.exc import IntegrityError
    day,body=prepare_publication(http)
    with Session(http['admin']) as db:
        pub=db.get(ClientPlanPublication,body['publication_id']);before=pub.plan_json
        pub.plan_json=before.replace('50','51',1)
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
        assert db.get(ClientPlanPublication,body['publication_id']).plan_json==before
    empty(http,day)
