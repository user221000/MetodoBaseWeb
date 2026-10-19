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
node tests/e2e/member_link_context.cjs > member-link-context.json
python scripts/check_frontend_report.py member-link-context.json --format counts --minimum 26
node tests/e2e/member_link_fragment.cjs > member-link-fragment.json
python scripts/check_frontend_report.py member-link-fragment.json --format counts --minimum 15
node tests/e2e/member_link_api.cjs > member-link-api.json
python scripts/check_frontend_report.py member-link-api.json --format counts --minimum 23
node tests/e2e/member_link_consumers.cjs > member-link-consumers.json
python scripts/check_frontend_report.py member-link-consumers.json --format counts --minimum 16
node tests/e2e/member_link_export.cjs > member-link-export.json
python scripts/check_frontend_report.py member-link-export.json --format counts --minimum 32
node tests/e2e/member_link_controls.cjs web/static/js/vinculos-ui.js > member-link-controls.json
python scripts/check_frontend_report.py member-link-controls.json --format counts --minimum 3
