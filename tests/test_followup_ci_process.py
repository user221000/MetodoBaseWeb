"""Run the new owned Bash process gate with explicit inert service seams."""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests import verify_history_index_ci as guard
from tests.test_followup_ci_trust import browser_report
from web.database.alembic.history_index_contract_v1 import expected_history_index


@pytest.mark.parametrize('mode', ['positive', 'driver-error', 'old-head', 'bad-report', 'finalizer-error'])
def test_followup_bash_owns_and_finalizes_exactly_its_fixture_even_when_gate_fails(tmp_path, mode):
    """No HTTP, PostgreSQL or Chrome executes in these orchestration probes."""
    bash = os.environ.get('METODOBASE_CI_BASH') or (
        'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
    assert bash
    base = Path(os.environ['METODOBASE_CI_PROCESS_EVIDENCE']) if os.environ.get('METODOBASE_CI_PROCESS_EVIDENCE') else tmp_path
    directory = base / mode
    directory.mkdir(parents=True, exist_ok=False)
    runner = directory / 'runner'; runner.mkdir()
    tree = ast.parse((guard.ROOT / 'tests/e2e/followup_server.py').read_text(encoding='utf8'))
    names = ast.literal_eval(next(node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                                 and any(isinstance(target, ast.Name) and target.id == 'names' for target in node.targets)))
    marker = {'fixture': 'r23-followup-real-pg', 'port': 8795,
              'database': 'metodobase_test_followup_' + 'a' * 16,
              'runtime_revision': '20261019_personal_history_index', 'model_tables': 29, 'actual_tables': 30,
              'application_role_restricted_nonowner': True,
              'history_order_index': expected_history_index('postgresql'),
              'sources': {name: hashlib.sha256((guard.ROOT / name).read_bytes()).hexdigest() for name in names}}
    if mode == 'old-head': marker['runtime_revision'] = '20261019_client_account_links'
    report = browser_report()
    if mode == 'bad-report': report['failure'] = {'name': 'SyntheticFailureAfterAllChecks'}
    (directory / 'template.json').write_text(json.dumps({'marker': marker, 'report': report}), encoding='utf8')
    writer = directory / 'writer.py'
    writer.write_text('''import json,os,sys
from pathlib import Path
value=json.loads(Path(os.environ['CI_TEMPLATE']).read_bytes())
kind,target=sys.argv[1:3]
if kind=='marker':
    data=value['marker'];data['pid']=int(sys.argv[3])
    Path(target).write_text(json.dumps(data),encoding='utf8')
else:
    Path(target,'report.json').write_text(json.dumps(value['report']),encoding='utf8')
''', encoding='utf8')
    prefix=r'''python() {
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
'''
    script = directory / 'probe.sh'; script.write_bytes((prefix + guard.FOLLOWUP_BROWSER_STEP['run']).encode())
    environment = dict(os.environ, RUNNER_TEMP=runner.as_posix(), GITHUB_WORKSPACE=guard.ROOT.as_posix(),
                       CI_PYTHON=Path(sys.executable).as_posix(), CI_WRITER=writer.as_posix(),
                       CI_TEMPLATE=(directory / 'template.json').as_posix(), CI_EVENTS=(directory / 'events.log').as_posix(),
                       CI_MODE=mode, METODOBASE_TEST_MIGRATOR_URL='postgresql+psycopg2://synthetic@127.0.0.1:55483/metodobase_test_inert',
                       METODOBASE_TEST_POSTGRES_URL='postgresql+psycopg2://synthetic@127.0.0.1:55483/metodobase_test_inert', METODOBASE_TEST_PG_BIN='/inert/not-executed')
    try:
        result = subprocess.run([bash, script.as_posix()], cwd=guard.ROOT, env=environment,
                                capture_output=True, timeout=30, check=False)
    finally:
        stop = runner / 'followup-private/stop'
        if stop.parent.is_dir():
            stop.touch(exist_ok=True)
    (directory / 'stdout.log').write_bytes(result.stdout); (directory / 'stderr.log').write_bytes(result.stderr)
    assert (result.returncode == 0) == (mode == 'positive'), result.stderr.decode(errors='replace')
    events = (directory / 'events.log').read_text().splitlines()
    starts = [line for line in events if line.startswith('start ')]
    closed = [line for line in events if line.startswith('closed ')]
    assert len(starts) == len(closed) == 1 and starts[0].split()[1] == closed[0].split()[1]
    assert events.count('driver') == (0 if mode == 'old-head' else 1)
