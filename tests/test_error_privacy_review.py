"""R17/R31 negative controls for global handlers and automatic alert payloads."""
import importlib
import json
import logging
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import StatementError


def private_error():
    return StatementError("Synthetic private error text",
        "UPDATE synthetic SET value=:value WHERE subject=:subject",
        {"value": "synthetic-private-health-note", "subject": "synthetic-private-subject"},
        RuntimeError("synthetic-private-inner-error"))


@pytest.mark.parametrize("factory", ["web.main_web", "api.app"])
def test_global_handler_logs_class_without_sql_parameters_or_traceback(factory, caplog):
    app = importlib.import_module(factory).create_app()
    @app.get("/security-review/{subject}")
    async def failed(subject: str):
        raise private_error()
    with TestClient(app, raise_server_exceptions=False) as client:
        caplog.clear()
        with caplog.at_level(logging.ERROR):
            response = client.get("/security-review/synthetic-private-path?note=synthetic-private-query")
    assert response.status_code == 500
    assert "synthetic-private" not in response.text
    assert "synthetic-private" not in caplog.text
    assert "UPDATE synthetic" not in caplog.text
    records = [record for record in caplog.records if "Unhandled" in record.getMessage()]
    assert len(records) == 1 and "StatementError" in records[0].getMessage()
    assert not records[0].exc_info


def test_api_global_error_omits_subject_path_and_arbitrary_client_context(monkeypatch):
    from api import app as module
    observed = []
    monkeypatch.setattr(module, "track_error", lambda *args, **kwargs: observed.append(kwargs))
    app = module.create_app()
    @app.get("/security-review/{subject}")
    async def failed(subject: str):
        raise private_error()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/security-review/synthetic-private-path?note=synthetic-private-query")
    assert response.status_code == 500
    assert len(observed) == 1
    payload = json.dumps(observed[0])
    assert "synthetic-private" not in payload and "client" not in payload
    assert observed[0].get("request_path", "") in {"", "/security-review/{subject}"}


def alerter_without_providers(monkeypatch):
    from web.middleware import alerting
    monkeypatch.setattr(alerting, "ALERT_SLACK_WEBHOOK", "")
    monkeypatch.setattr(alerting, "ALERT_EMAIL_TO", "")
    monkeypatch.setattr(alerting, "ALERT_WEBHOOK_URL", "")
    alerter = alerting.ErrorAlerter(enabled=True, cooldown_minutes=0)
    alerter._notifiers.clear()
    return alerter


def test_automatic_error_alert_history_only_contains_closed_context(monkeypatch):
    alerter = alerter_without_providers(monkeypatch)
    for _ in range(11):
        alerter.track_error(private_error(), request_path="/accounts/synthetic-private-path", extra_context={
            "method": "POST", "client": "synthetic-private-ip", "error_type": "forged-type",
            "authorization": "synthetic-private-bearer", "health": {"notes": "synthetic-private-note"}})
    history = alerter.get_alert_history()
    assert history
    assert "synthetic-private" not in json.dumps(history)
    for alert in history:
        context = alert["context"]
        assert set(context) <= {"error_type", "recent_errors_1min", "method"}
        assert context["error_type"] == "StatementError" and context["method"] == "POST"
    assert any(alert["severity"] == "critical" for alert in history)


@pytest.mark.parametrize("method", ["synthetic-private-method", ["GET"], None])
def test_alert_context_rejects_unrecognized_method_values(monkeypatch, method):
    alerter = alerter_without_providers(monkeypatch)
    for _ in range(6):
        alerter.track_error(RuntimeError("synthetic-private-error"), extra_context={"method": method})
    assert "method" not in alerter.get_alert_history()[0]["context"]


def test_tracker_never_calls_exception_string_or_representation(monkeypatch):
    class PrivateError(Exception):
        def __str__(self):
            raise AssertionError("Exception string must not be inspected")
        def __repr__(self):
            raise AssertionError("Exception repr must not be inspected")
    alerter = alerter_without_providers(monkeypatch)
    for _ in range(6):
        alerter.track_error(PrivateError())
    assert alerter.get_alert_history()[0]["context"]["error_type"] == "PrivateError"


def test_failed_rollback_stops_compensation_without_claiming_refund_or_logging_parameters(monkeypatch, caplog):
    from fastapi import HTTPException
    from web.services import gym_generation_quota
    session = Mock()
    session.rollback.side_effect = private_error()
    release = Mock(side_effect=AssertionError("Release must not run after failed rollback"))
    monkeypatch.setattr(gym_generation_quota, "fail_gym_generation", release)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(HTTPException) as failure:
            gym_generation_quota.compensate_generation_failure(session, "synthetic-owner", "synthetic-reservation")
    assert failure.value.status_code == 503
    assert failure.value.detail["code"] == "generation_reconciliation_required"
    assert "historial" in failure.value.detail["message"]
    assert "synthetic-private" not in caplog.text
    assert not any(record.exc_info for record in caplog.records)
    release.assert_not_called()
