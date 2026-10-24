"""Literal new-password HTTP bodies on a separate real38 PG fixture.

Both supported factories remain in the original fixture parametrization. The
invitation case retains its original SaaS-only parameter (the API has no team
invitation endpoint). No password/security DTO, route or auth dependency is mocked.
"""
import pytest

from tests import test_new_password_policy as policy
from tests import test_new_password_policy_http as policy_http
from tests.ci_web38.pg_fixtures import (database_schema, isolated_database,
    pg38_database, pg38_runtime, released)  # noqa: F401 -- explicit current38 PG fixtures


@pytest.fixture(scope='module')
def followup_db(pg38_database):
    return pg38_database.admin, pg38_database.app


account_http = policy.account_http
no_password_values_in_logs = policy_http.no_password_values_in_logs
no_new_credential_values_in_logs = policy.no_new_credential_values_in_logs

# Function objects, original parameter labels, helper globals and assertions
# remain in the Root-authored modules; only this namespace's DB fixture changes.
test_registration_rejection_does_not_persist_or_disclose_then_fifteen_succeeds = policy.test_registration_rejection_does_not_persist_or_disclose_then_fifteen_succeeds
test_existing_short_password_hash_still_logs_in_without_rotation = policy.test_existing_short_password_hash_still_logs_in_without_rotation
test_short_invitation_preserves_original_token_then_fifteen_succeeds = policy_http.test_short_invitation_preserves_original_token_then_fifteen_succeeds
test_short_reset_preserves_original_link_then_allowed_change_succeeds = policy_http.test_short_reset_preserves_original_link_then_allowed_change_succeeds
test_short_change_preserves_primary_and_factor_then_fifteen_succeeds = policy_http.test_short_change_preserves_primary_and_factor_then_fifteen_succeeds
