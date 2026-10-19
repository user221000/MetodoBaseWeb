from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

root = Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
ev = Path('docs/implementation/20261018-evolution/evidence')
base = '5b8d06bcb30b1cb9c4e863f120213fc157604014'
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == base and not git('status', '--porcelain', '--untracked-files=no')
definition = next(n for n in ast.parse((tmp / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
contents = {}
ledger = []
snapshots = [
    ('fb488e809415fd84c487ec3e2cdca90d987befd3', 'security-google-subject-association-independent-20261019', '220e75c6dbf3680439c444d1cb329cdf9eeb48de1057ffd4bc1c65215fab57b0', '3b559189ebfb23dc84bd358ab93c927ff26f34e285783daef381d988207ea2fe', 18),
    ('fcfb55e5849e0e20b568be8729dcc1b8c6b1762e', 'backend-progress32-retirement-20261019', 'e89a6655d54bb3abd539884932ffb49dbbfaf9374d8fad9bb2e918cd622735eb', 'cbdc9bd6a68020d0f7a709b08355bec7e0fe92b31599f4074ef5348e18f6cedf', 68),
    ('de216543a2eec05584168cdb888f627901b0e0b1', 'progress-retirement-ui', None, None, 32),
    ('6147f9300989f4115cf8d270025a3805926d32b1', 'security-progress-retirement-independent-20261019', 'fe37709f7e1a81aff1d89e84505050fcd9b023401a0d86e17d6fc14c7d0d8b7a', '5712a237f753667012861098705d781b7c7d4ca0301f180f8dde08e490ac643f', 42)]
for ref, prefix, manifest_sha, source_sha, count in snapshots:
    folder = ev / prefix
    names = git('ls-tree', '-r', '--name-only', '-z', ref, '--', str(folder)).decode().split('\0')[:-1]
    assert len(names) == count, (prefix, len(names))
    files = {name: git('show', ref + ':' + name) for name in names}
    if manifest_sha:
        manifest_blob = files[(folder / 'manifest.json').as_posix()]
        assert sha(manifest_blob) == manifest_sha
        manifest = json.loads(manifest_blob)
        manifest = manifest.get('files', manifest)
        assert set(manifest).issubset({str(Path(name).relative_to(folder)).replace('\\', '/') for name in files})
        for name, meta in manifest.items():
            blob = files[(folder / name).as_posix()]
            assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256']
        assert sha(files[(folder / 'source.json').as_posix()]) == source_sha
    else:
        assert sha(files[(folder / 'final-source.json').as_posix()]) == '6812df0854d8890a502e1d82b491bf3fc6be95d676ec673bcc078807460f4a38'
    for name, blob in files.items():
        assert name not in contents
        contents[name] = blob
        ledger.append({'path': name, 'Git_commit': ref, 'bytes': len(blob), 'sha256': sha(blob)})
doc = 'docs/implementation/20261018-evolution/RETIRO_CONSENTIMIENTOS_UI.md'
contents[doc] = git('show', 'de216543a2eec05584168cdb888f627901b0e0b1:' + doc)
local = [
    ('root-mfa31-reviewed-serial-20261019', '7cdb18113d5ae118e8ac6c689a113645dd8c585420e9f0bda088c95ff584cb62', '3ec2f25c9db499a17bb06f27196b45f6452e3d6fa348fedf661dd016dc250354'),
    ('root-mfa31-reviewed-parallel-20261019', 'afea6a02b0d478cf7b71a750ca0304bc15597c89f776dd4cf7a5bdc5d47169ed', 'a245d5fd2849846bc5414d2f04c38cac0f33959e592845e765ec272128c63aa6')]
for prefix, manifest_sha, source_sha in local:
    folder = root / ev / prefix
    mb = (folder / 'manifest.json').read_bytes()
    assert sha(mb) == manifest_sha and sha((folder / 'source.json').read_bytes()) == source_sha
    manifest = json.loads(mb)
    assert set(path.relative_to(folder).as_posix() for path in folder.rglob('*') if path.is_file()) == set(manifest) | {'manifest.json'}
    for name, meta in manifest.items():
        blob = (folder / name).read_bytes()
        assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256']
    for path in folder.rglob('*'):
        if path.is_file():
            name = path.relative_to(root).as_posix()
            blob = path.read_bytes()
            assert name not in contents
            contents[name] = blob
            ledger.append({'path': name, 'source_manifest_sha256': manifest_sha, 'bytes': len(blob), 'sha256': sha(blob)})
prepared = ev / 'prepared-wave127-20261019'
anchors = ['metodobase-retirement32-common-compose-20261019', 'metodobase-retirement32-common-finish-20261019', 'metodobase-retirement32-common-verified-20261019', 'metodobase-worker31-successor-prepared-v2-20261019']
for prefix in anchors:
    folder = tmp / prefix
    for path in folder.rglob('*'):
        if path.is_file():
            name = (prepared / prefix / path.relative_to(folder)).as_posix()
            assert name not in contents
            contents[name] = path.read_bytes()
controls = {'.gitattributes': b'* -text\n', 'driver.py': Path(__file__).read_bytes(),
    'import-ledger.json': enc({'base': base, 'imports': ledger, 'scope': 'Frozen evidence and preparation only; MAIN product schema remains30. Worker successor payload is prepared, not executed. Composition attempts retain checkout/index-stat errata.'})}
controls['manifest.json'] = enc({name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in controls.items()})
for name, blob in controls.items():
    contents[(prepared / name).as_posix()] = blob
for name, blob in contents.items():
    scan(blob, name)
for name, blob in sorted(contents.items(), key=lambda item: (Path(item[0]).name != '.gitattributes', item[0])):
    path = root / name
    if path.exists():
        assert path.read_bytes() == blob, name
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(blob)
receipt = {'base': base, 'files': {name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in contents.items()}}
out = tmp / 'metodobase-checkpoint127-import-result.json'
assert not out.exists()
out.write_bytes(enc(receipt))
print(json.dumps({'files': len(contents), 'bytes': sum(map(len, contents.values())), 'receipt': str(out)}))
