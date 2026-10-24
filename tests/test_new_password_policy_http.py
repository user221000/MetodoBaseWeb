"""Specialize the literal B19 HTTP regressions with the new short-value boundary.

Only the test's candidate source changes. Actual invitation/reset/MFA/password
services, persistent-state assertions, providers' local sinks and successful
operations are the original reviewed B19 cases. No application validator is
replaced. The fixtures run on each supported current factory.
"""
from contextlib import contextmanager

import logging

import pytest

from tests import account_security38_http as account_security37_http
from tests import test_password_blocklist19 as original

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http
no_password_values_in_logs = original.no_password_values_in_logs

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


def specialize_candidate(monkeypatch, candidate):
    @contextmanager
    def short_value(*args, **kwargs):
        yield candidate
    monkeypatch.setattr(original, "policy_fault", short_value)
    monkeypatch.setattr(original, "STRONG", FIFTEEN)


@pytest.mark.parametrize("account_http", ["web.main_web"], indirect=True)
@pytest.mark.parametrize("candidate", SHORT)
def test_short_invitation_preserves_original_token_then_fifteen_succeeds(account_http, monkeypatch, tmp_path, candidate):
    specialize_candidate(monkeypatch, candidate)
    original.test_invitation_policy_failure_preserves_same_token_then_strong_succeeds(
        account_http, monkeypatch, tmp_path, "common")


@pytest.mark.parametrize("candidate", SHORT)
def test_short_reset_preserves_original_link_then_allowed_change_succeeds(account_http, monkeypatch, tmp_path, candidate):
    specialize_candidate(monkeypatch, candidate)
    original.test_recovery_policy_failure_preserves_link_then_strong_succeeds(
        account_http, monkeypatch, tmp_path, "common")


@pytest.mark.parametrize("candidate", SHORT)
def test_short_change_preserves_primary_and_factor_then_fifteen_succeeds(account_http, monkeypatch, tmp_path, candidate):
    specialize_candidate(monkeypatch, candidate)
    original.test_account_policy_failure_preserves_primary_and_factor_then_strong_succeeds(
        account_http, monkeypatch, tmp_path, "common")
