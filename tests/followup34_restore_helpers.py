"""Synthetic34 ledger material; SQL/service restore witnesses, not login claims.

The unchanged33 full restore already exercises password/MFA/Google HTTP. These
additional task actors are explicit fixture data; no bearer is minted for them.
No credential/refresh row is added, hidden or removed to satisfy an old oracle.
"""
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from web.database.models import Cliente, FollowupTask as Task, FollowupTaskEvent as Event, Usuario, UserRole
from web.database.tenant_context import tenant_scope
from web.followup_schemas import CreateTask
from web.services import followup_domain as domain, followup_tasks as service
from web.database.followup_task_repository import sources

FOLLOWUP_TABLES = {"followup_tasks", "followup_task_events"}
OWNER = "restore-release-gym"
WORKER = "restore-task-worker"


def populate_followup34(admin):
    now = datetime.now(timezone.utc)
    expected = {"owner": OWNER, "worker": WORKER, "tasks": {}, "operations": {}}
    with Session(admin) as db:
        db.add(Usuario(id=WORKER, email="restore-task-worker@example.invalid", password_hash="synthetic-unusable",
            nombre="Synthetic prior worker", tipo="usuario", role=UserRole.NUTRIOLOGO, team_gym_id=OWNER))
        for label in ("assigned", "unassigned", "completed", "cancelled"):
            db.add(Cliente(id_cliente="restore-task-"+label, gym_id=OWNER, nombre="Synthetic task "+label))
        db.commit()
    with tenant_scope(OWNER), Session(admin) as db:
        from web.database.tenant_context import bind_verified_subject
        bind_verified_subject(db, OWNER)  # Explicit fixture subject, not an HTTP-authentication claim.
        for label in ("assigned", "unassigned", "completed", "cancelled"):
            client = "restore-task-"+label
            source = sources(db, OWNER, [client])[client]
            evidence = domain.causes(source, OWNER, now)[0]
            assigned = None if label == "unassigned" else WORKER
            command = CreateTask(client_id=client, cause="no_saved_plan", cause_evidence_hash=evidence["cause_evidence_hash"],
                next_step="review_plan_history", assignee_id=assigned, expected_active_task_id=None, confirm=True)
            identifier, key = str(uuid.uuid4()), str(uuid.uuid4())
            value = dict(gym_id=OWNER, client_id=client, cause="no_saved_plan", cause_evidence_hash=evidence["cause_evidence_hash"],
                observed_at=now, plan_count=0, last_plan_at=None, membership_end=None, priority_at_creation=1,
                next_step="review_plan_history", assignee_id=assigned, status="open", version=1, created_by=OWNER,
                created_at=now, updated_at=now, completed_by=None, completed_at=None, outcome=None,
                cancelled_by=None, cancelled_at=None, cancel_reason=None)
            event = Event(id=str(uuid.uuid4()), task_id=identifier, actor_id=OWNER, actor_role="owner", kind="created",
                request_key=key, request_hash=domain.request_hash(OWNER, OWNER, "POST", "/api/seguimiento/tareas", command), **value)
            db.add(event); db.flush()
            expected["operations"][label] = {"body": command.model_dump(mode="json"), "key": key, "event_id": event.id}
            expected["tasks"][label] = identifier
            if label in {"completed", "cancelled"}:
                value.update(version=2, updated_at=now+timedelta(seconds=1))
                if label == "completed":
                    value.update(status="completed", completed_by=WORKER, completed_at=value["updated_at"], outcome="review_recorded")
                else:
                    value.update(status="cancelled", cancelled_by=OWNER, cancelled_at=value["updated_at"], cancel_reason="created_in_error")
                db.add(Event(id=str(uuid.uuid4()), task_id=identifier, actor_id=WORKER if label == "completed" else OWNER,
                    actor_role="nutriologo" if label == "completed" else "owner", kind=label,
                    request_key=str(uuid.uuid4()), request_hash="c"*64, **value)); db.flush()
        db.commit()
        # A departure preserves references but must not reveal its new name.
        worker = db.get(Usuario, WORKER)
        worker.team_gym_id = None
        worker.nombre = "PRIVATE NEW CONTEXT NAME"
        db.commit()
    with Session(admin) as db:
        expected["task_rows"] = [dict(r) for r in db.execute(select(Task.__table__).order_by(Task.id)).mappings()]
        expected["event_rows"] = [dict(r) for r in db.execute(select(Event.__table__).order_by(Event.id)).mappings()]
        assert len(expected["task_rows"]) == 4 and len(expected["event_rows"]) == 6
    return expected


def verify_restored_followup34(admin, application, expected):
    from web.auth import identity_from_user
    with Session(admin) as db:
        assert [dict(r) for r in db.execute(select(Task.__table__).order_by(Task.id)).mappings()] == expected["task_rows"]
        assert [dict(r) for r in db.execute(select(Event.__table__).order_by(Event.id)).mappings()] == expected["event_rows"]
        actor = identity_from_user(db.get(Usuario, OWNER), db)
        foreign = identity_from_user(db.get(Usuario, "restore-foreign-gym"), db)
    with tenant_scope(OWNER), Session(application) as db:
        detail = service.read_task(db, actor, expected["tasks"]["assigned"])
        assert detail["responsible"] == {"id": WORKER, "display_name": None, "eligible": False}
        assert detail["capabilities"]["complete"] is False
        history = service.history(db, actor, expected["tasks"]["completed"], 50, 0)
        assert history["items"][1]["actor"] == {"id": WORKER, "display_name": None, "eligible": False}
        assert "PRIVATE NEW CONTEXT NAME" not in domain.canonical([detail, history]).decode()
    for label, operation in expected["operations"].items():
        with tenant_scope(OWNER), Session(application) as db:
            result = service.mutate(db, actor, "created", CreateTask.model_validate(operation["body"]), operation["key"], "/api/seguimiento/tareas")
            assert result["ack"] is True and result["task"] is None and result["read_required"] is True
            assert result["operation"]["id"] == operation["event_id"] and result["operation"]["replayed"] is True
    with tenant_scope(foreign["id"]), Session(application) as db:
        assert service.list_tasks(db, foreign, "open", 100, None)["items"] == []
        with pytest.raises(HTTPException) as caught:
            service.read_task(db, foreign, expected["tasks"]["assigned"])
        assert caught.value.status_code == 404
    with Session(application) as db:
        assert db.scalars(select(Task)).all() == [] and db.scalars(select(Event)).all() == []
    for statement in ("DELETE FROM followup_tasks", "UPDATE followup_task_events SET request_hash=:hash"):
        with pytest.raises(DBAPIError) as caught, tenant_scope(OWNER), application.begin() as db:
            db.execute(text(statement), {"hash": "a"*64})
        assert caught.value.orig.pgcode == "42501"
    with Session(admin) as db:
        assert [dict(r) for r in db.execute(select(Task.__table__).order_by(Task.id)).mappings()] == expected["task_rows"]
        assert [dict(r) for r in db.execute(select(Event.__table__).order_by(Event.id)).mappings()] == expected["event_rows"]
    return {"scope": "restricted_role_SQL_and_service_not_HTTP_authentication", "tasks": 4, "events": 6,
        "assigned_unavailable_and_unassigned_open": 2, "completed": 1, "cancelled": 1,
        "exact_durable_replays": 4, "foreign_and_missing_denied": True,
        "blank_tenant_zero_rows": True, "history_update_delete_denied": True}
