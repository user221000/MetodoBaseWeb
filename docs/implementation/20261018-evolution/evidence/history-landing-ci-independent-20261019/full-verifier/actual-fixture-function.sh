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
      if [ -z "$ready_marker" ] || python scripts/check_browser_fixture_startup.py "$fixture_log" --fixture "$ready_marker" --tables 26 --revision 20261019_account_recovery 2>/dev/null; then ready=1; break; fi
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
