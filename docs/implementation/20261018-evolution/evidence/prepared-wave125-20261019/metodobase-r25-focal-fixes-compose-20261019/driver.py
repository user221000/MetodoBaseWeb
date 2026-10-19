"""Prepare the two reviewed R25 corrections without touching any measured tree."""
from pathlib import Path
import hashlib
import json
import subprocess

repo = Path(r'F:\mb-r25-composed32-20261019')
root = Path(r'F:\mb-r25-reviewed32-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r25-focal-fixes-compose-20261019')
base = 'b7f8e129251dfd5216f811ba77d0b6183ca76735'
fixes = [
    ('2002959122f142162192a122fad7ba2cafbb12b1',
     {'web/middleware/security_headers.py', 'tests/test_progress32_export_privacy_headers.py'},
     'docs/implementation/20261018-evolution/evidence/backend-r25-export-private-headers-20261019/',
     'source.json', '8bb645d7b00373eb031b25f516ac0a7824c14e82752cb131adcb55a3be9b18bb'),
    ('ef9dca7aa7d7008def92a5ec64b12f4585798fd7', {'web/static/css/progreso.css'},
     'docs/implementation/20261018-evolution/evidence/r25-table-layout/',
     'freeze.json', '6576370da3cadfc901fc42f2cf621eba020ee7e33d879c12b74a600fc6e13862'),
]
git = lambda *args, cwd=repo: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)
sha = lambda data: hashlib.sha256(data).hexdigest()
assert not root.exists() and not out.exists()
assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')
def inventory(ref):
    result = {}
    for row in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            result[name.decode()] = metadata.decode()
    return result
changes_by_source = {}
for ref, allowed, prefix, attestation, digest in fixes:
    assert git('rev-parse', ref + '^').decode().strip() == base
    names = set(git('diff-tree', '--no-commit-id', '--name-only', '-z', '-r', ref).decode().split('\0')[:-1])
    assert {name for name in names if not name.startswith(prefix)} == allowed
    assert sha(git('show', ref + ':' + prefix + attestation)) == digest
    changes_by_source[ref] = sorted(names)
assert not set(changes_by_source[fixes[0][0]]) & set(changes_by_source[fixes[1][0]])
before = inventory(base)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.json').write_bytes((json.dumps({'base': base, 'Git_tree_entries': before}, indent=2) + '\n').encode())
def run(label, command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True)
    (out / (label + '.stdout.raw.log')).write_bytes(result.stdout)
    (out / (label + '.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode == 0, label
run('worktree', ['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '-b',
    'implementation/r25-reviewed32-20261019', str(root), base], repo)
for index, (ref, *_rest) in enumerate(fixes):
    run('merge-' + str(index), ['git', 'merge', '--no-edit', ref], root)
head = git('rev-parse', 'HEAD', cwd=root).decode().strip()
after = inventory(head)
changes = set().union(*map(set, changes_by_source.values()))
assert set(after) == set(before) | changes
assert all(after[name] == metadata for name, metadata in before.items() if name not in changes)
for ref, names in changes_by_source.items():
    assert all(git('show', head + ':' + name) == git('show', ref + ':' + name) for name in names)
assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')
assert not git('status', '--porcelain', '--untracked-files=no', cwd=root)
receipt = {'head': head, 'base': base, 'exact_changes_by_source': changes_by_source,
    'other_Git_tree_entries_exact': len(set(before) - changes), 'previous_measured_tree_unchanged': True,
    'scope': 'Prepared isolated32 only; QA must replay the same two privacy and four mobile layout canaries. No automatic reattribution of the earlier browser or broad runs.'}
(out / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps({key: value for key, value in receipt.items() if key != 'exact_changes_by_source'}))
