"""Review and compose opt-in current31 fixture adoption; preserve old business assertions."""
from pathlib import Path
from collections import Counter
import ast
import hashlib
import json
import re
import subprocess

ROOT = Path(r'F:\mb-mfa31-compose-20261019')
OUT = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-fixture-compose-v2-20261019')
BASE = 'c66902f39e64d0aa501392dfecd0a77660540fea'
INCOMING = 'e2f1d2f349387555f23e4acc184e8093aae10e57'
AUTHOR_BASE = '913cb66061ac754ad09344fc24e8f769b5722997'
PREFIX = 'docs/implementation/20261018-evolution/evidence/backend-mfa31-fixture-adoption'
SHA = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args, **kwargs: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, **kwargs)


def scan(blob, name):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])', blob):
        start = match.start()
        assert not (start >= 30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}', blob[start-30:start])), name
    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+|otpauth://totp/[^\s\x22\x27]+\?secret=[A-Z2-7]{16,}', blob), name


assert git('rev-parse', 'HEAD').decode().strip() == BASE and not git('status', '--porcelain', '--untracked-files=no')
freeze_blob = git('show', INCOMING + ':' + PREFIX + '/freeze.json')
assert SHA(freeze_blob) == 'ff524d818c9da668f6c059d493f23fc6cce4ecb9bc5e278da8c030031ba34d59'
freeze = json.loads(freeze_blob)
assert freeze['base'] == AUTHOR_BASE and freeze['source_commit_tested'] == 'dab090679a48cb8b064804a13622c415db0a170b'
proofs = {}
for name, meta in freeze['proof_files'].items():
    path = PREFIX + '/' + name
    blob = git('show', INCOMING + ':' + path)
    assert len(blob) == meta['bytes'] and SHA(blob) == meta['sha256'], name
    scan(blob, name)
    assert not name.lower().endswith(('.zip', '.tar', '.gz')), 'Expanded archive verification required before merge'
    proofs[path] = meta
for name, meta in freeze['source_hashes'].items():
    blob = git('show', INCOMING + ':' + name)
    assert SHA(blob) == meta['git_lf_sha256'], name
    scan(blob, name)
changed = git('diff', '--name-only', '-z', AUTHOR_BASE, INCOMING).decode().split('\0')[:-1]
assert {name for name in changed if not name.startswith('docs/')} == set(freeze['source_hashes'])
assert len(freeze['source_hashes']) == 5
assert all(name in proofs or name == PREFIX + '/freeze.json' or name in freeze['source_hashes'] for name in changed)
for name in ['conftest.py', 'web/database/schema_control.py', 'web/services/mfa_service.py', 'web/services/mfa_actions.py']:
    assert git('show', AUTHOR_BASE + ':' + name) == git('show', INCOMING + ':' + name), name
assert git('show', INCOMING + ':' + PREFIX + '/.gitattributes') == b'* -text\n'

assertions = {}
for name in ['tests/test_team_invitation_contract.py', 'tests/test_team_entitlement_review.py', 'tests/test_personal_diary_security_review.py']:
    old = ast.parse(git('show', AUTHOR_BASE + ':' + name))
    new = ast.parse(git('show', INCOMING + ':' + name))
    after_functions = {node.name: node for node in new.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    preserved = 0
    changed_asserts = 0
    for function in [node for node in old.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        assert function.name in after_functions
        expected = [node for node in ast.walk(function) if isinstance(node, ast.Assert)]
        available = Counter(ast.dump(node, include_attributes=False) for node in ast.walk(after_functions[function.name]) if isinstance(node, ast.Assert))
        for node in expected:
            original = ast.dump(node, include_attributes=False)
            if available[original]:
                available[original] -= 1
                preserved += 1
            else:
                assert name.endswith('test_team_invitation_contract.py') and function.name == 'test_team_mutations_never_cross_to_another_gym'
                assert ast.unparse(node) == 'assert response.status_code == 404'
                replacement = ast.dump(ast.parse('assert response.status_code == 403').body[0], include_attributes=False)
                assert available[replacement] == 1
                available[replacement] -= 1
                changed_asserts += 1
    assertions[name] = {'original_asserts_exact': preserved, 'approved_status_assert_changes': changed_asserts}
assert sum(row['approved_status_assert_changes'] for row in assertions.values()) == 1
assert sum(row['original_asserts_exact'] for name, row in assertions.items() if 'team_' in name) == 110
assert assertions['tests/test_personal_diary_security_review.py'] == {'original_asserts_exact': 66, 'approved_status_assert_changes': 0}
OUT.mkdir(exist_ok=False)
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
(OUT / 'freeze.json').write_bytes(freeze_blob)
expected_tree = git('merge-tree', '--write-tree', BASE, INCOMING).decode().strip()
result = subprocess.run(['git', 'merge', '--no-commit', '--no-ff', INCOMING], cwd=ROOT, capture_output=True)
(OUT / 'merge.stdout.log').write_bytes(result.stdout)
(OUT / 'merge.stderr.log').write_bytes(result.stderr)
assert result.returncode == 0 and git('write-tree').decode().strip() == expected_tree
staged = git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]
assert {name for name in staged if not name.startswith('docs/')} == set(freeze['source_hashes'])
for name in staged:
    assert git('show', ':' + name) == git('show', INCOMING + ':' + name), name
subprocess.run(['git', 'diff', '--cached', '--check', '--', *freeze['source_hashes']], cwd=ROOT, check=True, capture_output=True)
subprocess.run(['git', 'commit', '-m', 'Compose real MFA fixture adoption while retaining business denials'], cwd=ROOT, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'before': BASE, 'incoming': INCOMING, 'head': git('rev-parse', 'HEAD').decode().strip(),
           'tree_exact_automatic_merge': True, 'manual_conflicts': 0, 'test_files': 5, 'proof_files_exact': len(proofs),
           'assertions': assertions, 'product_conftest_targets_and_CI_changed': False,
           'author_174_scope': 'Author174/174 onDAB, no new test execution by this composition; all92 initial diagnostic case IDs retained. Its72initial passes were69auth/billing+3standalone team.',
           'root_review': 'Read every changed test/helper and causal ADR. Local opt-in only: real password/enrollment/TOTP/recovery login/exact grants, business always sent even after denied grant. Existing global primary-only control preserved. One404→403 assert over3cases changes precedence, with added opacity/integrity assertions; no MFA bypass or product repair.'}
receipt['assert_inventory_scope'] = 'Root counts all module functions including invite helper:110of111 original team/entitlement asserts exact plus1 approved status change. Author109of110 covers test functions only and excludes that unchanged helper assertion. Diary66of66 exact. No semantic assertion filter or comparison changed.'
(OUT / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
