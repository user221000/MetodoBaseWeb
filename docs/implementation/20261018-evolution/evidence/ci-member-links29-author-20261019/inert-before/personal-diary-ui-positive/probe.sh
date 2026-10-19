set -euo pipefail
browser_fixture_pid=''
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  printf '{"fixture":"%s","tables":%s,"model_target_revision":"%s"}\n' "$CI_MARKER" "$CI_TABLES" "$CI_REVISION"
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$CI_PYTHON" "$CI_STARTUP" "${@:2}"
 else
  "$CI_PYTHON" "$CI_GUARD" "${@:2}"
 fi
}
node() {
 printf 'driver %s\n' "$browser_fixture_pid" >> "$CI_EVENTS"
 if [[ "$CI_MODE" == 'driver-error' ]]; then return 7; fi
 if [[ -n "$second_driver" && "$1" == "$second_driver" ]]; then
  "$CI_PYTHON" "$CI_WRITER" "$second_report" positive "$second_minimum" "$second_screens" "$second_format"
 else
  "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$CI_MODE" "$minimum_checks" "$minimum_screens" "$report_format"
 fi
}
curl() { return 0; }
sleep() { /usr/bin/sleep 0.01; }
run_browser_fixture() {
  local fixture_script="$1" fixture_port="$2" driver="$3" expected_report="$4" minimum_checks="$5"
  local report_format="${6:-strings}" minimum_screens="${7:-0}"
  local second_driver="${8:-}" second_report="${9:-}" second_minimum="${10:-0}"
  local second_format="${11:-strings}" second_screens="${12:-0}" ready_marker="${13:-}"
  local fixture_log="docs/implementation/20261018-evolution/evidence/ux/ci-${fixture_port}-${driver##*/}-server.log"
  export METODOBASE_E2E_URL="http://127.0.0.1:${fixture_port}"
  python -X utf8 "$fixture_script" > "$fixture_log" 2>&1 &
  browser_fixture_pid=$!
  local ready=0
  for attempt in $(seq 1 30); do
    if ! kill -0 "$browser_fixture_pid" 2>/dev/null; then cat "$fixture_log"; return 1; fi
    if curl --fail --silent "${METODOBASE_E2E_URL}/health/ready"; then
      if [ -z "$ready_marker" ] || python scripts/check_browser_fixture_startup.py "$fixture_log" --fixture "$ready_marker" --tables 29 --revision 20261019_client_account_links 2>/dev/null; then ready=1; break; fi
    fi
    sleep 1
  done
  if [ "$ready" -ne 1 ]; then cat "$fixture_log"; return 1; fi
  kill -0 "$browser_fixture_pid" || return 1
  node "$driver" || return $?
  python scripts/check_frontend_report.py "$expected_report" --format "$report_format" --minimum "$minimum_checks" --minimum-screens "$minimum_screens" || return $?
  if [ -n "$second_driver" ]; then
    kill -0 "$browser_fixture_pid" || return 1
    node "$second_driver" || return $?
    python scripts/check_frontend_report.py "$second_report" --format "$second_format" --minimum "$second_minimum" --minimum-screens "$second_screens" || return $?
  fi
  kill "$browser_fixture_pid"
  wait "$browser_fixture_pid" || true
  browser_fixture_pid=''
}
run_browser_fixture tests/e2e/personal_diary_server.py 8776 tests/e2e/personal_diary.cjs "${browser_evidence}/diary-ui-browser-${METODOBASE_EVIDENCE_BATCH}/report.json" 17 named 8 tests/e2e/personal_export_context_browser.cjs "${browser_evidence}/diary-ui-consumer-fix-browser-${METODOBASE_EVIDENCE_BATCH}/report.json" 4 strings 4 personal-diary-ui
