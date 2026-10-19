"""Replay the unchanged independent criterion with explicit author test composition."""
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
before = json.loads((OUT / 'before.json').read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def photo():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == before['head']
    return {'sources': {path: sha(ROOT / path) for path in before['sources']},
            'packages': sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions())}


start = photo()
assert start['sources'] == before['sources'] and start['packages'] == before['packages']
scratch = Path(tempfile.mkdtemp(prefix='metodobase-landing-own-composition-20261019-'))
test = scratch / 'test_landing_dynamic_review.py'
test.write_bytes((OUT / 'test_landing_dynamic_review.py.txt').read_bytes())
target = OUT / 'own-dynamic-with-composition'; target.mkdir(exist_ok=False)
environment = dict(os.environ)
for name in ['DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL']:
    environment.pop(name, None)
argv = [sys.executable, '-X', 'utf8', 'tests/run_isolated.py', '-p', 'conftest', str(test),
        '-q', '--tb=short', '--junitxml=' + str(target / 'result.xml')]
result = subprocess.run(argv, cwd=ROOT, env=environment, capture_output=True, text=True, encoding='utf8', timeout=90)
(target / 'result.log').write_text(result.stdout + result.stderr, encoding='utf8')
tree = ET.parse(target / 'result.xml').getroot()
suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
totals = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
end = photo(); assert start == end
proof = {'head': before['head'], 'argv': argv, 'junit': totals, 'exit': result.returncode,
         'sources': len(start['sources']), 'sources_stable': True, 'packages': len(start['packages']), 'packages_stable': True,
         'criterion_byte_identical': sha(test) == sha(OUT / 'test_landing_dynamic_review.py.txt'),
         'initial_harness_error': 'External Temp test did not discover author root conftest. Initial2 setup errors preserved. Explicit -p conftest provides accepted real SQLite metadata and per-case cleanup; no criterion changed.'}
with (target / 'source.json').open('x', encoding='utf8') as stream:
    json.dump(proof, stream, indent=2); stream.write('\n')
print(json.dumps(proof))
assert totals['tests'] == 2 and totals['errors'] == totals['skipped'] == 0
