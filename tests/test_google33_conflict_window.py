"""Constraint failures before commit have the same signup conflict contract."""
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests import test_google33_http as fixtures

google_db = fixtures.google_db
google_http = fixtures.google_http


@pytest.mark.parametrize("rollback_uncertain", [False, True])
def test_profile_flush_conflict_preserves_atomic_signup_and_rollback_uncertainty(
    google_http, monkeypatch, rollback_uncertain,
):
    from web.database import repository
    from web.database.models import (
        AuthExternalIdentity,
        GymProfile,
        PlanSuscripcion,
        Usuario,
    )

    case = google_http
    case["google"]["sub"] = uuid.uuid4().hex
    case["google"]["email"] = uuid.uuid4().hex + "@example.invalid"
    original_create = repository.crear_gym_profile
    original_rollback = Session.rollback
    created = []

    def profile_conflict(db, gym_id, *args, **kwargs):
        original_create(db, gym_id, *args, **kwargs)
        created.append(gym_id)
        db.info["synthetic_profile_conflict"] = True
        raise IntegrityError("synthetic profile flush constraint", None, Exception("synthetic constraint"))

    def rollback(db):
        if rollback_uncertain and db.info.get("synthetic_profile_conflict"):
            raise RuntimeError("synthetic rollback unavailable")
        return original_rollback(db)

    monkeypatch.setattr(repository, "crear_gym_profile", profile_conflict)
    monkeypatch.setattr(Session, "rollback", rollback)
    response = case["client"].post("/api/auth/google", json={
        "credential": case["credential"](), "tipo": "gym",
    })
    assert response.status_code == (503 if rollback_uncertain else 409)
    assert response.json()["detail"]["code"] == (
        "google_link_unconfirmed" if rollback_uncertain else "google_link_conflict"
    )
    assert not {"token", "refresh_token", "reauthentication_token"} & response.json().keys()
    assert "synthetic" not in response.text
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["referrer-policy"] == "no-referrer"
    assert len(created) == 1
    with Session(case["admin"]) as db:
        assert db.get(Usuario, created[0]) is None
        assert db.scalar(select(func.count()).select_from(AuthExternalIdentity).where(
            AuthExternalIdentity.subject == case["google"]["sub"])) == 0
        assert db.scalar(select(func.count()).select_from(GymProfile).where(
            GymProfile.gym_id == created[0])) == 0
        assert db.scalar(select(func.count()).select_from(PlanSuscripcion).where(
            PlanSuscripcion.gym_id == created[0])) == 0
