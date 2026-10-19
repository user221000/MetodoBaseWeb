"""Run the same real CLI cases before/after with scoped byte/environment photos."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root = Path(r'F:\mb-bootstrap-log-20261019')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
phase = 'integration'
out = tmp / ('metodobase-bootstrap-log-' + phase + '-20261019')
assert not out.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
names = subprocess.check_output(['git', 'ls-files', '-z', 'web/database/alembic',
    'web/database/schema_control.py', 'web/database/tenant_policy.py', 'web/database/engine.py',
    'db_bootstrap.py', 'alembic.ini', 'tests/isolation.py', 'tests/run_isolated.py', 'tests/conftest.py'], cwd=root).decode().split('\0')[:-1]
names.extend(['tests/test_bootstrap_outcome_logging.py', 'tests/test_database_migrations.py', 'tests/test_migrator_connection.py', 'tests/test_migration_role_contract_review.py'])

def photo():
    return {'source_RAW_sha256': {name: sha((root / name).read_bytes()) for name in sorted(names)},
        'packages': sorted((item.metadata['Name'], item.version) for item in importlib.metadata.distributions()),
        'python_sha256': sha(Path(sys.executable).read_bytes())}

main = Path(r'F:\MetodoBaseWeb-execution-20261018')
closed = main / 'docs/implementation/20261018-evolution/evidence/root-mfa31-composed-serial-diagnostic-20261019'
manifest_raw = (closed / 'manifest.json').read_bytes()
assert sha(manifest_raw) == 'c20836dcf9c6b72ab1c4a1125d37e56d7164e3dc9001977bed831cb94636b80c'
case_raw = (closed / 'all-cases.STRUCTURAL.json').read_bytes()
assert sha(case_raw) == json.loads(manifest_raw)['all-cases.STRUCTURAL.json']['sha256']
modules = {'tests.test_database_migrations', 'tests.test_migrator_connection', 'tests.test_migration_role_contract_review'}
historical_ids = {row['case'] for row in json.loads(case_raw) if row['case'].split('::',1)[0] in modules}
expected_ids = historical_ids | {
 'tests.test_bootstrap_outcome_logging::test_cli_reports_post_alembic_failure_without_private_exception_details',
 'tests.test_bootstrap_outcome_logging::test_cli_reports_success_only_after_schema_verification',
}
assert len(historical_ids) == 34 and len(expected_ids) == 36

out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
before = photo()
(out / 'before.json').write_bytes((json.dumps(before, indent=2) + '\n').encode())
for moment in ['before']:
    pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
    (out / ('pip-' + moment + '.raw.log')).write_bytes(pip.stdout + pip.stderr)
    assert pip.returncode == 0
environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
for key in ['DATABASE_URL', 'MIGRATOR_DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_REDIS_URL', '_METODOBASE_TEST_ROOT']:
    environment.pop(key, None)
command = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py', 'tests/test_bootstrap_outcome_logging.py', 'tests/test_database_migrations.py', 'tests/test_migrator_connection.py', 'tests/test_migration_role_contract_review.py',
    '-q', '--tb=short', '--junitxml=' + str(out / 'results.xml'), '--basetemp=' + str(out / 'pytest_tmp')]
start = time.monotonic()
result = subprocess.run(command, cwd=root, env=environment, capture_output=True, timeout=240)
(out / 'stdout.private.raw.log').write_bytes(result.stdout)
(out / 'stderr.private.raw.log').write_bytes(result.stderr)
after = photo()
(out / 'after.json').write_bytes((json.dumps(after, indent=2) + '\n').encode())
pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(out / 'pip-after.raw.log').write_bytes(pip.stdout + pip.stderr)
cases = ET.parse(out / 'results.xml').findall('.//testcase')
failed = [case for case in cases if case.find('failure') is not None]
errors = [case for case in cases if case.find('error') is not None]
summary = {'phase': phase, 'exit': result.returncode, 'seconds': time.monotonic() - start,
    'cases': len(cases), 'failed': len(failed), 'errors': len(errors),
    'scoped_sources': len(names), 'packages': len(before['packages']), 'source_environment_exact': before == after,
    'test_sha256': before['source_RAW_sha256']['tests/test_bootstrap_outcome_logging.py'],
    'scope': 'Actual SQLite CLI migration success and failed29-to30 rollback; scoped source photos only, no PostgreSQL/image/broad claim.'}
(out / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(json.dumps(summary))
assert before == after and pip.returncode == 0 and not errors
assert {case.get('classname', '')+'::'+case.get('name', '') for case in cases} == expected_ids
assert result.returncode == 0 and not failed
