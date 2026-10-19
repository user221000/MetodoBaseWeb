import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

root = Path('F:/mb-mfa-ci31-20261019')
out = Path(__file__).resolve().parent / 'frozen-source-gates'
out.mkdir(exist_ok=False)
sys.path.insert(0, str(root))
from tests.run_reviewed_ci30 import trusted_baseline
from tests.ci_mfa31.publish import xml_projection, scan

git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=root)
head = git('rev-parse', 'HEAD').decode().strip()
assert head == 'e0c3f8b6d7a812c2b46d73748d56da72782c9f04'
assert not git('status', '--porcelain').strip()
changed = git('diff', '--name-only', '4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae', head).decode().splitlines()
assert len(changed) == 33
assert all(name == '.github/workflows/ci.yml' or name.startswith('tests/') for name in changed)
baseline = trusted_baseline()
locks = [name.decode() for name in git('ls-files', '-z').split(b'\0') if name.endswith(b'.lock') and not name.startswith(b'docs/')]
for name in locks:
    assert git('show', head + ':' + name) == git('show', '4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae:' + name)
names = sorted(set(changed) | set(baseline['helpers23_sha256']) | set(locks))
before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
packages = sorted((dist.metadata['Name'], dist.version) for dist in importlib.metadata.distributions() if dist.metadata['Name'])
records = []
def run(label, command, timeout=120):
    result = subprocess.run(command, cwd=root, capture_output=True, timeout=timeout)
    (out / (label + '.private.stdout.log')).write_bytes(result.stdout)
    (out / (label + '.private.stderr.log')).write_bytes(result.stderr)
    records.append({'gate': label, 'exit': result.returncode, 'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                    'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
    assert result.returncode == 0, label
    return result.stdout
run('trust-plus-preserved-tests', [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py',
    'tests/test_mfa31_ci_trust.py', 'tests/test_member_ci_trust.py', 'tests/test_history_index_ci_trust.py',
    'tests/test_followup_ci_trust.py', 'tests/test_followup_ci_process.py', '-q', '--tb=short',
    '--junitxml=' + str(out / 'trust.private.xml')])
projected = xml_projection((out / 'trust.private.xml').read_bytes())
scan(projected)
(out / 'trust-public.xml').write_bytes(projected)
run('ruff-undefined', [sys.executable, '-X', 'utf8', '-B', 'tests/check_quality.py', 'lint'])
run('static-final', [sys.executable, '-X', 'utf8', '-B', 'tests/verify_mfa31_ci.py', '--verify-only',
    '--output', str(out / 'static-final')])
for name in changed:
    if name.endswith('.py'):
        compile((root / name).read_bytes(), name, 'exec')
    if name.endswith('.cjs'):
        run('node-check-' + Path(name).stem, ['C:/Program Files/nodejs/node.exe', '--check', name])
after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
assert before == after and not git('status', '--porcelain').strip()
assert packages == sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions() if d.metadata['Name'])
report = {'source': head, 'product_source_equivalent_to_root': '4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae',
    'changed_CI_files_only': changed, 'helpers23_unchanged': True, 'lock_files_unchanged': locks,
    'file_sha256_before_after_identical': before, 'distribution_metadata_inventory': packages,
    'distribution_inventory_scope': 'Name/version metadata, not a full byte hash of installed package trees',
    'records': records, 'scope': 'Offline Windows source/AST/parser/owned inert checks; no PG/Chrome/image/Actions'}
(out / 'receipt.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
print(json.dumps({'source': head, 'gates': len(records), 'sources_quiet': True, 'locks': len(locks), 'package_metadata': len(packages)}))
