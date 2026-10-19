"""Independent actual-function startup/report/liveness canaries; owned children only."""
import re
import tempfile
import zipfile
from qa_support import *

before=photo('inert-own-before')
workflow=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf8')
import yaml
tree=yaml.safe_load(workflow)
block=next(step['run'] for step in tree['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run',''))
function=block[block.index('run_browser_fixture() {'):block.index('\nbrowser_evidence=')]
assert function+'\n' == (OUT/'full-verifier/actual-fixture-function.sh').read_text(encoding='utf8')
calls=[line for line in block.splitlines() if line.startswith('run_browser_fixture tests/e2e/personal_history_server.py ') or line.startswith('run_browser_fixture tests/e2e/landing_server.py ')]
assert len(calls)==2
scratch=Path(tempfile.mkdtemp(prefix='metodobase-history-ci-owned-process-'))
writer=scratch/'report_writer.py'
writer.write_text('''import json,sys
from pathlib import Path
path,mode,n,s=sys.argv[1:];n=int(n);s=int(s)
r={'checks':[str(i) for i in range(n)],'pageErrors':[],'screens':[str(i) for i in range(s)]}
if mode=='duplicate-checks':r['checks']=['repeated']*n
if mode=='nonstr-check':r['checks'][0]=False
if mode=='duplicate-screens':r['screens']=['repeated']*s
Path(path).parent.mkdir(parents=True,exist_ok=True)
Path(path).write_text('{' if mode=='malformed-report' else json.dumps(r))
''',encoding='utf8')
prefix=r'''set -euo pipefail
browser_fixture_pid=''
probes=0
kill() {
 if [[ "$1" == '-0' ]]; then
  probes=$((probes+1))
  for i in $(seq 1 100); do if grep -q '^start ' "$CI_EVENTS" 2>/dev/null; then break; fi; /usr/bin/sleep .01; done
  if [[ ( "$CI_MODE" == 'dead-before-ready' && "$probes" == 1 ) || ( "$CI_MODE" == 'dead-after-ready' && "$probes" == 2 ) ]]; then
   builtin kill "$2"; wait "$2" || true
   printf 'induced-death %s\n' "$2" >> "$CI_EVENTS"
  fi
  builtin kill "$@"
 else
  printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"
  builtin kill "$@"
 fi
}
trap 'if [[ -n "${browser_fixture_pid:-}" ]]; then kill "$browser_fixture_pid" 2>/dev/null || true; wait "$browser_fixture_pid" 2>/dev/null || true; fi; owned=$(sed -n "s/^start //p" "$CI_EVENTS"); if [[ -n "$owned" ]] && builtin kill -0 "$owned" 2>/dev/null; then printf "LEAK %s\n" "$owned" >> "$CI_EVENTS"; exit 91; fi; printf "closed\n" >> "$CI_EVENTS"' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  if [[ "$CI_MODE" == 'missing-marker' ]]; then printf 'synthetic healthy socket, no fixture marker\n'
  elif [[ "$CI_MODE" == 'bool-tables' ]]; then printf '{"fixture":"%s","tables":true,"model_target_revision":"20261019_account_recovery"}\n' "$CI_MARKER"
  else
   printf '{"fixture":"%s","tables":26,"model_target_revision":"20261019_account_recovery"}\n' "$CI_MARKER"
   if [[ "$CI_MODE" == 'duplicate-marker' ]]; then printf '{"fixture":"%s","tables":26,"model_target_revision":"20261019_account_recovery"}\n' "$CI_MARKER"; fi
  fi
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$CI_PYTHON" "$CI_STARTUP" "${@:2}"
 else
  "$CI_PYTHON" "$CI_GUARD" "${@:2}"
 fi
}
node() {
 printf 'driver %s\n' "$browser_fixture_pid" >> "$CI_EVENTS"
 "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$CI_MODE" "$minimum_checks" "$minimum_screens"
}
curl() { printf 'health\n' >> "$CI_EVENTS"; return 0; }
sleep() { /usr/bin/sleep .01; }
'''
rows=[]
for call in calls:
    marker=call.split()[-1]
    for mode in ['positive','missing-marker','duplicate-marker','bool-tables','duplicate-checks',
                 'nonstr-check','malformed-report','duplicate-screens','dead-before-ready','dead-after-ready']:
        directory=scratch/(marker+'-'+mode);directory.mkdir()
        (directory/'docs/implementation/20261018-evolution/evidence/ux').mkdir(parents=True)
        events=directory/'events.txt';events.write_text('',encoding='utf8')
        script=directory/'probe.sh';script.write_text(prefix+function+'\n'+call+'\n',encoding='utf8')
        env=environment() | {'CI_PYTHON':PYTHON.as_posix(),'CI_STARTUP':(ROOT/'scripts/check_browser_fixture_startup.py').as_posix(),
             'CI_GUARD':(ROOT/'scripts/check_frontend_report.py').as_posix(),'CI_WRITER':writer.as_posix(),
             'CI_EVENTS':events.as_posix(),'CI_MODE':mode,'CI_MARKER':marker,'METODOBASE_EVIDENCE_BATCH':'own-inert'}
        result=subprocess.run(['C:/Program Files/Git/bin/bash.exe',script.as_posix()],cwd=directory,env=env,
                              capture_output=True,encoding='utf8',timeout=25)
        (directory/'stdout.log').write_text(result.stdout,encoding='utf8')
        (directory/'stderr.log').write_text(result.stderr,encoding='utf8')
        log=events.read_text().splitlines()
        assert (result.returncode==0)==(mode=='positive'),(marker,mode,result.returncode,log)
        starts=[line.split()[1] for line in log if line.startswith('start ')]
        cleanup=[line.split()[1] for line in log if line.startswith('cleanup ')]
        drivers=[line.split()[1] for line in log if line.startswith('driver ')]
        assert len(starts)==1 and cleanup==starts and log[-1]=='closed' and not any(line.startswith('LEAK ') for line in log),log
        blocked=mode in ['missing-marker','duplicate-marker','bool-tables','dead-before-ready','dead-after-ready']
        assert drivers==([] if blocked else starts),log
        if mode=='dead-before-ready':assert 'health' not in log
        if mode in ['missing-marker','duplicate-marker','bool-tables']:assert log.count('health')==30
        rows.append({'fixture':marker,'case':mode,'exit':result.returncode,'events':log,
                     'actual_owned_child_reaped':True,'driver_blocked':blocked})
after=photo('inert-own-after');assert before==after
with zipfile.ZipFile(OUT/'own-inert-raw.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(scratch.rglob('*')):
        if path.is_file():archive.write(path,path.relative_to(scratch).as_posix())
save(OUT/'own-inert-summary.json',{'head':HEAD,'accepted':True,'cases':rows,
     'sources_stable':len(before['sources']),'packages':89,'raw_archive_sha256':sha((OUT/'own-inert-raw.zip').read_bytes()),
     'scope':'Unchanged actual workflow function and calls, real maintained parsers, simulated healthy socket without providers, owned Bash children actually killed/reaped on both liveness edges. No browser/HTTP/backend/PG/Actions claim.'})
print(json.dumps({'accepted':True,'own_inert':len(rows),'negatives':sum(row['case']!='positive' for row in rows)}))
