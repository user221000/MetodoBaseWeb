"""Synthetic negative controls for auth logs and the actual Sentry envelope."""
import json
import logging
import sys
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import StatementError


PRIVATE = "synthetic-private-auth-marker"
EMAIL = PRIVATE + "@example.invalid"
IP = "203.0.113.84"
URL = "https://example.invalid/" + PRIVATE + "?token=" + PRIVATE


def assert_operational_records_are_minimal(records, *extra_secrets):
    assert records, "Expected an operational classification"
    text = json.dumps([record.__dict__ for record in records], default=str)
    for secret in (PRIVATE, EMAIL, IP, *extra_secrets):
        assert secret not in text
    assert not any(record.exc_info for record in records)


@pytest.mark.parametrize("case", ["missing", "password", "account_type", "success"])
def test_password_auth_logs_classification_without_identity(case, test_gym_user, caplog):
    from web.auth import verificar_credenciales

    caplog.set_level(logging.INFO, logger="web.auth")
    result = verificar_credenciales(
        EMAIL if case == "missing" else test_gym_user["email"],
        PRIVATE if case == "password" else "test123",
        tipo_requerido=URL if case == "account_type" else None,
        ip=IP,
    )
    assert bool(result) is (case == "success")
    records = [r for r in caplog.records if r.name == "web.auth"]
    assert_operational_records_are_minimal(records, test_gym_user["id"], test_gym_user["email"])
    assert any("login_" in r.getMessage() for r in records)


def test_refresh_reuse_keeps_revocation_signal_without_token_identifier(test_gym_user, caplog):
    from web.auth import crear_token_pair, rotar_refresh_token, verificar_token

    pair = crear_token_pair(test_gym_user)
    payload = verificar_token(pair["refresh_token"])
    assert payload is None  # Refresh tokens cannot be used as access tokens.
    from web.auth import _decode_token
    payload = _decode_token(pair["refresh_token"])
    assert payload is not None
    assert rotar_refresh_token(pair["refresh_token"]) is not None
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="web.auth"):
        assert rotar_refresh_token(pair["refresh_token"]) is None
    records = [r for r in caplog.records if r.name == "web.auth"]
    assert_operational_records_are_minimal(records, payload["jti"], test_gym_user["id"])
    assert "refresh_reuse" in records[0].getMessage()


def test_audit_persists_authorized_security_fields_but_operational_log_omits_them(test_gym_user, caplog):
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.database.models import AuthAuditLog
    from web.services.auth_audit import AuthEventType, log_auth_event

    with caplog.at_level(logging.INFO, logger="web.services.auth_audit"):
        log_auth_event(AuthEventType.LOGIN_FAILED, gym_id=test_gym_user["id"],
                       user_id=test_gym_user["id"], ip_address=IP,
                       user_agent=PRIVATE, request_id=PRIVATE,
                       metadata={"email": EMAIL, "reason": "invalid_credentials"})
    with Session(get_engine()) as db:
        row = db.query(AuthAuditLog).filter(AuthAuditLog.request_id == PRIVATE).one()
        assert row.ip_address == IP and row.user_agent == PRIVATE
        assert row.user_id == test_gym_user["id"] and row.event_metadata["email"] == EMAIL
    records = [r for r in caplog.records if r.name == "web.services.auth_audit"]
    assert_operational_records_are_minimal(records, test_gym_user["id"])
    assert "login_failed" in records[0].getMessage()


def test_audit_failure_omits_exception_sql_and_parameters(caplog):
    from web.services.auth_audit import AuthEventType, log_auth_event

    db = Mock()
    db.commit.side_effect = StatementError("private error " + PRIVATE,
        "UPDATE synthetic SET password=:secret", {"secret": PRIVATE}, RuntimeError(URL))
    with caplog.at_level(logging.ERROR, logger="web.services.auth_audit"):
        log_auth_event(AuthEventType.LOGIN_FAILED, user_id=EMAIL, ip_address=IP, db=db)
    records = [r for r in caplog.records if r.name == "web.services.auth_audit"]
    assert_operational_records_are_minimal(records, "UPDATE synthetic")
    assert "StatementError" in records[0].getMessage()
    db.close.assert_not_called()  # The caller still owns an explicitly supplied session.


def test_audit_owns_session_cleanup_even_when_commit_and_rollback_fail(monkeypatch, caplog):
    from web.services import auth_audit

    class PrivateError(Exception):
        def __str__(self):
            raise AssertionError("Do not inspect exception strings")
        def __repr__(self):
            raise AssertionError("Do not inspect exception representations")

    db = Mock()
    db.commit.side_effect = PrivateError()
    db.rollback.side_effect = PrivateError()
    db.close.side_effect = PrivateError()
    monkeypatch.setattr(auth_audit, "SessionLocal", Mock(return_value=db))
    with caplog.at_level(logging.ERROR, logger=auth_audit.__name__):
        auth_audit.log_auth_event(auth_audit.AuthEventType.LOGIN_FAILED, ip_address=IP)
    db.rollback.assert_called_once()
    db.close.assert_called_once()
    records = [r for r in caplog.records if r.name == auth_audit.__name__]
    assert len(records) == 3
    assert_operational_records_are_minimal(records)


@pytest.mark.parametrize("bad", [[PRIVATE], {"secret": PRIVATE}, None, 10**400])
def test_sentry_unknown_and_malformed_values_do_not_escape_projection(bad):
    from web.observability.sentry_setup import _filter_events, _filter_transactions

    event = {"level": bad, "timestamp": bad, "release": bad, "tags": {"role": bad},
             "contexts": {"trace": {"status": bad, "op": bad}},
             "exception": {"values": [{"type": bad, "stacktrace": bad}]}, "spans": bad}
    assert PRIVATE not in json.dumps(_filter_events(event, {}))
    assert PRIVATE not in json.dumps(_filter_transactions(event, {}))


def private_event(transaction=False):
    event = {
        "event_id": "a" * 32, "level": "error", "platform": "python",
        "timestamp": 1792380000.0, "environment": "test",
        "message": URL, "logentry": {"message": PRIVATE, "formatted": URL, "params": [EMAIL]},
        "request": {"url": URL, "query_string": PRIVATE,
                    "data": {"note": PRIVATE}, "headers": {"Authorization": PRIVATE},
                    "env": {"REMOTE_ADDR": IP}, "method": "POST"},
        "user": {"id": PRIVATE, "email": EMAIL, "ip_address": IP},
        "extra": {"clinical": {"notes": PRIVATE}, "params": [EMAIL]},
        "tags": {"tenant": PRIVATE, "role": "owner"},
        "breadcrumbs": {"values": [{"message": PRIVATE, "data": {"url": URL, "params": [EMAIL]}}]},
        "contexts": {"health": {"notes": PRIVATE}, "trace": {
            "trace_id": "b" * 32, "span_id": "c" * 16,
            "op": "http.server", "data": {"sql": PRIVATE},
            "dynamic_sampling_context": {"user_segment": EMAIL}}},
        "exception": {"values": [{"type": "RuntimeError", "value": PRIVATE,
            "stacktrace": {"frames": [{"module": "web.auth", "filename": URL,
                "abs_path": URL, "lineno": 250, "function": PRIVATE, "vars": {"note": PRIVATE},
                "pre_context": [PRIVATE], "context_line": PRIVATE, "post_context": [PRIVATE]}]}}]},
        "profile": {"samples": [PRIVATE]}, "threads": {"values": [{"note": PRIVATE}]},
        "measurements": {PRIVATE: {"value": 1}}, "_meta": {"note": PRIVATE},
    }
    if transaction:
        event.update(type="transaction", transaction=URL, start_timestamp=1792379999.0,
                     spans=[{"span_id": "d" * 16, "trace_id": "b" * 32,
                             "parent_span_id": "c" * 16, "op": "db",
                             "start_timestamp": 1792379999.0, "timestamp": 1792380000.0,
                             "description": "SELECT " + PRIVATE, "data": {"params": [EMAIL]}}])
    return event


@pytest.mark.parametrize("transaction", [False, True])
def test_sentry_projects_closed_fields_at_final_boundary_and_clears_attachments(transaction):
    from web import auth  # Loaded application frames can retain location, never source/locals.
    from web.observability.sentry_setup import _filter_events, _filter_transactions

    original = private_event(transaction)
    hint = {"attachments": [Mock(filename=EMAIL)]}
    result = (_filter_transactions if transaction else _filter_events)(original, hint)
    assert result is not None
    rendered = json.dumps(result)
    for secret in (PRIVATE, EMAIL, IP, URL, "SELECT "):
        assert secret not in rendered
    assert hint["attachments"] == []
    assert result["event_id"] == "a" * 32
    if not transaction:
        exc = result["exception"]["values"][0]
        assert exc["type"] == "RuntimeError"
        frame = exc["stacktrace"]["frames"][0]
        assert frame == {"module": "web.auth", "filename": "web/auth.py", "lineno": 250, "in_app": True}
    else:
        assert result["transaction"] == "http.server"
        assert result["spans"][0]["op"] == "db"


def test_sentry_context_and_business_message_never_copy_identifiers_or_free_text():
    from web.observability.sentry_setup import capture_business_error, set_user_context

    with patch("web.observability.sentry_setup.sentry_sdk.set_user") as user, \
         patch("web.observability.sentry_setup.sentry_sdk.set_tag") as tag:
        set_user_context(EMAIL, PRIVATE, "owner")
        user.assert_called_once_with(None)
        assert EMAIL not in repr(user.call_args) and PRIVATE not in repr(tag.call_args)
    with patch("web.observability.sentry_setup.sentry_sdk.capture_message") as capture, \
         patch("web.observability.sentry_setup.sentry_sdk.push_scope") as scope:
        capture_business_error(URL, extra={"email": EMAIL, "clinical": {"note": PRIVATE}})
        capture.assert_called_once_with("Business operation failed", level="error")
        scope.return_value.__enter__.return_value.set_extra.assert_not_called()


def test_real_sentry_sdk_memory_envelopes_exclude_free_text_and_nonreviewed_channels():
    import sentry_sdk
    from sentry_sdk.transport import Transport
    from web.observability.sentry_setup import init_sentry

    class MemoryTransport(Transport):
        def __init__(self):
            super().__init__()
            self.envelopes = []
        def capture_envelope(self, envelope):
            self.envelopes.append(envelope)

    with patch("web.observability.sentry_setup.sentry_sdk.init") as initialize:
        init_sentry("https://public@example.invalid/1", "test", 1.0, 1.0)
    options = initialize.call_args.kwargs
    assert options["profiles_sample_rate"] == 0.0
    assert options["profile_session_sample_rate"] == 0.0
    assert options["enable_logs"] is False and options["enable_metrics"] is False
    transport = MemoryTransport()
    options["transport"] = transport
    options["default_integrations"] = False  # SDK serialization/envelopes remain real; no global patches.
    client = sentry_sdk.Client(**options)
    try:
        with sentry_sdk.isolation_scope() as scope:
            scope.set_client(client)
            scope.set_user({"email": EMAIL, "ip_address": IP})
            scope.set_extra("clinical", {"notes": PRIVATE})
            scope.add_attachment(bytes=PRIVATE.encode(), filename=EMAIL, add_to_transactions=True)
            sentry_sdk.add_breadcrumb(message=PRIVATE, category="sql", data={"query": PRIVATE})
            sentry_sdk.capture_event(private_event())
            sentry_sdk.capture_event(private_event(True))
            try:
                raise RuntimeError(URL)
            except RuntimeError:
                sentry_sdk.capture_exception()
            sentry_sdk.capture_message(PRIVATE)
            logging.getLogger("synthetic.telemetry").error("private %s", PRIVATE, extra={"note": EMAIL})
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            app = FastAPI()
            @app.post("/synthetic/{marker}")
            async def failing(marker: str, body: dict):
                raise StatementError("failure " + EMAIL, "UPDATE synthetic SET note=:note",
                                     {"note": body["note"]}, RuntimeError(URL))
            with TestClient(app, raise_server_exceptions=False) as http:
                response = http.post("/synthetic/" + PRIVATE + "?email=" + EMAIL,
                                     json={"note": PRIVATE}, headers={"Authorization": PRIVATE})
                assert response.status_code == 500
            sentry_sdk.flush()
    finally:
        client.close()
    assert len(transport.envelopes) >= 3
    rendered = b"\n".join(envelope.serialize() for envelope in transport.envelopes).decode()
    assert all(secret not in rendered for secret in (PRIVATE, EMAIL, IP, URL))
    item_types = {item.headers.get("type") for envelope in transport.envelopes for item in envelope.items}
    assert item_types <= {"event", "transaction"}
    assert {"event", "transaction"} <= item_types
    assert "RuntimeError" in rendered


@pytest.mark.parametrize("outcome", ["disabled", "sent", "failed"])
def test_email_logs_omit_recipient_subject_body_and_attachments(outcome, monkeypatch, caplog):
    from web.services import email_service

    monkeypatch.setattr(email_service, "_is_configured", lambda: outcome != "disabled")
    transport = Mock()
    if outcome == "sent":
        transport.Emails.send.return_value = {"id": "synthetic-provider-ack"}
    if outcome == "failed":
        transport.Emails.send.side_effect = RuntimeError(URL)
    monkeypatch.setitem(sys.modules, "resend", transport)
    with caplog.at_level(logging.INFO, logger=email_service.__name__):
        result = email_service._send(EMAIL, PRIVATE, URL, attachments=[{"content": PRIVATE}])
    assert result is (outcome == "sent")
    assert_operational_records_are_minimal([r for r in caplog.records if r.name == email_service.__name__])
    if outcome != "disabled":
        sent = transport.Emails.send.call_args.args[0]
        assert sent["to"] == [EMAIL] and sent["subject"] == PRIVATE
        assert sent["html"] == URL  # Privacy changes logs, never the authorized delivery payload.
