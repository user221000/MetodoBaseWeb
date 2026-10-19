"""Compose exact terminal-session and native sources in a new local worktree."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

repo = Path(r'F:\mb-mfa31-compose-20261019')
root = Path(r'F:\mb-mfa31-runtime-terminal-20261019')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
out = tmp / 'metodobase-mfa31-runtime-terminal-compose-20261019'
base = 'c5386ebaab835b72af692a0d74e9b78ed5c8f511'
fixed = '6a75d096ea3d63d9e78c76d33b7e243160b23364'

def git(*args, cwd=repo):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)

def inventory(ref, cwd=repo):
    result = {}
    for row in git('ls-tree', '-r', '-z', ref, cwd=cwd).split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        result[name.decode('utf-8')] = metadata.decode('ascii')
    return result

assert git('rev-parse', 'HEAD').decode().strip() == fixed
assert not git('status', '--porcelain', '--untracked-files=no')
assert not root.exists() and not out.exists()
assert git('merge-base', base, fixed).decode().strip() == '809eab28c40c112cb6e3c9d8caceebae28683abd'
changes = set(git('diff-tree', '--no-commit-id', '--name-only', '-z', '-r', fixed).decode().split('\0')[:-1])
assert changes == {'web/services/mfa_service.py', 'web/static/js/mfa-ui.js', 'tests/test_mfa31_terminal_session_version.py'}
before = inventory(base)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.json').write_bytes((json.dumps({'base': base, 'fixed': fixed, 'Git_tree_entries': before}, indent=2) + '\n').encode())

def command(label, args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    (out / (label + '.stdout.raw.log')).write_bytes(result.stdout)
    (out / (label + '.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode == 0, label

command('worktree', ['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '-b',
    'implementation/mfa31-runtime-terminal-20261019', str(root), base], repo)
command('merge', ['git', 'merge', '--no-edit', fixed], root)
head = git('rev-parse', 'HEAD', cwd=root).decode().strip()
after = inventory(head, root)
assert set(after) == set(before) | changes
assert all(after[name] == metadata for name, metadata in before.items() if name not in changes)
assert all(git('show', head + ':' + name, cwd=root) == git('show', fixed + ':' + name) for name in changes)
assert not git('status', '--porcelain', '--untracked-files=no', cwd=root)
assert git('rev-parse', 'HEAD').decode().strip() == fixed
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'head': head, 'runtime_base': base, 'terminal_session_source': fixed,
    'changed_paths_exact': sorted(changes), 'other_Git_tree_entries_exact': len(set(before) - changes),
    'common_running_regression_worktree_unchanged': True,
    'runtime_built': False, 'VM_mutated': False,
    'scope': 'Prepared local source only. SEC15 independent peer, broad regression and same-image acceptance remain pending.'}
(out / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())

old = (tmp / 'metodobase-runtime72-context-prepare.py').read_text(encoding='utf-8')
assert old.count("F:\\mb-mfa31-runtime72-20261019") == 1
new = old.replace("F:\\mb-mfa31-runtime72-20261019", str(root))
new = new.replace("metodobase-mfa31-runtime72-context-20261019", "metodobase-mfa31-runtime-terminal-context-20261019")
assert new.count(base) == 1
new = new.replace(base, head)
assert new.count("'app_base':'809eab28c40c112cb6e3c9d8caceebae28683abd'") == 1
new = new.replace("'app_base':'809eab28c40c112cb6e3c9d8caceebae28683abd'", "'app_base':'" + fixed + "'")
ast.parse(new)
target = tmp / 'metodobase-runtime-terminal-context-prepare.py'
with target.open('xb') as stream:
    stream.write(new.encode('utf-8'))
receipt['context_driver_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
# Keep the original receipt immutable; this file adds the derived context driver.
(out / 'context-prepared.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
