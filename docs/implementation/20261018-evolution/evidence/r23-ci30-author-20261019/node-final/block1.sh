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
node tests/e2e/personal_operation.cjs > personal-operation-contracts.json
node tests/e2e/personal_operation_ambiguity_review.cjs > personal-operation-ambiguity.json
python scripts/check_frontend_report.py personal-operation-contracts.json --format counts --minimum 18
python scripts/check_frontend_report.py personal-operation-ambiguity.json --format counts --minimum 2
