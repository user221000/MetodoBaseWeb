"""Verify the bounded CI30 delta while retaining exact historical CI29 and CI28.

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
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'tests/ci_history_index30'
WORKFLOW_SHA = 'a763cefded20c5ac2bcc602c58538a494c5ad84eb0fe874faaac3b176e5d1f82'
BASELINE_SHA = 'ac626b6d7c41c6e8a61240cd9cfad8a581dd936d1776f734c1353ae77b31cdc5'
PINNED_CURRENT_GATES = {'tests/check_member_link_reports.py': 'd617301259208f8fc8da91ddd6f8bdbdc43a35a4cdfb059d94f4de60513e8e62', 'tests/run_reviewed_ci28.py': '58cf6c165d155d13120c3fe2ea50f1fac26960a3456c438418de45a2e040bbed', 'tests/e2e/member_link_postgres_server.py': '4933f0fe7427f1c01975b5eda50f0d736a847046f86a1bd68e3f101bd515d0b5', 'tests/e2e/member_link_browser.cjs': '98268178c9f9ca164f3d7cba054a535262135dba9777e971467245a365a94f41', 'tests/e2e/normalize_member_link_report.py': '944da84612141d1872ee0c65a7e3e44d2cd293235078bfffa8b7c243d14da32c', 'tests/e2e/run_member_link_browser.py': '9cd8426619e2d29496f490ed30dd11ed3d64339c3cf7e0fe2071f319be9b472d', 'tests/e2e/member_link_controls.cjs': '51f9a1bc7a3b7a90d906017920ece2c5c54f37275aa2d9ed9728ba6c4f374c1d', 'tests/e2e/member_link_export.cjs': '287488236fe8cce0fee492145abf5e1b147ad9e038b7b03ada44285c9e6bd0d4', 'tests/run_reviewed_ci29.py': 'e4da4dbde73de7d322f4f3d2a1ea9e3948068891706d789e43ea7cdd82703cf6', 'tests/verify_member_links_ci.py': '4b6cedcd508d7b2941723c1148f5cf4b6f31fa6ab58ea6d0a316d90b18a83979', 'tests/check_history_index_reports.py': '06ec3d5bb0870dec6e8c08952b983a47481bcc53f1dbe6691e6ed4b428c22544', 'web/database/alembic/history_index_contract_v1.py': '6d9dec4104c2d9c60935677337e540bdbd9585042f789b61e2a849786ae1d161'}
EXPECTED_CURRENT_REPORTS = {
    'pytest-postgres-member-migrations.xml': (5, ('tests.integration_client_link_migrations',)),
    'pytest-postgres-member-services.xml': (16, ('tests.integration_client_link_services',)),
    'pytest-postgres-member-http.xml': (34, ('tests.integration_client_link_http',)),
    'pytest-postgres-member-races.xml': (4, ('tests.integration_client_link_service_races',
                                            'tests.integration_client_link_publication_cas')),
    'pytest-postgres-member-restore.xml': (1, ('tests.integration_client_link_restore',)),
}
REVISION = '20261019_personal_history_index'
PREVIOUS = '20261019_client_account_links'
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

EXPECTED_INDEX_REPORTS = {name: frozenset(tuple(item) for item in identities) for name, identities in {'pytest-postgres-history-index.xml': [('tests.integration_personal_history_index_migrations', 'test_failure_after_actual_index_ddl_rolls_back_rows_guards_and_revision[postgresql]'), ('tests.integration_personal_history_index_migrations', 'test_populated29_upgrade_repeat_and_index_only_rollback[postgresql]'), ('tests.integration_personal_history_index_migrations', 'test_same_columns_drift_or_missing_index_rejected_without_runtime_repair[postgresql-collation]'), ('tests.integration_personal_history_index_migrations', 'test_same_columns_drift_or_missing_index_rejected_without_runtime_repair[postgresql-direction]'), ('tests.integration_personal_history_index_migrations', 'test_same_columns_drift_or_missing_index_rejected_without_runtime_repair[postgresql-identity_order]'), ('tests.integration_personal_history_index_migrations', 'test_same_columns_drift_or_missing_index_rejected_without_runtime_repair[postgresql-missing]'), ('tests.integration_personal_history_index_migrations', 'test_unknown29_drift_aborts_before_any_index_ddl[postgresql]'), ('tests.integration_personal_history_ordered_query', 'test_mixed_history_order_ownership_complete_pages_and_pg_work_budget[postgresql]')], 'pytest-postgres-history-index-restore.xml': [('tests.integration_personal_history_index_restore', 'test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts')]}.items()}

OLD_WIRING_STEP = {'name': 'Member link CI29 preserves reviewed historical gates and requires current contracts', 'run': 'python -X utf8 tests/verify_member_links_ci.py --output "$RUNNER_TEMP/member-links-ci"'}
WIRING_STEP = {'name': 'Physical history CI30 retains exact CI29 and requires current index contracts', 'run': 'python -X utf8 tests/verify_history_index_ci.py --output "$RUNNER_TEMP/history-index-ci"'}
INDEX_STEPS = [{'name': 'Physical history index migration rollback and bounded ordered PostgreSQL query', 'run': 'python -X utf8 tests/run_isolated.py tests/integration_personal_history_index_migrations.py tests/integration_personal_history_ordered_query.py -k postgresql -q --tb=short --junitxml=pytest-postgres-history-index.xml'}, {'name': 'Current revision30 populated restore preserves history index and every prior contract', 'run': 'python -X utf8 tests/run_isolated.py tests/integration_personal_history_index_restore.py -q --tb=short --junitxml=pytest-postgres-history-index-restore.xml'}]
INDEX_REPORTS = ('pytest-postgres-history-index.xml', 'pytest-postgres-history-index-restore.xml')
INDEX_CHECKER = {'name': 'Physical history reports retain every exact selected PostgreSQL case', 'run': 'python tests/check_history_index_reports.py'}


def normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b'\r\n', b'\n')


def authenticate_current_gates() -> None:
    # Independent literals bind executable helpers before they are imported/run.
    for name, digest in PINNED_CURRENT_GATES.items():
        assert hashlib.sha256(normalized(ROOT / name)).hexdigest() == digest, name


def baseline() -> dict:
    authenticate_current_gates()
    raw = normalized(SNAPSHOT / 'ci29-before.yml')
    assert hashlib.sha256(raw).hexdigest() == WORKFLOW_SHA, 'Historical workflow changed'
    metadata = normalized(SNAPSHOT / 'baseline.json')
    assert hashlib.sha256(metadata).hexdigest() == BASELINE_SHA, 'Baseline trust anchor changed'
    for name, digest in json.loads(metadata)['unchanged_files'].items():
        assert hashlib.sha256(normalized(ROOT / name)).hexdigest() == digest, name
    return yaml.safe_load(raw)


def expected_workflow(old: dict) -> dict:
    """Only extend the accepted29 workflow; all other job fields stay exact."""
    expected = copy.deepcopy(old)
    steps = expected['jobs']['test-web']['steps']
    assert steps.count(OLD_WIRING_STEP) == 1
    steps[steps.index(OLD_WIRING_STEP)] = WIRING_STEP
    steps = expected['jobs']['postgres']['steps']
    restore = next(step for step in steps if step.get('name', '').startswith('Current revision29 populated restore'))
    restore['run'] = ('python -X utf8 tests/run_reviewed_ci29.py --output "$RUNNER_TEMP/reviewed-ci29-restore" '
                      '--junitxml=pytest-postgres-member-restore.xml')
    guard = next(step for step in steps if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    steps[steps.index(guard):steps.index(guard)] = copy.deepcopy(INDEX_STEPS)
    needle = "len(reports)==26 and len(set(reports))==26, 'Expected 26 distinct PostgreSQL reports'"
    assert guard['run'].count(needle) == 1
    guard['run'] = guard['run'].replace(needle,
        "len(reports)==28 and len(set(reports))==28, 'Expected 28 distinct PostgreSQL reports'")
    guard['run'] += ' ' + ' '.join(INDEX_REPORTS)
    checker = next(step for step in steps if step == REPORT_STEP)
    steps.insert(steps.index(checker) + 1, INDEX_CHECKER)
    browser = next(step for step in expected['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run', ''))
    needle = '--tables 29 --revision ' + PREVIOUS
    assert browser['run'].count(needle) == 1
    browser['run'] = browser['run'].replace(needle, '--tables 29 --revision ' + REVISION)
    return expected


def verify_workflow(workflow: dict, old: dict) -> tuple[list[str], list[str]]:
    assert workflow == expected_workflow(old), 'Workflow differs beyond the reviewed CI30 delta'
    steps = workflow['jobs']['postgres']['steps']
    guard = next(step['run'] for step in steps if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    parts = shlex.split(guard)
    assert parts[:2] == ['python', '-c']
    reports = parts[3:]
    old_guard = next(step['run'] for step in old['jobs']['postgres']['steps']
                     if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    assert reports == shlex.split(old_guard)[3:] + list(INDEX_REPORTS)
    assert len(reports) == len(set(reports)) == 28
    produced = [name for step in steps for name in re.findall(
        r'--junitxml=(pytest-postgres-[a-z-]+\.xml)', step.get('run', ''))]
    assert len(produced) == 28 and set(produced) == set(reports)
    return parts, reports


def actual_fixture_markers() -> list[dict]:
    """Evaluate just existing marker expressions with actual current ORM metadata."""
    sys.path.insert(0, str(ROOT))
    from tests.isolation import block_external_sockets, prepare_environment
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
    """Reject weakening new gates or changing any accepted older job."""
    changes = [
        ('missing-local-guard', lambda w: w['jobs']['test-web']['steps'].remove(WIRING_STEP)),
        ('shallow-web-history', lambda w: next(s for s in w['jobs']['test-web']['steps'] if s.get('uses') == 'actions/checkout@v4')['with'].update({'fetch-depth': 1})),
        ('shallow-PG-history', lambda w: next(s for s in w['jobs']['postgres']['steps'] if s.get('uses') == 'actions/checkout@v4')['with'].update({'fetch-depth': 1})),
        ('missing-index-selection', lambda w: w['jobs']['postgres']['steps'].remove(INDEX_STEPS[0])),
        ('missing-current30-restore', lambda w: w['jobs']['postgres']['steps'].remove(INDEX_STEPS[1])),
        ('missing-index-checker', lambda w: w['jobs']['postgres']['steps'].remove(INDEX_CHECKER)),
        ('missing-member-checker', lambda w: w['jobs']['postgres']['steps'].remove(REPORT_STEP)),
        ('missing-real-browser', lambda w: w['jobs']['image']['steps'].remove(BROWSER_STEP)),
        ('private-browser-upload', lambda w: next(s for s in w['jobs']['image']['steps'] if s == BROWSER_UPLOAD)['with'].update({'path': '${{ runner.temp }}/**'})),
        ('new-PG-continue', lambda w: next(s for s in w['jobs']['postgres']['steps'] if s == INDEX_STEPS[0]).update({'continue-on-error': True})),
        ('browser-continue', lambda w: next(s for s in w['jobs']['image']['steps'] if s == BROWSER_STEP).update({'continue-on-error': True})),
    ]
    replacements = [
        ('historical29-current-runtime', 'postgres', 'tests/run_reviewed_ci29.py', 'tests/integration_client_link_restore.py'),
        ('historical28-current-runtime', 'postgres', 'tests/run_reviewed_ci28.py', 'tests/integration_password_recovery_restore.py'),
        ('omit-index-PG-selection', 'postgres', 'tests/integration_personal_history_ordered_query.py -k postgresql', 'tests/integration_personal_history_ordered_query.py'),
        ('omit-ordered-query', 'postgres', ' tests/integration_personal_history_ordered_query.py', ''),
        ('omit-historical-report', 'postgres', ' pytest-postgres-quota.xml', ''),
        ('duplicate-new-report', 'postgres', 'pytest-postgres-history-index.xml pytest-postgres-history-index-restore.xml', 'pytest-postgres-history-index.xml pytest-postgres-history-index.xml'),
        ('reduce-report-count', 'postgres', 'len(reports)==28', 'len(reports)==27'),
        ('restore-old29-instead30', 'postgres', 'tests/integration_personal_history_index_restore.py', 'tests/integration_client_link_restore.py'),
        ('old-fixture-head', 'image', '--revision ' + REVISION, '--revision ' + PREVIOUS),
        ('wrong-business-table-count', 'image', '--tables 29', '--tables 30'),
        ('ignore-startup-failure', 'image', '--revision ' + REVISION + ' 2>/dev/null; then ready=1; break; fi', '--revision ' + REVISION + ' 2>/dev/null; then ready=1; break; fi; ready=1'),
        ('weaken-VM-export', 'frontend-contracts', '--minimum 32', '--minimum 1'),
        ('weaken-VM-controls', 'frontend-contracts', '--minimum 3\n', '--minimum 0\n'),
        ('weaken-browser-command', 'image', '--port 8794', '--port 8794 || true'),
        ('skip-new-checker', 'postgres', 'python tests/check_history_index_reports.py', 'echo bypass'),
        ('skip-old-checker', 'postgres', 'python tests/check_member_link_reports.py', 'echo bypass'),
    ]
    rows = []
    for name, change in changes:
        mutant = copy.deepcopy(workflow); change(mutant)
        try: verify_workflow(mutant, old)
        except AssertionError: rows.append({'case': name, 'rejected': True})
        else: raise AssertionError(name)
    for name, job, before, after in replacements:
        mutant = copy.deepcopy(workflow)
        matches = [s for s in mutant['jobs'][job]['steps'] if before in s.get('run', '')]
        assert len(matches) == 1, name
        matches[0]['run'] = matches[0]['run'].replace(before, after)
        try: verify_workflow(mutant, old)
        except AssertionError: rows.append({'case': name, 'rejected': True})
        else: raise AssertionError(name)
    assert len(rows) == 27
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
                                     '--directory', str(directory)], capture_output=True, timeout=10, check=False)
            (directory / 'stdout.log').write_bytes(result.stdout)
            (directory / 'stderr.log').write_bytes(result.stderr)
            assert (result.returncode == 0) == positive, (target, mode)
            rows.append({'report': target, 'case': mode, 'exit': result.returncode, 'expected_pass': positive})
    assert len(rows) == 55, 'Current report probes were reduced'
    return rows


def index_report_canaries(out: Path) -> list[dict]:
    authenticate_current_gates()
    from tests.check_history_index_reports import REPORTS
    assert REPORTS == EXPECTED_INDEX_REPORTS and len(REPORTS) == 2
    rows = []
    modes = ['positive', 'missing', 'malformed', 'empty', 'reduced', 'duplicate',
             'wrong-module', 'SQLite', 'skip', 'failure', 'error', 'substituted-case']
    for target in REPORTS:
        for mode in modes:
            directory = out / (target.removesuffix('.xml') + '-' + mode); directory.mkdir()
            for filename, identities in REPORTS.items():
                suite = ET.Element('testsuite')
                for module, name in sorted(identities):
                    ET.SubElement(suite, 'testcase', classname=module, name=name)
                if filename == target:
                    if mode == 'empty': suite.clear()
                    elif mode == 'reduced': suite.remove(suite[-1])
                    elif mode == 'duplicate': suite.append(copy.deepcopy(suite[0]))
                    elif mode == 'wrong-module': suite[0].set('classname', 'tests.unrelated')
                    elif mode == 'SQLite': suite[0].set('name', 'case_0[sqlite]')
                    elif mode == 'substituted-case': suite[0].set('name', 'unrelated_case[postgresql]')
                    elif mode in ['skip', 'failure', 'error']: ET.SubElement(suite[0], 'skipped' if mode == 'skip' else mode)
                ET.ElementTree(suite).write(directory / filename, encoding='utf8', xml_declaration=True)
            if mode == 'missing': (directory / target).unlink()
            elif mode == 'malformed': (directory / target).write_bytes(b'<testsuite')
            result = subprocess.run([sys.executable, str(ROOT / 'tests/check_history_index_reports.py'),
                '--directory', str(directory)], capture_output=True, timeout=10, check=False)
            (directory / 'stdout.log').write_bytes(result.stdout); (directory / 'stderr.log').write_bytes(result.stderr)
            assert (result.returncode == 0) == (mode == 'positive'), (target, mode)
            rows.append({'report': target, 'case': mode, 'exit': result.returncode})
    assert len(rows) == 24
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
                                    capture_output=True, timeout=25, check=False)
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
    historical = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tests/run_reviewed_ci29.py'),
        '--output', str(out / 'historical-ci29'), '--history-repository', str(args.history_repository)],
        cwd=ROOT, capture_output=True, timeout=90, check=False)
    (out / 'historical.log').write_bytes(historical.stdout + historical.stderr)
    assert historical.returncode == 0, 'Exact historical CI28 verification failed'
    report = {'scope': 'Local CI30 wiring/parsers/actual marker expressions and owned inert Bash; no Actions/browser/PG/provider execution',
        'historical_source_pin': 'fd636202045efa30b1430f4a9dd8ab287ec76357',
        'historical_exit': historical.returncode, 'reports': reports, 'retained_member_PG_minimum_cases': 60,
        'current_index_PG_exact_cases': 9,
        'VM_minima': VM_MODULES, 'VM_executions_in_full18': 300, 'VM_unique_criteria': 279,
        'duplicate_legacy_export_executions': 21, 'actual_markers': actual_fixture_markers(),
        'unauthorized_delta_canaries': delta_cases(workflow, old)}
    if not args.verify_only:
        bash = os.environ.get('METODOBASE_CI_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
        assert bash
        blocks = [step['run'] for job in workflow['jobs'].values() for step in job.get('steps', []) if 'run' in step]
        for block in blocks:
            result = subprocess.run([bash, '-n'], input=block.encode(), capture_output=True, timeout=15, check=False)
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
            report['index_report_canaries'] = index_report_canaries(scratch)
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
                      'index_report_canaries': len(report.get('index_report_canaries', [])),
                      'inert_cases': len(report.get('current_inert_fixture_cases', []))}))


if __name__ == '__main__':
    main()
