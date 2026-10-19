"""Check the bounded history/landing delta against immutable accepted CI28.

Uses real report/startup guards and inert owned Bash processes. Does not run
the browser, backend suite, services or Actions. Historical CI27/28 verifiers
and their assertions stay intact and apply only to their reviewed snapshots.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'tests/ci_history_landing28/ci28-before.yml'
SNAPSHOT_SHA = 'ec7938ccb76783666023588147685c0acf84454040f5e94d09a839bd06b18524'
HISTORICAL_VERIFIER_SHA = 'e6d60b0054d30df615cde47b93f2df7315530728357e2462bc39f2e1e86fdc78'
REVISION = '20261019_account_recovery'
WIRING_STEP = {
    'name': 'History and landing CI delta preserves reviewed CI28 and all acceptance gates',
    'run': 'python -X utf8 tests/verify_history_landing_ci.py --output "$RUNNER_TEMP/history-landing-ci"',
}
HISTORY_STEP = {
    'name': 'Bounded private history consumer contracts',
    'run': 'node tests/e2e/personal_history.cjs > personal-history-contracts.json\n'
           'python scripts/check_frontend_report.py personal-history-contracts.json --format counts --minimum 23\n',
}
NEW_CALLS = (
    'run_browser_fixture tests/e2e/personal_history_server.py 8780 tests/e2e/personal_history_browser.cjs '
    '"docs/implementation/20261018-evolution/evidence/history-pagination/browser-${METODOBASE_EVIDENCE_BATCH}/report.json" '
    '10 strings 4 "" "" 0 strings 0 personal-history-ui',
    'run_browser_fixture tests/e2e/landing_server.py 8781 tests/e2e/landing.cjs '
    '"docs/implementation/20261018-evolution/evidence/landing/browser-${METODOBASE_EVIDENCE_BATCH}/report.json" '
    '8 strings 4 "" "" 0 strings 0 public-landing',
)


def normalized(path):
    return Path(path).read_bytes().replace(b'\r\n', b'\n')


def baseline():
    raw = normalized(SNAPSHOT)
    assert hashlib.sha256(raw).hexdigest() == SNAPSHOT_SHA, 'Reviewed CI28 snapshot changed'
    assert hashlib.sha256(normalized(ROOT / 'tests/verify_recovery_ci.py')).hexdigest() == HISTORICAL_VERIFIER_SHA, 'Historical verifier changed'
    return yaml.safe_load(raw)


def expected_workflow(old):
    expected = copy.deepcopy(old)
    steps = expected['jobs']['test-web']['steps']
    index = next(i for i, step in enumerate(steps) if step.get('name') == 'SaaS regression suite in fresh isolated data')
    steps.insert(index, WIRING_STEP)
    steps = expected['jobs']['frontend-contracts']['steps']
    upload = next(step for step in steps if step.get('with', {}).get('name') == 'frontend-session-contracts')
    steps.insert(steps.index(upload), HISTORY_STEP)
    upload['with']['path'] += 'personal-history-contracts.json\n'
    steps = expected['jobs']['image']['steps']
    browser = next(step for step in steps if 'run_browser_fixture() {' in step.get('run', ''))
    browser['run'] += '\n'.join(NEW_CALLS) + '\n'
    upload = next(step for step in steps if step.get('with', {}).get('name') == 'candidate-browser-evidence')
    upload['with']['path'] = ('docs/implementation/20261018-evolution/evidence/ux\n'
        'docs/implementation/20261018-evolution/evidence/history-pagination/browser-ci-*\n'
        'docs/implementation/20261018-evolution/evidence/landing/browser-ci-*\n')
    return expected


def verify_workflow(workflow, old):
    assert workflow == expected_workflow(old), 'Workflow differs beyond the authorized history/landing delta'


def delta_cases(workflow, old):
    rows = []
    for name in ['missing-history-node', 'node-minimum22', 'history-minimum9', 'landing-minimum7',
                 'history-no-screens', 'landing-no-marker', 'old-revision27', 'omit-old-fixture',
                 'changed-pid-liveness', 'changed-process-cleanup', 'unrelated-postgres',
                 'omit-history-upload', 'omit-local-guard']:
        mutant = copy.deepcopy(workflow)
        steps = mutant['jobs']['frontend-contracts']['steps']
        node = next(step for step in steps if step.get('name') == HISTORY_STEP['name'])
        browser = next(step for step in mutant['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run', ''))
        if name == 'missing-history-node':
            steps.remove(node)
        elif name == 'node-minimum22':
            node['run'] = node['run'].replace('--minimum 23', '--minimum 22')
        elif name == 'history-minimum9':
            browser['run'] = browser['run'].replace('10 strings 4 ""', '9 strings 4 ""')
        elif name == 'landing-minimum7':
            browser['run'] = browser['run'].replace('8 strings 4 ""', '7 strings 4 ""')
        elif name == 'history-no-screens':
            browser['run'] = browser['run'].replace('10 strings 4 ""', '10 strings 0 ""')
        elif name == 'landing-no-marker':
            browser['run'] = browser['run'].replace(' strings 0 public-landing', ' strings 0 ""')
        elif name == 'old-revision27':
            browser['run'] = browser['run'].replace(REVISION, '20261019_personal_diary')
        elif name == 'omit-old-fixture':
            browser['run'] = '\n'.join(line for line in browser['run'].splitlines() if not line.startswith('run_browser_fixture tests/e2e/gym_generation_server.py')) + '\n'
        elif name == 'changed-pid-liveness':
            browser['run'] = browser['run'].replace('kill -0 "$browser_fixture_pid" || return 1', 'true')
        elif name == 'changed-process-cleanup':
            browser['run'] = browser['run'].replace('kill "$browser_fixture_pid"\n', 'true\n')
        elif name == 'unrelated-postgres':
            mutant['jobs']['postgres']['runs-on'] = 'windows-latest'
        elif name == 'omit-history-upload':
            upload = next(step for step in mutant['jobs']['image']['steps'] if step.get('with', {}).get('name') == 'candidate-browser-evidence')
            upload['with']['path'] = upload['with']['path'].replace('docs/implementation/20261018-evolution/evidence/history-pagination/browser-ci-*\n', '')
        elif name == 'omit-local-guard':
            mutant['jobs']['test-web']['steps'].remove(WIRING_STEP)
        assert mutant != workflow, name
        try:
            verify_workflow(mutant, old)
        except AssertionError:
            rows.append({'case': name, 'rejected': True})
        else:
            raise AssertionError('Unauthorized delta accepted: ' + name)
    return rows


def inert_cases(function, bash, out):
    writer = out / 'write_report.py'
    writer.write_text("import json,sys\nfrom pathlib import Path\np,mode,n,screens=sys.argv[1:];n=int(n);screens=int(screens)\nif mode=='missing-report':sys.exit(0)\nif mode=='too-few':n-=1\nif mode=='no-screens':screens=0\nr={'checks':[str(i) for i in range(n)],'pageErrors':['synthetic error'] if mode=='page-error' else [],'screens':[str(i) for i in range(screens)]}\nPath(p).parent.mkdir(parents=True,exist_ok=True)\nPath(p).write_text(json.dumps(r))\n", encoding='utf-8')
    prefix = r'''set -euo pipefail
browser_fixture_pid=''
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  printf '{"fixture":"%s","tables":26,"model_target_revision":"%s"}\n' "$CI_MARKER" "$CI_REVISION"
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
 "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$CI_MODE" "$minimum_checks" "$minimum_screens"
}
curl() { return 0; }
sleep() { /usr/bin/sleep 0.01; }
'''
    rows = []
    for call in NEW_CALLS:
        marker = call.split()[-1]
        for mode in ['positive', 'wrong-marker', 'old-revision', 'missing-report', 'too-few', 'no-screens', 'page-error', 'driver-error']:
            directory = out / (marker + '-' + mode)
            directory.mkdir()
            (directory / 'docs/implementation/20261018-evolution/evidence/ux').mkdir(parents=True)
            script = directory / 'probe.sh'
            script.write_text(prefix + function + '\n' + call + '\n', encoding='utf-8')
            events_path = directory / 'events.txt'
            environment = dict(os.environ, CI_PYTHON=Path(sys.executable).as_posix(),
                CI_GUARD=(ROOT / 'scripts/check_frontend_report.py').as_posix(),
                CI_STARTUP=(ROOT / 'scripts/check_browser_fixture_startup.py').as_posix(),
                CI_WRITER=writer.as_posix(), CI_EVENTS=events_path.as_posix(), CI_MODE=mode,
                CI_MARKER='wrong' if mode == 'wrong-marker' else marker,
                CI_REVISION='20261019_personal_diary' if mode == 'old-revision' else REVISION,
                METODOBASE_EVIDENCE_BATCH='inert')
            result = subprocess.run([bash, script.as_posix()], cwd=directory, env=environment,
                                    capture_output=True, text=True, timeout=25)
            (directory / 'stdout.log').write_text(result.stdout, encoding='utf-8')
            (directory / 'stderr.log').write_text(result.stderr, encoding='utf-8')
            assert (result.returncode == 0) == (mode == 'positive'), (marker, mode, result.returncode)
            events = events_path.read_text().splitlines()
            starts = [row for row in events if row.startswith('start ')]
            cleanup = [row for row in events if row.startswith('cleanup ')]
            drivers = [row for row in events if row.startswith('driver ')]
            assert len(starts) == len(cleanup) == 1 and starts[0].split()[1] == cleanup[0].split()[1], events
            assert len(drivers) == (0 if mode in ['wrong-marker','old-revision'] else 1), events
            assert all(row.split()[1] == starts[0].split()[1] for row in drivers), events
            rows.append({'fixture':marker,'case':mode,'exit':result.returncode,'events':events,'owned_cleanup':True})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workflow', type=Path, default=ROOT / '.github/workflows/ci.yml')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    old = baseline()
    workflow = yaml.safe_load(args.workflow.read_text(encoding='utf-8'))
    verify_workflow(workflow, old)
    historical = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tests/verify_recovery_ci.py'),
        '--workflow', str(SNAPSHOT), '--output', str(out / 'historical-ci28'), '--verify-only'],
        cwd=ROOT, capture_output=True, text=True, timeout=30)
    (out / 'historical-ci28.log').write_text(historical.stdout + historical.stderr, encoding='utf-8')
    assert historical.returncode == 0, 'Historical CI28 verification against pinned CI28 failed'
    report = {'scope':'Local CI delta and inert owned Bash; no backend/browser/Actions/services execution',
        'historical_verifier_preserved':True,'snapshot_sha256':SNAPSHOT_SHA,
        'history_vm_minimum':23,'history_browser_minimum':10,'landing_browser_minimum':8,
        'both_new_fixtures_minimum_screens':4,'historical_ci28_exit':historical.returncode,
        'unauthorized_delta_canaries':delta_cases(workflow,old)}
    if not args.verify_only:
        bash = os.environ.get('METODOBASE_CI_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
        assert bash
        blocks = [step['run'] for job in workflow['jobs'].values() for step in job.get('steps',[]) if 'run' in step]
        for block in blocks:
            result = subprocess.run([bash, '-n'],input=block,capture_output=True,text=True,timeout=15)
            assert result.returncode == 0, result.stderr
        report['bash_blocks'] = len(blocks)
        refs = sorted(set(re.findall(r'(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)',args.workflow.read_text(encoding='utf-8'))))
        assert all((ROOT / name).is_file() for name in refs)
        report['references'] = refs
        browser = next(block for block in blocks if 'run_browser_fixture() {' in block)
        function = browser[browser.index('run_browser_fixture() {'):browser.index('\nbrowser_evidence=')]
        (out / 'actual-fixture-function.sh').write_text(function+'\n',encoding='utf-8')
        with tempfile.TemporaryDirectory(prefix='metodobase-history-landing-ci-') as temporary:
            scratch=Path(temporary)
            report['new_inert_fixture_cases']=inert_cases(function,bash,scratch)
            with zipfile.ZipFile(out/'canaries-raw.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(scratch.rglob('*')):
                    if path.is_file():
                        archive.write(path,path.relative_to(scratch).as_posix())
        report['raw_archive_sha256']=hashlib.sha256((out/'canaries-raw.zip').read_bytes()).hexdigest()
    (out/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'historical_ci28_exit':0,'delta_canaries':len(report['unauthorized_delta_canaries']),
                     'inert_cases':len(report.get('new_inert_fixture_cases',[]))}))


if __name__ == '__main__':
    main()
