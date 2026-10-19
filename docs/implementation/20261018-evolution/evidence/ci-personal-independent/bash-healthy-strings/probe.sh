set -euo pipefail
browser_fixture_pid=''
kill() { printf '%s\n' "$1" >> "$QA_KILLS"; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  if [[ "${QA_SERVER_EXIT:-0}" == 1 ]]; then return 0; fi
  exec /usr/bin/sleep 20
 else
  "$QA_PYTHON" "$QA_GUARD" "${@:2}"
 fi
}
node() {
 if [[ "${QA_DRIVER_FAIL:-0}" == 1 ]]; then return 7; fi
 if [[ "${QA_REPORT_MISSING:-0}" == 1 ]]; then return 0; fi
 "$QA_PYTHON" "$QA_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens" "${QA_REPORT_BAD:-0}"
}
curl() { [[ "${QA_NOT_READY:-0}" != 1 ]]; }
sleep() { :; }

run_browser_fixture() {
  local fixture_script="$1" fixture_port="$2" driver="$3" expected_report="$4" minimum_checks="$5"
  local report_format="${6:-strings}" minimum_screens="${7:-0}"
  local fixture_log="docs/implementation/20261018-evolution/evidence/ux/ci-${fixture_port}-${driver##*/}-server.log"
  export METODOBASE_E2E_URL="http://127.0.0.1:${fixture_port}"
  python -X utf8 "$fixture_script" > "$fixture_log" 2>&1 &
  browser_fixture_pid=$!
  local ready=0
  for attempt in $(seq 1 30); do
    if curl --fail --silent "${METODOBASE_E2E_URL}/health/ready"; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" -ne 1 ]; then cat "$fixture_log"; return 1; fi
  node "$driver"
  python scripts/check_frontend_report.py "$expected_report" --format "$report_format" --minimum "$minimum_checks" --minimum-screens "$minimum_screens"
  kill "$browser_fixture_pid"
  wait "$browser_fixture_pid" || true
  browser_fixture_pid=''
}
run_browser_fixture synthetic_fixture.py 9999 synthetic_driver.cjs report.json 15 strings 0
