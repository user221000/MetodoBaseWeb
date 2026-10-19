"""Current33 fixture binding; imported original function objects retain every assertion."""

import pytest

from tests.ci_google33.owned import migration_database

from tests.integration_personal_diary_postgres import diary_pg

from tests.integration_personal_diary_postgres import (
    test_force_rls_own_dml_foreign_absent_and_pool_reuse,
    test_http_member_personal_scope_export_and_foreign_source_under_force_rls,
    test_mexico_midnight_and_typed_utc_are_independent_of_session_timezone,
    test_rollback_and_real_commit_ack_uncertainty_are_visible_and_recoverable,
    test_two_processes_have_one_winner_for_absent_and_existing_day,
)

from tests.integration_personal_diary_security_review import (
    test_committed_session_cannot_change_subject_for_diary_or_export,
    test_identity_is_revalidated_after_account_lock_is_acquired,
)

pytestmark=pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
