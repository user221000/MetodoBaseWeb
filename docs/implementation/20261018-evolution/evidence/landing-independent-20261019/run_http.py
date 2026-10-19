"""Landing real HTTP and independent runtime-catalog criterion; no product edits."""
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

ROOT = Path(r'F:\MetodoBaseWeb-landing-20261019')
OUT = Path(__file__).resolve().parent
HEAD = 'ad541ae6b8a7de18719c08b6584b5fdb47018e6c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def command(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf8', timeout=180, **kwargs)


def photo():
    assert command(['git', 'rev-parse', 'HEAD']).stdout.strip() == HEAD
    assert command(['git', 'status', '--porcelain']).stdout == ''
    selected = [path for path in command(['git', 'ls-files', '-z']).stdout.split('\0')
                if path and (not path.startswith('docs/') or '/evidence/landing/' in path or '/R29_LANDING_' in path)]
    return {'head': HEAD, 'sources': {path: sha(ROOT / path) for path in selected},
            'packages': sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions())}


before = photo(); save(OUT / 'before.json', before)
pip_before = command([sys.executable, '-m', 'pip', 'check'])
(OUT / 'pip-before.log').write_text(pip_before.stdout + pip_before.stderr, encoding='utf8')
assert pip_before.returncode == 0 and len(before['packages']) == 89
manifest = ROOT / 'docs/implementation/20261018-evolution/evidence/landing/source-freeze.json'
assert sha(manifest) == 'ced358945e60bbd1c9185c0ca454186b83221619ecf8270b7162d1ac93527529'
scratch = Path(tempfile.mkdtemp(prefix='metodobase-landing-http-independent-20261019-'))
test = scratch / 'test_landing_dynamic_review.py'
test.write_bytes((OUT / 'test_landing_dynamic_review.py.txt').read_bytes())
save(OUT / 'owned-temp.json', {'path': str(scratch), 'test_sha256': sha(test)})
environment = dict(os.environ)
for name in ['DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL']:
    environment.pop(name, None)
phases = []
for label, files in [('author12', ['tests/test_landing_commercial.py']), ('own-dynamic', [str(test)])]:
    target = OUT / label; target.mkdir(exist_ok=False)
    argv = [sys.executable, '-X', 'utf8', 'tests/run_isolated.py', *files, '-q', '--tb=short', '--junitxml=' + str(target / 'result.xml')]
    save(target / 'command.json', {'argv': argv, 'cwd': str(ROOT)})
    started = time.monotonic(); result = command(argv, env=environment)
    (target / 'result.log').write_text(result.stdout + result.stderr, encoding='utf8')
    tree = ET.parse(target / 'result.xml').getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
    totals = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    phase = {'label': label, 'exit': result.returncode, 'seconds': round(time.monotonic() - started, 3), 'junit': totals}
    save(target / 'summary.json', phase); phases.append(phase)
after = photo(); save(OUT / 'after.json', after)
pip_after = command([sys.executable, '-m', 'pip', 'check'])
(OUT / 'pip-after.log').write_text(pip_after.stdout + pip_after.stderr, encoding='utf8')
assert before == after and pip_after.returncode == 0
save(OUT / 'http-source.json', {'head': HEAD, 'sources': len(before['sources']), 'sources_stable': True,
                              'packages': len(before['packages']), 'packages_stable': True,
                              'pip_check_before_after': [0, 0], 'phases': phases,
                              'scope': 'Isolated real SQLite through both factories with no provider. Expected contract and observed red kept separate; no author/product mutation.'})
print(json.dumps({'sources': len(before['sources']), 'packages': len(before['packages']), 'phases': phases}))
assert phases[0]['junit'] == {'tests': 12, 'failures': 0, 'errors': 0, 'skipped': 0}
