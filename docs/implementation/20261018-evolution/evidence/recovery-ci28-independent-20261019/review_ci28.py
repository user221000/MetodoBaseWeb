"""Independent CI28 wiring review; synthetic reports and inert owned processes only."""
import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile

import yaml

ROOT = Path(r'F:\MetodoBaseWeb-recovery-ci-20261019')
OUT = Path(__file__).resolve().parent
HEAD = '5db0732f33f8dea60b2d1192e1105a18f79d01c1'
BASH = 'C:/Program Files/Git/bin/bash.exe'
REVISION = '20261019_account_recovery'
PREVIOUS = '20261019_personal_diary'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def run(args, cwd=ROOT, **kwargs):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf8',
                          timeout=45, **kwargs)


def photo():
    head = run(['git', 'rev-parse', 'HEAD']).stdout.strip()
    assert head == HEAD
    files = run(['git', 'ls-files', '-z']).stdout.split('\0')
    selected = [path for path in files if path and (not path.startswith('docs/') or
                path.startswith('docs/implementation/20261018-evolution/evidence/backend-recovery-ci28/'))]
    sources = {path: sha((ROOT / path).read_bytes()) for path in selected}
    packages = sorted((dist.metadata['Name'], dist.version) for dist in importlib.metadata.distributions())
    dependency_paths = [path for path in selected if re.search(
        r'(^|/)(requirements[^/]*\.txt|[^/]*lock[^/]*|package\.json|pyproject\.toml|setup\.(?:py|cfg)|Pipfile|pytest\.ini)$', path)]
    assert run(['git', 'status', '--porcelain']).stdout == ''
    return {'head': head, 'sources': sources, 'packages': packages,
            'dependency_paths': dependency_paths}


def assert_rejected(result, label):
    assert result.returncode != 0, label


def main():
    before = photo()
    save(OUT / 'before.json', before)
    pip_before = run([sys.executable, '-m', 'pip', 'check'])
    (OUT / 'pip-before.log').write_text(pip_before.stdout + pip_before.stderr, encoding='utf8')
    assert pip_before.returncode == 0
    raw = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf8')
    workflow = yaml.safe_load(raw)
    steps = workflow['jobs']['postgres']['steps']
    guard = next(step['run'] for step in steps if step.get('name', '').startswith('Required PostgreSQL acceptance'))
    parts = shlex.split(guard)
    assert parts[:2] == ['python', '-c']
    reports = parts[3:]
    assert len(reports) == len(set(reports)) == 21
    new_reports = ['pytest-postgres-recovery-migrations.xml', 'pytest-postgres-recovery.xml']
    assert reports[-2:] == new_reports
    history = {}
    for commit in ['00d2114', '8435bd0', '92615d7']:
        baseline_raw = run(['git', 'show', commit + ':.github/workflows/ci.yml'])
        assert baseline_raw.returncode == 0
        old = yaml.safe_load(baseline_raw.stdout)
        old_guard = next(step['run'] for step in old['jobs']['postgres']['steps']
                         if step.get('name', '').startswith('Required PostgreSQL acceptance'))
        old_reports = shlex.split(old_guard)[3:]
        assert len(old_reports) == 19 and reports == old_reports + new_reports
        history[commit] = sha(baseline_raw.stdout.encode())
    assert len(set(history.values())) == 1
    snapshot = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-recovery-ci28'
    assert sha((snapshot / 'ci27-baseline.yml').read_bytes().replace(b'\r\n', b'\n')) == history['00d2114']
    immutable = ['tests/verify_diary_ci.py', 'scripts/check_browser_fixture_startup.py',
                 'scripts/check_frontend_report.py', 'tests/test_frontend_report_guard.py',
                 'tests/e2e/personal_diary.cjs', 'tests/e2e/personal_export_context_browser.cjs',
                 'tests/integration_diary_restore_review.py']
    immutable_sha = {}
    for path in immutable:
        previous = run(['git', 'show', '00d2114:' + path])
        assert previous.returncode == 0
        actual = (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
        assert previous.stdout.encode() == actual, path
        immutable_sha[path] = sha(actual)
    # Resolve every exact pytest node through AST, without importing backend or collecting tests.
    nodes = []
    for step in steps:
        for path, name in re.findall(r'(tests/[\w/]+\.py)::([A-Za-z0-9_]+)', step.get('run', '')):
            functions = {node.name for node in ast.parse((ROOT / path).read_text(encoding='utf8')).body
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            assert name in functions, (path, name)
            nodes.append(path + '::' + name)
    restore = next(step['run'] for step in steps if step.get('name', '').startswith('Encrypted PostgreSQL'))
    assert 'test_encrypted_pg_restore_preserves_rows_constraints_and_private_objects' in restore
    assert 'tests/integration_recovery28_restore_review.py::test_revision28_restore_preserves_recovery_and_all_revision26_27_contracts' in restore
    assert 'tests/integration_diary_restore_review.py' not in restore
    browser = next(step['run'] for step in workflow['jobs']['image']['steps']
                   if 'run_browser_fixture() {' in step.get('run', ''))
    function = browser[browser.index('run_browser_fixture() {'):browser.index('\nbrowser_evidence=')]
    assert '--tables 26 --revision ' + REVISION in function
    assert PREVIOUS not in function
    (OUT / 'actual-fixture-function.sh').write_text(function + '\n', encoding='utf8')

    scratch = Path(tempfile.mkdtemp(prefix='metodobase-ci28-independent-20261019-'))
    save(OUT / 'owned-scratch.json', {'path': str(scratch), 'ownership': 'Created exclusively by this review; retained without deleting any external artifact.'})
    author_output = scratch / 'author-replay'
    author = run([sys.executable, '-X', 'utf8', str(ROOT / 'tests/verify_recovery_ci.py'), '--output', str(author_output)])
    (OUT / 'author-replay.log').write_text(author.stdout + author.stderr, encoding='utf8')
    assert author.returncode == 0
    author_report = json.loads((author_output / 'review.json').read_text())
    assert len(author_report['new_report_canaries']) == 18
    assert len(author_report['unauthorized_delta_canaries']) == 8
    assert len(author_report['inert_fixture_cases']) == 2
    assert author_report['bash_blocks'] == 63

    # Each required report independently gates acceptance; malformed new reports cannot hide behind the other20.
    guard_dir = scratch / 'own-junit'; guard_dir.mkdir()
    positive = '<testsuites><testsuite tests="1"><testcase name="owned-independent"/></testsuite></testsuites>'
    for name in reports:
        (guard_dir / name).write_text(positive, encoding='utf8')
    junit = []
    passed = run([sys.executable, '-c', parts[2], *reports], cwd=guard_dir)
    assert passed.returncode == 0
    junit.append({'case': 'all21-positive', 'exit': passed.returncode})
    for name in reports:
        for label, content in [('missing', None), ('skipped', '<testsuite><testcase><skipped/></testcase></testsuite>')]:
            path = guard_dir / name
            if content is None:
                path.unlink()
            else:
                path.write_text(content, encoding='utf8')
            result = run([sys.executable, '-c', parts[2], *reports], cwd=guard_dir)
            assert_rejected(result, (name, label))
            junit.append({'report': name, 'case': label, 'exit': result.returncode})
            path.write_text(positive, encoding='utf8')
    for name in new_reports:
        for label, content in [('empty-file', ''), ('zero-testcase', '<testsuite tests="0"/>'),
                               ('failure', '<testsuite><testcase><failure/></testcase></testsuite>'),
                               ('error', '<testsuite><testcase><error/></testcase></testsuite>')]:
            (guard_dir / name).write_text(content, encoding='utf8')
            result = run([sys.executable, '-c', parts[2], *reports], cwd=guard_dir)
            assert_rejected(result, (name, label))
            junit.append({'report': name, 'case': label, 'exit': result.returncode})
            (guard_dir / name).write_text(positive, encoding='utf8')
    for label, names in [('old19', reports[:-2]), ('only20', reports[:-1]),
                          ('21-with-duplicate', reports[:-1] + [reports[0]]), ('22', reports + [reports[0]])]:
        result = run([sys.executable, '-c', parts[2], *names], cwd=guard_dir)
        assert_rejected(result, label)
        junit.append({'case': label, 'exit': result.returncode})
    assert len(junit) == 55

    # New independent mutations exercise the full CLI and immutable baseline verification.
    delta = []
    for name in ['continue-on-error', 'runtime-mask-exit', 'marker-port8777', 'other-job-timeout',
                 'restore-wrong-node', 'fixture-extra-statement', 'fixture-head28-hardcoded']:
        folder = scratch / ('own-delta-' + name); folder.mkdir()
        candidate = copy.deepcopy(workflow)
        fixture_text = (ROOT / 'tests/e2e/personal_diary_server.py').read_text(encoding='utf8')
        candidate_steps = candidate['jobs']['postgres']['steps']
        recovery = next(step for step in candidate_steps if 'tests/integration_password_recovery_postgres.py' in step.get('run', ''))
        if name == 'continue-on-error':
            recovery['continue-on-error'] = True
        elif name == 'runtime-mask-exit':
            recovery['run'] += ' || true'
        elif name == 'marker-port8777':
            step = next(step for step in candidate['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run', ''))
            assert 'personal_diary_server.py 8776' in step['run']
            step['run'] = step['run'].replace('personal_diary_server.py 8776', 'personal_diary_server.py 8777')
        elif name == 'other-job-timeout':
            candidate['jobs']['redis']['timeout-minutes'] = 1
        elif name == 'restore-wrong-node':
            step = next(step for step in candidate_steps if step.get('name', '').startswith('Encrypted PostgreSQL'))
            step['run'] = step['run'].replace('test_revision28_restore_preserves_recovery_and_all_revision26_27_contracts', 'test_missing_restore28')
        elif name == 'fixture-extra-statement':
            fixture_text += '\nprint("unauthorized-code")\n'
        elif name == 'fixture-head28-hardcoded':
            assert "'model_target_revision':expected_head()" in fixture_text
            fixture_text = fixture_text.replace("'model_target_revision':expected_head()", "'model_target_revision':'20261019_account_recovery'")
        supplied_workflow = folder / 'candidate.yml'; supplied_workflow.write_text(yaml.safe_dump(candidate), encoding='utf8')
        supplied_fixture = folder / 'fixture.py'; supplied_fixture.write_text(fixture_text, encoding='utf8')
        result = run([sys.executable, '-X', 'utf8', str(ROOT / 'tests/verify_recovery_ci.py'),
                      '--workflow', str(supplied_workflow), '--fixture', str(supplied_fixture),
                      '--output', str(folder / 'rejected-output'), '--verify-only'])
        assert_rejected(result, name)
        (folder / 'verifier.log').write_text(result.stdout + result.stderr, encoding='utf8')
        delta.append({'case': name, 'exit': result.returncode})

    writer = scratch / 'own_writer.py'
    writer.write_text("import json,sys\nfrom pathlib import Path\np,k,n,s,bad=sys.argv[1:]\nn=int(n);s=int(s)\nr={'checks':[{'name':str(i)} if k=='named' else str(i) for i in range(n)],'pageErrors':[],'screens':[str(i) for i in range(s)]}\nif bad=='empty':r['checks']=[]\nPath(p).write_text(json.dumps(r))\n", encoding='utf8')
    prefix = r'''set -euo pipefail
browser_fixture_pid=''
owned_fixture_pid=''
driver_count=0
kill() {
 if [[ "$1" != '-0' ]]; then
  printf 'cleanup %s\n' "$1" >> "$QA_EVENTS"
  owned_fixture_pid="$1"
 fi
 builtin kill "$@"
}
close_owned() {
 local result=$?
 if [[ -n "${browser_fixture_pid:-}" ]]; then kill "$browser_fixture_pid" 2>/dev/null || true; wait "$browser_fixture_pid" || true; fi
 if [[ -n "${owned_fixture_pid:-}" ]]; then
  if builtin kill -0 "$owned_fixture_pid" 2>/dev/null; then exit 88; fi
  printf 'closed %s\n' "$owned_fixture_pid" >> "$QA_EVENTS"
 fi
 exit "$result"
}
trap close_owned EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$QA_EVENTS"
  case "$QA_MARKER" in
   head28) printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261019_account_recovery"}';;
   head27) printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261019_personal_diary"}';;
   missing) printf '%s\n' 'HTTP readiness may precede fixture metadata';;
  esac
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$QA_PYTHON" "$QA_STARTUP" "${@:2}"
 else
  "$QA_PYTHON" "$QA_GUARD" "${@:2}"
 fi
}
curl() { printf 'health-stub\n' >> "$QA_EVENTS"; return 0; }
sleep() { /usr/bin/sleep 0.01; }
node() {
 driver_count=$((driver_count+1))
 printf 'driver%s %s\n' "$driver_count" "$browser_fixture_pid" >> "$QA_EVENTS"
 if [[ "$driver_count" == 2 && "$QA_SECOND" == fail ]]; then return 7; fi
 if [[ "$driver_count" == 1 ]]; then
  "$QA_PYTHON" "$QA_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens" good
 else
  "$QA_PYTHON" "$QA_WRITER" "$second_report" "$second_format" "$second_minimum" "$second_screens" "$QA_SECOND"
 fi
}
'''
    inert = []
    for name, marker, second, expected_exit, expected_drivers in [
        ('head28', 'head28', 'good', 0, 2), ('head27', 'head27', 'good', 1, 0),
        ('health-before-marker', 'missing', 'good', 1, 0),
        ('second-driver-fails', 'head28', 'fail', 7, 2),
        ('second-report-empty', 'head28', 'empty', 1, 2),
    ]:
        folder = scratch / ('own-inert-' + name); folder.mkdir()
        (folder / 'docs/implementation/20261018-evolution/evidence/ux').mkdir(parents=True)
        script = folder / 'probe.sh'
        call = 'run_browser_fixture unused-fixture.py 9998 first.cjs first.json 17 named 8 second.cjs second.json 4 strings 4 personal-diary-ui\n'
        script.write_text(prefix + function + '\n' + call, encoding='utf8')
        env = dict(os.environ, QA_EVENTS=(folder / 'events.txt').as_posix(), QA_MARKER=marker,
                   QA_SECOND=second, QA_PYTHON=Path(sys.executable).as_posix(), QA_WRITER=writer.as_posix(),
                   QA_STARTUP=(ROOT / 'scripts/check_browser_fixture_startup.py').as_posix(),
                   QA_GUARD=(ROOT / 'scripts/check_frontend_report.py').as_posix())
        result = run([BASH, script.as_posix()], cwd=folder, env=env)
        (folder / 'result.log').write_text(result.stdout + result.stderr, encoding='utf8')
        assert result.returncode == expected_exit, (name, result.returncode, result.stderr)
        events = (folder / 'events.txt').read_text().splitlines()
        starts = [row.split()[1] for row in events if row.startswith('start ')]
        cleanup = [row.split()[1] for row in events if row.startswith('cleanup ')]
        closed = [row.split()[1] for row in events if row.startswith('closed ')]
        drivers = [row for row in events if row.startswith('driver')]
        assert len(starts) == 1 and starts == cleanup == closed, (name, events)
        assert len(drivers) == expected_drivers
        assert all(row.split()[1] == starts[0] for row in drivers)
        assert 'health-stub' in events
        inert.append({'case': name, 'exit': result.returncode, 'events': events,
                      'owned_pid_closed_after_wait': True, 'network': 'curl stub only; no listener or socket'})

    save(OUT / 'own-canaries.json', {'junit': junit, 'unauthorized_delta': delta, 'inert_bash': inert})
    with zipfile.ZipFile(OUT / 'raw-owned-canaries.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(scratch.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(scratch).as_posix())
    after = photo()
    save(OUT / 'after.json', after)
    assert before == after
    pip_after = run([sys.executable, '-m', 'pip', 'check'])
    (OUT / 'pip-after.log').write_text(pip_after.stdout + pip_after.stderr, encoding='utf8')
    assert pip_after.returncode == 0
    summary = {'head': HEAD, 'accepted_ci27_baseline_sha256': history,
               'reports': reports, 'unchanged_accepted_sources_lf_sha256': immutable_sha,
               'exact_postgres_nodes_resolve_without_collection': nodes,
               'source_count': len(before['sources']), 'sources_stable': True,
               'dependency_paths': before['dependency_paths'], 'packages': len(before['packages']),
               'packages_stable': True, 'pip_check_before_after': [0, 0],
               'author_replay': {'report_canaries': 18, 'delta_canaries': 8, 'inert_cases': 2, 'bash_blocks': 63},
               'own_canaries': {'report': len(junit), 'delta': len(delta), 'inert_bash': len(inert)},
               'marker': author_report['actual_fixture_marker'],
               'scope': 'Windows-local candidate Python and Git Bash, synthetic XML and inert owned sleep processes. No PG/backend/browser/VM/Actions/Linux execution. No product/CI/author source edits or commits.'}
    save(OUT / 'summary.json', summary)
    files = {path.relative_to(OUT).as_posix(): sha(path.read_bytes()) for path in sorted(OUT.rglob('*')) if path.is_file()}
    save(OUT / 'manifest.json', {'files': files, 'count': len(files), 'scope': 'All evidence except self-referential manifest.'})
    print(json.dumps({'source_count': len(before['sources']), 'packages': len(before['packages']),
                      'author': summary['author_replay'], 'own': summary['own_canaries'],
                      'summary_sha256': sha((OUT / 'summary.json').read_bytes()),
                      'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))


if __name__ == '__main__':
    main()
