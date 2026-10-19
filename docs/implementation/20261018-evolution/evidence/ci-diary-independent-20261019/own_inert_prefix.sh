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
