"""Real concurrent SQLite HTTP; clocks/factors stay real during business."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.nutrition35_fixtures import followup_db, followup_http, candidate, create, PASSWORD
from tests.mfa31_contract_client import MfaContractClient
from web.database.models import FollowupTask, FollowupTaskEvent, PlanGenerado


def _parallel(functions):
    barrier=Barrier(len(functions))
    def start(function):
        barrier.wait(timeout=10)
        return function()
    with ThreadPoolExecutor(max_workers=len(functions)) as workers:
        return list(workers.map(start,functions))


def test_two_identical_explicit_keys_have_one_durable_operation(followup_http):
    c=followup_http;raw=c["raw"];evidence=candidate(c);key=str(uuid.uuid4())
    body={"client_id":c["profile"],"cause":"no_saved_plan","cause_evidence_hash":evidence["cause_evidence_hash"],
        "next_step":"review_plan_history","assignee_id":None,"expected_active_task_id":None,"confirm":True}
    def request():return raw.post("/api/seguimiento/tareas",json=body,headers={"Idempotency-Key":key})
    results=_parallel([request,request])
    assert [r.status_code for r in results]==[200,200]
    assert sorted(r.json()["operation"]["replayed"] for r in results)==[False,True]
    assert len({r.json()["operation"]["id"] for r in results})==1
    with Session(c["admin"]) as db:
        assert len(db.scalars(select(FollowupTaskEvent).where(FollowupTaskEvent.gym_id==c["user"])).all())==1


def test_concurrent_edit_and_complete_have_one_cas_winner(followup_http):
    c=followup_http;raw=c["raw"];made,_,_=create(c);assert made.status_code==200
    identifier=made.json()["task"]["id"]
    edit=lambda:raw.patch("/api/seguimiento/tareas/"+identifier,json={"expected_version":1,"next_step":"review_client_record",
        "assignee_id":c["member"],"confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    complete=lambda:raw.post("/api/seguimiento/tareas/"+identifier+"/completar",json={"expected_version":1,"outcome":"review_recorded",
        "confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    results=_parallel([edit,complete])
    assert sorted(r.status_code for r in results)==[200,409]
    assert next(r for r in results if r.status_code==409).json()["detail"]["code"]=="followup_version_conflict"
    with Session(c["admin"]) as db:
        assert db.get(FollowupTask,identifier).version==2
        assert len(db.scalars(select(FollowupTaskEvent).where(FollowupTaskEvent.task_id==identifier)).all())==2


def test_new_plan_invalidates_observed_no_plan_cause_without_creating_task(followup_http):
    c=followup_http;raw=c["raw"];evidence=candidate(c)
    with Session(c["admin"]) as db:
        db.add(PlanGenerado(gym_id=c["user"],id_cliente=c["profile"],plan_json='{"synthetic":true}',fecha_generacion=datetime.now(timezone.utc)))
        db.commit()
    response=raw.post("/api/seguimiento/tareas",json={"client_id":c["profile"],"cause":"no_saved_plan",
        "cause_evidence_hash":evidence["cause_evidence_hash"],"next_step":"review_plan_history","assignee_id":None,
        "expected_active_task_id":None,"confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert response.status_code==409 and response.json()["detail"]["code"]=="followup_cause_changed"
    with Session(c["admin"]) as db:
        assert db.scalar(select(FollowupTask.id).where(FollowupTask.gym_id==c["user"])) is None


def test_other_canonical_owner_gets_identical_foreign_missing_denial(followup_http):
    c=followup_http;raw=c["raw"];made,_,_=create(c);assert made.status_code==200
    identifier=made.json()["task"]["id"]
    email=uuid.uuid4().hex+"@example.invalid"
    # Public registration must not inherit the first actor's ambient bearer.
    # The real subject-binding guard correctly rejects that mixed setup.
    raw.headers.pop("Authorization")
    registered=raw.post("/api/auth/registro",json={"email":email,"password":PASSWORD,"nombre":"Other synthetic manager","tipo":"gym"})
    assert registered.status_code==200
    response=raw.post("/api/auth/login",json={"email":email,"password":PASSWORD});assert response.status_code==200
    raw.headers["Authorization"]="Bearer "+response.json()["token"]
    me=raw.get("/api/auth/me");assert me.status_code==200
    other=MfaContractClient(raw,{"id":me.json()["id"]},c["factory"],PASSWORD);other.authenticate()
    foreign=raw.get("/api/seguimiento/tareas/"+identifier)
    missing=raw.get("/api/seguimiento/tareas/"+str(uuid.uuid4()))
    assert foreign.status_code==missing.status_code==404 and foreign.json()==missing.json()
    changed=raw.post("/api/seguimiento/tareas/"+identifier+"/cancelar",json={"expected_version":1,"reason":"duplicate",
        "confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert changed.status_code==404
    listed=raw.get("/api/seguimiento/tareas")
    assert listed.status_code==200 and listed.json()["items"]==[]
    with Session(c["admin"]) as db:
        assert db.get(FollowupTask,identifier).version==1
