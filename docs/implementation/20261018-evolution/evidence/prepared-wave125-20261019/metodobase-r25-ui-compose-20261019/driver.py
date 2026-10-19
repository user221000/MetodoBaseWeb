"""Compose the frozen progress UI with backend32; preserve both authors' trees."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(r'F:\mb-r25-composed32-20261019')
author = Path(r'F:\mb-r25-progress-ui-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r25-ui-compose-20261019')
before_head = 'e5f90e3f3bb054529e5733e9ebe587e1d434a4cc'
ui = '8dc91899c894a83fd0adb9ea0b2969d406b72ece'
ui_base = '809eab28c40c112cb6e3c9d8caceebae28683abd'
prefix = 'docs/implementation/20261018-evolution/evidence/r25-ui/'
sha = lambda data: hashlib.sha256(data).hexdigest()

def git(*args, cwd=root):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)

def inventory(ref):
    result = {}
    for row in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            result[name.decode()] = metadata.decode()
    return result

assert not out.exists()
assert git('rev-parse', 'HEAD').decode().strip() == before_head
assert not git('status', '--porcelain', '--untracked-files=no')
assert git('rev-parse', 'HEAD', cwd=author).decode().strip() == ui
assert not git('status', '--porcelain', '--untracked-files=no', cwd=author)
manifest_raw = (author / (prefix + 'functional-source.json')).read_bytes()
assert sha(manifest_raw) == '08f4724a2fd5cda23adfe6885df1cd7e3841ea17dfcef54434acc4af7b030f0f'
assert git('show', ui + ':' + prefix + 'functional-source.json') == manifest_raw
manifest = json.loads(manifest_raw)
expected = set().union(*map(set, manifest['inventory'].values()))
changes = set(git('diff', '--name-only', '-z', ui_base, ui).decode().split('\0')[:-1])
assert len(changes) == 82 and len(expected) == 30
assert {name for name in changes if not name.startswith(prefix)} == expected
assert set(manifest['files']) == expected
for name, record in manifest['files'].items():
    assert sha(git('show', ui + ':' + name)) == record['git_lf_sha256'], name
    assert sha((author / name).read_bytes()) == record['raw_sha256'], name
before = inventory(before_head)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.json').write_bytes((json.dumps({'head': before_head, 'ui': ui, 'Git_tree_entries': before}, indent=2) + '\n').encode())
result = subprocess.run(['git', 'merge', '--no-edit', ui], cwd=root, capture_output=True)
(out / 'merge.stdout.raw.log').write_bytes(result.stdout)
(out / 'merge.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode == 0
head = git('rev-parse', 'HEAD').decode().strip()
after = inventory(head)
assert set(after) == set(before) | changes
assert all(after[name] == metadata for name, metadata in before.items() if name not in changes)
assert all(git('show', head + ':' + name) == git('show', ui + ':' + name) for name in changes)
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'head': head, 'backend_composition': before_head, 'ui_source': ui,
    'ui_changed_paths_exact': 82, 'ui_product_paths': 18, 'ui_test_paths': 10,
    'other_Git_tree_entries_exact': len(set(before) - changes),
    'author_manifest_sha256': sha(manifest_raw),
    'scope': 'Prepared common32 with exact frozen API and UI only; no HTTP, browser, PG, broad or independent acceptance inferred.'}
(out / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
