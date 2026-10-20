"""Independent actual-PG cookie/bearer and MFA proof boundaries."""
import json
import pytest
from sqlalchemy import inspect,select,text,func
from sqlalchemy.orm import Session
from tests.integration_nutrition35_postgres import followup_db,followup_http,blank_pool
from tests import test_browser_session31_transport as wire
from tests import followup34_http as historical
from web import auth
from web.database.models import RefreshToken
from web.database.schema_control import verify_runtime_schema
browser=wire.browser

def bearer(access):
    return {'Authorization':'Bearer '+access}

def test_cookie_B_never_selects_resource_actor_A_and_logout_only_revokes_B(browser):
    c=browser;raw=c['raw'];access_A=raw.headers['Authorization']
    actor_A=raw.get('/api/auth/me').json()['id']
    _,registered=wire.account(c,browser_mode=True);access_B=wire.pair(registered);proof_B=wire.cookie(c)
    identity_B=raw.get('/api/auth/me',headers=bearer(access_B));assert identity_B.status_code==200
    actor_B=identity_B.json()['id'];assert actor_B!=actor_A
    assert raw.get('/api/auth/me').json()['id']==actor_A
    raw.headers.pop('Authorization',None)
    assert raw.get('/api/auth/me').status_code==401
    raw.headers['Authorization']=access_A
    exported=raw.get('/api/usuario/privacidad/exportar',headers=bearer(access_B))
    assert exported.status_code==200 and exported.json()['account']['id']==actor_B
    wire.private(exported)
    assert all(record.get('id_cliente')!=c['profile'] for record in exported.json()['profiles']['records'])
    closed=wire.post(c,'/api/auth/browser/logout')
    assert closed.status_code==200 and closed.json()=={'success':True,'server_confirmed':True,'session_mode':'browser'}
    assert auth.verificar_refresh_token(proof_B) is None and auth.verificar_token(access_B) is None
    assert raw.get('/api/auth/me',headers=bearer(access_B)).status_code==401
    preserved=raw.get('/api/auth/me');assert preserved.status_code==200 and preserved.json()['id']==actor_A

def test_rejected_migration_and_duplicate_cookie_leave_exact_proof_unconsumed(browser):
    c=browser;_,registered=wire.account(c);old=registered.json()['refresh_token']
    rejected=wire.post(c,'/api/auth/browser/migrate',{'refresh_token':old,'extra':True})
    assert rejected.status_code==422 and auth.verificar_refresh_token(old) is not None
    wire.private(rejected)
    migrated=wire.post(c,'/api/auth/browser/migrate',{'refresh_token':old});wire.pair(migrated)
    assert auth.verificar_refresh_token(old) is None
    proof=wire.cookie(c)
    headers={**wire.HEADERS,'Cookie':'__Host-mb_refresh='+proof+'; __Host-mb_refresh='+proof}
    duplicate=c['raw'].post('/api/auth/refresh',json={},headers=headers)
    assert duplicate.status_code==401 and duplicate.json()['detail']['code']=='browser_session_unavailable'
    assert auth.verificar_refresh_token(proof) is not None
    rotated=c['raw'].post('/api/auth/refresh',json={},headers={**wire.HEADERS,'Cookie':'__Host-mb_refresh='+proof})
    wire.pair(rotated);current=wire.cookie(c)
    assert current!=proof and auth.verificar_refresh_token(proof) is None
    stale=wire.post(c,'/api/auth/browser/migrate',{'refresh_token':old})
    assert stale.status_code==401
    assert auth.verificar_refresh_token(current) is not None

def test_MFA_202_clears_cookie_without_minting_any_refresh_row(browser):
    c=browser;_,registered=wire.account(c,browser_mode=True);wire.pair(registered)
    with Session(c['admin']) as db:
        before=db.scalar(select(func.count()).select_from(RefreshToken))
    challenged=wire.post(c,'/api/auth/login',{'email':c['client'].principal['email'],'password':historical.PASSWORD})
    assert challenged.status_code==202
    data=challenged.json();assert set(data)=={'mfa_required','challenge','expires_at','methods','session_mode'}
    assert data['mfa_required'] is True and data['session_mode']=='browser'
    assert 'token' not in data and 'refresh_token' not in data
    assert c['raw'].cookies.get('__Host-mb_refresh') is None
    wire.private(challenged)
    with Session(c['admin']) as db:
        assert db.scalar(select(func.count()).select_from(RefreshToken))==before
    no_cookie=wire.post(c,'/api/auth/refresh')
    assert no_cookie.status_code==401 and no_cookie.json()['detail']['code']=='browser_session_unavailable'

@pytest.fixture(autouse=True)
def exact35_restricted_pool_witness(followup_http,record_property):
    case=followup_http;engine=case['engine']
    assert engine.dialect.name=='postgresql'
    assert engine.pool.size()==1 and engine.pool._max_overflow==0
    with engine.connect() as db:
        flags=tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') FROM pg_roles WHERE rolname=current_user")).one())
        assert flags==(False,False,False,False,False)
        forced=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
        tables=len(inspect(db).get_table_names())
        head=db.scalar(text('SELECT version_num FROM alembic_version'))
        assert forced==28 and tables==38 and head=='20261020_nutrition_profile'
    # This check gets its own checkout; never nest it inside a pool1 connection.
    verify_runtime_schema(engine)
    record_property('PG35_restricted_witness',json.dumps({'dialect':'postgresql','flags4_and_membership':[False]*5,'FORCE_RLS_tables':forced,'physical_tables':tables,'head':head,'pool_size':1,'max_overflow':0,'factory':case['factory_name']}))
    yield
    blank_pool(engine)
