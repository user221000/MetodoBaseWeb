"""Frozen R34 independent phases; author worktree stays read only."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(r'F:\MetodoBaseWeb-history-ui-20261019')
MAIN = Path(r'F:\MetodoBaseWeb-execution-20261018')
OUT = Path(__file__).resolve().parent
HEAD = '49eb44124d36a0d0aeaf732d7f720d969f1d517c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def command(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf8',
                          timeout=300, **kwargs)


def photo():
    head = command(['git', 'rev-parse', 'HEAD']).stdout.strip()
    assert head == HEAD
    assert command(['git', 'status', '--porcelain']).stdout == ''
    paths = command(['git', 'ls-files', '-z']).stdout.split('\0')
    selected = [path for path in paths if path and (not path.startswith('docs/') or
                '/history-pagination/' in path or '/history-headers-followup/' in path or
                '/HISTORIAL_PERSONAL_' in path)]
    packages = sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions())
    assert len(packages) == 89
    node_paths = []
    for module in ['playwright-core', 'axe-core']:
        directory = MAIN / 'tests/e2e/node_modules' / module
        assert directory.is_dir()
        node_paths.extend(path for path in directory.rglob('*') if path.is_file())
    return {'head': head, 'sources': {path: sha(ROOT / path) for path in selected},
            'packages': packages,
            'readonly_browser_dependencies': {str(path.relative_to(MAIN)).replace('\\', '/'): sha(path) for path in sorted(node_paths)}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['backend', 'vm', 'own'])
    parser.add_argument('--label', required=True)
    parser.add_argument('--own-test', type=Path)
    args = parser.parse_args()
    out = OUT / args.label; out.mkdir(exist_ok=False)
    before = photo(); save(out / 'before.json', before)
    pip_before = command([sys.executable, '-m', 'pip', 'check'])
    (out / 'pip-before.log').write_text(pip_before.stdout + pip_before.stderr, encoding='utf8')
    assert pip_before.returncode == 0
    environment = dict(os.environ)
    for name in ['METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_DATABASE_URL',
                 'DATABASE_URL', 'METODOBASE_HISTORY_EXPLAIN_OUTPUT']:
        environment.pop(name, None)
    if args.phase == 'vm':
        argv = ['node', 'tests/e2e/personal_history.cjs']
    else:
        files = ['tests/test_personal_history_pagination.py', 'tests/test_personal_history_cursor.py',
                 'tests/test_personal_plan_ui_contract.py'] if args.phase == 'backend' else [str(args.own_test.resolve())]
        assert args.phase != 'own' or args.own_test.is_file()
        argv = [sys.executable, '-X', 'utf8', 'tests/run_isolated.py', *files,
                '-q', '--tb=short', '--junitxml=' + str(out / 'result.xml')]
        scratch = Path(tempfile.mkdtemp(prefix='metodobase-r34-' + args.phase + '-qa-20261019-'))
        save(out / 'owned-temp.json', {'path': str(scratch), 'scope': 'Fresh caller-owned explicit EXPLAIN output only; no historical path.'})
        environment['METODOBASE_HISTORY_EXPLAIN_OUTPUT'] = str(scratch / 'explain')
    save(out / 'command.json', {'argv': argv, 'cwd': str(ROOT), 'head': HEAD,
                                'scope': 'Offline providers and isolated real SQLite; no PostgreSQL configured.'})
    started = time.monotonic()
    result = command(argv, env=environment)
    seconds = round(time.monotonic() - started, 3)
    (out / 'result.log').write_text(result.stdout + result.stderr, encoding='utf8')
    if args.phase == 'vm':
        payload = json.loads(result.stdout)
        save(out / 'result.json', payload)
        assert payload['passed'] == payload['total'] == 23
        assert len({row['case'] for row in payload['results']}) == 23
        totals = {'tests': 23, 'failure': 0, 'error': 0, 'skipped': 0}
    else:
        xml = ET.parse(out / 'result.xml').getroot()
        suites = [xml] if xml.tag == 'testsuite' else list(xml.iter('testsuite'))
        totals = {key: sum(int(suite.attrib.get(attr, 0)) for suite in suites)
                  for key, attr in [('tests', 'tests'), ('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')]}
        if args.phase == 'backend':
            assert totals['tests'] == 74
        if (scratch / 'explain').exists():
            explains = {path.name: json.loads(path.read_text()) for path in sorted((scratch / 'explain').glob('*.json'))}
            save(out / 'explain.json', explains)
            assert len(explains) == 2 if args.phase == 'backend' else True
    after = photo(); save(out / 'after.json', after)
    pip_after = command([sys.executable, '-m', 'pip', 'check'])
    (out / 'pip-after.log').write_text(pip_after.stdout + pip_after.stderr, encoding='utf8')
    source = {'phase': args.phase, 'head': HEAD, 'exit': result.returncode, 'seconds': seconds,
              'junit_or_vm': totals, 'sources': len(before['sources']), 'sources_stable': before['sources'] == after['sources'],
              'packages': len(before['packages']), 'packages_stable': before['packages'] == after['packages'],
              'readonly_browser_dependency_files': len(before['readonly_browser_dependencies']),
              'readonly_browser_dependencies_stable': before['readonly_browser_dependencies'] == after['readonly_browser_dependencies'],
              'pip_check_before_after': [pip_before.returncode, pip_after.returncode]}
    save(out / 'source.json', source)
    print(json.dumps(source))
    assert before == after and result.returncode == 0 and pip_after.returncode == 0
    assert totals['failure'] == totals['error'] == totals['skipped'] == 0


if __name__ == '__main__':
    main()
