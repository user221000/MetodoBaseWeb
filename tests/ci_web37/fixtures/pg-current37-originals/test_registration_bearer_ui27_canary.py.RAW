"""Candidate QA-26: public legacy registration with an existing valid Bearer.

Preserved RED canary. No tenant/auth implementation is changed here.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db as followup_db, notification_http as notification_http


def test_public_registration_ignores_unrelated_valid_bearer_without_partial_account(notification_http, record_property):
    from web.database.models import Usuario, UserRole

    case = notification_http
    email = "public-registration-canary-" + uuid.uuid4().hex + "@example.invalid"
    assert case["raw"].headers.get("Authorization", "").startswith("Bearer ")
    response = case["raw"].post("/api/auth/registro", json={
        "email": email, "password": "Synthetic-public-registration-only-2026!",
        "nombre": "Synthetic independent account", "tipo": "gym",
    })
    with Session(case["admin"]) as db:
        created = list(db.scalars(select(Usuario).where(Usuario.email == email)))
        manager = db.get(Usuario, case["user"])
        record_property("http_status", response.status_code)
        record_property("new_rows_after_response", len(created))
        record_property("factory", case["factory_name"])
        assert manager is not None and manager.role == UserRole.OWNER and manager.team_gym_id is None
        if response.status_code != 200:
            assert not created, "Rejected public registration must not leave a partial persisted identity"
        assert response.status_code == 200, "A valid unrelated Bearer must not turn public registration into500"
        assert len(created) == 1
        assert created[0].id != case["user"]
        assert created[0].role == UserRole.OWNER and created[0].team_gym_id is None
        assert response.json().get("token")
