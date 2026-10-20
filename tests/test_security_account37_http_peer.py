"""Independent finite admission and privacy probes on both actual factories."""
import uuid

import pytest
from sqlalchemy import event

from tests import account_security37_http as current_http
from tests.test_account_security37_http import headers
from web.services import account_security as account

account37_engine = current_http.account37_engine
followup_db = current_http.followup_db
account_http = current_http.account_http
PREFIX = "/api/account/security"


def private(response):
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert all("mb_refresh" not in value for value in response.headers.get_list("set-cookie"))


def test_rejected_admission_has_zero_sql_or_auth_lookup_before_both_factories(account_http, monkeypatch):
    from web import auth
    case = account_http
    checks = []
    statements = []
    monkeypatch.setattr(auth, "verificar_token", lambda *_args, **_options: checks.append(True))
    def capture(_connection, _cursor, statement, _params, _context, _many):
        statements.append(statement)
    origin = headers(case)["Origin"]
    good = [("Origin", origin), ("X-MetodoBase-Browser", "1"), ("Content-Type", "application/json")]
    variants = [([], ""), (good[1:], ""), ([good[0], good[2]], ""),
                (good + [("Origin", origin)], ""), (good + [("X-MetodoBase-Browser", "1")], ""),
                ([("Origin", "https://foreign.invalid"), *good[1:]], ""),
                ([*good[:2], ("Content-Type", "text/plain")], ""),
                (good + [("Content-Type", "application/json")], ""), (good, "?unexpected=1")]
    event.listen(case["engine"], "before_cursor_execute", capture)
    try:
        for suffix in ("/email/request", "/email/confirm", "/password"):
            for request_headers, query in variants:
                response = case["raw"].post(PREFIX + suffix + query, content="{}", headers=request_headers)
                assert response.status_code in {403, 415}
                private(response)
    finally:
        event.remove(case["engine"], "before_cursor_execute", capture)
    assert checks == [] and statements == []


@pytest.mark.parametrize("route", ["status", "confirm", "password"])
def test_unexpected_failure_is_opaque_private_and_never_a_success_ack(account_http, monkeypatch, route):
    case = account_http
    marker = "PRIVATE-PEER-" + uuid.uuid4().hex
    def explode(*_args, **_kwargs):
        raise RuntimeError(marker)
    target = {"status": "email_status", "confirm": "confirm_email", "password": "change_password"}[route]
    monkeypatch.setattr(account, target, explode)
    if route == "status":
        response = case["raw"].get(PREFIX)
    elif route == "confirm":
        response = case["raw"].post(PREFIX + "/email/confirm", json={"token": "X" * 43}, headers=headers(case))
    else:
        response = case["raw"].post(PREFIX + "/password", json={"reauthentication_token": "X" * 43,
            "new_password": "Synthetic private changed password 42!", "confirm_password": "Synthetic private changed password 42!"},
            headers=headers(case))
    assert response.status_code == 503
    assert response.json()["detail"]["code"] in {"account_security_unconfirmed", "browser_session_unconfirmed"}
    assert marker not in response.text and '"sessions_revoked"' not in response.text
    private(response)


def test_public_get_with_proof_in_query_cannot_consume_or_echo_the_proof(account_http):
    case = account_http
    token = "Y" * 43
    response = case["raw"].get("/auth/verify-email?token=" + token)
    assert response.status_code == 200 and token not in response.text
    private(response)
    assert "api.js" not in response.text and "localStorage" not in response.text
