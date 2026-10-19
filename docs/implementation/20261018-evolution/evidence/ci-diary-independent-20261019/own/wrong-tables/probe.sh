set -euo pipefail
browser_fixture_pid=''
seen_drivers=0
health_checks=0
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$QA_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$QA_EVENTS"
  case "$QA_MODE" in
   no-marker|delayed-marker) true ;;
   wrong-fixture) printf '%s\n' '{"fixture":"foreign-fixture","tables":26,"model_target_revision":"20261019_personal_diary"}' ;;
   wrong-head) printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261018_individual_publication"}' ;;
   wrong-tables) printf '%s\n' '{"fixture":"personal-diary-ui","tables":27,"model_target_revision":"20261019_personal_diary"}' ;;
   *) printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261019_personal_diary"}' ;;
  esac
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$QA_PYTHON" "$QA_STARTUP" "${@:2}"
 else
  "$QA_PYTHON" "$QA_GUARD" "${@:2}"
 fi
}
node() {
 seen_drivers=$((seen_drivers+1))
 printf 'driver%s %s\n' "$seen_drivers" "$browser_fixture_pid" >> "$QA_EVENTS"
 if [[ "$seen_drivers" == 1 ]]; then
  "$QA_PYTHON" "$QA_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens" good
  if [[ "$QA_MODE" == 'dead-after-first' ]]; then builtin kill "$browser_fixture_pid"; wait "$browser_fixture_pid" || true; fi
 else
  case "$QA_MODE" in
   second-missing) return 0 ;;
   second-empty) : > "$second_report" ;;
   second-page-errors) "$QA_PYTHON" "$QA_WRITER" "$second_report" "$second_format" "$second_minimum" "$second_screens" errors ;;
   *) "$QA_PYTHON" "$QA_WRITER" "$second_report" "$second_format" "$second_minimum" "$second_screens" good ;;
  esac
  if [[ "$QA_MODE" == 'second-exit23' ]]; then return 23; fi
 fi
 return 0
}
curl() {
 health_checks=$((health_checks+1))
 printf 'health%s\n' "$health_checks" >> "$QA_EVENTS"
 if [[ "$QA_MODE" == 'delayed-marker' && "$health_checks" == 3 ]]; then
  printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261019_personal_diary"}' >> "$fixture_log"
  printf 'marker\n' >> "$QA_EVENTS"
 fi
 return 0
}
sleep() { /usr/bin/sleep 0.005; }

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
run_browser_fixture own-fixture.py 9998 first.cjs first.json 17 named 8 second.cjs second.json 4 strings 4 personal-diary-ui
