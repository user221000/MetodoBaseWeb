set -euo pipefail
browser_fixture_pid=''
seen_drivers=0
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  case "$CI_MARKER" in
   valid) printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261019_personal_diary"}' ;;
   malformed) printf '%s\n' '{"fixture":"personal-diary-ui",' ;;
   wrong) printf '%s\n' '{"fixture":"personal-diary-ui","tables":25,"model_target_revision":"20261019_personal_diary"}' ;;
  esac
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$CI_PYTHON" "$CI_STARTUP" "${@:2}"
 else
  "$CI_PYTHON" "$CI_GUARD" "${@:2}"
 fi
}
node() {
 seen_drivers=$((seen_drivers+1))
 printf 'driver%s %s\n' "$seen_drivers" "$browser_fixture_pid" >> "$CI_EVENTS"
 if [[ "$CI_FAIL" == "$seen_drivers" ]]; then return 7; fi
 if [[ "$CI_MISSING" == "$seen_drivers" ]]; then return 0; fi
 if [[ "$seen_drivers" == 1 ]]; then
  "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens" good
  if [[ "$CI_DEAD" == 1 ]]; then builtin kill "$browser_fixture_pid"; wait "$browser_fixture_pid" || true; fi
 else
  "$CI_PYTHON" "$CI_WRITER" "$second_report" "$second_format" "$second_minimum" "$second_screens" "$CI_BAD"
 fi
}
curl() { [[ "$CI_NOT_READY" != 1 ]]; }
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
      if [ -z "$ready_marker" ] || python scripts/check_browser_fixture_startup.py "$fixture_log" --fixture "$ready_marker" --tables 26 --revision 20261019_personal_diary 2>/dev/null; then ready=1; break; fi
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
run_browser_fixture fixture.py 9999 first.cjs first.json 9
