"""Replay exactly the two frozen dynamic-period criteria against the one-phrase fix."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(r'F:\MetodoBaseWeb-landing-20261019')
OUT = Path(__file__).resolve().parent
HEAD = '55f72149e7e05d032b5a865c664fb13070eb3df6'
target = OUT / 'period55-after'; target.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    with (target / name).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')


original = json.loads((OUT / 'before.json').read_text())
old_manifest = json.loads((OUT / 'partial-manifest.json').read_text())
assert all(sha(OUT / path) == value for path, value in old_manifest['files'].items())


def photo():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True) == ''
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT, text=True).split('\0')
    selected = [path for path in paths if path and (not path.startswith('docs/') or '/evidence/landing/' in path or '/evidence/landing-period-note/' in path)]
    return {'head': HEAD, 'sources': {path: sha(ROOT / path) for path in selected},
            'packages': sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions())}


before = photo(); save('before.json', before)
changed = [path for path, value in original['sources'].items() if sha(ROOT / path) != value]
assert changed == ['web/templates/landing.html']
scratch = Path(tempfile.mkdtemp(prefix='metodobase-landing-period-after-20261019-'))
test = scratch / 'test_landing_dynamic_review.py'
test.write_bytes((OUT / 'test_landing_dynamic_review.py.txt').read_bytes())
assert sha(test) == old_manifest['files']['test_landing_dynamic_review.py.txt']
environment = dict(os.environ)
for name in ['DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL']:
    environment.pop(name, None)
argv = [sys.executable, '-X', 'utf8', 'tests/run_isolated.py', '-p', 'conftest', str(test), '-q', '--tb=short',
        '--junitxml=' + str(target / 'result.xml')]
save('command.json', {'argv': argv, 'cwd': str(ROOT), 'criterion_sha256': sha(test)})
result = subprocess.run(argv, cwd=ROOT, env=environment, capture_output=True, text=True, encoding='utf8', timeout=90)
(target / 'result.log').write_text(result.stdout + result.stderr, encoding='utf8')
tree = ET.parse(target / 'result.xml').getroot()
suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
totals = {name: sum(int(suite.attrib.get(name, 0)) for suite in suites) for name in ['tests', 'failures', 'errors', 'skipped']}
after = photo(); save('after.json', after); assert before == after
pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, encoding='utf8', timeout=30)
(target / 'pip-after.log').write_text(pip.stdout + pip.stderr, encoding='utf8'); assert pip.returncode == 0
summary = {'head': HEAD, 'junit': totals, 'exit': result.returncode,
           'sources': len(before['sources']), 'sources_stable': True, 'packages': len(before['packages']),
           'packages_stable': True, 'pip_check_after': 0, 'only_previously_frozen_source_changed': changed,
           'original_criterion_and_red_evidence_unchanged': True,
           'scope': 'Neutral note now defers currency, amount and billing period to each card. Synthetic year/TST mutation probes binding only; no annual offer/support/purchase claim. No original12 HTTP replay.'}
save('summary.json', summary); print(json.dumps(summary))
assert result.returncode == 0 and totals == {'tests': 2, 'failures': 0, 'errors': 0, 'skipped': 0}
