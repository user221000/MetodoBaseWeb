"""Prepare backend32 over the frozen common31 without editing the broad run."""
from pathlib import Path
import hashlib
import json
import subprocess

repo = Path(r'F:\mb-mfa31-compose-20261019')
author = Path(r'F:\mb-r25-progress32-20261019')
root = Path(r'F:\mb-r25-composed32-20261019')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
out = tmp / 'metodobase-r25-backend-compose-20261019'
base = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
backend = 'bd0501cdfbad1e48d483718b66e31bb65559f05e'
prefix = 'docs/implementation/20261018-evolution/evidence/backend-r25-progress32-20261019/'
sha = lambda data: hashlib.sha256(data).hexdigest()

def git(*args, cwd=repo):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)

def inventory(ref):
    result = {}
    for row in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            result[name.decode()] = metadata.decode()
    return result

assert not root.exists() and not out.exists()
assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')
assert git('rev-parse', 'HEAD', cwd=author).decode().strip() == backend
assert not git('status', '--porcelain', '--untracked-files=no', cwd=author)
freeze_raw = (author / (prefix + 'source-freeze.json')).read_bytes()
assert sha(freeze_raw) == '9ed37bf31493d538c0f4e23390f09c3b90947c56db94dc4d1251365a5149793e'
assert git('show', backend + ':' + prefix + 'source-freeze.json') == freeze_raw
freeze = json.loads(freeze_raw)
changes = set(git('diff-tree', '--no-commit-id', '--name-only', '-z', '-r', backend).decode().split('\0')[:-1])
product = {row['path'] for row in freeze['sources']}
assert len(product) == 29 and len(changes) == 49
assert {name for name in changes if not name.startswith(prefix)} == product
for row in freeze['sources']:
    blob = git('show', backend + ':' + row['path'])
    assert sha(blob) == row['LF_sha256'], row['path']
    assert sha((author / row['path']).read_bytes()) == row['RAW_sha256'], row['path']
mount = json.loads((tmp / 'metodobase-r25-router-mount-20261019/receipt.json').read_bytes())
for name, record in mount['sources'].items():
    assert sha(git('show', backend + ':' + name)) == record['after_GitLF_sha256']
    assert sha((author / name).read_bytes()) == record['after_RAW_sha256']
before = inventory(base)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.json').write_bytes((json.dumps({'common_base': base, 'backend': backend, 'Git_tree_entries': before}, indent=2) + '\n').encode())

def run(label, command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True)
    (out / (label + '.stdout.raw.log')).write_bytes(result.stdout)
    (out / (label + '.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode == 0, label

run('worktree', ['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '-b',
    'implementation/r25-composed32-20261019', str(root), base], repo)
run('merge', ['git', 'merge', '--no-edit', backend], root)
head = git('rev-parse', 'HEAD', cwd=root).decode().strip()
after = inventory(head)
assert set(after) == set(before) | changes
assert all(after[name] == metadata for name, metadata in before.items() if name not in changes)
assert all(git('show', head + ':' + name) == git('show', backend + ':' + name) for name in changes)
assert not git('status', '--porcelain', '--untracked-files=no', cwd=root)
assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'head': head, 'common31_source': base, 'backend32_source': backend,
    'backend_changed_paths_exact': 49, 'backend_product_paths_exact': 29,
    'other_Git_tree_entries_exact': len(set(before) - changes),
    'root_two_router_mounts_exact': True, 'common_running_broad_unchanged': True,
    'frontend_integrated': False, 'HTTP_or_QA_or_SEC_acceptance': False,
    'scope': 'Prepared isolated source only. Frozen author lease-exclusivity wording remains an explicitly pending correction.'}
(out / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
