"""Original B19 canaries: whole common passwords must not establish identity."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests import account_security37_http

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http


def common_candidate():
    # Public test value constructed at runtime; no plaintext corpus is stored.
    return chr(49) * 12


def test_whole_common_candidate_is_rejected_by_shared_validator():
    from web.account_values import validate_new_password
    with pytest.raises(ValueError):
        validate_new_password(common_candidate())


def test_http_registration_rejects_common_candidate_without_identity(account_http):
    from web.database.models import Usuario
    case = account_http
    email = uuid.uuid4().hex + "@example.invalid"
    response = case["raw"].post("/api/auth/registro", json={
        "email": email, "password": common_candidate(), "nombre": "Synthetic B19", "tipo": "usuario"})
    with Session(case["admin"]) as db:
        assert db.scalar(select(Usuario.id).where(Usuario.email == email)) is None
    assert response.status_code == 400
    assert common_candidate() not in response.text
    assert "access_token" not in response.json() and "refresh_token" not in response.json()
