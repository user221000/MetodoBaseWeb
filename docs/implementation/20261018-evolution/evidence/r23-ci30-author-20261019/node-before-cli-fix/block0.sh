set -euo pipefail
node() {
 local script="$1"; shift
 local args=()
 for arg in "$@"; do
  if [[ "$arg" == web/* ]]; then args+=("$CI_ROOT/$arg"); else args+=("$arg"); fi
 done
 "$CI_NODE" "$CI_ROOT/$script" "${args[@]}"
}
python() { local script="$1"; shift; "$CI_PYTHON" "$CI_ROOT/$script" "$@"; }
node tests/e2e/auth_refresh.cjs > auth-refresh-contracts.json
node tests/e2e/auth_refresh_storage.cjs > auth-refresh-storage.json
node tests/e2e/auth_refresh_race_review.cjs > auth-refresh-reproductions.json
node tests/e2e/auth_refresh_security_review.cjs > auth-refresh-security.json
node -e "const fs=require('fs'),a=JSON.parse(fs.readFileSync('auth-refresh-contracts.json')),b=JSON.parse(fs.readFileSync('auth-refresh-reproductions.json')),c=JSON.parse(fs.readFileSync('auth-refresh-security.json')),d=JSON.parse(fs.readFileSync('auth-refresh-storage.json')),valid=(r,n)=>Number.isSafeInteger(r.total)&&r.total>=n&&Number.isSafeInteger(r.passed)&&r.passed===r.total;if(!valid(a,33)||!Array.isArray(b.report)||b.report.length<2||b.report.some(x=>x.passed!==true)||!valid(c,13)||!valid(d,26))process.exit(1)"
