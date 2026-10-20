"""Current34 restricted-role mechanisms; run only under an explicit own lease.

The reused HTTP fixture authenticates password, enrollment and MFA through the
real mounted factories. No historical fixture is retargeted or principal minted.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib
import os
from threading import Event as ThreadEvent
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from tests.followup34_fixtures import owned_database, REVISION
from tests.followup34_http import followup_http, create, candidate
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from tests.test_followup34_http import (
    test_full_mfa_context_and_create_edit_complete_history_replay as _workflow,
    test_nutri_only_its_assigned_scope_no_stats_or_management as _assigned_scope,
)
from tests.test_followup34_races import test_other_canonical_owner_gets_identical_foreign_missing_denial as _foreign_http
from tests.test_followup34_lock_projection import test_moved_assignee_lock_never_fetches_other_context_contact_fields as _projection
from tests.test_followup34_boundaries import (
    test_commit_failure_never_publishes_ack_and_explicit_replay_is_one_operation as _commit_failure,
    test_owned_session_cleanup_failure_is_visible_before_headers as _cleanup_failure,
)
from web.database.models import FollowupTask as Task, FollowupTaskEvent as TaskEvent, PlanGenerado
from web.database.tenant_context import configure_tenant_engine, tenant_scope


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("Explicit own PostgreSQL lease profile required")
    with owned_database("postgresql", tmp_path_factory.mktemp("followup34-pg")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        application = application_engine(url, admin)
        try:
            with application.connect() as db:
                assert tuple(db.execute(text("""SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,
                    pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER')
                    FROM pg_roles WHERE rolname=current_user""")).one()) == (False, False, False, False, False)
                assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 28
                assert db.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'")) == 38
            yield admin, application
        finally:
            application.dispose()


def blank_pool(engine):
    assert engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one()) == ("", "", "")


def test_full_operational_workflow_on_restricted_pool1(followup_http):
    _workflow(followup_http)
    blank_pool(followup_http["engine"])


@pytest.mark.parametrize("committed", [False, True])
def test_commit_ack_failure_and_explicit_replay_preserve_one_event(followup_http, monkeypatch, committed):
    _commit_failure(followup_http, monkeypatch, committed)
    blank_pool(followup_http["engine"])


@pytest.mark.parametrize("after_close", [False, True])
def test_cleanup_errors_are_visible_before_headers_and_release_checkout(followup_http, monkeypatch, after_close):
    _cleanup_failure(followup_http, monkeypatch, after_close)
    blank_pool(followup_http["engine"])


@pytest.mark.parametrize("invalidated", [False, True])
def test_dual_cleanup_errors_are_visible_and_checkout_limit_is_explicit(followup_http, monkeypatch, invalidated):
    from web.services import followup_tasks as service
    c = followup_http
    original = service.context
    captured = []
    def instrument(db, *args, **kwargs):
        result = original(db, *args, **kwargs)
        close, invalidate = db.close, db.invalidate
        captured.append((db, close, invalidate))
        def close_error():
            raise RuntimeError("Synthetic close failure before release")
        def invalidate_error():
            if invalidated:
                invalidate()
            raise RuntimeError("Synthetic invalidation ACK unavailable")
        db.close, db.invalidate = close_error, invalidate_error
        return result
    monkeypatch.setattr(service, "context", instrument)
    try:
        response = c["raw"].get("/api/seguimiento/contexto")
        assert response.status_code == 503 and "capabilities" not in response.json()
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert len(captured) == 1
        # If both injected methods fail BEFORE release, no code can assert that
        # the checkout was released. This is a visible failure, not pool repair.
        assert c["engine"].pool.checkedout() == (0 if invalidated else 1)
    finally:
        for db, close, invalidate in captured:
            db.close, db.invalidate = close, invalidate
            close()  # Harness owns this exact captured Session; no global dispose.
    blank_pool(c["engine"])


def test_force_rls_blank_foreign_history_and_projection_denials(followup_http):
    c = followup_http
    made, _, _ = create(c)
    assert made.status_code == 200
    identifier = made.json()["task"]["id"]
    with Session(c["engine"]) as db:
        assert db.scalars(select(Task)).all() == []
        assert db.scalars(select(TaskEvent)).all() == []
    with tenant_scope(str(uuid.uuid4())), Session(c["engine"]) as db:
        assert db.scalar(select(Task.id).where(Task.id == identifier)) is None
        assert db.scalar(select(TaskEvent.id).where(TaskEvent.task_id == identifier)) is None
    with tenant_scope(c["user"]), Session(c["engine"]) as db:
        assert db.scalar(select(Task.id).where(Task.id == identifier).with_for_update()) == identifier
    attempts = [
        ("UPDATE followup_tasks SET version=version+1 WHERE id=:id", "23514"),
        ("DELETE FROM followup_tasks WHERE id=:id", "42501"),
        ("UPDATE followup_task_events SET request_hash=:hash WHERE task_id=:id", "42501"),
        ("DELETE FROM followup_task_events WHERE task_id=:id", "42501"),
    ]
    for statement, code in attempts:
        with pytest.raises(DBAPIError) as caught, tenant_scope(c["user"]), c["engine"].begin() as db:
            db.execute(text(statement), {"id": identifier, "hash": "e"*64})
        assert caught.value.orig.pgcode == code
    with Session(c["admin"]) as db:
        assert db.get(Task, identifier).version == 1
        assert len(db.scalars(select(TaskEvent).where(TaskEvent.task_id == identifier)).all()) == 1
    blank_pool(c["engine"])


def test_real_account_lock_denies_without_consuming_key_then_explicit_retry(followup_http):
    c = followup_http
    evidence = candidate(c)
    key = str(uuid.uuid4())
    body = {"client_id": c["profile"], "cause": "no_saved_plan", "cause_evidence_hash": evidence["cause_evidence_hash"],
        "next_step": "review_plan_history", "assignee_id": c["member"], "expected_active_task_id": None, "confirm": True}
    with c["admin"].connect() as blocker:
        blocker.execute(text("SELECT id FROM usuarios WHERE id=:actor FOR UPDATE"), {"actor": c["member"]})
        denied = c["raw"].post("/api/seguimiento/tareas", json=body, headers={"Idempotency-Key": key})
        assert denied.status_code == 409 and denied.json()["detail"]["code"] == "followup_busy"
    with Session(c["admin"]) as db:
        assert db.scalar(select(TaskEvent.id).where(TaskEvent.gym_id == c["user"])) is None
    accepted = c["raw"].post("/api/seguimiento/tareas", json=body, headers={"Idempotency-Key": key})
    assert accepted.status_code == 200 and accepted.json()["operation"]["replayed"] is False
    blank_pool(c["engine"])


def test_source_changes_after_service_snapshot_are_denied_by_actual_trigger(followup_http, monkeypatch):
    from web.database import followup_task_repository as repository
    c = followup_http
    # INSERT would wait for the route's Usuario FOR UPDATE through its FK.
    # An existing Plan's non-key date update can legitimately commit meanwhile.
    with Session(c["admin"]) as seed:
        plan = PlanGenerado(gym_id=c["user"], id_cliente=c["profile"], plan_json='{"synthetic":true}',
            fecha_generacion=datetime.now(timezone.utc)-timedelta(days=60))
        seed.add(plan);seed.flush();plan_id=plan.id;seed.commit()
    response = c["raw"].get("/api/seguimiento/clientes/"+c["profile"]+"/candidatos")
    assert response.status_code == 200
    evidence = next(row for row in response.json()["candidates"] if row["cause"] == "no_plan_in_window")
    original = repository.sources
    inserted = []
    def observed(db, gym, ids):
        rows = original(db, gym, ids)
        if gym == c["user"] and not inserted:
            with Session(c["admin"]) as writer:
                writer.execute(text("SET LOCAL lock_timeout = '3s'"))
                current = writer.get(PlanGenerado, plan_id)
                current.fecha_generacion = datetime.now(timezone.utc)
                writer.commit()
            inserted.append(True)
        return rows
    monkeypatch.setattr(repository, "sources", observed)
    response = c["raw"].post("/api/seguimiento/tareas", json={"client_id": c["profile"], "cause": "no_plan_in_window",
        "cause_evidence_hash": evidence["cause_evidence_hash"], "next_step": "review_plan_history", "assignee_id": None,
        "expected_active_task_id": None, "confirm": True}, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert inserted == [True]
    assert response.status_code == 409 and response.json()["detail"]["code"] == "followup_cause_changed"
    with Session(c["admin"]) as db:
        assert db.scalar(select(Task.id).where(Task.gym_id == c["user"])) is None
        assert db.scalar(select(TaskEvent.id).where(TaskEvent.gym_id == c["user"])) is None
    blank_pool(c["engine"])


def test_concurrent_same_key_has_one_ack_and_one_busy_or_replay(followup_http, monkeypatch):
    from web.database import engine as database
    c = followup_http
    evidence = candidate(c)
    key = str(uuid.uuid4())
    body = {"client_id": c["profile"], "cause": "no_saved_plan", "cause_evidence_hash": evidence["cause_evidence_hash"],
        "next_step": "review_plan_history", "assignee_id": c["member"], "expected_active_task_id": None, "confirm": True}
    parallel = configure_tenant_engine(create_engine(c["engine"].url, pool_size=6, max_overflow=0, pool_timeout=5))
    at_insert, contender_done = ThreadEvent(), ThreadEvent()
    arrivals = []
    @event.listens_for(parallel, "before_cursor_execute")
    def hold_winner(connection, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO followup_task_events"):
            arrivals.append(True)
            at_insert.set()
            assert contender_done.wait(10), "Second request did not finish under the held account lock"
    try:
        with monkeypatch.context() as patch:
            patch.setattr(database, "_engine", parallel)
            patch.setattr(database, "_SessionLocal", sessionmaker(bind=parallel, autoflush=False, expire_on_commit=True))
            with TestClient(importlib.import_module(c["factory_name"]).create_app(), raise_server_exceptions=False,
                            client=("127.6.1.1", 50001)) as other:
                headers = {"Authorization": c["raw"].headers["Authorization"], "Idempotency-Key": key}
                def first():
                    return c["raw"].post("/api/seguimiento/tareas", json=body, headers={"Idempotency-Key": key})
                with ThreadPoolExecutor(max_workers=1) as workers:
                    future = workers.submit(first)
                    assert at_insert.wait(10)
                    try:
                        loser = other.post("/api/seguimiento/tareas", json=body, headers=headers)
                        assert loser.status_code == 409 and loser.json()["detail"]["code"] == "followup_busy"
                    finally:
                        contender_done.set()
                    winner = future.result(timeout=10)
                assert winner.status_code == 200 and winner.json()["operation"]["replayed"] is False
                replay = other.post("/api/seguimiento/tareas", json=body, headers=headers)
                assert replay.status_code == 200 and replay.json()["operation"]["replayed"] is True
                assert replay.json()["operation"]["id"] == winner.json()["operation"]["id"]
                assert arrivals == [True]
        with Session(c["admin"]) as db:
            assert len(db.scalars(select(TaskEvent).where(TaskEvent.gym_id == c["user"])).all()) == 1
        blank_pool(parallel)
    finally:
        contender_done.set()
        parallel.dispose()


def test_moved_assignee_locks_load_eligibility_only(followup_http, record_property):
    _projection(followup_http, record_property)
    blank_pool(followup_http["engine"])


def test_nutri_role_is_assigned_only_with_real_mfa_on_pool1(followup_http):
    _assigned_scope(followup_http)
    blank_pool(followup_http["engine"])


def test_other_real_mfa_owner_gets_foreign_missing_opaque_denial(followup_http):
    _foreign_http(followup_http)
    blank_pool(followup_http["engine"])
