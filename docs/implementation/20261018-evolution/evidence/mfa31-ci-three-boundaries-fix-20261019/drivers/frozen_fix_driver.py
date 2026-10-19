"""Own offline receipt for the frozen CI31 three-boundary correction."""
import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-mfa-ci31-20261019')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'frozen-source-gates'
OUT.mkdir(exist_ok=False)
HEAD = 'ed4a3be11fb1e921962182812362b515afd8885a'
BASE = 'e0c3f8b6d7a812c2b46d73748d56da72782c9f04'
PRODUCT = '4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae'
sys.path.insert(0, str(ROOT))
from tests import verify_mfa31_ci as verifier
from tests.ci_mfa31 import run_current_browser as controller
from tests.ci_mfa31.publish import scan, xml_projection
from tests.run_reviewed_ci30 import trusted_baseline

git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
digest = lambda raw: hashlib.sha256(raw).hexdigest()
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert not git('status', '--porcelain').strip()
baseline = trusted_baseline()
names = [n.decode() for n in git('ls-files', '-z').split(b'\0') if n and not n.startswith(b'docs/')]
photo = lambda: {name: digest((ROOT / name).read_bytes()) for name in names}
packages = lambda: sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())
before, package_before = photo(), packages()
assert len(package_before) == 89
locks = [name for name in names if name.endswith('.lock')]
assert len(locks) == 8
for name in locks + list(baseline['helpers23_sha256']):
    assert git('show', HEAD + ':' + name) == git('show', BASE + ':' + name)
for name in ['tests/check_mfa31_reports.py', 'tests/ci_mfa31/current-report-nodeids.json']:
    assert git('show', HEAD + ':' + name) == git('show', BASE + ':' + name)
changed = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
assert len(changed) == 11 and all(n == '.github/workflows/ci.yml' or n.startswith('tests/') for n in changed)
product_delta = git('diff', '--name-only', PRODUCT, HEAD).decode().splitlines()
assert len(product_delta) == 33 and all(n == '.github/workflows/ci.yml' or n.startswith('tests/') for n in product_delta)
environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
                   METODOBASE_CI_BASH='C:/Program Files/Git/bin/bash.exe')
records = []


def run(label, command, *, cwd=ROOT, expected=0, timeout=180):
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, timeout=timeout)
    (OUT / (label + '.private.stdout.log')).write_bytes(result.stdout)
    (OUT / (label + '.private.stderr.log')).write_bytes(result.stderr)
    records.append({'gate': label, 'exit': result.returncode, 'expected': expected,
                    'stdout_sha256': digest(result.stdout), 'stderr_sha256': digest(result.stderr)})
    assert result.returncode == expected, (label, result.returncode)
    return result


run('pip-check', [sys.executable, '-B', '-m', 'pip', 'check'])
run('full-verifier', [sys.executable, '-X', 'utf8', '-B', 'tests/verify_mfa31_ci.py',
    '--output', str(OUT / 'full-review')])
raw = (OUT / 'full-review/parser-canaries.xml').read_bytes()
tree = ET.fromstring(raw)
assert len(tree.findall('.//testcase')) == 205
assert not any(tree.findall('.//' + tag) for tag in ('failure', 'error', 'skipped'))
public = xml_projection(raw)
scan(public)
(OUT / 'trust-projected.xml').write_bytes(public)

# Repeat the independently reported main-only mutation without editing source.
shadow = OUT / 'main-only-mutant'
(shadow / 'tests').mkdir(parents=True)
source = (ROOT / 'tests/check_mfa31_reports.py').read_text(encoding='utf8')
function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
lines = source.splitlines(keepends=True)
mutant = ''.join(lines[:function.lineno - 1]) + 'def main() -> int:\n    return 0\n' + ''.join(lines[function.end_lineno:])
checker = shadow / 'tests/check_mfa31_reports.py'
checker.write_bytes(mutant.encode())
(shadow / 'tests/verify_mfa31_ci.py').write_bytes((ROOT / 'tests/verify_mfa31_ci.py').read_bytes())
empty = OUT / 'empty-reports'
empty.mkdir()
run('actual-empty-cli', [sys.executable, '-X', 'utf8', '-B', 'tests/check_mfa31_reports.py',
                        '--directory', str(empty)], expected=1)
run('mutant-empty-cli-false-success', [sys.executable, '-X', 'utf8', '-B', str(checker),
                                     '--directory', str(empty)], cwd=shadow)
reject = run('mutant-full-verifier-rejected-before-import', [sys.executable, '-X', 'utf8', '-B',
             'tests/verify_mfa31_ci.py', '--output', str(OUT / 'must-not-be-created')], cwd=shadow, expected=1)
assert b'report checker executable differs' in reject.stderr
assert not (OUT / 'must-not-be-created').exists()

marker = {'pid': 123, 'runtime_revision': '20261019_mfa', 'model_tables': 32, 'actual_tables': 33}
try:
    controller.validate_pg_marker(marker, 123)
except KeyError:
    pass
else:
    raise AssertionError('Missing role witness accepted')
controller.validate_pg_marker(dict(marker, application_role_restricted_nonowner=True), 123)

workflow = verifier.expected_workflow()
mutated = copy.deepcopy(workflow)
step = next(s for s in mutated['jobs']['frontend-contracts']['steps'] if 'MFA31 transport' in s.get('name', ''))
step['run'] = '\n'.join(line for line in step['run'].splitlines() if 'daily_plan_snapshot.cjs' not in line
                        and 'daily-plan-snapshot-current31.json' not in line)
try:
    verifier.verify_workflow(mutated)
except ValueError:
    pass
else:
    raise AssertionError('Omitted snapshot accepted')
run('ruff', [sys.executable, '-X', 'utf8', '-B', 'tests/check_quality.py', 'lint'])
for name in changed:
    if name.endswith('.py'):
        compile((ROOT / name).read_bytes(), name, 'exec')
after = photo()
assert before == after and package_before == packages()
assert not git('status', '--porcelain').strip()
receipt = {'source': HEAD, 'preserved_e0': BASE, 'product_equivalent_to': PRODUCT,
    'changed_files': changed, 'tracked_non_evidence_files_quiet': len(names), 'source_sha256_before_after': before,
    'helpers23_unchanged': True, 'locks8_unchanged': locks, 'checker_and173_nodeids_unchanged': True,
    'package_inventory89_name_versions_only': package_before, 'python_sha256': digest(Path(sys.executable).read_bytes()),
    'new_tests': 205, 'CLI_negative_subprocesses': 132, 'CLI_positive173_subprocess': 1,
    'SQL_role_fragment_mock_cases': 24, 'missing_role_witness_rejected': True,
    'main_only_mutant_false_success_reproduced_then_verifier_rejected': True,
    'snapshot_only_workflow_omission_rejected': True, 'records': records,
    'scope': 'Offline Windows AST/CLI/parser and owned inert child tests. No PG, Chrome, image, Linux permissions or Actions execution.'}
raw = (json.dumps(receipt, indent=2) + '\n').encode()
scan(raw)
(OUT / 'receipt.json').write_bytes(raw)
print(json.dumps({'source': HEAD, 'source_quiet': True, 'tests': 205, 'gates': len(records),
                  'receipt_sha256': digest(raw)}))
