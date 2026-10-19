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
