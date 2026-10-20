"""Stable HTTP reservation handoff preserves durable quota and replay semantics."""
import json

import pytest
from sqlalchemy.orm import Session

from tests import test_gym_generation_quota as fixtures
from web.database import repository
from web.database.models import GymGenerationReservation, PlanGenerado
from web.services.gym_generation_quota import (
    complete_gym_generation,
    reserve_gym_generation,
)

gym_quota_case = fixtures.gym_quota_case


@pytest.mark.parametrize("expire", [True, False])
def test_completed_stable_replay_has_no_new_transaction_or_quota_spend(gym_quota_case, expire):
    engine, owner = gym_quota_case
    with Session(engine, expire_on_commit=expire) as db:
        first = reserve_gym_generation(db, owner, fixtures.payload(), "stable-replay", stable_result=True)
        assert not db.in_transaction()
        identifier = first.id
        assert first.status == "reserved"
        assert not db.in_transaction()
        plan_id = repository.registrar_plan(db, owner, fixtures.payload()["id_cliente"], {"plan_json": "{}"},
            return_id=True, reservation_id=identifier)
        db.commit()
        result = {"success": True, "plan_id": plan_id}
        assert complete_gym_generation(db, owner, identifier, result) == result
        replay = reserve_gym_generation(db, owner, fixtures.payload(), "stable-replay", stable_result=True)
        assert not db.in_transaction()
        assert replay.id == identifier and replay.status == "completed"
        assert json.loads(replay.result_json) == result
        assert not db.in_transaction()
    with Session(engine) as db:
        assert db.query(GymGenerationReservation).filter_by(gym_id=owner).count() == 1
        assert db.query(PlanGenerado).filter_by(gym_id=owner).count() == 1


@pytest.mark.parametrize("expire", [True, False])
def test_lost_commit_ack_never_returns_a_claim_or_retries_the_reservation(gym_quota_case, monkeypatch, expire):
    engine, owner = gym_quota_case
    with Session(engine, expire_on_commit=expire) as db:
        original = db.commit

        def lost_ack():
            original()
            raise RuntimeError("Synthetic commit acknowledgement unavailable")

        with monkeypatch.context() as patch:
            patch.setattr(db, "commit", lost_ack)
            with pytest.raises(RuntimeError, match="Synthetic commit acknowledgement"):
                reserve_gym_generation(db, owner, fixtures.payload(), "stable-uncertain", stable_result=True)
        assert not db.in_transaction()
    with Session(engine) as db:
        row = db.query(GymGenerationReservation).filter_by(gym_id=owner).one()
        assert row.status == "reserved" and row.persisted_at is None
        assert db.query(PlanGenerado).filter_by(gym_id=owner).count() == 0
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as denied:
            reserve_gym_generation(db, owner, fixtures.payload(), "stable-uncertain", stable_result=True)
        assert denied.value.status_code == 409 and denied.value.detail["code"] == "generation_in_progress"
        db.rollback()
        assert db.query(GymGenerationReservation).filter_by(gym_id=owner).count() == 1
