"""Both mounted factories and durable wire34 operations, no outbound ports."""
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from tests.nutrition35_fixtures import followup_db, followup_http, candidate, create, PASSWORD
from web.database.models import FollowupTask, FollowupTaskEvent, Usuario


def test_full_mfa_context_and_create_edit_complete_history_replay(followup_http):
    c = followup_http; raw = c["raw"]
    context = raw.get("/api/seguimiento/contexto")
    assert context.status_code == 200
    assert context.json()["scope"] == "gym" and context.json()["timezone"] == "America/Mexico_City"
    made, body, key = create(c)
    assert made.status_code == 200, "create34 HTTP "+str(made.status_code)
    task = made.json()["task"]
    assert task["version"] == 1 and task["responsible"]["id"] == c["member"]
    identifier = task["id"]
    replay = raw.post("/api/seguimiento/tareas", json=body, headers={"Idempotency-Key": key})
    assert replay.status_code == 200 and replay.json()["task"] is None
    assert replay.json()["operation"]["id"] == made.json()["operation"]["id"]
    assert replay.json()["read_required"] is True and replay.json()["operation"]["replayed"] is True
    changed = raw.patch("/api/seguimiento/tareas/"+identifier, json={"expected_version": 1,
        "next_step": "review_client_record", "assignee_id": c["member"], "confirm": True}, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert changed.status_code == 200 and changed.json()["task"]["version"] == 2
    done = raw.post("/api/seguimiento/tareas/"+identifier+"/completar", json={"expected_version": 2,
        "outcome": "review_recorded", "confirm": True}, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert done.status_code == 200 and done.json()["task"]["status"] == "completed"
    history = raw.get("/api/seguimiento/tareas/"+identifier+"/historial")
    assert history.status_code == 200 and [i["kind"] for i in history.json()["items"]] == ["created", "updated", "completed"]
    with Session(c["admin"]) as db:
        assert len(db.scalars(select(FollowupTaskEvent).where(FollowupTaskEvent.task_id == identifier)).all()) == 3
        assert db.get(FollowupTask, identifier).version == 3


def test_same_key_different_body_stale_cas_and_duplicate_open_do_not_write(followup_http):
    c=followup_http;raw=c["raw"]
    made, body, key=create(c)
    assert made.status_code==200
    identifier=made.json()["task"]["id"]
    mismatch=raw.post("/api/seguimiento/tareas",json={**body,"assignee_id":None},headers={"Idempotency-Key":key})
    assert mismatch.status_code==409 and mismatch.json()["detail"]["code"]=="followup_key_reused"
    duplicate=raw.post("/api/seguimiento/tareas",json=body,headers={"Idempotency-Key":str(uuid.uuid4())})
    assert duplicate.status_code==409 and duplicate.json()["detail"]["code"]=="followup_open_task_exists"
    stale=raw.patch("/api/seguimiento/tareas/"+identifier,json={"expected_version":2,"next_step":"review_client_record",
        "assignee_id":None,"confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert stale.status_code==409 and stale.json()["detail"]["code"]=="followup_version_conflict"
    with Session(c["admin"]) as db:
        assert db.get(FollowupTask,identifier).version==1


def test_nutri_only_its_assigned_scope_no_stats_or_management(followup_http):
    from tests.mfa31_contract_client import MfaContractClient
    c=followup_http;raw=c["raw"]
    made,_,_=create(c);assert made.status_code==200
    task=made.json()["task"]
    member=MfaContractClient(raw,{"id":c["member"]},c["factory"],PASSWORD);member.authenticate()
    context=raw.get("/api/seguimiento/contexto")
    assert context.status_code==200 and context.json()["scope"]=="assigned"
    listed=raw.get("/api/seguimiento/tareas")
    assert listed.status_code==200 and [r["id"] for r in listed.json()["items"]]==[task["id"]]
    assert raw.get("/api/seguimiento/metricas").status_code==403
    assert raw.get("/api/seguimiento/responsables").status_code==403
    edited=raw.patch("/api/seguimiento/tareas/"+task["id"],json={"expected_version":1,"next_step":"review_client_record",
        "assignee_id":c["member"],"confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert edited.status_code==403
    done=raw.post("/api/seguimiento/tareas/"+task["id"]+"/completar",json={"expected_version":1,"outcome":"review_recorded","confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert done.status_code==200


def test_moved_assignee_and_actor_history_never_discloses_new_context_name(followup_http):
    c=followup_http;raw=c["raw"]
    made,_,_=create(c);assert made.status_code==200
    identifier=made.json()["task"]["id"]
    with Session(c["admin"]) as db:
        member=db.get(Usuario,c["member"]);member.team_gym_id=None;member.nombre="PRIVATE NEW CONTEXT NAME";db.commit()
    current=raw.get("/api/seguimiento/tareas/"+identifier)
    assert current.status_code==200
    assert current.json()["responsible"]=={"id":c["member"],"display_name":None,"eligible":False}
    assert "PRIVATE NEW CONTEXT NAME" not in current.text and current.json()["capabilities"]["complete"] is False
    rejected=raw.post("/api/seguimiento/tareas/"+identifier+"/completar",json={"expected_version":1,"outcome":"review_recorded","confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert rejected.status_code==409
    cancel=raw.post("/api/seguimiento/tareas/"+identifier+"/cancelar",json={"expected_version":1,"reason":"no_longer_applicable","confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert cancel.status_code==200


def test_read_has_no_dml_or_commit_and_stats_evidence_is_server_generated(followup_http):
    from sqlalchemy import event
    c=followup_http;sql=[]
    def record(connection,cursor,statement,parameters,context,executemany):sql.append(statement.lstrip().upper())
    event.listen(c["engine"],"before_cursor_execute",record)
    try:
        response=c["raw"].get("/api/estadisticas/seguimiento")
        assert response.status_code==200
        item=next(i for i in response.json()["items"] if i["id_cliente"]==c["profile"])
        evidence=candidate(c)
        assert item["cause_candidates"][0]["cause_evidence_hash"]==evidence["cause_evidence_hash"]
        assert response.json()["responsibility"]=="per_cause_tasks"
        assert not any(q.startswith(("UPDATE ","INSERT ","DELETE ","COMMIT")) for q in sql)
    finally:event.remove(c["engine"],"before_cursor_execute",record)
