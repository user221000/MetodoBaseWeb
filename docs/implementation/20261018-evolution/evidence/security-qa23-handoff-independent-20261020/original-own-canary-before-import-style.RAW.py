"""Independent real SQLite pool1 and commit-uncertainty handoff probes."""
from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from tests import test_gym_generation_quota as fixtures
from web.database import repository
from web.database.models import GymGenerationReservation, PlanGenerado
from web.services.gym_generation_quota import complete_gym_generation, reserve_gym_generation

gym_quota_case = fixtures.gym_quota_case
MARKER = "SYNTHETIC_QA23_REPLAY_PAYLOAD"


def _complete(db, owner, key):
    first = reserve_gym_generation(db, owner, fixtures.payload(), key, stable_result=True)
    identifier = first.id
    plan_id = repository.registrar_plan(db, owner, fixtures.payload()["id_cliente"], {"plan_json": "{}"},
        return_id=True, reservation_id=identifier)
    db.commit()
    result = {"success": True, "plan_id": plan_id, "private": MARKER}
    assert complete_gym_generation(db, owner, identifier, result) == result
    return identifier, result


@pytest.mark.parametrize("expire", [True, False])
@pytest.mark.parametrize("completed", [False, True])
def test_stable_values_survive_closed_session_without_SQL_or_checkout(gym_quota_case, expire, completed):
    original, owner = gym_quota_case
    engine = create_engine(original.url, poolclass=QueuePool, pool_size=1, max_overflow=0,
        pool_timeout=0.2, connect_args={"check_same_thread": False})
    events = []

    @event.listens_for(engine, "before_cursor_execute")
    def observed(connection, cursor, statement, parameters, context, executemany):
        events.append(statement)

    try:
        with Session(engine, expire_on_commit=expire) as db:
            identifier = None
            if completed:
                identifier, _ = _complete(db, owner, "closed-handoff")
            result = reserve_gym_generation(db, owner, fixtures.payload(), "closed-handoff", stable_result=True)
            assert not db.in_transaction() and engine.pool.checkedout() == 0
        count = len(events)
        assert result.status == ("completed" if completed else "reserved")
        assert result.id and (identifier is None or result.id == identifier)
        assert (MARKER in result.result_json) if completed else result.result_json is None
        assert MARKER not in repr(result)
        with pytest.raises(FrozenInstanceError):
            result.status = "completed"
        assert len(events) == count and engine.pool.checkedout() == 0
        with engine.connect() as worker:
            assert worker.scalar(text("SELECT 1")) == 1
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()


@pytest.mark.parametrize("expire", [True, False])
def test_completed_replay_lost_commit_ACK_never_returns_cached_success(gym_quota_case, expire, monkeypatch):
    engine, owner = gym_quota_case
    with Session(engine, expire_on_commit=expire) as db:
        identifier, expected = _complete(db, owner, "completed-ACK")
        original = db.commit
        calls = []

        def uncertain():
            original()
            calls.append(True)
            raise RuntimeError("Synthetic completed acknowledgement uncertainty")

        with monkeypatch.context() as patch:
            patch.setattr(db, "commit", uncertain)
            with pytest.raises(RuntimeError, match="Synthetic completed acknowledgement"):
                reserve_gym_generation(db, owner, fixtures.payload(), "completed-ACK", stable_result=True)
        assert calls == [True] and not db.in_transaction()
        replay = reserve_gym_generation(db, owner, fixtures.payload(), "completed-ACK", stable_result=True)
        assert replay.id == identifier and replay.status == "completed"
        assert expected["plan_id"] == db.query(PlanGenerado).filter_by(gym_id=owner).one().id
        assert db.query(GymGenerationReservation).filter_by(gym_id=owner).count() == 1


@pytest.mark.parametrize("expire", [True, False])
def test_snapshot_is_not_returned_when_commit_fails_before_durability(gym_quota_case, expire, monkeypatch):
    engine, owner = gym_quota_case
    with Session(engine, expire_on_commit=expire) as db:
        calls = []

        def uncommitted():
            calls.append(True)
            raise RuntimeError("Synthetic commit before durability")

        with monkeypatch.context() as patch:
            patch.setattr(db, "commit", uncommitted)
            with pytest.raises(RuntimeError, match="Synthetic commit before durability"):
                reserve_gym_generation(db, owner, fixtures.payload(), "precommit-ACK", stable_result=True)
        assert calls == [True]
        db.rollback()  # The caller owns cleanup; the service does not claim a refund.
    with Session(engine) as db:
        assert db.query(GymGenerationReservation).filter_by(gym_id=owner).count() == 0
        assert db.query(PlanGenerado).filter_by(gym_id=owner).count() == 0
