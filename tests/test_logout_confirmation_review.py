"""Independent authority and replay checks for the additive logout ACK."""

import importlib
import uuid

import pytest


@pytest.mark.parametrize("factory", ["web.main_web", "api.app"])
def test_unidentified_logout_never_acknowledges_or_revokes(factory, test_gym_user):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import RefreshToken, Usuario

    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        pair = auth.crear_token_pair(test_gym_user)
        for headers in ({}, {"Authorization": "Bearer synthetically-invalid"}):
            response = client.post("/api/auth/logout", headers=headers)
            assert response.status_code == 401
            assert response.json().get("success") is not True
        with Session(get_engine()) as db:
            assert db.get(Usuario, test_gym_user["id"]).session_version == 0
            rows = db.query(RefreshToken).filter_by(user_id=test_gym_user["id"]).all()
            assert len(rows) == 1 and rows[0].revoked is False
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + pair["access_token"]}).status_code == 200
        assert client.post("/api/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 200


@pytest.mark.parametrize("factory", ["web.main_web", "api.app"])
def test_logout_ack_is_subject_bound_and_old_bearer_cannot_repeat_it(factory, test_gym_user):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import RefreshToken, Usuario, UserRole

    other_id = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Usuario(id=other_id, email=other_id + "@example.test", nombre="Synthetic Other",
                       password_hash=auth.hash_password("SyntheticOther123!"), tipo="gym",
                       role=UserRole.OWNER, activo=True, session_version=0))
        db.commit()
        other = auth.identity_from_user(db.get(Usuario, other_id), db)
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        own_pair = auth.crear_token_pair(test_gym_user)
        other_pair = auth.crear_token_pair(other)
        headers = {"Authorization": "Bearer " + own_pair["access_token"]}
        response = client.post("/api/auth/logout", headers=headers,
                               json={"id": other_id, "user_id": other_id})
        assert response.status_code == 200 and response.json()["success"] is True
        repeated = client.post("/api/auth/logout", headers=headers)
        assert repeated.status_code == 401 and repeated.json().get("success") is not True
        with Session(get_engine()) as db:
            assert db.get(Usuario, test_gym_user["id"]).session_version == 1
            assert db.get(Usuario, other_id).session_version == 0
            own_rows = db.query(RefreshToken).filter_by(user_id=test_gym_user["id"]).all()
            other_rows = db.query(RefreshToken).filter_by(user_id=other_id).all()
            assert len(own_rows) == len(other_rows) == 1
            assert own_rows[0].revoked is True and other_rows[0].revoked is False
        assert client.get("/api/auth/me", headers=headers).status_code == 401
        assert client.post("/api/auth/refresh", json={"refresh_token": own_pair["refresh_token"]}).status_code == 401
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + other_pair["access_token"]}).status_code == 200
        assert client.post("/api/auth/refresh", json={"refresh_token": other_pair["refresh_token"]}).status_code == 200
