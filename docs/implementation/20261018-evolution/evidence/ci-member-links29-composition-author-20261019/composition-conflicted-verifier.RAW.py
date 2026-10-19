"""Verify the bounded CI29 delta while retaining exact historical CI28.

Checks actual parsers, fixture marker expressions and owned inert Bash
processes. It does not execute Actions, browsers, PostgreSQL or providers.
The pinned historical runner evaluates actual old metadata in old source.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'tests/ci_member_links29'
WORKFLOW_SHA = '7077a47e2d5255695117d07d8b42fe1fff33876141abbb67375e3154de0b45c8'
BASELINE_SHA = 'fddb39ddbf9dc59460464192b44a2833a9546625ad492f49c1e7cab1f4f5198c'
<<<<<<< HEAD
PINNED_CURRENT_GATES = {
    'tests/check_member_link_reports.py': 'd617301259208f8fc8da91ddd6f8bdbdc43a35a4cdfb059d94f4de60513e8e62',
    'tests/run_reviewed_ci28.py': 'ae535aab4f27b0ea2f76da4ef6068129c2a7520326012c77c1142a1a6cea14e6',
    'tests/e2e/member_link_postgres_server.py': '307d95b8f4644b462b036863ac22f65c03772f900f4fbe5d6425550d1d9347fc',
    'tests/e2e/member_link_browser.cjs': '90c826948d84ed1b2556ffa395e8911f5520490a082c904a0c9a191a6bccbce8',
    'tests/e2e/normalize_member_link_report.py': 'd415ec90669856e6613840a3c09da7c1881a37ea96da9f5b51b0d01bd715eaab',
    'tests/e2e/run_member_link_browser.py': 'b0c23986c4d02693f4713b8e9bf8e1cc7f9e115f442218e1bfe86281c90190ba',
    'tests/e2e/member_link_controls.cjs': '51f9a1bc7a3b7a90d906017920ece2c5c54f37275aa2d9ed9728ba6c4f374c1d',
    'tests/e2e/member_link_export.cjs': '287488236fe8cce0fee492145abf5e1b147ad9e038b7b03ada44285c9e6bd0d4',
}
=======
PINNED_CURRENT_GATES = {'tests/check_member_link_reports.py': 'd617301259208f8fc8da91ddd6f8bdbdc43a35a4cdfb059d94f4de60513e8e62', 'tests/run_reviewed_ci28.py': '58cf6c165d155d13120c3fe2ea50f1fac26960a3456c438418de45a2e040bbed'}
>>>>>>> 98ef40f (Verify reviewed archives against original pinned Git blobs)
EXPECTED_CURRENT_REPORTS = {
    'pytest-postgres-member-migrations.xml': (5, ('tests.integration_client_link_migrations',)),
    'pytest-postgres-member-services.xml': (16, ('tests.integration_client_link_services',)),
    'pytest-postgres-member-http.xml': (34, ('tests.integration_client_link_http',)),
    'pytest-postgres-member-races.xml': (4, ('tests.integration_client_link_service_races',
                                            'tests.integration_client_link_publication_cas')),
    'pytest-postgres-member-restore.xml': (1, ('tests.integration_client_link_restore',)),
}
REVISION = '20261019_client_account_links'
PREVIOUS = '20261019_account_recovery'
WIRING_STEP = {
    'name': 'Member link CI29 preserves reviewed historical gates and requires current contracts',
    'run': 'python -X utf8 tests/verify_member_links_ci.py --output "$RUNNER_TEMP/member-links-ci"',
}
VM_MODULES = {'member_link_context': 26, 'member_link_fragment': 15,
              'member_link_api': 23, 'member_link_consumers': 16, 'member_link_export': 32,
              'member_link_controls': 3}
VM_STEP = {
    'name': 'Member link API, context, fragment, consumers and seven-collection export contracts',
    'run': ''.join('node tests/e2e/' + name + '.cjs' +
                   (' web/static/js/vinculos-ui.js' if name == 'member_link_controls' else '') +
                   ' > ' + name.replace('_', '-') + '.json\n'
                   'python scripts/check_frontend_report.py ' + name.replace('_', '-') +
                   '.json --format counts --minimum ' + str(minimum) + '\n'
                   for name, minimum in VM_MODULES.items()),
}
PG_SPECS = (
    ('Member link migration preserves exact revision28, guards and rollback',
     'tests/integration_client_link_migrations.py', 'member-migrations'),
    ('Member link service authorization and bounded projection under restricted role',
     'tests/integration_client_link_services.py', 'member-services'),
    ('Member link real HTTP and worker contracts across both factories',
     'tests/integration_client_link_http.py', 'member-http'),
    ('Member proof races and exact publication identity CAS',
     'tests/integration_client_link_service_races.py tests/integration_client_link_publication_cas.py', 'member-races'),
    ('Current revision29 populated restore preserves all prior contracts and member links',
     'tests/integration_client_link_restore.py', 'member-restore'),
)
NEW_REPORTS = tuple('pytest-postgres-' + suffix + '.xml' for _, _, suffix in PG_SPECS)
REPORT_STEP = {'name': 'Current member link reports retain all selected PostgreSQL cases',
               'run': 'python tests/check_member_link_reports.py'}
BROWSER_STEP = {
    'name': 'Real member linking browser with restricted migrated PostgreSQL and private mail transport',
    'env': {
        'METODOBASE_TEST_MIGRATOR_URL': 'postgresql+psycopg2://metodobase_test_admin:synthetic-ci-only@127.0.0.1:55483/metodobase_test_image',
        'METODOBASE_TEST_POSTGRES_URL': 'postgresql+psycopg2://metodobase_test_app:synthetic-app-only@127.0.0.1:55483/metodobase_test_image',
        'METODOBASE_TEST_PG_BIN': '/usr/bin',
    },
    'run': 'export QA_NODE_MODULES="$GITHUB_WORKSPACE/tests/e2e/node_modules"\n'
           'export QA_CHROME=$(node -e "process.stdout.write(require(\'./tests/e2e/node_modules/playwright-core\').chromium.executablePath())")\n'
           'python -X utf8 tests/e2e/run_member_link_browser.py --output "$RUNNER_TEMP/member-link-public" --port 8794\n',
}
BROWSER_UPLOAD = {
    'uses': 'actions/upload-artifact@v4', 'if': 'always()',
    'with': {'name': 'member-link-real-browser', 'path': '${{ runner.temp }}/member-link-public',
             'if-no-files-found': 'error'},
}


def normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b'\r\n', b'\n')


def authenticate_current_gates() -> None:
    # Independent literals bind executable helpers before they are imported/run.
    for name, digest in PINNED_CURRENT_GATES.items():
        assert hashlib.sha256(normalized(ROOT / name)).hexdigest() == digest, name


def baseline() -> dict:
    authenticate_current_gates()
    raw = normalized(SNAPSHOT / 'ci28-before.yml')
    assert hashlib.sha256(raw).hexdigest() == WORKFLOW_SHA, 'Historical workflow changed'
    metadata = normalized(SNAPSHOT / 'baseline.json')
    assert hashlib.sha256(metadata).hexdigest() == BASELINE_SHA, 'Baseline trust anchor changed'
    for name, digest in json.loads(metadata)['unchanged_files'].items():
        assert hashlib.sha256(normalized(ROOT / name)).hexdigest() == digest, name
    return yaml.safe_load(raw)


def expected_workflow(old: dict) -> dict:
    expected = copy.deepcopy(old)
    steps = expected['jobs']['test-web']['steps']
    guard = next(step for step in steps if step.get('name', '').startswith('History and landing CI delta'))
    steps[steps.index(guard)] = WIRING_STEP
    for job in ['test-web', 'postgres']:
        checkout = next(step for step in expected['jobs'][job]['steps'] if step.get('uses') == 'actions/checkout@v4')
        assert 'with' not in checkout
        checkout['with'] = {'fetch-depth': 0}
    steps = expected['jobs']['frontend-contracts']['steps']
    upload = next(step for step in steps if step.get('with', {}).get('name') == 'frontend-session-contracts')
    steps.insert(steps.index(upload), VM_STEP)
    upload['with']['path'] += 'member-link-*.json\n'
    steps = expected['jobs']['postgres']['steps']
    restore = next(step for step in steps if step.get('name', '').startswith('Encrypted PostgreSQL'))
    restore['run'] = ('python -X utf8 tests/run_reviewed_ci28.py --output "$RUNNER_TEMP/reviewed-ci28-restore" '
                      '--junitxml=pytest-postgres-restore.xml')
    guard = next(step for step in steps if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    index = steps.index(guard)
    steps[index:index] = [{'name': name, 'run': 'python -X utf8 tests/run_isolated.py ' + modules +
                            (' -k postgresql' if suffix != 'member-restore' else '') +
                            ' -q --tb=short --junitxml=pytest-postgres-' + suffix + '.xml'}
                           for name, modules, suffix in PG_SPECS]
    needle = "len(reports)==21 and len(set(reports))==21, 'Expected 21 distinct PostgreSQL reports'"
    assert guard['run'].count(needle) == 1
    guard['run'] = guard['run'].replace(needle,
        "len(reports)==26 and len(set(reports))==26, 'Expected 26 distinct PostgreSQL reports'")
    guard['run'] += ' ' + ' '.join(NEW_REPORTS)
    upload = next(step for step in steps if step.get('with', {}).get('name') == 'postgres-integration')
    steps.insert(steps.index(upload), REPORT_STEP)
    browser = next(step for step in expected['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run', ''))
    needle = '--tables 26 --revision ' + PREVIOUS
    assert browser['run'].count(needle) == 1
    browser['run'] = browser['run'].replace(needle, '--tables 29 --revision ' + REVISION)
    image_steps = expected['jobs']['image']['steps']
    index = image_steps.index(browser) + 1
    image_steps[index:index] = [BROWSER_STEP, BROWSER_UPLOAD]
    return expected


def verify_workflow(workflow: dict, old: dict) -> tuple[list[str], list[str]]:
    assert workflow == expected_workflow(old), 'Workflow differs beyond the reviewed CI29 delta'
    steps = workflow['jobs']['postgres']['steps']
    guard = next(step['run'] for step in steps if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    parts = shlex.split(guard)
    assert parts[:2] == ['python', '-c']
    reports = parts[3:]
    old_guard = next(step['run'] for step in old['jobs']['postgres']['steps']
                     if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    assert reports == shlex.split(old_guard)[3:] + list(NEW_REPORTS)
    assert len(reports) == len(set(reports)) == 26
    produced = [name for step in steps for name in re.findall(
        r'--junitxml=(pytest-postgres-[a-z-]+\.xml)', step.get('run', ''))]
    assert len(produced) == 26 and set(produced) == set(reports)
    return parts, reports


def actual_fixture_markers() -> list[dict]:
    """Evaluate just existing marker expressions with actual current ORM metadata."""
    sys.path.insert(0, str(ROOT))
    from tests.isolation import prepare_environment, block_external_sockets
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from web.database.models import Base
    from web.database.schema_control import expected_head
    rows = []
    for name, fixture in [('personal_diary_server', 'personal-diary-ui'),
                          ('personal_history_server', 'personal-history-ui'), ('landing_server', 'public-landing')]:
        tree = ast.parse((ROOT / ('tests/e2e/' + name + '.py')).read_text(encoding='utf8'))
        dictionaries = [node for node in ast.walk(tree) if isinstance(node, ast.Dict) and any(
            isinstance(key, ast.Constant) and key.value == 'model_target_revision' for key in node.keys)]
        assert len(dictionaries) == 1
        marker = {}
        for key, value in zip(dictionaries[0].keys, dictionaries[0].values):
            if isinstance(key, ast.Constant) and key.value in {'fixture', 'model_target_revision', 'tables'}:
                marker[key.value] = eval(compile(ast.Expression(value), 'actual-fixture-marker', 'eval'),
                    {'__builtins__': {'len': len}, 'Base': Base, 'expected_head': expected_head})
        assert marker == {'fixture': fixture, 'model_target_revision': REVISION, 'tables': 29}
        rows.append(marker)
    return rows


def delta_cases(workflow: dict, old: dict) -> list[dict]:
    rows = []
    names = ['missing-local-guard', 'missing-history-fetch', 'missing-restore-fetch',
             'current-runtime-for-historical-restore', 'missing-current-restore', 'missing-race-CAS',
             'allow-SQLite-in-PG', 'missing-report-parser', 'lower-report-count',
             'missing-new-report', 'omit-historical-report', 'missing-VM', 'lower-VM-minimum',
             'missing-VM-upload', 'old-fixture-head', 'old-fixture-tables',
             'changed-process-cleanup', 'changed-liveness', 'omit-old-browser', 'unrelated-job',
             'missing-real-member-browser', 'public-private-directory-glob',
             'missing-real-browser-upload', 'missing-owned-controls', 'wrong-owned-controls-source']
    for name in names:
        mutant = copy.deepcopy(workflow)
        web = mutant['jobs']['test-web']['steps']
        pg = mutant['jobs']['postgres']['steps']
        front = mutant['jobs']['frontend-contracts']['steps']
        browser = next(step for step in mutant['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run', ''))
        guard = next(step for step in pg if step.get('name', '').startswith('Required PostgreSQL acceptance'))
        if name == 'missing-local-guard': web.remove(WIRING_STEP)
        elif name in ['missing-history-fetch', 'missing-restore-fetch']:
            target = web if name == 'missing-history-fetch' else pg
            next(step for step in target if step.get('uses') == 'actions/checkout@v4')['with']['fetch-depth'] = 1
        elif name == 'current-runtime-for-historical-restore':
            next(step for step in pg if step.get('name', '').startswith('Encrypted PostgreSQL'))['run'] = 'python tests/run_isolated.py'
        elif name == 'missing-current-restore': pg.remove(next(step for step in pg if step.get('name') == PG_SPECS[-1][0]))
        elif name == 'missing-race-CAS':
            step = next(step for step in pg if step.get('name') == PG_SPECS[-2][0])
            step['run'] = step['run'].replace(' tests/integration_client_link_publication_cas.py', '')
        elif name == 'allow-SQLite-in-PG':
            step = next(step for step in pg if step.get('name') == PG_SPECS[0][0])
            step['run'] = step['run'].replace(' -k postgresql', '')
        elif name == 'missing-report-parser': pg.remove(REPORT_STEP)
        elif name == 'lower-report-count': guard['run'] = guard['run'].replace('==26', '==25')
        elif name == 'missing-new-report': guard['run'] = guard['run'].replace(' ' + NEW_REPORTS[-1], '')
        elif name == 'omit-historical-report': guard['run'] = guard['run'].replace(' pytest-postgres-quota.xml', '')
        elif name == 'missing-VM': front.remove(VM_STEP)
        elif name == 'lower-VM-minimum':
            step = next(step for step in front if step.get('name') == VM_STEP['name'])
            step['run'] = step['run'].replace('--minimum 26', '--minimum 25')
        elif name == 'missing-VM-upload':
            step = next(step for step in front if step.get('with', {}).get('name') == 'frontend-session-contracts')
            step['with']['path'] = step['with']['path'].replace('member-link-*.json\n', '')
        elif name == 'old-fixture-head': browser['run'] = browser['run'].replace(REVISION, PREVIOUS)
        elif name == 'old-fixture-tables': browser['run'] = browser['run'].replace('--tables 29', '--tables 26')
        elif name == 'changed-process-cleanup': browser['run'] = browser['run'].replace('kill "$browser_fixture_pid"\n', 'true\n')
        elif name == 'changed-liveness': browser['run'] = browser['run'].replace('kill -0 "$browser_fixture_pid" || return 1', 'true')
        elif name == 'omit-old-browser': browser['run'] = '\n'.join(line for line in browser['run'].splitlines() if not line.startswith('run_browser_fixture tests/e2e/gym_generation_server.py')) + '\n'
        elif name == 'unrelated-job': mutant['jobs']['redis']['runs-on'] = 'windows-latest'
        elif name == 'missing-real-member-browser': mutant['jobs']['image']['steps'].remove(BROWSER_STEP)
        elif name == 'public-private-directory-glob':
            step = next(step for step in mutant['jobs']['image']['steps']
                        if step.get('with', {}).get('name') == BROWSER_UPLOAD['with']['name'])
            step['with']['path'] = '${{ runner.temp }}/**'
        elif name == 'missing-real-browser-upload': mutant['jobs']['image']['steps'].remove(BROWSER_UPLOAD)
        elif name in ['missing-owned-controls', 'wrong-owned-controls-source']:
            step = next(step for step in front if step.get('name') == VM_STEP['name'])
            if name == 'missing-owned-controls':
                step['run'] = '\n'.join(line for line in step['run'].splitlines()
                                         if 'member-link-controls' not in line and 'member_link_controls' not in line) + '\n'
            else:
                step['run'] = step['run'].replace(' web/static/js/vinculos-ui.js', ' web/static/js/api.js')
        assert mutant != workflow, name
        try: verify_workflow(mutant, old)
        except AssertionError: rows.append({'case': name, 'rejected': True})
        else: raise AssertionError('Unauthorized delta accepted: ' + name)
    return rows


def report_canaries(out: Path) -> list[dict]:
    authenticate_current_gates()
    from tests.check_member_link_reports import REPORTS
    assert REPORTS == EXPECTED_CURRENT_REPORTS and len(REPORTS) == 5
    rows = []
    modes = ['positive', 'missing', 'malformed', 'empty', 'reduced', 'duplicate',
             'wrong-module', 'SQLite', 'skip', 'failure', 'error']
    for target in REPORTS:
        for mode in modes:
            directory = out / (target.removesuffix('.xml') + '-' + mode)
            directory.mkdir()
            for name, (minimum, modules) in REPORTS.items():
                suite = ET.Element('testsuite')
                for index in range(minimum):
                    ET.SubElement(suite, 'testcase', classname=modules[index % len(modules)],
                                  name='case_' + str(index) + '[postgresql]' if name != NEW_REPORTS[-1] else
                                  'test_revision29_restore_preserves_member_links_and_all_revision26_27_28_contracts')
                if name == target and mode not in ['missing', 'malformed']:
                    if mode == 'empty': suite.clear()
                    elif mode == 'reduced': suite.remove(suite[-1])
                    elif mode == 'duplicate': suite.append(copy.deepcopy(suite[0]))
                    elif mode == 'wrong-module': suite[0].set('classname', 'tests.unrelated')
                    elif mode == 'SQLite': suite[0].set('name', 'case_0[sqlite]')
                    elif mode in ['skip', 'failure', 'error']:
                        ET.SubElement(suite[0], 'skipped' if mode == 'skip' else mode)
                ET.ElementTree(suite).write(directory / name, encoding='utf8', xml_declaration=True)
            if mode == 'missing': (directory / target).unlink()
            elif mode == 'malformed': (directory / target).write_bytes(b'<testsuite')
            positive = mode == 'positive'
            result = subprocess.run([sys.executable, str(ROOT / 'tests/check_member_link_reports.py'),
                                     '--directory', str(directory)], capture_output=True, timeout=10)
            (directory / 'stdout.log').write_bytes(result.stdout)
            (directory / 'stderr.log').write_bytes(result.stderr)
            assert (result.returncode == 0) == positive, (target, mode)
            rows.append({'report': target, 'case': mode, 'exit': result.returncode, 'expected_pass': positive})
    assert len(rows) == 55, 'Current report probes were reduced'
    return rows


def inert_cases(function: str, calls: list[str], bash: str, out: Path) -> list[dict]:
    writer = out / 'write_report.py'
    writer.write_bytes(b"import json,sys\nfrom pathlib import Path\np,mode,n,screens,kind=sys.argv[1:];n=int(n);screens=int(screens)\nif mode=='missing-report':sys.exit(0)\nif mode=='too-few':n-=1\nif mode=='no-screens':screens=0\nchecks=[{'name':str(i),'passed':True} if kind=='named' else str(i) for i in range(n)]\nr={'checks':checks,'pageErrors':['synthetic'] if mode=='page-error' else [],'screens':[str(i) for i in range(screens)]}\nPath(p).parent.mkdir(parents=True,exist_ok=True)\nPath(p).write_text(json.dumps(r))\n")
    prefix = r'''set -euo pipefail
browser_fixture_pid=''
browser_evidence=docs/implementation/20261018-evolution/evidence/ux
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  printf '{"fixture":"%s","tables":%s,"model_target_revision":"%s"}\n' "$CI_MARKER" "$CI_TABLES" "$CI_REVISION"
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
 if [[ -n "$second_driver" && "$1" == "$second_driver" ]]; then
  "$CI_PYTHON" "$CI_WRITER" "$second_report" positive "$second_minimum" "$second_screens" "$second_format"
 else
  "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$CI_MODE" "$minimum_checks" "$minimum_screens" "$report_format"
 fi
}
curl() { return 0; }
sleep() { /usr/bin/sleep 0.01; }
'''
    rows = []
    modes = ['positive', 'wrong-marker', 'old-head', 'old-tables', 'missing-report',
             'too-few', 'no-screens', 'page-error', 'driver-error']
    for call in calls:
        marker = call.split()[-1]
        for mode in modes:
            directory = out / (marker + '-' + mode)
            directory.mkdir()
            (directory / 'docs/implementation/20261018-evolution/evidence/ux').mkdir(parents=True)
            script = directory / 'probe.sh'
            script.write_bytes((prefix + function + '\n' + call + '\n').encode())
            events = directory / 'events.txt'
            environment = dict(os.environ, CI_PYTHON=Path(sys.executable).as_posix(),
                CI_GUARD=(ROOT / 'scripts/check_frontend_report.py').as_posix(),
                CI_STARTUP=(ROOT / 'scripts/check_browser_fixture_startup.py').as_posix(),
                CI_WRITER=writer.as_posix(), CI_EVENTS=events.as_posix(), CI_MODE=mode,
                CI_MARKER='wrong' if mode == 'wrong-marker' else marker,
                CI_REVISION=PREVIOUS if mode == 'old-head' else REVISION,
                CI_TABLES='26' if mode == 'old-tables' else '29', METODOBASE_EVIDENCE_BATCH='inert')
            result = subprocess.run([bash, script.as_posix()], cwd=directory, env=environment,
                                    capture_output=True, timeout=25)
            (directory / 'stdout.log').write_bytes(result.stdout)
            (directory / 'stderr.log').write_bytes(result.stderr)
            assert (result.returncode == 0) == (mode == 'positive'), (marker, mode, result.returncode)
            observed = events.read_text().splitlines()
            starts = [row for row in observed if row.startswith('start ')]
            cleanups = [row for row in observed if row.startswith('cleanup ')]
            drivers = [row for row in observed if row.startswith('driver ')]
            assert len(starts) == len(cleanups) == 1 and starts[0].split()[1] == cleanups[0].split()[1]
            expected = 0 if mode in ['wrong-marker', 'old-head', 'old-tables'] else 2 if mode == 'positive' and marker == 'personal-diary-ui' else 1
            assert len(drivers) == expected and all(row.split()[1] == starts[0].split()[1] for row in drivers)
            rows.append({'fixture': marker, 'case': mode, 'exit': result.returncode, 'events': observed})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workflow', type=Path, default=ROOT / '.github/workflows/ci.yml')
    parser.add_argument('--history-repository', type=Path, default=ROOT)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    old = baseline()
    workflow = yaml.safe_load(args.workflow.read_text(encoding='utf8'))
    _, reports = verify_workflow(workflow, old)
    historical = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tests/run_reviewed_ci28.py'),
        '--output', str(out / 'historical-ci28'), '--history-repository', str(args.history_repository)],
        cwd=ROOT, capture_output=True, timeout=90)
    (out / 'historical.log').write_bytes(historical.stdout + historical.stderr)
    assert historical.returncode == 0, 'Exact historical CI28 verification failed'
    report = {'scope': 'Local CI29 wiring/parsers/actual marker expressions and owned inert Bash; no Actions/browser/PG/provider execution',
        'historical_source_pin': '66d9dec0e15dd873038bd248d3883daeeb27d4ca',
        'historical_exit': historical.returncode, 'reports': reports, 'current_PG_minimum_cases': 60,
        'VM_minima': VM_MODULES, 'VM_executions_in_full18': 300, 'VM_unique_criteria': 279,
        'duplicate_legacy_export_executions': 21, 'actual_markers': actual_fixture_markers(),
        'unauthorized_delta_canaries': delta_cases(workflow, old)}
    if not args.verify_only:
        bash = os.environ.get('METODOBASE_CI_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
        assert bash
        blocks = [step['run'] for job in workflow['jobs'].values() for step in job.get('steps', []) if 'run' in step]
        for block in blocks:
            result = subprocess.run([bash, '-n'], input=block.encode(), capture_output=True, timeout=15)
            assert result.returncode == 0, result.stderr
        refs = sorted(set(re.findall(r'(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)', args.workflow.read_text(encoding='utf8'))))
        assert all((ROOT / name).is_file() for name in refs)
        report['references'] = refs
        report['bash_blocks'] = len(blocks)
        browser = next(block for block in blocks if 'run_browser_fixture() {' in block)
        function = browser[browser.index('run_browser_fixture() {'):browser.index('\nbrowser_evidence=')]
        calls = [line for line in browser.splitlines() if line.startswith('run_browser_fixture ') and
                 line.split()[-1] in ['personal-diary-ui', 'personal-history-ui', 'public-landing']]
        assert len(calls) == 3
        # Keep failed process/parser probes too. The output directory was
        # created exclusively by this invocation and is never recursively deleted.
        scratch = out / 'owned-probes'
        scratch.mkdir()
        try:
            report['current_report_canaries'] = report_canaries(scratch)
            report['current_inert_fixture_cases'] = inert_cases(function, calls, bash, scratch)
        finally:
            with zipfile.ZipFile(out / 'canaries-raw.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(scratch.rglob('*')):
                    if path.is_file(): archive.write(path, path.relative_to(scratch).as_posix())
        report['canaries_archive_sha256'] = hashlib.sha256((out / 'canaries-raw.zip').read_bytes()).hexdigest()
    (out / 'review.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf8'))
    print(json.dumps({'historical_exit': historical.returncode, 'reports': len(reports),
                      'delta_canaries': len(report['unauthorized_delta_canaries']),
                      'report_canaries': len(report.get('current_report_canaries', [])),
                      'inert_cases': len(report.get('current_inert_fixture_cases', []))}))


if __name__ == '__main__':
    main()
