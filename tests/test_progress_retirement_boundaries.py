"""Admission survives failed work, exact headers and whole-input rejection."""
# ruff: noqa: F811 -- pytest fixture parameters intentionally use fixture names
import uuid

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.test_progress_retirement_http import (  # noqa:F401
    METADATA,
    WITHDRAW,
    enrollment,
    primary,
    progress_db,
    progress_http,
    query,
    retired_scope,
    snapshot,
    withdrawal,
)


def test_failed_primaries_persist_shared_actor_budget(retired_scope):
    from fastapi import HTTPException

    from web.database.models import AuthAuditLog
    from web.progress_retirement_schemas import Metadata, Withdrawal
    from web.services import progress_retirement as service
    c = retired_scope
    for index in range(10):
        data = query(c, primary=primary(c, password="Incorrect proof")) if index % 2 else withdrawal(c, primary=primary(c, password="Incorrect proof"))
        model, operation = (Metadata, "metadata") if index % 2 else (Withdrawal, "withdraw")
        with Session(c["engine"]) as db, pytest.raises(HTTPException) as failed:
            service.perform(db, model.model_validate(data), operation=operation, now=c["clock"][0])
        assert failed.value.status_code == 401
    with Session(c["engine"]) as db, pytest.raises(HTTPException) as limited:
        service.perform(db, Metadata.model_validate(query(c)), operation="metadata", now=c["clock"][0])
    assert limited.value.status_code == 429
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(AuthAuditLog).where(
            AuthAuditLog.user_id == c["person"], AuthAuditLog.event_type == service.ATTEMPT_EVENT)) == 10
    assert [row[1] for row in snapshot(c)["events"]] == ["grant"]


def test_source_sql_failure_rolls_back_factor_and_withdraw_but_not_admission(retired_scope):
    from web.database.models import AuthAuditLog, MfaRecoveryCode
    from web.services.mfa_crypto import opaque_digest
    c = retired_scope; _, codes = enrollment(c)
    def fail(connection, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO progress_consents"):
            raise RuntimeError("PRIVATE_RETIREMENT_SQL_PARAMETERS")
    event.listen(c["engine"], "before_cursor_execute", fail)
    try:
        response = c["client_http"].post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[0]}))
    finally:
        event.remove(c["engine"], "before_cursor_execute", fail)
    assert response.status_code == 503 and "PRIVATE_RETIREMENT_SQL_PARAMETERS" not in response.text
    assert [row[1] for row in snapshot(c)["events"]] == ["grant"]
    with Session(c["admin"]) as db:
        assert db.scalar(select(MfaRecoveryCode.used_at).where(MfaRecoveryCode.code_hash == opaque_digest("recovery", codes[0]))) is None
        assert db.scalar(select(func.count()).select_from(AuthAuditLog).where(AuthAuditLog.user_id == c["person"], AuthAuditLog.event_type == "progress_retirement_attempt")) == 1
    assert c["client_http"].post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[0]})).status_code == 200


def test_metadata_lost_ack_consumes_factor_without_returning_rows(retired_scope, monkeypatch):
    from web.database import engine as database
    c = retired_scope; _, codes = enrollment(c)
    class Lost(Session):
        def commit(self):
            loss = any(getattr(row, "event_type", None) == "progress_retirement_metadata" for row in self.new)
            super().commit()
            if loss: raise RuntimeError("Synthetic lost metadata ACK")
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=c["engine"], class_=Lost, expire_on_commit=True))
    response = c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[0]}))
    assert response.status_code == 503 and "items" not in response.json()
    assert c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[0]})).status_code == 401
    assert [row[1] for row in snapshot(c)["events"]] == ["grant"]


@pytest.mark.parametrize("tipo", ["usuario", "gym"])
def test_owner_and_terminal_sv_can_only_discover_or_withdraw_existing_own_event(retired_scope, tipo):
    from web.database.models import UserRole, Usuario
    c = retired_scope
    with Session(c["admin"]) as db:
        actor = db.get(Usuario, c["person"])
        actor.tipo = tipo; actor.role = UserRole.OWNER; actor.session_version = 2147483647
        db.commit()
    before = snapshot(c)
    client = c["client_http"]
    listed = client.post(METADATA, json=query(c))
    assert listed.status_code == 200
    assert listed.json()["items"][0]["capabilities"] == {"withdraw": True, "grant": False}
    assert client.post(WITHDRAW, json=withdrawal(c)).status_code == 200
    assert {key: value for key, value in snapshot(c).items() if key != "events"} == {key: value for key, value in before.items() if key != "events"}


def test_empty_history_does_not_create_consent_or_authorize_body_subject(progress_http):
    c = progress_http
    body = {"primary": {"method": "password", "email": c["emails"]["other"], "password": "Synthetic progress password 42!"}}
    response = c["client_http"].post(METADATA, json=body)
    assert response.status_code == 200 and response.json() == {"scope": "own_consent_retirement_only", "items": [], "next_after": None}
    assert c["client_http"].post(METADATA, json={**body, "user_id": c["person"]}).status_code == 422


def test_redis_failure_and_unconfigured_production_close_before_primary_lookup(progress_http, monkeypatch):
    from web import rate_limiter_redis
    from web.settings import get_settings
    c = progress_http; client = c["client_http"]; settings = get_settings()
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "is_production", True)
    monkeypatch.setattr(settings, "REDIS_URL", "")
    response = client.post(METADATA, json={"primary": primary(c)})
    assert response.status_code == 503
    monkeypatch.setattr(settings, "REDIS_URL", "redis://synthetic.invalid/0")
    async def unavailable(): raise ConnectionError("PRIVATE_REDIS_ENDPOINT")
    monkeypatch.setattr(rate_limiter_redis, "_get_redis", unavailable)
    response = client.post(METADATA, json={"primary": primary(c)})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "rate_limit_backend_unavailable"
    assert "PRIVATE_REDIS_ENDPOINT" not in response.text


def test_bounded_stream_duplicate_keys_and_unknown_identity_fields_are_rejected(progress_http):
    c = progress_http; client = c["client_http"]
    assert client.post(METADATA, content=b'{' + b' ' * 8192, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post(METADATA, content=b'{"limit":1,"limit":2}', headers={"Content-Type": "application/json"}).status_code == 422
    assert client.post(METADATA, json=query(c, limit=True)).status_code == 422
    assert client.post(METADATA, json=query(c, after=str(uuid.uuid4()).upper())).status_code == 422
    assert client.post(METADATA, content=b'{}', headers={"Content-Type": "text/plain"}).status_code == 415


def test_arbitrary_bearer_cannot_replace_primary_and_neighbors_keep_existing_policy(progress_http):
    c = progress_http; client = c["client_http"]
    response = client.post(METADATA, headers=c["headers"]["person"], json={})
    assert response.status_code == 422
    neighbor = client.get(METADATA + "-neighbor")
    assert neighbor.status_code == 404 and neighbor.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_outer_exception_is_opaque_and_private_on_exact_operation(progress_http, monkeypatch, caplog):
    from web.routes import progress_retirement
    c = progress_http
    async def failure(*args): raise RuntimeError("PRIVATE_RETIREMENT_OUTER_PARAMETERS")
    monkeypatch.setattr(progress_retirement, "invoke", failure)
    result = c["client_http"].post(METADATA, json=query(c))
    assert result.status_code == 500
    assert result.headers["cache-control"] == "no-store" and result.headers["referrer-policy"] == "no-referrer"
    assert "PRIVATE_RETIREMENT_OUTER_PARAMETERS" not in result.text


def test_unknown_account_uses_same_redis_account_budget_across_both_operations(progress_http, monkeypatch):
    from web import rate_limiter_redis
    from web.settings import get_settings
    c = progress_http
    email = uuid.uuid4().hex + "@example.invalid"
    counters = {}
    class Transport:
        async def eval(self, script, number, key, window):
            assert script == rate_limiter_redis._FIXED_WINDOW_LUA and number == 1 and window == 300
            counters[key] = counters.get(key, 0) + 1
            return [counters[key], 300]
    transport = Transport()
    async def redis(): return transport
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://synthetic.invalid/0")
    monkeypatch.setattr(rate_limiter_redis, "_get_redis", redis)
    for number in range(10):
        body = {"primary": {"method": "password", "email": email, "password": "Incorrect proof"}}
        if number % 2:
            body.update(link_id=str(uuid.uuid4()), expected_consent_id=str(uuid.uuid4()), expected_version=1)
        response = c["client_http"].post(WITHDRAW if number % 2 else METADATA, json=body)
        assert response.status_code == 401
    response = c["client_http"].post(METADATA, json={"primary": {"method": "password", "email": email, "password": "Incorrect proof"}})
    assert response.status_code == 429
    assert len([key for key in counters if ":account:" in key]) == 1
    assert all(email not in key and "Incorrect proof" not in key for key in counters)
