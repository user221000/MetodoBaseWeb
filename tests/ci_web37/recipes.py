"""Finite current web selection. Revision-specific migration histories stay old."""
from __future__ import annotations

WEB_SELECTORS = (
    "tests", "--ignore=tests/test_login_desktop.py",
    "--ignore-glob=tests/test_desktop*.py",
    "--ignore=tests/test_license_offline_security.py",
    "--deselect=tests/test_catalog_contract.py::test_catalog_copies_keep_personal_monthly_limits_separate_from_gym_daily_limits",
)
CURRENT_RUNTIME_SELECTORS = (*WEB_SELECTORS, "--ignore=tests/test_nutrition35_migrations.py",
    "--ignore=tests/test_security_container37_inputs_peer.py",
    "--ignore=tests/test_security_r31_browser_boundaries_peer.py",
    "--ignore=tests/test_mfa31_primary_privacy.py",
    "--ignore=tests/test_retention_followup.py",
    "--ignore=tests/test_security_r05_v5_current_peer.py",
    "--ignore=tests/test_secret_scan_finite_v6.py",
    "--ignore=tests/test_secret_scan_finite_v7.py",
    "--ignore=tests/test_security_r05_753_peer.py",
    "--ignore=tests/test_secret_scan_safety.py",
    "--deselect=tests/test_security_native35_original_expiry_canary.py::test_original_expired_sql_ack_must_refuse_before_first_fixture_admission",
    "--deselect=tests/test_security_native35_v7_peer.py::test_derived_harness_has_exact_full_inverse_and_original22_RAW_are_unchanged",
    "-p", "tests.ci_web37.composition", "--web37-current-fixtures",
    "-p", "tests.ci_web37.scope")
HISTORICAL35_SELECTORS = ("tests/test_nutrition35_migrations.py",)
# The first two original modules require their own immutable registry versions.
# The third module's literal24 criteria run in test_current37_r05_750.py against
# the current classifier with original Git reads authenticated by the capsule.
R05_FROZEN_PHASES = (("frozen-v5-peer60", 60), ("frozen-v6-author48", 48), ("frozen-v7-author15", 15))
# The original source/code objects remain unchanged in qa33_safety_transport.
# Its successful mocked tool I/O now carries the required complete summary.
SCANNER_SAFETY_ORIGINAL = "tests.test_secret_scan_safety"
SCANNER_SAFETY_COMPANION = "tests.test_current_scanner_completion_safety"
SCANNER_SAFETY_CASES = (
    "test_report_drops_matches_secrets_and_author_metadata",
    "test_scanner_failure_withholds_captured_output",
    "test_files_changed_or_added_during_scan_invalidate_gate[changed]",
    "test_files_changed_or_added_during_scan_invalidate_gate[added]",
    "test_unreviewed_binary_version_is_rejected",
    r"test_bom_text_is_transcoded_only_in_private_snapshot[utf-16-le-\xff\xfe-utf-16]",
    r"test_bom_text_is_transcoded_only_in_private_snapshot[utf-16-be-\xfe\xff-utf-16]",
    r"test_bom_text_is_transcoded_only_in_private_snapshot[utf-32-le-\xff\xfe\x00\x00-utf-32]",
    r"test_bom_text_is_transcoded_only_in_private_snapshot[utf-32-be-\x00\x00\xfe\xff-utf-32]",
    r"test_bom_text_is_transcoded_only_in_private_snapshot[utf-8-\xef\xbb\xbf-utf-8-sig]",
    "test_invalid_bom_text_fails_closed_without_modifying_original",
)


def require_scanner_safety_companion(identities):
    required = {(SCANNER_SAFETY_COMPANION, name) for name in SCANNER_SAFETY_CASES}
    selected = [tuple(row) for row in identities
                if row[0] in {SCANNER_SAFETY_ORIGINAL, SCANNER_SAFETY_COMPANION}]
    if len(selected) != len(required) or set(selected) != required:
        raise ValueError("All eleven original scanner safety identities require their exact current companion")


NATIVE_EXPIRED_ORIGINAL = ("tests.test_security_native35_original_expiry_canary",
    "test_original_expired_sql_ack_must_refuse_before_first_fixture_admission")
NATIVE_EXPIRY_REQUIRED = (
    ("tests.test_security_native35_original_expiry_canary",
     "test_original_unexpired_control_reaches_only_fake_fixture_marker"),
    ("tests.test_security_native35_v7_peer",
     "test_actual_new_launcher_refuses_expired_before_fake_SQL_fixture_and_has_valid_control[True]"),
    ("tests.test_security_native35_v7_peer",
     "test_expiry_during_child_allows_own_finalizer_but_refuses_next_phase"),
    ("tests.test_security_native35_v7_peer",
     "test_browser_readmission_requires_SQL_then_Chrome_and_stops_on_expired_SQL"),
    ("tests.test_current37_native_original22",
     "test_derived_harness_has_exact_full_inverse_and_original22_RAW_are_unchanged"),
)
NATIVE_PHYSICAL_ORIGINAL = ("tests.test_security_native35_v7_peer",
    "test_derived_harness_has_exact_full_inverse_and_original22_RAW_are_unchanged")


def require_native_expiry_replacement(identities):
    rows = [tuple(row) for row in identities]
    if (NATIVE_EXPIRED_ORIGINAL in rows or NATIVE_PHYSICAL_ORIGINAL in rows
            or any(rows.count(case) != 1 for case in NATIVE_EXPIRY_REQUIRED)):
        raise ValueError("The historical native expiry refusal requires V7 admission and phase controls")


SMOKE_SELECTORS = (
    "tests/test_followup34_http.py::test_full_mfa_context_and_create_edit_complete_history_replay",
    "tests/test_nutrition35_http.py::test_gym_declaration_survives_omitted_and_null_edits_and_reads_are_private",
    "tests/test_personal_progress_http.py::test_real_personal_context_measurement_cas_and_double_owner",
    "tests/test_google33_http.py::test_google_success_preserves_prior_audit_without_provider_or_session_secrets",
    "tests/test_current_publication_fixture_review.py::test_actual_factor_login_does_not_grant_a_privileged_mutation",
    "tests/test_followup34_mechanisms.py::test_event_atomically_creates_and_advances_exact_projection",
    "-p", "tests.ci_web37.composition", "--web37-current-fixtures",
)
CONTROL_SELECTORS = (
    "tests/test_ci_web37_reports.py", "tests/test_ci_web37_composition.py",
    "tests/test_ci_web37_scope.py", "tests/test_ci_web37_raw_git.py",
    "tests/test_ci_web37_git_recipe.py",
    "tests/test_ci_web37_node_current.py",
    "tests/test_ci_web37_pg_legacy.py",
    "tests/test_ci_web37_container_inputs.py",
    "tests/test_security_container37_extras_peer.py", "tests/test_security_container37_count57_peer.py",
    "tests/test_security_container37_portable_peer.py",
    "-p", "tests.ci_web37.composition", "--web37-current-fixtures",
    "-p", "tests.ci_web37.scope",
)
PG_PHASES = (
    ("nutrition", ("tests/integration_current37_nutrition.py",)),
    ("notifications", ("tests/integration_current37_notifications.py",)),
    ("account", ("tests/integration_current37_account.py",)),
    ("restore", ("tests/integration_current37_restore.py",)),
)
SHUFFLE_SEED = 20261018
NODE_MAP = "docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_CI_MAP.json"

# These remain explicit transition gates on their original predecessors, not
# misleading physical37 witnesses. A current test factory must use a37 fixture.
MIGRATION_PHASES = (
    ("nutrition35", ("tests/test_nutrition35_migrations.py",)),
    ("notifications36", ("tests/integration_notifications36_migrations.py", "-k", "postgresql")),
    ("account37", ("tests/integration_account_security37_pg_migrations.py",)),
)
