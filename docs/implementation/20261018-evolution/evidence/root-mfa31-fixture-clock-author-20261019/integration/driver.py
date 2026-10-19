"""Run one immutable fixture boundary phase; retain the original broad error."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root = Path(r'F:\mb-mfa31-clock-fixture-20261019')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
phase = 'integration'
out = tmp / ('metodobase-mfa31-fixture-clock-' + phase + '-20261019')
assert not out.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
names = subprocess.check_output(['git', 'ls-files', '-z', 'api', 'web', 'core', 'tests'], cwd=root).decode().split('\0')[:-1]
names.append('tests/test_current_mfa31_fixture_clock.py')

def photo():
    return {'source_RAW_sha256': {name: sha((root / name).read_bytes()) for name in sorted(names)},
        'packages': sorted((item.metadata['Name'], item.version) for item in importlib.metadata.distributions()),
        'python_sha256': sha(Path(sys.executable).read_bytes())}

closed = Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/root-mfa31-composed-serial-diagnostic-20261019')
manifest_raw = (closed / 'manifest.json').read_bytes()
assert sha(manifest_raw) == 'c20836dcf9c6b72ab1c4a1125d37e56d7164e3dc9001977bed831cb94636b80c'
old_raw = (closed / 'all-cases.STRUCTURAL.json').read_bytes()
assert sha(old_raw) == json.loads(manifest_raw)['all-cases.STRUCTURAL.json']['sha256']
expected_ids = {row['case'] for row in json.loads(old_raw) if row['case'].startswith('tests.test_publication_diary_consumption::')}
assert len(expected_ids) == 29
expected_ids |= {case.get('classname','')+'::'+case.get('name','') for case in ET.parse(tmp / 'metodobase-mfa31-fixture-clock-before-20261019/results.xml').findall('.//testcase')}
assert len(expected_ids) == 31

out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
before = photo()
(out / 'before.json').write_bytes((json.dumps(before, indent=2) + '\n').encode())
pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(out / 'pip-before.raw.log').write_bytes(pip.stdout + pip.stderr)
assert pip.returncode == 0
environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
for key in ['DATABASE_URL', 'MIGRATOR_DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_REDIS_URL', '_METODOBASE_TEST_ROOT']:
    environment.pop(key, None)
command = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py', 'tests/test_current_mfa31_fixture_clock.py', 'tests/test_publication_diary_consumption.py',
    '-q', '--tb=short', '--junitxml=' + str(out / 'results.xml')]
start = time.monotonic()
result = subprocess.run(command, cwd=root, env=environment, capture_output=True, timeout=240)
(out / 'stdout.private.raw.log').write_bytes(result.stdout)
(out / 'stderr.private.raw.log').write_bytes(result.stderr)
after = photo()
(out / 'after.json').write_bytes((json.dumps(after, indent=2) + '\n').encode())
pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(out / 'pip-after.raw.log').write_bytes(pip.stdout + pip.stderr)
cases = ET.parse(out / 'results.xml').findall('.//testcase')
errors = [case for case in cases if case.find('error') is not None]
failed = [case for case in cases if case.find('failure') is not None]
summary = {'phase': phase, 'exit': result.returncode, 'seconds': time.monotonic() - start,
    'cases': len(cases), 'errors': len(errors), 'failures': len(failed),
    'scoped_source_files': len(names), 'packages': len(before['packages']), 'source_environment_exact': before == after,
    'test_sha256': before['source_RAW_sha256']['tests/test_current_mfa31_fixture_clock.py'],
    'scope': 'Actual SQLite31/factory HTTP with a controlled generation-to-arrival counter crossing. No auth/endpoint override; no claim of original broad clock telemetry.'}
(out / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(json.dumps(summary))
assert before == after and pip.returncode == 0 and len(cases) == 31 and not failed
assert result.returncode == 0 and not errors
assert {case.get('classname','')+'::'+case.get('name','') for case in cases} == expected_ids
