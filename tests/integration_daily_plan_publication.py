"""One owned migrated head30 UUID, restricted app role, real diary/publication HTTP."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import event,text
from sqlalchemy.orm import Session
import pytest

from tests.integration_schema_migrations import migration_database,run_migration
from tests.integration_provider_subjects import application_engine
from tests.integration_client_link_services import case
from tests.integration_client_link_http import http
from tests.test_publication_diary_consumption import prepare_publication


@pytest.fixture(scope='module')
def link_db(tmp_path_factory):
    generator=migration_database.__wrapped__(SimpleNamespace(param='postgresql'),tmp_path_factory.mktemp('r24-pg'))
    url,admin=next(generator);app=None
    root=Path(os.environ['R24_PG_OUTPUT']);root.mkdir(parents=True,exist_ok=True)
    names=['web/personal_diary_schemas.py','web/routes/personal_diary.py','web/services/personal_diary_service.py',
        'web/services/personal_diary_persistence.py','web/services/client_link_plans.py','web/services/client_link_context.py',
        'web/services/client_link_projection.py','web/database/models.py','web/database/tenant_context.py','web/database/tenant_policy.py',
        'tests/integration_daily_plan_publication.py','tests/test_publication_diary_consumption.py']
    project=Path(__file__).resolve().parents[1]
    snapshot=lambda:{name:hashlib.sha256((project/name).read_bytes()).hexdigest() for name in names}
    start=snapshot();resource={'owned_database':admin.url.database,'source_before':start}
    try:
        run_migration(url,'db_bootstrap.py','--revision','head')
        app=application_engine(url,admin)
        with app.connect() as db:
            role=db.execute(text('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user')).one()
            assert role==(False,False)
            assert db.execute(text("SELECT count(*) FROM pg_class WHERE relname IN ('personal_diary_days','client_account_links','client_plan_publications') AND relrowsecurity AND relforcerowsecurity")).scalar_one()==3
            assert db.execute(text("SELECT count(*) FROM pg_class WHERE relname='personal_diary_days' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)")).scalar_one()==0
            resource.update(role_super=False,role_bypass=False,app_owns_diary=False,force_rls_families=3,
                runtime_revision=db.execute(text('SELECT version_num FROM alembic_version')).scalar_one())
        yield admin,app
    finally:
        if app is not None:app.dispose()
        generator.close();resource['source_after']=snapshot();assert resource['source_after']==start
        import psycopg2
        with psycopg2.connect(os.environ['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as control,control.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(resource['owned_database'],));assert cursor.fetchone()[0]==0
        resource['owned_database_absent_after']=True
        (root/'resource-and-source.json').write_bytes((json.dumps(resource,indent=2)+'\n').encode())


def test_published_source_commit_is_personal_only_double_owner_scoped_and_revocation_blocks_new_reads(http):
    from web.database.models import PersonalDiaryDay
    from web.database.tenant_context import tenant_scope
    client=http['client_http'];day,body=prepare_publication(http);statements=[]
    def observe(conn,cursor,statement,parameters,context,many):statements.append(statement)
    event.listen(http['app'],'before_cursor_execute',observe)
    try:
        saved=client.patch(day,headers=http['headers']['person'],json=body);assert saved.status_code==200,saved.text
    finally:event.remove(http['app'],'before_cursor_execute',observe)
    assert saved.json()['meals']['desayuno']['source_context']['publication_id']==body['publication_id']
    assert not [s for s in statements if s.lstrip().upper().startswith(('INSERT INTO CLIENTES','UPDATE CLIENTES','INSERT INTO PLANES_GENERADOS','UPDATE PLANES_GENERADOS'))]
    assert client.patch(day,headers=http['headers']['other'],json=body).status_code==404
    with Session(http['app']) as db:assert db.query(PersonalDiaryDay).count()==0
    with tenant_scope(http['other']),Session(http['app']) as db:assert db.query(PersonalDiaryDay).count()==0
    with tenant_scope(http['person']),Session(http['app']) as db:assert db.query(PersonalDiaryDay).filter_by(user_id=http['person']).count()==1
    revoked=client.request('DELETE','/api/usuario/vinculos/'+body['link_id'],headers=http['headers']['person'],json={'expected_version':2});assert revoked.status_code==200
    assert client.patch(day,headers=http['headers']['person'],json={**body,'expected_version':1}).status_code==404
    assert client.get(day,headers=http['headers']['person']).json()['meals']==saved.json()['meals']
    removed=client.patch(day,headers=http['headers']['person'],json={'operation':'remove_meal','expected_version':1,'meal':'desayuno'})
    assert removed.status_code==200 and removed.json()['meals']=={}
