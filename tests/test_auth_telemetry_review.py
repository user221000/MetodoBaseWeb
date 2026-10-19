"""Independent checks of SDK defaults, incoming baggage and audit ownership."""
import json
import logging
from unittest.mock import Mock, patch

import pytest


def test_default_sdk_integrations_cannot_export_incoming_baggage_or_attachments():
    import sentry_sdk
    from sentry_sdk.transport import Transport
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from web.observability.sentry_setup import init_sentry

    marker = "independent-private-trace-marker"
    class MemoryTransport(Transport):
        def __init__(self):
            super().__init__()
            self.envelopes = []
        def capture_envelope(self, envelope):
            self.envelopes.append(envelope)
    transport = MemoryTransport()
    with patch("web.observability.sentry_setup.sentry_sdk.init") as initialize:
        init_sentry("https://public@example.invalid/1", "test", 1.0, 1.0)
    options = initialize.call_args.kwargs
    options["transport"] = transport
    # Product uses the SDK's default integrations in addition to explicit ones.
    client = sentry_sdk.Client(**options)
    try:
        with sentry_sdk.isolation_scope() as scope:
            scope.set_client(client)
            scope.set_transaction_name(marker)
            scope.add_attachment(bytes=marker.encode(), filename=marker, add_to_transactions=True)
            app = FastAPI()
            @app.post("/private/{subject}")
            def fail(subject: str, body: dict):
                sentry_sdk.set_context("clinical", {"note": body["note"]})
                sentry_sdk.set_user({"email": marker + "@example.invalid"})
                raise RuntimeError(marker)
            with TestClient(app, raise_server_exceptions=False) as http:
                response = http.post("/private/" + marker + "?token=" + marker,
                    headers={"sentry-trace": "a" * 32 + "-" + "b" * 16 + "-1",
                        "baggage": "sentry-trace_id=" + "a" * 32 + ",sentry-transaction=" + marker + ",sentry-user_segment=" + marker},
                    json={"note": marker})
                assert response.status_code == 500
            sentry_sdk.flush()
    finally:
        client.close()
    assert transport.envelopes
    for envelope in transport.envelopes:
        serialized = envelope.serialize().decode()
        assert marker not in serialized
        assert set(item.headers["type"] for item in envelope.items) <= {"event", "transaction"}
        assert "trace" not in envelope.headers  # No unprojected dynamic sampling baggage.


def test_failed_audit_with_borrowed_session_does_not_rollback_or_close_it(caplog):
    from web.services.auth_audit import AuthEventType, log_auth_event
    session = Mock()
    session.commit.side_effect = RuntimeError("independent-private-audit-marker")
    with caplog.at_level(logging.ERROR, logger="web.services.auth_audit"):
        log_auth_event(AuthEventType.LOGIN_FAILED, db=session)
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    assert "independent-private-audit-marker" not in json.dumps([r.__dict__ for r in caplog.records], default=str)


@pytest.mark.parametrize("reader", ["attempts", "stats"])
def test_audit_readers_close_their_own_real_session(test_gym_user, monkeypatch, reader):
    from web.database.engine import SessionLocal
    from web.services import auth_audit
    observed = []
    def make_session():
        session = SessionLocal()
        original = session.close
        def close():
            observed.append(True)
            original()
        session.close = close
        return session
    monkeypatch.setattr(auth_audit, "SessionLocal", make_session)
    auth_audit.log_auth_event(auth_audit.AuthEventType.LOGIN_FAILED,
        gym_id=test_gym_user["id"], metadata={"email": test_gym_user["email"]})
    observed.clear()
    if reader == "attempts":
        assert len(auth_audit.get_recent_login_attempts(test_gym_user["email"])) == 1
    else:
        assert auth_audit.get_login_stats_for_gym(test_gym_user["id"])["failed_logins"] == 1
    assert observed == [True]
