"""Unchanged nutrition35 HTTP criteria, explicitly executed on current37 PG.

Only the database/physical witness changes. No old migration assertion is
retargeted and no password, factor, permission, provider or repository bypass
is introduced. Personal generation retains its SaaS-only factory boundary.
"""
from tests.ci_web37.fixtures import current37_witness, followup_db
from tests.followup34_http import followup_http
from tests.test_nutrition35_http import (
    personal35_http,
    test_declared_profile_is_rejected_before_any_quota_CPU_or_object,
    test_gym_declaration_survives_omitted_and_null_edits_and_reads_are_private,
    test_independent_personal_profile_preserves_declaration_without_consuming_quota,
    test_invalid_declaration_is_not_echoed_or_saved,
    test_real_PDF_cannot_become_ready_after_restrictions_change,
    test_worker_rechecks_a_new_declaration_and_compensates_the_reservation,
)

__all__ = ['current37_witness', 'followup_db', 'followup_http', 'personal35_http', 'test_declared_profile_is_rejected_before_any_quota_CPU_or_object', 'test_gym_declaration_survives_omitted_and_null_edits_and_reads_are_private', 'test_independent_personal_profile_preserves_declaration_without_consuming_quota', 'test_invalid_declaration_is_not_echoed_or_saved', 'test_real_PDF_cannot_become_ready_after_restrictions_change', 'test_worker_rechecks_a_new_declaration_and_compensates_the_reservation']
