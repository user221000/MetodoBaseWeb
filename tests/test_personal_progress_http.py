"""Real migrated32 factories, registration/login and explicit consent, offline.

Only delivery and the uncertainty seam are doubles. No dependency/auth/MFA
override, bearer mint, create_all-as-migration or artificial router mounting.
"""
from datetime import timedelta
from html import unescape
import importlib
import json
import re
from threading import Event
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from tests.progress32_fixtures import owned_database, REVISION
from tests.integration_schema_migrations import run_migration


@pytest.fixture(scope="module")
def progress_db(tmp_path_factory):
    with owned_database("sqlite",tmp_path_factory.mktemp("progress-http32")) as (url,engine):
        run_migration(url,"db_bootstrap.py","--revision",REVISION)
        @event.listens_for(engine,"connect")
        def enforce_fk(connection,record):connection.execute("PRAGMA foreign_keys=ON")
        engine.dispose()
        yield engine


@pytest.fixture(params=["web.main_web","api.app"])
def progress_http(progress_db,request,monkeypatch):
    from web.database import engine as database
    from web.database.models import Cliente,Subscription
    from web.services.personal_diary_service import local_today,_clock
    from web.services import email_service
    from web.settings import get_settings
    admin,application=progress_db if isinstance(progress_db,tuple) else (progress_db,progress_db)
    settings=get_settings();monkeypatch.setattr(settings,"BASE_URL","https://member.example.invalid")
    monkeypatch.setattr(settings,"RESEND_API_KEY","re_synthetic_offline_only")
    monkeypatch.setattr(database,"_engine",application)
    monkeypatch.setattr(database,"_SessionLocal",sessionmaker(bind=application,expire_on_commit=True,autoflush=False))
    mail=[];ready=Event()
    def send(recipient,subject,html,**kwargs):mail.append(html);ready.set();return True
    monkeypatch.setattr(email_service,"_send",send)
    number=int(uuid.uuid4().hex[:4],16)
    with TestClient(importlib.import_module(request.param).create_app(),raise_server_exceptions=False,
            client=(f"192.1.{number//256}.{number%256}",50000)) as client:
        identities={};headers={};emails={}
        for kind in ("gym","person","other"):
            email=uuid.uuid4().hex+"@example.invalid";password="Synthetic progress password 42!"
            response=client.post("/api/auth/registro",json={"email":email,"password":password,"nombre":"Synthetic","tipo":"gym" if kind=="gym" else "usuario"})
            assert response.status_code==200,"Real registration failed"
            login=client.post("/api/auth/login",json={"email":email,"password":password})
            assert login.status_code==200,"Real primary login failed"
            headers[kind]={"Authorization":"Bearer "+login.json()["token"]}
            me=client.get("/api/auth/me",headers=headers[kind]);assert me.status_code==200
            identities[kind]=me.json()["id"];emails[kind]=email
        ids={key:str(uuid.uuid4()) for key in ("client","profile","otherprofile")};now=_clock(None)
        with Session(admin) as db:
            db.add_all([Cliente(id_cliente=ids["client"],gym_id=identities["gym"],nombre="Professional source",activo=True),
                Cliente(id_cliente=ids["profile"],gym_id=identities["person"],nombre="Explicit own profile",activo=True),
                Cliente(id_cliente=ids["otherprofile"],gym_id=identities["other"],nombre="Other personal profile",activo=True)])
            db.add(Subscription(gym_id=identities["gym"],plan="clinica",status="active",provider="stripe",max_clientes=0,
                current_period_start=now-timedelta(days=1),current_period_end=now+timedelta(days=2)))
            db.commit()
        yield {**identities,**ids,"client_http":client,"headers":headers,"emails":emails,"mail":mail,"ready":ready,
            "engine":application,"admin":admin,"today":local_today(),"factory":request.param}


def accepted(case):
    client=case["client_http"];issue=client.post("/api/clientes/"+case["client"]+"/vinculacion/invitaciones",
        headers=case["headers"]["gym"],json={"recipient_email":case["emails"]["person"],"request_key":str(uuid.uuid4())})
    assert issue.status_code==202 and case["ready"].wait(5)
    token=re.search(r"#token=([A-Za-z0-9_-]{43})",unescape(case["mail"][-1])).group(1)
    accepted=client.post("/api/usuario/vinculaciones/aceptar",headers=case["headers"]["person"],json={"token":token,"expected_version":1,"confirm":True})
    assert accepted.status_code==200
    return issue.json()["link_id"]


def command(case,**changes):
    return {"expected_version":0,"source_profile_id":case["profile"],"measured_on":case["today"].isoformat(),"values":{"peso_kg":71.5,"grasa_corporal_pct":21},**changes}


def grant(case,link,**changes):
    body={"expected_consent_id":None,"expected_version":0,"expected_link_version":2,"event":"grant","protocol":"progress_share_v1",
        "source_profile_id":case["profile"],"categories":{"weight":True,"body_fat":False,"lean_mass":False,"completion":True},
        "from_date":case["today"].isoformat(),"through_date":None,"ongoing":True,**changes}
    response=case["client_http"].put("/api/usuario/vinculos/"+link+"/progreso/consentimiento",headers=case["headers"]["person"],json=body)
    return response,body


def shared_path(case,link,consent):
    return ("/api/clientes/"+case["client"]+"/vinculacion/"+link+"/progreso?expected_consent_id="+consent["id"]+
        "&expected_version="+str(consent["version"])+"&expected_link_version=2&from="+case["today"].isoformat()+"&through="+case["today"].isoformat())


def test_real_personal_context_measurement_cas_and_double_owner(progress_http):
    c=progress_http;client=c["client_http"];headers=c["headers"]["person"]
    context=client.get("/api/usuario/progreso/contexto",headers=headers)
    assert context.status_code==200 and context.json()["profiles"]["items"]==[{"id":c["profile"],"display_name":"Explicit own profile","active":True,"can_record":True}]
    key=str(uuid.uuid4());path="/api/usuario/progreso/mediciones/"+key
    created=client.put(path,headers=headers,json=command(c));assert created.status_code==200
    assert created.json()["source_kind"]=="self_reported" and created.json()["measured_on"]==c["today"].isoformat()
    assert created.json()["legacy_recording_timestamp"] is None and created.json()["values"]["peso_kg"]==71.5
    assert client.put(path,headers=headers,json=command(c)).status_code==409
    assert client.get(path,headers=c["headers"]["other"]).status_code==404
    assert client.put("/api/usuario/progreso/mediciones/"+str(uuid.uuid4()),headers=headers,json=command(c,source_profile_id=c["otherprofile"])).status_code==404
    altered=client.put(path,headers=headers,json=command(c,expected_version=1,values={"peso_kg":72}));assert altered.status_code==200 and altered.json()["version"]==2
    removed=client.post(path+"/retirar",headers=headers,json={"expected_version":2});assert removed.status_code==200 and removed.json()["version"]==3
    assert client.put(path,headers=headers,json=command(c,expected_version=3)).status_code==409


def test_exact_consent_selected_fields_and_withdrawal_survive_source_ineligibility(progress_http):
    from web.database.models import Usuario
    c=progress_http;client=c["client_http"];link=accepted(c)
    saved=client.put("/api/usuario/progreso/mediciones/"+str(uuid.uuid4()),headers=c["headers"]["person"],json=command(c));assert saved.status_code==200
    result,body=grant(c,link);assert result.status_code==200
    consent=result.json()["consent"];path=shared_path(c,link,consent)
    projection=client.get(path,headers=c["headers"]["gym"]);assert projection.status_code==200
    assert projection.json()["measurements"]["items"][0]["values"]=={"peso_kg":71.5}
    assert projection.json()["completion"]["items"]==[]
    assert c["otherprofile"] not in projection.text and "grasa_corporal_pct" not in projection.text and "notas" not in projection.text
    assert client.put("/api/usuario/vinculos/"+link+"/progreso/consentimiento",headers=c["headers"]["person"],json=body).status_code==409
    with Session(c["admin"]) as db:db.get(Usuario,c["gym"]).activo=False;db.commit()
    discovered=client.get("/api/usuario/progreso/consentimientos",headers=c["headers"]["person"])
    assert discovered.status_code==200 and discovered.json()["items"][0]["link_id"]==link
    withdrawal=client.post("/api/usuario/vinculos/"+link+"/progreso/consentimiento/retirar",headers=c["headers"]["person"],json={"expected_consent_id":consent["id"],"expected_version":1})
    assert withdrawal.status_code==200 and withdrawal.json()["consent"]["event"]=="withdraw"
    with Session(c["admin"]) as db:db.get(Usuario,c["gym"]).activo=True;db.commit()
    assert client.get(path,headers=c["headers"]["gym"]).status_code==409
    other=client.get("/api/usuario/vinculos/"+link+"/progreso/consentimiento",headers=c["headers"]["other"])
    assert other.status_code==404


def test_observed_completion_comes_from_registered_snapshots_not_four_meals(progress_http):
    from web.database.models import PlanGenerado
    c=progress_http;client=c["client_http"];headers=c["headers"]["person"]
    with Session(c["admin"]) as db:
        plan=PlanGenerado(gym_id=c["person"],id_cliente=c["profile"],plan_json=json.dumps({"desayuno":{"alimentos":{"huevo":50}}}))
        db.add(plan);db.commit();plan_id=plan.id
    day="/api/usuario/diario/"+c["today"].isoformat()
    write=client.patch(day,headers=headers,json={"operation":"meal","expected_version":0,"source_plan_id":plan_id,"meal":"desayuno","selections":{"include_fixed_menu":True}})
    assert write.status_code==200
    query="/api/usuario/progreso/completados?from="+c["today"].isoformat()+"&through="+c["today"].isoformat()
    observed=client.get(query,headers=headers);assert observed.status_code==200
    assert observed.json()["items"]==[{"local_date":c["today"].isoformat(),"registered_snapshots":1,"completed_snapshots":0,"ratio":0.0,"status":"observed"}]
    completed=client.patch(day,headers=headers,json={"operation":"completion","expected_version":1,"meal":"desayuno","completed":True});assert completed.status_code==200
    assert client.get(query,headers=headers).json()["items"][0]["ratio"]==1


@pytest.mark.parametrize("invalid",[{"values":{"peso_kg":True}},{"measured_on":0},{"user_id":"not-authority"},{"values":{"peso_kg":300.01}}])
def test_invalid_or_untrusted_input_is_rejected_whole(progress_http,invalid):
    c=progress_http;client=c["client_http"];key=str(uuid.uuid4());path="/api/usuario/progreso/mediciones/"+key
    response=client.put(path,headers=c["headers"]["person"],json=command(c,**invalid));assert response.status_code==422
    assert client.get(path,headers=c["headers"]["person"]).status_code==404


def test_commit_ack_uncertainty_is_visible_and_exact_readback_prevents_adoption(progress_http,monkeypatch,caplog):
    from web.database import engine as database
    c=progress_http;client=c["client_http"];real=Session.commit;once=True
    class Uncertain(Session):
        def commit(self):
            nonlocal once
            real(self)
            if once and self.info.get("progress_commit_attempted"):
                once=False;raise RuntimeError("PRIVATE_PROGRESS_PARAMETERS")
    monkeypatch.setattr(database,"_SessionLocal",sessionmaker(bind=c["engine"],class_=Uncertain,expire_on_commit=True))
    path="/api/usuario/progreso/mediciones/"+str(uuid.uuid4())
    result=client.put(path,headers=c["headers"]["person"],json=command(c));assert result.status_code==503
    assert result.json()["detail"]["code"]=="progress_unconfirmed"
    verified=client.get(path,headers=c["headers"]["person"]);assert verified.status_code==200 and verified.json()["version"]==1
    assert "PRIVATE_PROGRESS_PARAMETERS" not in result.text+caplog.text


def test_progress_export_is_own_eighth_dataset_and_uuid_keyset(progress_http):
    c=progress_http;client=c["client_http"];link=accepted(c);result,_=grant(c,link);assert result.status_code==200
    exported=client.get("/api/usuario/privacidad/exportar?limit=1",headers=c["headers"]["person"])
    assert exported.status_code==200
    record=exported.json()["progress_consents"]["records"][0]
    assert record["link_id"]==link and record["id"]==result.json()["consent"]["id"]
    assert set(record)=={"id","link_id","version","event","protocol","link_version","source_profile_id","categories","from_date","through_date","ongoing","created_at"}
    assert exported.json()["scope"]["max_response_bytes"]==1064960
    assert client.get("/api/usuario/privacidad/exportar",headers=c["headers"]["other"]).json()["progress_consents"]["records"]==[]


@pytest.mark.parametrize("tipo",["gym","usuario"])
def test_own_consent_discovery_and_withdrawal_do_not_adopt_owner_personal_space(progress_http,tipo):
    from web.database.models import Usuario,UserRole
    c=progress_http;client=c["client_http"];link=accepted(c);result,_=grant(c,link);assert result.status_code==200
    consent=result.json()["consent"]
    with Session(c["admin"]) as db:
        actor=db.get(Usuario,c["person"]);actor.tipo=tipo;actor.role=UserRole.OWNER;actor.session_version+=1;db.commit()
    assert client.get("/api/usuario/progreso/consentimientos",headers=c["headers"]["person"]).status_code==401
    fresh=client.post("/api/auth/login",json={"email":c["emails"]["person"],"password":"Synthetic progress password 42!"})
    assert fresh.status_code==200
    headers={"Authorization":"Bearer "+fresh.json()["token"]}
    personal=client.get("/api/usuario/progreso/contexto",headers=headers)
    assert personal.status_code==(403 if tipo=="gym" else 409)
    discover=client.get("/api/usuario/progreso/consentimientos",headers=headers)
    assert discover.status_code==200 and discover.json()["items"][0]["link_id"]==link
    exact=client.get("/api/usuario/vinculos/"+link+"/progreso/consentimiento",headers=headers)
    assert exact.status_code==200 and exact.json()["scope"]=="own_consent_metadata_only"
    assert exact.json()["capabilities"]=={"withdraw":True,"grant":False} and exact.json()["effective"] is None
    withdrawn=client.post("/api/usuario/vinculos/"+link+"/progreso/consentimiento/retirar",headers=headers,json={"expected_consent_id":consent["id"],"expected_version":1})
    assert withdrawn.status_code==200 and withdrawn.json()["consent"]["event"]=="withdraw"
    assert client.get("/api/usuario/vinculos/"+str(uuid.uuid4())+"/progreso/consentimiento",headers=headers).status_code==404
