"""Extend the reviewed30 workflow only with explicit R23/session gates."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(r'F:\mb-r23-history30-20261019')
norm=lambda path:path.read_bytes().replace(b'\r\n',b'\n')
def write(name,value):
    (ROOT/name).write_bytes(value.encode('utf8') if isinstance(value,str) else value)
security=norm(ROOT/'docs/implementation/20261018-evolution/evidence/r23-session-expiry/security-driver-frozen.cjs')
before=b"process.env.SESSION_EVENT_REVIEW_ROOT || 'F:/mb-event-sec'";after=b"process.env.SESSION_EVENT_REVIEW_ROOT || path.resolve(__dirname,'../..')"
assert security.count(before)==1
maintained=security.replace(before,after);write('tests/e2e/session_expiry_security.cjs',maintained)
assert maintained.replace(after,before)==security
tree=ast.parse(norm(ROOT/'tests/e2e/followup_server.py').decode())
source_names=ast.literal_eval(next(node.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in node.targets)))
assert len(source_names)==28
checker=norm(ROOT/'scripts/check_followup_fixture.py').decode()
start=checker.index('    required = ');end=checker.index('    for name, digest',start)
checker=checker[:start]+'    required = frozenset('+repr(source_names)+')\n    assert set(sources) == required\n'+checker[end:]
write('scripts/check_followup_fixture.py',checker)
vm_names={'session_revision_events':11,'session_expiry_fences':3,'dashboard_followup':20,'session_expiry_security':10}
vm_step={'name':'Follow-up facts and synchronous session expiry regressions','run':''.join('node tests/e2e/'+name+'.cjs > followup-contracts-'+name+'.json\npython scripts/check_frontend_report.py followup-contracts-'+name+'.json --format counts --minimum '+str(minimum)+'\n' for name,minimum in vm_names.items())}
pg_step={'name':'Readonly follow-up facts under both current PostgreSQL factories','run':'python -X utf8 tests/run_isolated.py tests/integration_followup_postgres.py -q --tb=short --junitxml=pytest-postgres-followup.xml'}
report_step={'name':'Both follow-up PostgreSQL factory identities must pass','run':'python tests/check_followup_reports.py'}
browser_run='''set -euo pipefail
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
trap finish_followup EXIT INT TERM
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
python scripts/check_frontend_report.py "$public/report.json" --format results --minimum 8 --screens 5
python scripts/check_followup_fixture.py "$public/startup.json" --pid "$fixture_pid" --port 8795
'''
browser_step={'name':'Host checkout follow-up browser uses current restricted PostgreSQL fixture','timeout-minutes':5,'env':{'METODOBASE_TEST_MIGRATOR_URL':'postgresql+psycopg2://metodobase_test_admin:synthetic-ci-only@127.0.0.1:55483/metodobase_test_image','METODOBASE_TEST_POSTGRES_URL':'postgresql+psycopg2://metodobase_test_app:synthetic-app-only@127.0.0.1:55483/metodobase_test_image','METODOBASE_TEST_PG_BIN':'/usr/bin'},'run':browser_run}
browser_upload={'uses':'actions/upload-artifact@v4','if':'always()','with':{'name':'followup-host-real-browser','path':'${{ runner.temp }}/followup-public','if-no-files-found':'error'}}
path=ROOT/'tests/verify_history_index_ci.py';guard=norm(path).decode();assert 'FOLLOWUP_VM_STEP' not in guard
extra='\nFOLLOWUP_VM_MINIMA = '+repr(vm_names)+'\nFOLLOWUP_VM_STEP = '+repr(vm_step)+'\nFOLLOWUP_PG_STEP = '+repr(pg_step)+'\nFOLLOWUP_REPORT_STEP = '+repr(report_step)+'\nFOLLOWUP_BROWSER_STEP = '+repr(browser_step)+'\nFOLLOWUP_BROWSER_UPLOAD = '+repr(browser_upload)+'\nFOLLOWUP_REPORT = \'pytest-postgres-followup.xml\'\n'
guard=guard.replace('\n\ndef normalized(',extra+'\n\ndef normalized(',1)
old='''    browser['run'] = browser['run'].replace(needle, '--tables 29 --revision ' + REVISION)
    return expected'''
new='''    browser['run'] = browser['run'].replace(needle, '--tables 29 --revision ' + REVISION)
    frontend = expected['jobs']['frontend-contracts']['steps']
    upload = next(step for step in frontend if step.get('with', {}).get('name') == 'frontend-session-contracts')
    frontend.insert(frontend.index(upload), FOLLOWUP_VM_STEP)
    upload['with']['path'] += 'followup-contracts-*.json\\n'
    steps.insert(steps.index(guard), FOLLOWUP_PG_STEP)
    needle = "len(reports)==28 and len(set(reports))==28, 'Expected 28 distinct PostgreSQL reports'"
    assert guard['run'].count(needle) == 1
    guard['run'] = guard['run'].replace(needle,
        "len(reports)==29 and len(set(reports))==29, 'Expected 29 distinct PostgreSQL reports'")
    guard['run'] += ' ' + FOLLOWUP_REPORT
    steps.insert(steps.index(INDEX_CHECKER) + 1, FOLLOWUP_REPORT_STEP)
    expected['jobs']['image']['steps'].extend([FOLLOWUP_BROWSER_STEP, FOLLOWUP_BROWSER_UPLOAD])
    return expected'''
assert guard.count(old)==1;guard=guard.replace(old,new)
guard=guard.replace('+ list(INDEX_REPORTS)','+ list(INDEX_REPORTS) + [FOLLOWUP_REPORT]').replace('== 28\n    produced','== 29\n    produced').replace('len(produced) == 28','len(produced) == 29')
guard=guard.replace("'VM_executions_in_full18': 300, 'VM_unique_criteria': 279", "'legacy_VM_executions_in18': 300, 'legacy_VM_unique_criteria': 279,\n        'current_VM_executions_in22': 344, 'additional_checks_no_dedup_claim': 44")
# These extra cases leave all27 existing weakening cases intact.
needle="    assert len(rows) == 27\n    return rows"
new='''    for name, action in [
        ('missing-followup-PG', lambda w: w['jobs']['postgres']['steps'].remove(FOLLOWUP_PG_STEP)),
        ('missing-followup-checker', lambda w: w['jobs']['postgres']['steps'].remove(FOLLOWUP_REPORT_STEP)),
        ('missing-followup-VM', lambda w: w['jobs']['frontend-contracts']['steps'].remove(FOLLOWUP_VM_STEP)),
        ('missing-followup-browser', lambda w: w['jobs']['image']['steps'].remove(FOLLOWUP_BROWSER_STEP)),
        ('followup-browser-continue', lambda w: next(s for s in w['jobs']['image']['steps'] if s == FOLLOWUP_BROWSER_STEP).update({'continue-on-error': True})),
        ('private-followup-upload', lambda w: next(s for s in w['jobs']['image']['steps'] if s == FOLLOWUP_BROWSER_UPLOAD)['with'].update({'path': '${{ runner.temp }}/followup-private'})),
    ]:
        mutant = copy.deepcopy(workflow); action(mutant)
        try: verify_workflow(mutant, old)
        except AssertionError: rows.append({'case': name, 'rejected': True})
        else: raise AssertionError(name)
    assert len(rows) == 33
    return rows'''
assert guard.count(needle)==1;guard=guard.replace(needle,new)
# Current helper hashes are fixed literals; no executable can supply its own pin.
tree=ast.parse(guard);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_CURRENT_GATES' for t in n.targets));pins=ast.literal_eval(node.value)
for name in ['tests/check_followup_reports.py','scripts/check_followup_fixture.py','tests/e2e/followup_server.py','tests/e2e/dashboard_followup_browser.cjs',*['tests/e2e/'+name+'.cjs' for name in vm_names]]:
    pins[name]=hashlib.sha256(norm(ROOT/name)).hexdigest()
lines=guard.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['PINNED_CURRENT_GATES = '+repr(pins)+'\n'];guard=''.join(lines)
ast.parse(guard);write('tests/verify_history_index_ci.py',guard)
# Preserve workflow text and the on: key; use YAML only to locate the accepted delta.
import importlib.util
spec=importlib.util.spec_from_file_location('r23_guard_prepare',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
import yaml
workflow=norm(ROOT/'.github/workflows/ci.yml').decode();oldworkflow=yaml.safe_load(workflow)
expected=module.expected_workflow(module.baseline())
assert len(oldworkflow['jobs']['postgres']['steps'])+2==len(expected['jobs']['postgres']['steps'])
needle='      - uses: actions/upload-artifact@v4\n        if: always()\n        with:\n          name: frontend-session-contracts'
assert workflow.count(needle)==1
workflow=workflow.replace(needle,'      - name: '+vm_step['name']+'\n        run: |\n'+''.join('          '+line+'\n' for line in vm_step['run'].splitlines())+needle)
needle='            member-link-*.json\n';assert workflow.count(needle)==1;workflow=workflow.replace(needle,needle+'            followup-contracts-*.json\n')
needle='      - name: Required PostgreSQL acceptance';assert workflow.count(needle)==1;workflow=workflow.replace(needle,'      - name: '+pg_step['name']+'\n        run: '+pg_step['run']+'\n'+needle)
workflow=workflow.replace("len(reports)==28 and len(set(reports))==28, 'Expected 28 distinct PostgreSQL reports'","len(reports)==29 and len(set(reports))==29, 'Expected 29 distinct PostgreSQL reports'")
needle='pytest-postgres-history-index.xml pytest-postgres-history-index-restore.xml';assert workflow.count(needle)==1;workflow=workflow.replace(needle,needle+' pytest-postgres-followup.xml')
needle='        run: python tests/check_history_index_reports.py\n';assert workflow.count(needle)==1;workflow=workflow.replace(needle,needle+'      - name: '+report_step['name']+'\n        run: '+report_step['run']+'\n')
text='      - name: '+browser_step['name']+'\n        timeout-minutes: 5\n        env:\n'+''.join('          '+key+': '+value+'\n' for key,value in browser_step['env'].items())+'        run: |\n'+''.join('          '+line+'\n' for line in browser_run.splitlines())+'      - uses: actions/upload-artifact@v4\n        if: always()\n        with:\n          name: followup-host-real-browser\n          path: ${{ runner.temp }}/followup-public\n          if-no-files-found: error\n'
workflow=workflow.rstrip()+'\n'+text
assert yaml.safe_load(workflow)==expected
write('.github/workflows/ci.yml',workflow)
print(json.dumps({'PG_reports':29,'Node_modules':22,'Node_execution_minima':344,'new_gates_pinned':len(pins),'new_workflow_mutants':6,'original27_mutants_preserved':True,'security_driver_only_portable_root_change':True}))
