"""Real SQLite mechanism probes; no claim of PostgreSQL/RLS acceptance."""
from datetime import datetime, timedelta
import uuid
import shutil

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import run_migration
from web.database.models import Usuario, UserRole, Cliente, FollowupTask, FollowupTaskEvent
from web.database.followup_policy import install


@pytest.fixture(scope="module")
def ledger_template(tmp_path_factory):
    path = tmp_path_factory.mktemp("followup34-mechanisms")/"template.db"
    url = "sqlite:///"+path.as_posix()
    run_migration(url, "db_bootstrap.py", "--revision", "20261019_google_subjects")
    engine = create_engine(url)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
    with engine.begin() as c:
        FollowupTask.__table__.create(c)
        FollowupTaskEvent.__table__.create(c)
        install(c)
    with Session(engine) as db:
        db.add_all([Usuario(id="gym-a", email="a@example.invalid", password_hash="synthetic", nombre="A", tipo="gym", role=UserRole.OWNER),
                    Usuario(id="gym-b", email="b@example.invalid", password_hash="synthetic", nombre="B", tipo="gym", role=UserRole.OWNER),
                    Usuario(id="nutri-a", email="n@example.invalid", password_hash="synthetic", nombre="N", tipo="usuario", role=UserRole.NUTRIOLOGO, team_gym_id="gym-a")])
        db.flush()
        db.add(Cliente(id_cliente="client-a", gym_id="gym-a", nombre="Synthetic"))
        db.commit()
    engine.dispose()
    return path


@pytest.fixture
def ledger(ledger_template, tmp_path):
    path = tmp_path/"mechanism.db"
    shutil.copyfile(ledger_template, path)
    engine = create_engine("sqlite:///"+path.as_posix())
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield engine
    finally:
        engine.dispose()


def creation(**changes):
    now = datetime(2026, 10, 19, 18)
    result = dict(id=str(uuid.uuid4()), task_id=str(uuid.uuid4()), gym_id="gym-a", client_id="client-a",
        cause="no_saved_plan", cause_evidence_hash="a"*64, observed_at=now, plan_count=0,
        last_plan_at=None, membership_end=None, priority_at_creation=1, next_step="review_plan_history",
        assignee_id="nutri-a", status="open", version=1, created_by="gym-a", created_at=now, updated_at=now,
        completed_by=None, completed_at=None, outcome=None, cancelled_by=None, cancelled_at=None, cancel_reason=None,
        actor_id="gym-a", actor_role="owner", kind="created", request_key=str(uuid.uuid4()), request_hash="b"*64)
    return {**result, **changes}


def append(engine, value):
    with engine.begin() as c:
        c.execute(FollowupTaskEvent.__table__.insert(), value)


def advance(value, **changes):
    return {**value, "id": str(uuid.uuid4()), "request_key": str(uuid.uuid4()), "version": value["version"]+1,
        "updated_at": value["updated_at"]+timedelta(seconds=1), "kind": "updated", **changes}


def test_event_atomically_creates_and_advances_exact_projection(ledger):
    first = creation()
    append(ledger, first)
    second = advance(first, assignee_id=None)
    append(ledger, second)
    with Session(ledger) as db:
        task = db.get(FollowupTask, first["task_id"])
        assert task.version == 2 and task.current_event_id == second["id"] and task.assignee_id is None
        assert len(db.scalars(select(FollowupTaskEvent)).all()) == 2


@pytest.mark.parametrize("operation", ["task_update", "task_delete", "event_update", "event_delete"])
def test_direct_rewrite_or_delete_cannot_bypass_history(ledger, operation):
    first = creation(); append(ledger, first)
    statements = {"task_update": "UPDATE followup_tasks SET assignee_id=NULL,version=2",
        "task_delete": "DELETE FROM followup_tasks", "event_update": "UPDATE followup_task_events SET request_hash='x'",
        "event_delete": "DELETE FROM followup_task_events"}
    with pytest.raises(IntegrityError), ledger.begin() as c:
        c.execute(text(statements[operation]))
    with Session(ledger) as db:
        assert db.get(FollowupTask, first["task_id"]).version == 1
        assert db.scalar(select(FollowupTaskEvent.id)) == first["id"]


@pytest.mark.parametrize("change", [{"gym_id":"gym-b"}, {"assignee_id":"gym-b"}, {"plan_count":1},
    {"version":2}, {"actor_role":"admin"}, {"actor_id":"nutri-a", "actor_role":"nutriologo"}])
def test_invalid_create_has_neither_event_nor_projection(ledger, change):
    with pytest.raises(IntegrityError):
        append(ledger, creation(**change))
    with Session(ledger) as db:
        assert db.scalar(select(FollowupTask.id)) is None
        assert db.scalar(select(FollowupTaskEvent.id)) is None


def test_terminal_event_is_one_use_and_never_reopens(ledger):
    first=creation(); append(ledger,first)
    done=advance(first, kind="completed", status="completed", actor_id="nutri-a", actor_role="nutriologo",
        completed_by="nutri-a", completed_at=first["updated_at"]+timedelta(seconds=1), outcome="review_recorded")
    append(ledger,done)
    with pytest.raises(IntegrityError): append(ledger,advance(done,status="open",completed_by=None,completed_at=None,outcome=None))
    with Session(ledger) as db:
        task=db.get(FollowupTask,first["task_id"])
        assert task.status=="completed" and task.version==2


def test_cause_unique_open_and_closed_recurrence_is_explicit(ledger):
    first=creation();append(ledger,first)
    with pytest.raises(IntegrityError):append(ledger,creation())
    cancelled=advance(first,kind="cancelled",status="cancelled",cancelled_by="gym-a",
        cancelled_at=first["updated_at"]+timedelta(seconds=1),cancel_reason="no_longer_applicable")
    append(ledger,cancelled)
    next_task=creation();append(ledger,next_task)
    with Session(ledger) as db:
        assert len(db.scalars(select(FollowupTask)).all())==2


def test_request_collision_rolls_back_without_extra_projection(ledger):
    first=creation();append(ledger,first)
    with pytest.raises(IntegrityError):append(ledger,advance(first,next_step="review_client_record",request_key=first["request_key"]))
    with Session(ledger) as db:
        assert db.get(FollowupTask,first["task_id"]).version==1
        assert len(db.scalars(select(FollowupTaskEvent)).all())==1


@pytest.mark.parametrize("change", [{"id":"X"*36}, {"request_key":"a"*36}, {"request_hash":"Z"*64},
    {"cause":"membership_date_passed","next_step":"review_membership_date"}])
def test_direct_noncanonical_keys_or_absent_cause_are_rejected(ledger,change):
    with pytest.raises(IntegrityError):append(ledger,creation(**change))
    with Session(ledger) as db:
        assert db.scalar(select(FollowupTask.id)) is None
        assert db.scalar(select(FollowupTaskEvent.id)) is None
