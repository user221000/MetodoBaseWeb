from pathlib import Path
import hashlib
import json
import subprocess

tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
root = Path(r'F:\mb-progress32-retirement-composed-20261019')
first = tmp / 'metodobase-retirement32-common-compose-20261019'
second = tmp / 'metodobase-retirement32-common-finish-20261019'
out = tmp / 'metodobase-retirement32-common-verified-20261019'
base = '345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
head = '219f89a5ee0196061fea5b67e36ae07daf7f4316'
clock_base = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
refs = ['fcfb55e5849e0e20b568be8729dcc1b8c6b1762e', 'de216543a2eec05584168cdb888f627901b0e0b1', 'de506b6077ba055587f02e7d839387e7f5c56f84']
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.autocrlf=false', *args], cwd=root)
enc = lambda value: (json.dumps(value, indent=2) + '\n').encode()
sha = lambda blob: hashlib.sha256(blob).hexdigest()
assert not out.exists() and git('rev-parse', 'HEAD').decode().strip() == head
assert not git('diff', '--cached', '--name-only') and not git('diff', '--name-only')
changes = {ref: git('diff', '--name-only', '-z', clock_base if ref == refs[-1] else base, ref).decode().split('\0')[:-1] for ref in refs}
altered = set().union(*map(set, changes.values()))
before = json.loads((first / 'before.json').read_bytes())['Git_tree_entries']
after = {}
for row in git('ls-tree', '-r', '-z', head).split(b'\0'):
    if row:
        meta, name = row.split(b'\t', 1)
        after[name.decode()] = meta.decode()
assert set(after) == set(before) | altered
assert all(after[name] == meta for name, meta in before.items() if name not in altered)
for ref, names in changes.items():
    for name in names:
        blob = git('show', ref + ':' + name)
        assert git('show', head + ':' + name) == (root / name).read_bytes() == blob, name
corrections = json.loads((second / 'checkout-corrections-before.json').read_bytes())
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'status-before-index-stat-refresh.RAW.log').write_bytes(git('status', '--porcelain', '--untracked-files=no'))
names = sorted(corrections)
for offset in range(0, len(names), 20):
    git('add', '--', *names[offset:offset + 20])
assert git('write-tree').decode().strip() == git('rev-parse', 'HEAD^{tree}').decode().strip()
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'base': base, 'head': head, 'exact_changes_by_source': changes, 'other_Git_tree_entries_exact': len(set(before) - altered),
    'all_changed_working_bytes_equal_producer_Git_blobs': True, 'checkout_CRLF_only_corrections': corrections,
    'index_tree_unchanged_after_stat_refresh': True,
    'errata': ['Initial successful merges checked out CRLF on text files; first final byte assertion rejected those working bytes.',
        'Second preparation verified CRLF-only differences and restored exact GitLF bytes, then rejected stale index-stat modified markers despite empty actual diff.',
        'This successor independently verifies every producer blob and all unrelated Git entries, refreshes only the known corrected paths in the index, and verifies write-tree exactly equals HEAD tree. All initial drivers and controls remain immutable. No committed or semantic product change.'],
    'preparation_controls': {str(folder): {path.name: sha(path.read_bytes()) for path in folder.iterdir() if path.is_file()} for folder in [first, second]},
    'scope': 'Composition only; no browser, PostgreSQL, runtime or broad test attribution.'}
(out / 'receipt.json').write_bytes(enc(receipt))
print(json.dumps({'head': head, 'other_Git_tree_entries_exact': receipt['other_Git_tree_entries_exact'], 'working_bytes_Git_exact': True, 'index_tree_unchanged': True}))
