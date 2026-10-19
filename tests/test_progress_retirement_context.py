"""Ambient general-session context cannot select this fresh-proof subject."""
# ruff: noqa: F811 -- pytest fixture parameters intentionally use fixture names
import pytest
from sqlalchemy.orm import Session

from tests.test_progress_retirement_http import (  # noqa:F401
    METADATA,
    progress_db,
    progress_http,
    query,
    retired_scope,
)


def test_incidental_other_bearer_does_not_select_or_block_primary_subject(retired_scope):
    c = retired_scope
    result = c["client_http"].post(METADATA, headers=c["headers"]["other"], json=query(c))
    assert result.status_code == 200
    assert result.json()["items"][0]["link_id"] == c["link"]
    # The operation supplied no general capability for the primary account.
    assert c["client_http"].get("/api/auth/me", headers=c["headers"]["other"]).status_code == 200
    assert c["client_http"].get("/api/auth/me", headers=c["headers"]["person"]).status_code == 401


def test_malformed_expired_and_absent_headers_are_not_primary_proof(retired_scope, monkeypatch):
    from web import auth
    c = retired_scope
    for headers in ({}, {"Authorization": "Bearer malformed"}):
        response = c["client_http"].post(METADATA, headers=headers, json=query(c))
        assert response.status_code == 200 and response.json()["items"][0]["link_id"] == c["link"]
    real = auth.time.time
    # The bearer came from real HTTP login. Move only its validator's clock;
    # the separate fresh password/MFA operation still uses its own real clock.
    with monkeypatch.context() as clock:
        clock.setattr(auth.time, "time", lambda: real() + 3600)
        expired = c["client_http"].post(METADATA, headers=c["headers"]["other"], json=query(c))
    assert expired.status_code == 200
    wrong = query(c)
    wrong["primary"]["password"] = "Incorrect proof"
    response = c["client_http"].post(METADATA, headers=c["headers"]["other"], json=wrong)
    assert response.status_code == 401 and c["link"] not in response.text


@pytest.mark.parametrize("valid", [True, False])
def test_local_scope_restores_previous_context_without_retagging_existing_session(retired_scope, valid):
    from fastapi import HTTPException

    from web.database.tenant_context import bind_verified_subject, current_tenant
    from web.progress_retirement_schemas import Metadata
    from web.routes.progress_retirement import _execute
    c = retired_scope
    token = current_tenant.set(c["other"])
    try:
        with Session(c["engine"]) as previous:
            bind_verified_subject(previous, c["other"])
            original = dict(previous.info)
            data = query(c)
            if not valid: data["primary"]["password"] = "Incorrect proof"
            if valid:
                assert _execute(Metadata.model_validate(data), "metadata")["items"][0]["link_id"] == c["link"]
            else:
                with pytest.raises(HTTPException) as failed: _execute(Metadata.model_validate(data), "metadata")
                assert failed.value.status_code == 401
            assert previous.info == original and current_tenant.get() == c["other"]
    finally:
        current_tenant.reset(token)


def test_session_close_failure_does_not_publish_success_or_leave_scope(retired_scope, monkeypatch, caplog):
    from fastapi import HTTPException
    from sqlalchemy.orm import sessionmaker

    from web.database import engine as database
    from web.database.tenant_context import current_tenant
    from web.progress_retirement_schemas import Metadata
    from web.routes.progress_retirement import _execute
    c = retired_scope
    class UnconfirmedClose(Session):
        def close(self):
            fault = self.info.pop("retirement_commit_attempted", False)
            super().close()
            if fault: raise RuntimeError("PRIVATE_RETIREMENT_CLOSE_PARAMETERS")
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=c["engine"], class_=UnconfirmedClose, expire_on_commit=True))
    outer = current_tenant.set(c["other"])
    try:
        with pytest.raises(HTTPException) as failed:
            _execute(Metadata.model_validate(query(c)), "metadata")
        assert failed.value.status_code == 503 and failed.value.detail["code"] == "progress_retirement_unconfirmed"
        assert current_tenant.get() == c["other"]
        assert "PRIVATE_RETIREMENT_CLOSE_PARAMETERS" not in caplog.text
    finally: current_tenant.reset(outer)
