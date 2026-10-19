python() {
 if [[ "$1" == '-X' ]]; then
  shift 3
  local report='' stop='' own_pid="$BASHPID"
  while [[ $# -gt 0 ]]; do
   if [[ "$1" == '--report' ]]; then report="$2"; shift 2
   elif [[ "$1" == '--stop-file' ]]; then stop="$2"; shift 2
   else shift; fi
  done
  printf 'start %s\n' "$own_pid" >> "$CI_EVENTS"
  "$CI_PYTHON" "$CI_WRITER" marker "$report" "$own_pid"
  if [[ "$CI_MODE" == 'old-head' ]]; then /usr/bin/sleep 0.5
  else while [[ ! -f "$stop" ]]; do /usr/bin/sleep 0.005; done; fi
  printf 'closed %s\n' "$own_pid" >> "$CI_EVENTS"
  if [[ "$CI_MODE" == 'finalizer-error' ]]; then return 4; fi
 else "$CI_PYTHON" "$@"; fi
}
node() {
 if [[ "$1" == '-e' ]]; then printf '/inert/no-chrome'; return; fi
 printf 'driver\n' >> "$CI_EVENTS"
 if [[ "$CI_MODE" == 'driver-error' ]]; then return 7; fi
 "$CI_PYTHON" "$CI_WRITER" report "$2"
}
curl() { return 0; }
sleep() { /usr/bin/sleep 0.005; }
set -euo pipefail
private="$RUNNER_TEMP/followup-private"
public="$RUNNER_TEMP/followup-public"
mkdir "$private" "$public"
fixture_pid=""
finish_followup() {
  status=$?
  trap - EXIT INT TERM
  touch "$private/stop"
  if [ -n "$fixture_pid" ]; then
    for attempt in $(seq 1 100); do
      if ! jobs -pr | grep -qx "$fixture_pid"; then break; fi
      sleep 0.2
    done
    if jobs -pr | grep -qx "$fixture_pid"; then
      echo "Owned follow-up fixture did not finalize" >&2
      status=1
    elif ! wait "$fixture_pid"; then
      status=1
    fi
  fi
  exit "$status"
}
trap finish_followup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
python -c 'import json,os,pathlib; keys=("METODOBASE_TEST_MIGRATOR_URL","METODOBASE_TEST_POSTGRES_URL","METODOBASE_TEST_PG_BIN"); pathlib.Path(os.environ["RUNNER_TEMP"],"followup-private","config.json").write_text(json.dumps({key:os.environ[key] for key in keys}),encoding="utf8")'
export FOLLOWUP_NODE_MODULES="$GITHUB_WORKSPACE/tests/e2e/node_modules"
export CHROME_PATH=$(node -e "process.stdout.write(require('./tests/e2e/node_modules/playwright-core').chromium.executablePath())")
python -X utf8 tests/e2e/followup_server.py --pg-config "$private/config.json" --report "$public/startup.json" --stop-file "$private/stop" --port 8795 >"$private/server.stdout.log" 2>"$private/server.stderr.log" &
fixture_pid=$!
ready=0
for attempt in $(seq 1 90); do
  if ! jobs -pr | grep -qx "$fixture_pid"; then break; fi
  if python scripts/check_followup_fixture.py "$public/startup.json" --pid "$fixture_pid" --port 8795 2>/dev/null && curl --fail --silent http://127.0.0.1:8795/health >/dev/null; then ready=1; break; fi
  sleep 1
done
test "$ready" = 1
export FOLLOWUP_STARTUP_REPORT="$public/startup.json"
node tests/e2e/dashboard_followup_browser.cjs "$public"
python tests/e2e/normalize_followup_report.py "$public/report.json" "$public/normalized.json" --kind browser --minimum 8
python scripts/check_frontend_report.py "$public/normalized.json" --format named --minimum 8 --minimum-screens 5
python scripts/check_followup_fixture.py "$public/startup.json" --pid "$fixture_pid" --port 8795
