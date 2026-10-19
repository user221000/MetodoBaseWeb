"""Run existing UI assertions on the composed candidate after presentation-only changes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(r'F:\mb-mfa31-compose-20261019')
OUT = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa-ui31-copy-check-20261019')
HEAD = 'da34304aaf9066f45c6fc854cfd81d00e2fbc581'
NODE = r'C:\Program Files\nodejs\node.exe'
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == HEAD and not git('status', '--porcelain', '--untracked-files=no')
OUT.mkdir(exist_ok=False)
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
names = git('ls-files', '-z', '--', 'web', 'api', 'core', 'config', 'src', 'tests').decode().split('\0')[:-1]


def photo():
    return {'files': {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
            'packages': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
            'node': hashlib.sha256(Path(NODE).read_bytes()).hexdigest()}


before = photo()
(OUT / 'before.json').write_bytes((json.dumps(before, indent=2) + '\n').encode())
env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHON_DOTENV_DISABLED': '1'}
for key in ['DATABASE_URL', 'MIGRATOR_DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL',
            'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_REDIS_URL', '_METODOBASE_TEST_ROOT']:
    env.pop(key, None)


def run(name, command):
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=180, check=False)
    (OUT / (name + '.stdout.private.log')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.private.log')).write_bytes(result.stderr)
    return {'name': name, 'exit': result.returncode, 'seconds': time.monotonic() - started}


commands = [(name, [NODE, 'tests/e2e/' + name + '.cjs']) for name in ['mfa_api', 'mfa_state', 'mfa_consumers', 'mfa_prompt']]
commands.append(('pages_http', [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py', 'tests/test_mfa_ui_pages.py',
                             'tests/test_mfa_ui_login_labels.py', 'tests/test_mfa_ui_http_bridge.py',
                             '-q', '--tb=short', '--junitxml=' + str(OUT / 'pages-http.xml')]))
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(lambda entry: run(*entry), commands))
after = photo()
(OUT / 'after.json').write_bytes((json.dumps(after, indent=2) + '\n').encode())
vm = {}
for name, _command in commands[:-1]:
    data = json.loads((OUT / (name + '.stdout.private.log')).read_bytes())
    assert isinstance(data['total'], int) and data['total'] >= 8 and data['passed'] == data['total']
    vm[name] = {'total': data['total'], 'passed': data['passed']}
cases = ET.fromstring((OUT / 'pages-http.xml').read_bytes()).findall('.//testcase')
counts = {tag: sum(case.find(tag) is not None for case in cases) for tag in ['failure', 'error', 'skipped']}
summary = {'head': HEAD, 'results': results, 'VM': vm, 'HTTP_SSR_cases': len(cases), 'HTTP_SSR_counts': counts,
           'source_files': len(names), 'packages': len(before['packages']), 'sources_packages_node_quiet': before == after,
           'scope': 'Existing author tests replayed on root composed candidate after20literal replacements in3UI files. Not independent QA, full regression, browser, PostgreSQL, provider or accessibility acceptance.'}
(OUT / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(json.dumps(summary))
assert before == after and all(row['exit'] == 0 for row in results)
assert counts == {'failure': 0, 'error': 0, 'skipped': 0} and len(cases) == 14
