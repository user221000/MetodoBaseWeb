"""Add bounded CI30 gates, preserving true archived29 and28 acceptance."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
ROOT=Path(r'F:\mb-r12-history30-20261019')
def norm(path):return path.read_bytes().replace(b'\r\n',b'\n')
def digest(value):return hashlib.sha256(value).hexdigest()
def write(name,value):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value.encode('utf8') if isinstance(value,str) else value)
old=norm(ROOT/'tests/verify_member_links_ci.py').decode();workflow=norm(ROOT/'.github/workflows/ci.yml').decode()
assert 'verify_history_index_ci' not in workflow
snapshot=ROOT/'tests/ci_history_index30';snapshot.mkdir(exist_ok=False)
oldworkflow=subprocess.check_output(['git','show','fd636202045efa30b1430f4a9dd8ab287ec76357:.github/workflows/ci.yml'],cwd=ROOT)
assert workflow.encode()==oldworkflow
write('tests/ci_history_index30/ci29-before.yml',oldworkflow)
previous=json.loads(norm(ROOT/'tests/ci_member_links29/baseline.json'))
unchanged=dict(previous['unchanged_files'])
for name in ['tests/verify_member_links_ci.py','tests/check_member_link_reports.py','tests/run_reviewed_ci28.py']:
    unchanged[name]=digest(norm(ROOT/name))
baseline=json.dumps({'commit':'fd636202045efa30b1430f4a9dd8ab287ec76357','workflow_sha256':digest(oldworkflow),'unchanged_files':unchanged},indent=2)+'\n'
write('tests/ci_history_index30/baseline.json',baseline)
checker='''"""Require all selected physical-index30 and populated-restore acceptance cases.

Historical29 reports retain their separate unchanged checker. These exact
identities prevent replacing a missing index case with an unrelated PG case.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

MIGRATIONS = 'tests.integration_personal_history_index_migrations'
QUERY = 'tests.integration_personal_history_ordered_query'
RESTORE = 'tests.integration_personal_history_index_restore'
REPORTS = {
    'pytest-postgres-history-index.xml': frozenset({
        (MIGRATIONS, 'test_populated29_upgrade_repeat_and_index_only_rollback[postgresql]'),
        *((MIGRATIONS, 'test_same_columns_drift_or_missing_index_rejected_without_runtime_repair[postgresql-' + kind + ']')
          for kind in ('direction', 'identity_order', 'collation', 'missing')),
        (MIGRATIONS, 'test_unknown29_drift_aborts_before_any_index_ddl[postgresql]'),
        (MIGRATIONS, 'test_failure_after_actual_index_ddl_rolls_back_rows_guards_and_revision[postgresql]'),
        (QUERY, 'test_mixed_history_order_ownership_complete_pages_and_pg_work_budget[postgresql]'),
    }),
    'pytest-postgres-history-index-restore.xml': frozenset({
        (RESTORE, 'test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts'),
    }),
}


def validate(directory: Path) -> int:
    """Read only public JUnit structure and reject omissions/substitutions."""
    seen = set()
    for filename, required in REPORTS.items():
        root = ET.parse(directory / filename).getroot()
        cases = root.findall('.//testcase')
        if any(root.findall('.//' + tag) for tag in ('skipped', 'failure', 'error')):
            raise ValueError('Unsuccessful physical index acceptance')
        actual = [(case.get('classname'), case.get('name')) for case in cases]
        if len(actual) != len(required) or set(actual) != required or seen.intersection(actual):
            raise ValueError('Missing, repeated or substituted physical index acceptance')
        seen.update(actual)
    return len(seen)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        count = validate(args.directory)
    except (OSError, ET.ParseError, ValueError):
        parser.exit(1, 'Physical history index PostgreSQL reports are missing or unsuccessful\\n')
    print(f'{count} physical history index PostgreSQL cases accepted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
'''
write('tests/check_history_index_reports.py',checker)
def replace_function(source,name,replacement):
    tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=source.splitlines(keepends=True);return ''.join(lines[:node.lineno-1])+replacement.rstrip()+'\n'+''.join(lines[node.end_lineno:])
new=old.replace('bounded CI29 delta while retaining exact historical CI28','bounded CI30 delta while retaining exact historical CI29 and CI28')
new=new.replace("SNAPSHOT = ROOT / 'tests/ci_member_links29'","SNAPSHOT = ROOT / 'tests/ci_history_index30'")
new=new.replace(re.search(r"WORKFLOW_SHA = '[^']+'",new)[0],"WORKFLOW_SHA = '"+digest(oldworkflow)+"'")
new=new.replace(re.search(r"BASELINE_SHA = '[^']+'",new)[0],"BASELINE_SHA = '"+digest(baseline.encode())+"'")
new=new.replace("'ci28-before.yml'","'ci29-before.yml'")
new=new.replace("REVISION = '20261019_client_account_links'","REVISION = '20261019_personal_history_index'")
new=new.replace("PREVIOUS = '20261019_account_recovery'","PREVIOUS = '20261019_client_account_links'")
oldwiring=ast.literal_eval(next(n.value for n in ast.parse(old).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='WIRING_STEP' for t in n.targets)))
newwiring={'name':'Physical history CI30 retains exact CI29 and requires current index contracts','run':'python -X utf8 tests/verify_history_index_ci.py --output "$RUNNER_TEMP/history-index-ci"'}
indexsteps=[{'name':'Physical history index migration rollback and bounded ordered PostgreSQL query','run':'python -X utf8 tests/run_isolated.py tests/integration_personal_history_index_migrations.py tests/integration_personal_history_ordered_query.py -k postgresql -q --tb=short --junitxml=pytest-postgres-history-index.xml'},
{'name':'Current revision30 populated restore preserves history index and every prior contract','run':'python -X utf8 tests/run_isolated.py tests/integration_personal_history_index_restore.py -q --tb=short --junitxml=pytest-postgres-history-index-restore.xml'}]
indexchecker={'name':'Physical history reports retain every exact selected PostgreSQL case','run':'python tests/check_history_index_reports.py'}
extra='\nOLD_WIRING_STEP = '+repr(oldwiring)+'\nWIRING_STEP = '+repr(newwiring)+'\nINDEX_STEPS = '+repr(indexsteps)+'\nINDEX_REPORTS = (\'pytest-postgres-history-index.xml\', \'pytest-postgres-history-index-restore.xml\')\nINDEX_CHECKER = '+repr(indexchecker)+'\n'
new=new.replace('\n\ndef normalized(',extra+'\n\ndef normalized(',1)
expected='''def expected_workflow(old: dict) -> dict:
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
'''
new=replace_function(new,'expected_workflow',expected)
new=new.replace("reviewed CI29 delta'","reviewed CI30 delta'").replace("+ list(NEW_REPORTS)","+ list(INDEX_REPORTS)")
new=new.replace('== 26\n    produced','== 28\n    produced').replace('len(produced) == 26','len(produced) == 28')
delta='''def delta_cases(workflow: dict, old: dict) -> list[dict]:
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
        ('ignore-startup-failure', 'image', 'then ready=1; break; fi', 'then ready=1; break; fi; ready=1'),
        ('weaken-VM-export', 'frontend-contracts', '--minimum 32', '--minimum 1'),
        ('weaken-VM-controls', 'frontend-contracts', '--minimum 3', '--minimum 0'),
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
'''
new=replace_function(new,'delta_cases',delta)
indexcanaries='''def index_report_canaries(out: Path) -> list[dict]:
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
                '--directory', str(directory)], capture_output=True, timeout=10)
            (directory / 'stdout.log').write_bytes(result.stdout); (directory / 'stderr.log').write_bytes(result.stderr)
            assert (result.returncode == 0) == (mode == 'positive'), (target, mode)
            rows.append({'report': target, 'case': mode, 'exit': result.returncode})
    assert len(rows) == 24
    return rows


'''
new=new.replace('def inert_cases(',indexcanaries+'def inert_cases(',1)
# Execute the exact accepted29 guard; its nested28 archive uses the real repository.
new=new.replace("str(ROOT / 'tests/run_reviewed_ci28.py')","str(ROOT / 'tests/run_reviewed_ci29.py')")
new=new.replace("str(out / 'historical-ci28')","str(out / 'historical-ci29')")
new=new.replace("Historical CI28 verification failed","Historical CI29 verification failed")
new=new.replace("'66d9dec0e15dd873038bd248d3883daeeb27d4ca'","'fd636202045efa30b1430f4a9dd8ab287ec76357'")
new=new.replace('Local CI29 wiring','Local CI30 wiring')
new=new.replace("report['current_report_canaries'] = report_canaries(scratch)","report['current_report_canaries'] = report_canaries(scratch)\n            report['index_report_canaries'] = index_report_canaries(scratch)")
new=new.replace("'report_canaries': len(report.get('current_report_canaries', [])),","'report_canaries': len(report.get('current_report_canaries', [])),\n                      'index_report_canaries': len(report.get('index_report_canaries', [])),")
# New checker expected identities are captured as independently reviewable literals.
namespace={};exec(compile(checker,'checker-definitions','exec'),namespace)
literal={name:sorted(values) for name,values in namespace['REPORTS'].items()}
literalcode='EXPECTED_INDEX_REPORTS = {name: frozenset(tuple(item) for item in identities) for name, identities in '+repr(literal)+'.items()}\n'
new=new.replace('OLD_WIRING_STEP = ',literalcode+'\nOLD_WIRING_STEP = ',1)
# Bind every executable affected helper, historical guard and physical witness.
tree=ast.parse(new);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_CURRENT_GATES' for t in n.targets))
pins=ast.literal_eval(node.value)
for name in list(pins)+['tests/run_reviewed_ci29.py','tests/verify_member_links_ci.py','tests/check_history_index_reports.py','web/database/alembic/history_index_contract_v1.py']:
    pins[name]=digest(norm(ROOT/name))
lines=new.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['PINNED_CURRENT_GATES = '+repr(pins)+'\n'];new=''.join(lines)
ast.parse(new);write('tests/verify_history_index_ci.py',new)
# Keep the old four negative criteria; only select the current guard import.
trust=norm(ROOT/'tests/test_member_ci_trust.py').decode();assert trust.count('verify_member_links_ci as guard')==1
write('tests/test_member_ci_trust.py',trust.replace('verify_member_links_ci as guard','verify_history_index_ci as guard'))
workflow=workflow.replace(oldwiring['name'],newwiring['name']).replace(oldwiring['run'],newwiring['run'])
oldrestore='python -X utf8 tests/run_isolated.py tests/integration_client_link_restore.py -q --tb=short --junitxml=pytest-postgres-member-restore.xml'
assert workflow.count(oldrestore)==1
workflow=workflow.replace(oldrestore,'python -X utf8 tests/run_reviewed_ci29.py --output "$RUNNER_TEMP/reviewed-ci29-restore" --junitxml=pytest-postgres-member-restore.xml')
needle='      - name: Required PostgreSQL acceptance';assert workflow.count(needle)==1
position=workflow.index(needle)
workflow=workflow[:position]+''.join('      - name: '+step['name']+'\n        run: '+step['run']+'\n' for step in indexsteps)+workflow[position:]
workflow=workflow.replace("len(reports)==26 and len(set(reports))==26, 'Expected 26 distinct PostgreSQL reports'","len(reports)==28 and len(set(reports))==28, 'Expected 28 distinct PostgreSQL reports'")
needle='pytest-postgres-member-races.xml pytest-postgres-member-restore.xml';assert workflow.count(needle)==1
workflow=workflow.replace(needle,needle+' pytest-postgres-history-index.xml pytest-postgres-history-index-restore.xml')
needle='        run: python tests/check_member_link_reports.py\n';assert workflow.count(needle)==1
workflow=workflow.replace(needle,needle+'      - name: '+indexchecker['name']+'\n        run: '+indexchecker['run']+'\n')
needle='--tables 29 --revision 20261019_client_account_links';assert workflow.count(needle)==1
workflow=workflow.replace(needle,'--tables 29 --revision 20261019_personal_history_index')
write('.github/workflows/ci.yml',workflow)
print(json.dumps({'workflow29_sha':digest(oldworkflow),'baseline_sha':digest(baseline.encode()),'new_guard_sha':digest(new.encode()),'pins':len(pins),'selected_index_PG_cases':8,'restore30_cases':1,'workflow_expected_reports':28,'original_member_checker_unchanged':True,'historical_tests_unchanged':True}))
