"""Actual32 RLS/pool1/HTTP source projection, own UUID only, no load/providers."""
from datetime import timedelta
import json
import os
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from tests.progress32_fixtures import owned_database, REVISION
from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
from tests.test_personal_progress_http import progress_http, accepted, command, grant, shared_path


@pytest.fixture(scope="module")
def progress_db(tmp_path_factory):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):pytest.skip("Explicit own synthetic PostgreSQL profile required")
    with owned_database("postgresql",tmp_path_factory.mktemp("progress-pg32")) as (url,admin):
        run_migration(url,"db_bootstrap.py","--revision",REVISION)
        app=application_engine(url,admin)
        try:
            with app.connect() as db:
                assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one())==(False,False,False,False)
                assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))==26
            yield admin,app
        finally:app.dispose()


def make_source(c):
    from web.database.models import PlanGenerado
    client=c["client_http"];headers=c["headers"]["person"]
    with Session(c["admin"]) as db:
        plan=PlanGenerado(gym_id=c["person"],id_cliente=c["profile"],plan_json=json.dumps({"desayuno":{"alimentos":{"huevo":50}}}))
        db.add(plan);db.commit();plan_id=plan.id
    response=client.patch("/api/usuario/diario/"+c["today"].isoformat(),headers=headers,json={"operation":"meal","expected_version":0,"source_plan_id":plan_id,"meal":"desayuno","selections":{"include_fixed_menu":True}})
    assert response.status_code==200
    key=str(uuid.uuid4());response=client.put("/api/usuario/progreso/mediciones/"+key,headers=headers,json=command(c))
    assert response.status_code==200
    link=accepted(c);result,_=grant(c,link);assert result.status_code==200
    return link,result.json()["consent"]


def blank_pool(app):
    with app.connect() as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==""
        assert db.scalar(text("SELECT current_setting('app.client_invitation_digest',true)"))==""
        assert db.scalar(text("SELECT current_setting('app.mfa_actor',true)"))==""


def test_same_connection_pool1_projects_only_selected_scalars_and_cannot_use_a_fake_actor_guc(progress_http):
    c=progress_http;link,consent=make_source(c);descriptions=[]
    def observed(connection,cursor,statement,parameters,context,many):
        if "WITH days AS MATERIALIZED" in statement:
            descriptions.append(tuple(column[0] for column in cursor.description))
    event.listen(c["engine"],"after_cursor_execute",observed)
    try:result=c["client_http"].get(shared_path(c,link,consent),headers=c["headers"]["gym"])
    finally:event.remove(c["engine"],"after_cursor_execute",observed)
    assert result.status_code==200
    assert result.json()["measurements"]["items"][0]["values"]=={"peso_kg":71.5}
    assert result.json()["completion"]["items"][0]["registered_snapshots"]==1
    assert descriptions==[("local_date","registered","completed","valid")]
    assert all(word not in result.json() for word in ("Session","Connection","meals_json","foods","notas"))
    assert c["engine"].pool.size()==1 and c["engine"].pool.checkedout()==0
    with c["engine"].begin() as db:
        db.execute(text("SELECT set_config('app.current_tenant',:gym,true)"),{"gym":c["gym"]})
        db.execute(text("SELECT set_config('app.progress_actor',:fake,true)"),{"fake":c["person"]})
        assert db.scalar(text("SELECT count(*) FROM personal_diary_days WHERE user_id=:id"),{"id":c["person"]})==0
        assert db.scalar(text("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'r25_%' AND p.prosecdef"))==0
    blank_pool(c["engine"])


def test_aborted_source_statement_restores_context_before_visible_failure_and_reuse(progress_http,monkeypatch):
    from web.services import progress_readers as readers
    c=progress_http;link,consent=make_source(c)
    monkeypatch.setattr(readers,"_counts_sql",lambda dialect:text("SELECT 1/0"))
    failed=c["client_http"].get(shared_path(c,link,consent),headers=c["headers"]["gym"])
    assert failed.status_code==409 and failed.json()["detail"]["code"]=="progress_source_requires_review"
    assert "peso_kg" not in failed.text
    blank_pool(c["engine"])
    assert c["client_http"].get("/api/auth/me",headers=c["headers"]["other"]).status_code==200


def test_withdraw_after_inactive_source_is_durable_and_cannot_be_read_with_stale_scope(progress_http):
    from web.database.models import Usuario,ProgressConsent
    c=progress_http;link,consent=make_source(c)
    with Session(c["admin"]) as db:db.get(Usuario,c["gym"]).activo=False;db.commit()
    withdrawn=c["client_http"].post("/api/usuario/vinculos/"+link+"/progreso/consentimiento/retirar",headers=c["headers"]["person"],json={"expected_consent_id":consent["id"],"expected_version":1})
    assert withdrawn.status_code==200
    with Session(c["admin"]) as db:
        db.get(Usuario,c["gym"]).activo=True;db.commit()
        assert [row.event for row in db.scalars(select(ProgressConsent).where(ProgressConsent.link_id==link).order_by(ProgressConsent.version))]==["grant","withdraw"]
    failed=c["client_http"].get(shared_path(c,link,consent),headers=c["headers"]["gym"])
    assert failed.status_code==409
    blank_pool(c["engine"])
