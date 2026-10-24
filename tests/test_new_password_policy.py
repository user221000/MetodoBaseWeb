"""New-credential minimums and existing-login compatibility, with real validators.

HTTP cases use the owned current-schema fixtures and both actual web factories.
All credentials and identities in this module are synthetic.
"""
import logging
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests import account_security38_http as account_security37_http

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http

FIFTEEN = "cedro nube luna"
SHORT = [pytest.param("nube cedro x", id="twelve-codepoints"),
         pytest.param("cedro nube lun", id="fourteen-codepoints"),
         pytest.param("\U0001f33f" * 14, id="fourteen-astral-codepoints")]


@pytest.fixture(autouse=True)
def no_new_credential_values_in_logs(caplog):
    yield
    formatted = "\n".join(logging.Formatter().format(record)
        for phase in ("setup", "call", "teardown")
        for record in caplog.get_records(phase))
    for candidate in (FIFTEEN, *(row.values[0] for row in SHORT)):
        assert candidate not in formatted


@pytest.mark.parametrize("value", SHORT)
def test_new_credential_rejects_less_than_fifteen_unicode_codepoints(value):
    from web.account_values import validate_new_password
    with pytest.raises(ValueError):
        validate_new_password(value)


@pytest.mark.parametrize("value", [pytest.param(FIFTEEN, id="fifteen-ascii"),
    pytest.param("\U0001f33f" * 15, id="fifteen-astral-codepoints"),
    pytest.param("\U0001f33f" * 18, id="exact-seventy-two-utf8-bytes"),
    pytest.param("cedro " + "nube " * 12 + "final!", id="seventy-two-ascii-bytes")])
def test_new_credential_preserves_valid_value_exactly(value):
    from web.account_values import validate_new_password
    assert validate_new_password(value) == value


@pytest.mark.parametrize("value", [pytest.param("\U0001f33f" * 19, id="utf8-overflow"),
    pytest.param("cedro " + "nube " * 12 + "final!x", id="ascii-overflow"),
    pytest.param(FIFTEEN + "\ud800", id="invalid-unicode"),
    pytest.param(None, id="not-text")])
def test_existing_utf8_and_type_boundaries_stay_closed(value):
    from web.account_values import validate_new_password
    with pytest.raises(ValueError):
        validate_new_password(value)


def credential_schema(kind, value):
    if kind == "change":
        from web.account_security_schemas import PasswordChange
        return PasswordChange(reauthentication_token="A" * 43,
                              new_password=value, confirm_password=value)
    if kind == "reset":
        from web.routes.password_recovery import RecoveryConfirm
        return RecoveryConfirm(token="synthetic-opaque-reset-token",
                               new_password=value, confirm_password=value)
    from web.routes.team import AcceptInviteRequest
    return AcceptInviteRequest(token="A" * 43, password=value)


@pytest.mark.parametrize("kind", ["change", "reset", "invite"])
@pytest.mark.parametrize("value", SHORT)
def test_all_new_credential_dtos_reject_short_values(kind, value):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        credential_schema(kind, value)


@pytest.mark.parametrize("kind", ["change", "reset", "invite"])
def test_all_new_credential_dtos_accept_fifteen(kind):
    parsed = credential_schema(kind, FIFTEEN)
    assert getattr(parsed, "new_password", getattr(parsed, "password", None)) == FIFTEEN


@pytest.mark.parametrize("value", SHORT)
def test_registration_rejection_does_not_persist_or_disclose_then_fifteen_succeeds(account_http, value):
    from web import auth
    from web.database.models import Usuario
    case = account_http
    email = uuid.uuid4().hex + "@example.invalid"
    body = {"email": email, "nombre": "Synthetic minimum policy", "tipo": "usuario"}
    response = case["raw"].post("/api/auth/registro", json={**body, "password": value})
    assert response.status_code in {400, 422}
    assert value not in response.text and "traceback" not in response.text.lower()
    with Session(case["admin"]) as db:
        assert db.scalar(select(Usuario.id).where(Usuario.email == email)) is None
    accepted = case["raw"].post("/api/auth/registro", json={**body, "password": FIFTEEN})
    assert accepted.status_code == 200
    with Session(case["admin"]) as db:
        user = db.scalar(select(Usuario).where(Usuario.email == email))
        assert user is not None and auth.verify_password(FIFTEEN, user.password_hash)


def test_existing_short_password_hash_still_logs_in_without_rotation(account_http):
    from web import auth
    from web.database.models import Usuario, UserRole
    case = account_http
    identity, email = str(uuid.uuid4()), uuid.uuid4().hex + "@example.invalid"
    legacy = "nube cedro x"
    previous_hash = auth.hash_password(legacy)
    with Session(case["admin"]) as db:
        db.add(Usuario(id=identity, email=email, nombre="Synthetic existing account",
                       tipo="usuario", role=UserRole.VIEWER, activo=True,
                       password_hash=previous_hash, session_version=1))
        db.commit()
    case["raw"].headers.pop("Authorization", None)
    case["raw"].cookies.clear()
    response = case["raw"].post("/api/auth/login", json={"email": email, "password": legacy})
    assert response.status_code == 200 and response.json().get("token")
    me = case["raw"].get("/api/auth/me", headers={"Authorization": "Bearer " + response.json()["token"]})
    assert me.status_code == 200 and me.json()["id"] == identity
    with Session(case["admin"]) as db:
        assert db.get(Usuario, identity).password_hash == previous_hash
