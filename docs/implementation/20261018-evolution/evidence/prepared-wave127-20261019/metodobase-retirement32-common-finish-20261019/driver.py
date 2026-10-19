from pathlib import Path
import hashlib
import json
import subprocess

tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
first = tmp / 'metodobase-retirement32-common-compose-20261019'
out = tmp / 'metodobase-retirement32-common-finish-20261019'
root = Path(r'F:\mb-progress32-retirement-composed-20261019')
repo = Path(r'F:\mb-r25-reviewed32-20261019')
base = '345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
clock_base = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
refs = ['fcfb55e5849e0e20b568be8729dcc1b8c6b1762e', 'de216543a2eec05584168cdb888f627901b0e0b1', 'de506b6077ba055587f02e7d839387e7f5c56f84']
git = lambda *args, cwd=root: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, indent=2) + '\n').encode()
assert not out.exists()
assert git('rev-parse', 'HEAD', cwd=repo).decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')
head = git('rev-parse', 'HEAD').decode().strip()
before = json.loads((first / 'before.json').read_bytes())['Git_tree_entries']
changes = {ref: git('diff', '--name-only', '-z', clock_base if ref == refs[-1] else base, ref).decode().split('\0')[:-1] for ref in refs}
altered = set().union(*map(set, changes.values()))
after = {}
for row in git('ls-tree', '-r', '-z', head).split(b'\0'):
    if row:
        meta, name = row.split(b'\t', 1)
        after[name.decode()] = meta.decode()
assert set(after) == set(before) | altered
assert all(after[name] == meta for name, meta in before.items() if name not in altered)
corrections = {}
for ref, names in changes.items():
    for name in names:
        blob = git('show', ref + ':' + name)
        assert git('show', head + ':' + name) == blob
        current = (root / name).read_bytes()
        if current != blob:
            assert current.replace(b'\r\n', b'\n') == blob, name
            corrections[name] = {'before_bytes': len(current), 'before_sha256': sha(current), 'GitLF_bytes': len(blob), 'GitLF_sha256': sha(blob)}
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'checkout-corrections-before.json').write_bytes(enc(corrections))
for name in corrections:
    blob = git('show', head + ':' + name)
    (root / name).write_bytes(blob)
for ref, names in changes.items():
    for name in names:
        assert (root / name).read_bytes() == git('show', ref + ':' + name), name
assert not git('-c', 'core.autocrlf=false', 'status', '--porcelain', '--untracked-files=no')
receipt = {'base': base, 'head': head, 'exact_changes_by_source': changes, 'other_Git_tree_entries_exact': len(set(before) - altered),
    'checkout_line_endings_corrected_to_GitLF': corrections,
    'erratum': 'Initial composition merged successfully but its final working-byte assertion detected CRLF checkout conversion. Worktree-add had core.autocrlf=false only for that command; subsequent merges used the inherited setting. Initial driver/logs remain immutable. This successor verifies CRLF-only differences before restoring exact Git blobs in this owned worktree. No semantic code or committed blob changed.',
    'scope': 'Composition only. Schema32 unchanged; no runtime, browser, PostgreSQL or broad result attributed.'}
(out / 'receipt.json').write_bytes(enc(receipt))
print(json.dumps({'head': head, 'other_Git_tree_entries_exact': receipt['other_Git_tree_entries_exact'], 'CRLF_only_checkout_corrections': len(corrections)}))
