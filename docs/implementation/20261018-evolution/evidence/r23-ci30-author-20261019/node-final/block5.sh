set -euo pipefail
node() {
 if [[ "$1" == -* ]]; then "$CI_NODE" "$@"; return; fi
 local script="$1"; shift
 local args=()
 for arg in "$@"; do
  if [[ "$arg" == web/* ]]; then args+=("$CI_ROOT/$arg"); else args+=("$arg"); fi
 done
 "$CI_NODE" "$CI_ROOT/$script" "${args[@]}"
}
python() { local script="$1"; shift; "$CI_PYTHON" "$CI_ROOT/$script" "$@"; }
node tests/e2e/session_revision_events.cjs > followup-contracts-session_revision_events.raw.json
python tests/e2e/normalize_followup_report.py followup-contracts-session_revision_events.raw.json followup-contracts-session_revision_events.json --kind counts --minimum 11
python scripts/check_frontend_report.py followup-contracts-session_revision_events.json --format counts --minimum 11
node tests/e2e/session_expiry_fences.cjs > followup-contracts-session_expiry_fences.raw.json
python tests/e2e/normalize_followup_report.py followup-contracts-session_expiry_fences.raw.json followup-contracts-session_expiry_fences.json --kind counts --minimum 3
python scripts/check_frontend_report.py followup-contracts-session_expiry_fences.json --format counts --minimum 3
node tests/e2e/dashboard_followup.cjs > followup-contracts-dashboard_followup.raw.json
python tests/e2e/normalize_followup_report.py followup-contracts-dashboard_followup.raw.json followup-contracts-dashboard_followup.json --kind counts --minimum 20
python scripts/check_frontend_report.py followup-contracts-dashboard_followup.json --format counts --minimum 20
node tests/e2e/session_expiry_security.cjs > followup-contracts-session_expiry_security.raw.json
python tests/e2e/normalize_followup_report.py followup-contracts-session_expiry_security.raw.json followup-contracts-session_expiry_security.json --kind counts --minimum 10
python scripts/check_frontend_report.py followup-contracts-session_expiry_security.json --format counts --minimum 10
node tests/e2e/dashboard_followup_focus.cjs > followup-contracts-dashboard_followup_focus.raw.json
python tests/e2e/normalize_followup_report.py followup-contracts-dashboard_followup_focus.raw.json followup-contracts-dashboard_followup_focus.json --kind counts --minimum 4
python scripts/check_frontend_report.py followup-contracts-dashboard_followup_focus.json --format counts --minimum 4
