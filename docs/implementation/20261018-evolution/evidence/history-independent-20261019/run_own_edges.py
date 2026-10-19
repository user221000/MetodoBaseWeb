"""Run the eight pre-fix-frozen independent page-edge criteria on corrected57."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(r'F:\MetodoBaseWeb-history-ui-20261019')
OUT = Path(__file__).resolve().parent
HEAD = '57cdc0d51848203bdd89c0b9f0f3c426f1b285d8'
target = OUT / 'own8-57cdc0d'; target.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    with (target / name).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')


def photo():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True) == ''
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT, text=True).split('\0')
    selected = [path for path in paths if path and (not path.startswith('docs/') or '/evidence/history-' in path)]
    return {'head': HEAD, 'sources': {path: sha(ROOT / path) for path in selected},
            'packages': sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions())}


frozen = json.loads((OUT / 'partial-manifest.json').read_text())
assert all(sha(OUT / path) == expected for path, expected in frozen['files'].items())
before = photo(); save('before.json', before)
assert len(before['packages']) == 89
scratch = Path(tempfile.mkdtemp(prefix='metodobase-history-own8-20261019-'))
test = scratch / 'test_history_edges_review.py'
test.write_bytes((OUT / 'test_history_edges_review.py.txt').read_bytes())
environment = dict(os.environ)
for name in ['DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL',
             'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_HISTORY_EXPLAIN_OUTPUT']:
    environment.pop(name, None)
argv = [sys.executable, '-X', 'utf8', 'tests/run_isolated.py', '-p', 'conftest', str(test),
        '-q', '--tb=short', '--junitxml=' + str(target / 'result.xml')]
save('command.json', {'argv': argv, 'cwd': str(ROOT), 'source_sha256': sha(test),
                      'scope': 'Explicit accepted root fixture plugin; fresh real SQLite, providers disabled.'})
result = subprocess.run(argv, cwd=ROOT, env=environment, capture_output=True, text=True, encoding='utf8', timeout=180)
(target / 'result.log').write_text(result.stdout + result.stderr, encoding='utf8')
tree = ET.parse(target / 'result.xml').getroot()
suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
totals = {name: sum(int(suite.attrib.get(name, 0)) for suite in suites) for name in ['tests', 'failures', 'errors', 'skipped']}
after = photo(); save('after.json', after); assert before == after
assert sha(test) == frozen['files']['test_history_edges_review.py.txt']
pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, encoding='utf8', timeout=30)
(target / 'pip-after.log').write_text(pip.stdout + pip.stderr, encoding='utf8'); assert pip.returncode == 0
summary = {'head': HEAD, 'exit': result.returncode, 'junit': totals, 'sources': len(before['sources']),
           'sources_stable': True, 'packages': 89, 'packages_stable': True, 'pip_check_after': 0,
           'own_criteria_byte_identical_to_frozen_prefix': True,
           'scope': '50/51 frontier, older/newer live insert and deleted NULL-position continuation through both real factories; no security/74/VM suite repeated.'}
save('summary.json', summary)
print(json.dumps(summary))
assert result.returncode == 0 and totals == {'tests': 8, 'failures': 0, 'errors': 0, 'skipped': 0}
