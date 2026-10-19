from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

root = Path(r'F:\mb-retirement32-owned-cleanup-20261019')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
phase = tmp / 'metodobase-retirement32-cleanup-author-20261019'
base = '219f89a5ee0196061fea5b67e36ae07daf7f4316'
prefix = 'docs/implementation/20261018-evolution/evidence/root-retirement32-owned-cleanup-20261019'
folder = root / prefix
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.autocrlf=false', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, indent=2) + '\n').encode()
assert not folder.exists() and git('rev-parse', 'HEAD').decode().strip() == base
route = 'web/routes/progress_retirement.py'
test = 'tests/test_progress_retirement_cleanup.py'
assert set(git('diff', '--name-only', '-z').decode().split('\0')[:-1]) == {route}
before = git('show', base + ':' + route)
after = (root / route).read_bytes()
old_doc = b'    The prior context is restored even after admission/commit uncertainty.\n'
new_doc = old_doc + b'    If session cleanup fails before releasing its connection, invalidate only\n    this owned session before restoring that context. A cleanup failure still\n    returns the unconfirmed result, including after a confirmed commit.\n'
old_body = b'        with SessionLocal() as db:\n            return service.perform(db, command, operation=operation)\n'
new_body = b'        db = SessionLocal()\n        try:\n            return service.perform(db, command, operation=operation)\n        finally:\n            try:\n                db.close()\n            except Exception:  # noqa: BLE001 -- discard only this owned connection on cleanup failure\n                try:\n                    db.invalidate()\n                except Exception as cleanup_error:  # noqa: BLE001 -- preserve the original unconfirmed result\n                    logger.error("Consent retirement invalidation class=%s", type(cleanup_error).__name__)\n                raise\n'
assert after.count(new_doc) == after.count(new_body) == 1
assert after.replace(new_doc, old_doc).replace(new_body, old_body) == before
assert sha((root / test).read_bytes()) == '1002b027643932e0579eb5cf46b264ec46f129aea9f0f4346be0b579f7bd757a'
summary = json.loads((phase / 'summary.json').read_bytes())
assert summary['exit'] == 0 and len(summary['cases']) == 6 and all(row['outcome'] == 'passed' for row in summary['cases'])
assert summary['sources_packages_python_exact'] and summary['pip_before'] == summary['pip_after'] == 0
assert (phase / 'before.json').read_bytes() == (phase / 'after.json').read_bytes()
blobs = {'.gitattributes': b'* -text\n', 'freeze-driver.py': Path(__file__).read_bytes(),
    'author-driver.py': (phase / 'driver.py').read_bytes(), 'summary.RAW.json': (phase / 'summary.json').read_bytes(),
    'before.RAW.json': (phase / 'before.json').read_bytes(), 'after.RAW.json': (phase / 'after.json').read_bytes(),
    'route-before.GitLF.py': before, 'pip-before.RAW.log': (phase / 'pip-before.RAW.log').read_bytes(), 'pip-after.RAW.log': (phase / 'pip-after.RAW.log').read_bytes(),
    'source.json': enc({'base': base, 'status': 'AUTHOR_SQLITE_FOCAL_PASS_PEER_PENDING', 'product': {route: sha(after)},
        'maintained_test': {test: sha((root / test).read_bytes())}, 'route_inverse_to_base_exact': True,
        'original_case_expectations_unchanged': True, 'original_SQLite_and_PG_reds_remain_immutable': '6147f9300989f4115cf8d270025a3805926d32b1',
        'author_cases': 6, 'sources': summary['sources'], 'packages': summary['packages'],
        'private_original_files': {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in phase.iterdir() if path.is_file()},
        'scope': 'Only the new retirement Session gets an invalidation fallback after close fails. No engine dispose, ambient Session retagging, auth expansion or schema change. No actual driver failure or exploit demonstrated. Original runner directory ACL at creation not attested. Independent PG pool1 review pending.'})}
definition = next(n for n in ast.parse((tmp / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
for name, blob in blobs.items():
    scan(blob, name)
folder.mkdir()
(folder / '.gitattributes').write_bytes(blobs.pop('.gitattributes'))
for name, blob in blobs.items():
    with (folder / name).open('xb') as handle:
        handle.write(blob)
manifest = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in folder.iterdir() if path.is_file()}
(folder / 'manifest.json').write_bytes(enc(manifest))
names = [route, test] + [(folder / name).relative_to(root).as_posix() for name in list(manifest) + ['manifest.json']]
git('add', '-f', '--', *names)
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names)
for name in names:
    assert git('show', ':' + name) == (root / name).read_bytes()
subprocess.run(['git', '-c', 'core.autocrlf=false', 'diff', '--cached', '--check'], cwd=root, check=True, capture_output=True)
subprocess.run(['git', '-c', 'core.autocrlf=false', 'commit', '-m', 'Invalidate owned retirement session when cleanup fails before release'], cwd=root, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
print(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), 'files': len(names), 'source_sha256': sha((folder / 'source.json').read_bytes()), 'manifest_sha256': sha((folder / 'manifest.json').read_bytes())}))
