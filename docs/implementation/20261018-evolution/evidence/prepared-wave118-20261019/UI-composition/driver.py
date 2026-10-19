"""Compose the frozen author UI into the isolated reviewed MFA backend."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(r'F:\mb-mfa31-compose-20261019')
TMP = Path(r'C:\Users\Consu\AppData\Local\Temp')
OUT = TMP / 'metodobase-mfa-ui31-compose-20261019'
BASE = '913cb66061ac754ad09344fc24e8f769b5722997'
INCOMING = '087c807cc777d553f3fe5d28fb2a723758d695a9'


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


preflight_blob = (TMP / 'metodobase-mfa-ui31-compose-preflight-20261019/receipt.json').read_bytes()
assert hashlib.sha256(preflight_blob).hexdigest() == '5bd4603af4e0a01368e59873855b69ddcb29af9684df1dc40ee7d1bf59844c6b'
preflight = json.loads(preflight_blob)
assert preflight['status'] == 'PREFLIGHT_PASS' and preflight['base'] == BASE and preflight['incoming'] == INCOMING
assert git('rev-parse', 'HEAD').decode().strip() == BASE and not git('status', '--porcelain', '--untracked-files=no')
OUT.mkdir(exist_ok=False)
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
expected_tree = git('merge-tree', '--write-tree', BASE, INCOMING).decode().strip()
result = subprocess.run(['git', 'merge', '--no-commit', '--no-ff', INCOMING], cwd=ROOT, capture_output=True)
(OUT / 'merge.stdout.log').write_bytes(result.stdout)
(OUT / 'merge.stderr.log').write_bytes(result.stderr)
assert result.returncode == 0
assert git('write-tree').decode().strip() == expected_tree
source = json.loads(git('show', INCOMING + ':docs/implementation/20261018-evolution/evidence/mfa-ui31/source.json'))
expected = {**source['ui_product13'], **source['vm_tests5'], **source['new_test_fixture_sources']}
assert len(expected) == 24
changed = git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]
assert {n for n in changed if not n.startswith('docs/')} == set(expected)
for name in expected:
    assert git('show', ':' + name) == git('show', INCOMING + ':' + name)
for name in ['api/routes/pagos.py', 'web/services/mfa_service.py', 'web/services/mfa_actions.py',
             'web/middleware/security_headers.py', 'web/database/schema_control.py']:
    assert git('show', ':' + name) == git('show', BASE + ':' + name)
subprocess.run(['git', 'diff', '--cached', '--check', '--', *expected], cwd=ROOT, check=True, capture_output=True)
result = subprocess.run(['git', 'commit', '-m', 'Compose frozen MFA account and privileged action UI for independent review'],
                        cwd=ROOT, capture_output=True)
(OUT / 'commit.stdout.log').write_bytes(result.stdout)
(OUT / 'commit.stderr.log').write_bytes(result.stderr)
assert result.returncode == 0
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'before': BASE, 'incoming': INCOMING, 'head': git('rev-parse', 'HEAD').decode().strip(),
           'tree_exact_automatic_merge': True, 'manual_conflicts': 0, 'UI_product13_and_tests11_exact_incoming': True,
           'backend5_exact_before': True, 'preflight_sha256': hashlib.sha256(preflight_blob).hexdigest(),
           'scope': 'Isolated candidate composition only. Author VM/HTTP/browser scopes remain on their original freezes. No new execution or independent UI acceptance by this merge.'}
(OUT / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
