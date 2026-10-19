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
node tests/e2e/personal_history.cjs > personal-history-contracts.json
python scripts/check_frontend_report.py personal-history-contracts.json --format counts --minimum 23
