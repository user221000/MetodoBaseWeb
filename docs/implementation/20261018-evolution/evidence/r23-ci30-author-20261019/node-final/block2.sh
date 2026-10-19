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
node tests/e2e/personal_diary_api.cjs > personal-diary-api.json
node tests/e2e/personal_diary_controller.cjs > personal-diary-controller.json
node tests/e2e/personal_logout.cjs > personal-diary-logout.json
node tests/e2e/personal_logout_ack.cjs > personal-diary-logout-ack.json
node tests/e2e/personal_export_controls.cjs > personal-export-controls.json
python scripts/check_frontend_report.py personal-diary-api.json --format counts --minimum 7
python scripts/check_frontend_report.py personal-diary-controller.json --format counts --minimum 18
python scripts/check_frontend_report.py personal-diary-logout.json --format counts --minimum 10
python scripts/check_frontend_report.py personal-diary-logout-ack.json --format counts --minimum 12
python scripts/check_frontend_report.py personal-export-controls.json --format counts --minimum 21
