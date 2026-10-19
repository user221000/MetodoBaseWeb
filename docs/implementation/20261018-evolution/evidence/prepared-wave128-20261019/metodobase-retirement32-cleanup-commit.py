from pathlib import Path
import hashlib
import json
import subprocess

root = Path(r'F:\mb-retirement32-owned-cleanup-20261019')
base = '219f89a5ee0196061fea5b67e36ae07daf7f4316'
prefix = 'docs/implementation/20261018-evolution/evidence/root-retirement32-owned-cleanup-20261019'
folder = root / prefix
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.autocrlf=false', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
assert git('rev-parse', 'HEAD').decode().strip() == base
manifest = json.loads((folder / 'manifest.json').read_bytes())
for name, meta in manifest.items():
    blob = (folder / name).read_bytes()
    assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256']
names = ['web/routes/progress_retirement.py', 'tests/test_progress_retirement_cleanup.py'] + [prefix + '/' + name for name in list(manifest) + ['manifest.json']]
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names)
for name in names:
    assert git('show', ':' + name) == (root / name).read_bytes()
check = subprocess.run(['git', '-c', 'core.autocrlf=false', 'diff', '--cached', '--check'], cwd=root, capture_output=True)
expected = b''.join((prefix + '/' + name + ':1: trailing whitespace.\n+No broken requirements found.\r\n').encode() for name in ['pip-after.RAW.log', 'pip-before.RAW.log'])
assert check.returncode == 2 and check.stdout == expected and not check.stderr
subprocess.run(['git', '-c', 'core.autocrlf=false', 'diff', '--cached', '--check', '--', *names[:2]], cwd=root, check=True, capture_output=True)
subprocess.run(['git', '-c', 'core.autocrlf=false', 'commit', '-m', 'Invalidate owned retirement session when cleanup fails before release'], cwd=root, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
receipt = {'head': git('rev-parse', 'HEAD').decode().strip(), 'files': len(names),
    'source_sha256': sha((folder / 'source.json').read_bytes()), 'manifest_sha256': sha((folder / 'manifest.json').read_bytes()),
    'erratum': 'Initial freeze/stage succeeded; whole-diff whitespace gate rejected exactly the two byte-preserved pip RAW CRLF lines. This commit authenticates unchanged manifest/staged bytes, requires exactly those diagnostics and checks both source paths without exception. RAW logs are not normalized.'}
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-retirement32-cleanup-commit-receipt.json')
assert not out.exists()
out.write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
