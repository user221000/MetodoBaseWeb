"""Actual SQLite37 facts, tenant authority, source coherence and cleanup."""
import uuid
from datetime import UTC, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import Session, sessionmaker

from tests import product_analytics_fixtures as f
from web.database.models import Cliente, PlanGenerado, UserRole, Usuario
from web.database.models import GymGenerationReservation as Gym
from web.database.tenant_context import current_tenant
from web.services.product_analytics import read_report

account37_engine = f.account37_engine
analytics_engine = f.analytics_engine
analytics_case = f.analytics_case


def read(case, who, context="gym", **kw):
    return read_report(who, context, factory=case.factory, now=f.NOW, **kw)


def test_current_preparation_is_not_manual_plan_generation(analytics_case):
    c = analytics_case
    owner, other = c.user(), c.user()
    profile = c.profile(owner)
    foreign_profile = c.profile(other)
    c.plan(owner, profile)
    c.plan(owner, foreign_profile)  # Historical single FK alone is not ownership.
    value = read(c, owner)
    assert value["preparation_as_of"] == {"client_registered": True, "plan_saved": True}
    assert sum(row["saved_publications"] for row in value["weekly"]) == 0
    assert value["cohort"]["anchor_week"] is None
    assert read(c, other)["preparation_as_of"]["plan_saved"] is False


def test_tenant_markers_ackloss_legacy_replay_and_setnull(analytics_case):
    c = analytics_case
    owner, other = c.user(), c.user()
    profile = c.profile(owner)
    plan = c.plan(owner, profile)
    c.saved(owner, f.NOW - timedelta(days=1), plan_id=plan, client_id=profile)
    c.saved(owner, f.NOW - timedelta(days=2), status="reserved", result_json=None)
    c.saved(owner, None, status="released")
    c.saved(other, f.NOW - timedelta(days=1))
    c.saved(owner, f.NOW - timedelta(days=1), plan_id=c.plan(other, c.profile(other)))
    with c.factory() as db:
        db.delete(db.get(PlanGenerado, plan))
        db.commit()
    first = read(c, owner)
    second = read(c, owner)
    assert sum(row["saved_publications"] for row in first["weekly"]) == 2
    assert first == second
    assert sum(row["saved_publications"] for row in read(c, other)["weekly"]) == 1
    assert owner["id"] not in str(first) and other["id"] not in str(first)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER])
def test_team_personal_reads_only_own_ledger_gym_roles_remain_separate(analytics_case, role):
    c = analytics_case
    owner = c.user()
    actor = c.user(role=role, tipo="usuario", parent=owner["id"])
    c.saved(owner, f.NOW - timedelta(days=1))
    c.saved(actor, f.NOW - timedelta(days=2), context="personal")
    c.saved(actor, None, context="personal", publication_protocol=0, status="completed")
    result = read(c, actor, "personal")
    assert result["unit"] == "personal_account"
    assert sum(row["saved_publications"] for row in result["weekly"]) == 1
    assert all(set(row) == {"week_start", "complete", "saved_publications"} for row in result["weekly"])
    assert result["preparation_as_of"] == {"profile_present": False, "plan_present": False}
    if role == UserRole.ADMIN:
        assert read(c, actor, "gym")["unit"] == "workspace"
    else:
        with pytest.raises(HTTPException) as denied:
            read(c, actor, "gym")
        assert denied.value.status_code == 403


@pytest.mark.parametrize("condition", ["inactive", "deleted", "invited_empty", "sv", "tipo", "role", "parent", "parent_off", "parent_deleted", "parent_team", "owner_ambiguous"])
def test_identity_reloaded_with_exact_current_fields(analytics_case, condition):
    c = analytics_case
    owner = c.user()
    actor = c.user(role=UserRole.ADMIN, tipo="usuario", parent=owner["id"])
    try:
        with c.factory() as db:
            row = db.get(Usuario, actor["id"])
            if condition == "inactive":
                row.activo = False
            elif condition == "deleted":
                row.deleted_at = f.NOW
            elif condition == "invited_empty":
                row.invitation_token = ""
            elif condition == "sv":
                row.session_version += 1
            elif condition == "tipo":
                row.tipo = "gym"
            elif condition == "role":
                row.role = UserRole.VIEWER
            elif condition == "parent":
                db.get(Usuario, owner["id"]).invitation_token = ""
            elif condition == "parent_off":
                db.get(Usuario, owner["id"]).activo = False
            elif condition == "parent_deleted":
                db.get(Usuario, owner["id"]).deleted_at = f.NOW
            elif condition == "parent_team":
                db.get(Usuario, owner["id"]).team_gym_id = actor["id"]
            else:
                row.role = UserRole.OWNER
                row.team_gym_id = None
                actor.update(role="owner", team_gym_id=None)
            db.commit()
        with pytest.raises(HTTPException) as denied:
            read(c, actor)
        assert denied.value.status_code in (401, 403)
    finally:
        if condition in ("invited_empty", "parent"):
            with c.factory() as db:
                db.get(Usuario, owner["id"] if condition == "parent" else actor["id"]).invitation_token = None
                db.commit()


def test_max_sv_read_and_no_dml_no_profile_no_forbidden_projection(analytics_case):
    c = analytics_case
    actor = c.user(tipo="usuario", role=UserRole.VIEWER, session_version=2147483647)
    queries = []
    def observe(_c, _cursor, sql, _params, _ctx, _many):
        queries.append(sql.lower())
    event.listen(c.engine, "before_cursor_execute", observe)
    try:
        value = read(c, actor, "personal")
    finally:
        event.remove(c.engine, "before_cursor_execute", observe)
    assert value["preparation_as_of"] == {"profile_present": False, "plan_present": False}
    assert not any(q.lstrip().split(None, 1)[0] in {"insert", "update", "delete", "create", "alter"} for q in queries)
    forbidden = ("plan_json", "result_json", "password_hash", "peso_kg", "notas", "kcal", "recipient_email", "auth_audit", "personal_diary")
    assert not any(field in query for field in forbidden for query in queries)
    with c.factory() as db:
        assert db.query(Cliente).filter_by(gym_id=actor["id"]).count() == 0


@pytest.mark.parametrize("sv", [True, -1, 2147483648])
def test_invalid_session_version_never_gains_analytics_authority(analytics_case, sv):
    c = analytics_case
    actor = c.user()
    actor["session_version"] = sv
    with pytest.raises(HTTPException) as denied:
        read(c, actor)
    assert denied.value.status_code == 401


def test_snapshot_keeps_one_authority_and_fact_view_while_later_read_rechecks_revocation(analytics_case):
    """SQLite WAL is only this owned fixture; no claim about unexecuted PG hooks."""
    from threading import Thread
    c = analytics_case
    actor = c.user()
    c.saved(actor, f.NOW - timedelta(days=1))
    with c.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar().lower() == "wal"
    changed, errors = [], []
    def writer():
        try:
            c.saved(actor, f.NOW - timedelta(hours=1))
            with c.factory() as db:
                db.get(Usuario, actor["id"]).activo = False
                db.commit()
        except Exception as error:  # noqa: BLE001 -- surface a worker failure in the main test
            errors.append(type(error).__name__)
    def after(_connection, _cursor, sql, _params, _context, _many):
        if not changed and sql.startswith("SELECT usuarios.id, usuarios.tipo"):
            changed.append(True)
            worker = Thread(target=writer)
            worker.start()
            worker.join(10)
            assert not worker.is_alive(), "Owned SQLite writer did not finish"
    event.listen(c.engine, "after_cursor_execute", after)
    try:
        value = read(c, actor)
    finally:
        event.remove(c.engine, "after_cursor_execute", after)
    assert changed == [True] and errors == []
    assert sum(row["saved_publications"] for row in value["weekly"]) == 1
    with pytest.raises(HTTPException) as denied:
        read(c, actor)
    assert denied.value.status_code == 401


def test_10001_facts_reject_entire_report_not_truncate(analytics_case):
    c = analytics_case
    actor = c.user()
    rows = [{"id": str(uuid.uuid4()), "gym_id": actor["id"], "request_key": str(n), "request_hash": "a" * 64,
        "period": "2026-10", "local_date": f.NOW.date(), "timezone": "America/Mexico_City", "catalog_plan": "free",
        "status": "reserved", "persisted_at": f.NOW - timedelta(days=1)} for n in range(10001)]
    with c.factory() as db:
        db.execute(insert(Gym), rows)
        db.commit()
    with pytest.raises(HTTPException) as denied:
        read(c, actor)
    assert denied.value.status_code == 413 and denied.value.detail["code"] == "analytics_volume_limit"


def test_end_midnight_is_exclusive_before_volume_accounting(analytics_case):
    c = analytics_case
    actor = c.user()
    end = f.NOW.replace(day=20, hour=6, minute=0, second=0, microsecond=0)
    c.saved(actor, end - timedelta(microseconds=1))
    c.saved(actor, end)
    value = read(c, actor, start="2026-10-19", through="2026-10-19")
    assert sum(row["saved_publications"] for row in value["weekly"]) == 1


def test_real_r12_consumption_and_assignment_are_distinct_from_saved_generation(analytics_case):
    """Existing issue/consume/publish services establish the metadata, not fake events."""
    from datetime import datetime

    from tests import integration_client_link_services as links
    from web.services import client_link_plans
    c = analytics_case
    owner, other = c.user(), c.user()
    member = c.user(tipo="usuario", role=UserRole.VIEWER)
    profile = c.profile(owner)
    with c.factory() as db:
        email = db.get(Usuario, member["id"]).email
    case = {"gym": owner["id"], "person": member["id"], "client": profile,
            "email": email, "admin": c.engine, "app": c.engine}
    issued, token = links.issue(case)
    pending = read_report(owner, "gym", factory=c.factory)
    assert sum(w["link_acceptances"] for w in pending["weekly"]) == 0
    accepted = links.accept(case, issued, token)
    source, _, _ = links.source(case, pdf=False)
    publication = links.publish(case, accepted, source)
    after = read_report(owner, "gym", factory=c.factory)
    assert sum(w["link_acceptances"] for w in after["weekly"]) == 1
    assert sum(w["plan_assignments_published"] for w in after["weekly"]) == 1
    assert sum(w["saved_publications"] for w in after["weekly"]) == 0
    assert sum(w["link_acceptances"] for w in read_report(other, "gym", factory=c.factory)["weekly"]) == 0
    with links.session(case, "gym") as db:
        client_link_plans.withdraw_plan(db, links.principal(owner["id"]), profile, accepted["link_id"],
            publication["publication_id"], 1)
    withdrawn = read_report(owner, "gym", factory=c.factory, now=datetime.now(UTC))
    assert sum(w["plan_assignments_published"] for w in withdrawn["weekly"]) == 0
    assert sum(w["plan_assignments_withdrawn"] for w in withdrawn["weekly"]) == 1
    assert sum(w["link_acceptances"] for w in withdrawn["weekly"]) == 1
    assert email not in str(withdrawn) and member["id"] not in str(withdrawn)


@pytest.mark.parametrize("fault", ["rollback", "close_before", "close_after", "both_and_invalidate"])
def test_cleanup_uncertainty_returns_no_report_and_restores_context(analytics_case, fault):
    c = analytics_case
    actor = c.user()
    sessions = []
    class FaultSession(Session):
        def rollback(self):
            if fault in ("rollback", "both_and_invalidate"):
                raise RuntimeError("Synthetic rollback error, not public")
            return super().rollback()
        def close(self):
            if fault in ("close_before", "both_and_invalidate"):
                raise RuntimeError("Synthetic early close error")
            super().close()
            if fault == "close_after":
                raise RuntimeError("Synthetic late close error")
        def invalidate(self):
            if fault == "both_and_invalidate":
                raise RuntimeError("Synthetic invalidation error")
            return super().invalidate()
    def factory():
        session = FaultSession(c.engine, autoflush=False)
        sessions.append(session)
        return session
    token = current_tenant.set("previous-context")
    try:
        with pytest.raises(HTTPException) as denied:
            read_report(actor, "gym", factory=factory, now=f.NOW)
        assert denied.value.status_code == 503 and denied.value.detail["code"] == "analytics_unavailable"
        assert current_tenant.get() == "previous-context"
    finally:
        current_tenant.reset(token)
        for session in sessions:
            Session.rollback(session)
            Session.close(session)


def test_pool1_exhaustion_is_opaque_then_reuse_has_no_residual_context(analytics_case):
    c = analytics_case
    actor = c.user(tipo="usuario", role=UserRole.VIEWER)
    engine = create_engine(c.engine.url, pool_size=1, max_overflow=0, pool_timeout=0.05,
                          connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    try:
        held = engine.connect()
        try:
            with pytest.raises(HTTPException) as denied:
                read_report(actor, "personal", factory=factory, now=f.NOW)
            assert denied.value.status_code == 503
        finally:
            held.close()
        token = current_tenant.set("parent-that-is-not-source")
        try:
            value = read_report(actor, "personal", factory=factory, now=f.NOW)
            assert value["scope"] == "personal"
            assert current_tenant.get() == "parent-that-is-not-source"
            assert engine.pool.checkedout() == 0
        finally:
            current_tenant.reset(token)
    finally:
        engine.dispose()
