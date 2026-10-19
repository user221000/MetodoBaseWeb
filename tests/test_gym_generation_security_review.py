"""Independent integrated privacy check for failed quota compensation.

Real factories, bearer validation, persisted tenant and reservation are used.
Only CPU work and the unavailable compensation boundary are controlled doubles.
"""
import importlib
import logging
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session


@pytest.mark.parametrize("factory,route", [("web.main_web", "web.routes.planes"), ("api.app", "api.routes.planes")])
@pytest.mark.parametrize("failure", [ValueError, RuntimeError])
def test_failed_compensation_never_exposes_private_exception_parameters(test_gym_user, monkeypatch, caplog, factory, route, failure):
    from web.database.engine import get_engine
    from web.database.models import Cliente, GymGenerationReservation
    from web.services import gym_generation_quota

    client_id = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Cliente(id_cliente=client_id, gym_id=test_gym_user["id"], nombre="Synthetic Review"))
        db.commit()
    private_marker = "synthetic-private-compensation-details"
    def failed_worker(*args, **kwargs):
        raise failure("Synthetic generation domain failure")
    def failed_compensation(*args, **kwargs):
        raise StatementError("Synthetic compensation unavailable",
            "UPDATE synthetic_quota SET status=:status WHERE gym_id=:gym_id",
            {"status": "released", "gym_id": private_marker}, RuntimeError("Synthetic adapter failure"))
    monkeypatch.setattr(importlib.import_module(route), "_generar_plan_sync", failed_worker)
    monkeypatch.setattr(gym_generation_quota, "fail_gym_generation", failed_compensation)
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        caplog.clear()
        with caplog.at_level(logging.ERROR):
            response = client.post("/api/generar-plan", json={"id_cliente": client_id},
                headers={**test_gym_user["auth_headers"], "Idempotency-Key": "security-compensation-review"})
    assert private_marker not in response.text
    assert private_marker not in caplog.text
    assert response.status_code in {422, 500, 503}
    assert isinstance(response.json()["detail"], dict)
    with Session(get_engine()) as db:
        reservation = db.execute(select(GymGenerationReservation).where(GymGenerationReservation.gym_id == test_gym_user["id"])).scalar_one()
        assert reservation.status == "reserved" and reservation.persisted_at is None
