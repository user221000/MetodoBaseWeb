from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-execution-20261018')
TMP = Path(r'C:\Users\Consu\AppData\Local\Temp')
RUN = Path('docs/implementation/20261018-evolution')
EV = RUN/'evidence'
BASE = 'edf267ca9f44228620535c8a661c3196598c1b8d'
digest = lambda data: hashlib.sha256(data).hexdigest()
def git(wt, *args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=wt)
assert git(ROOT, 'rev-parse', 'HEAD').decode().strip() == BASE
assert not git(ROOT, 'status', '--porcelain', '--untracked-files=no')
definition = next(n for n in ast.parse((TMP/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
contents = {}
ledger = []
def remember(name, blob, provenance):
    path = Path(name)
    assert not path.is_absolute() and '..' not in path.parts
    assert path.as_posix().startswith(RUN.as_posix()+'/')
    scan(blob, path.as_posix())
    if name in contents:
        assert contents[name] == blob, name
    contents[name] = blob
    ledger.append({'path': name, 'bytes': len(blob), 'sha256': digest(blob), **provenance})

imports = [
    (r'F:\mb-security-terminal-sv-peer-20261019', 'df444cca5c226e670c49dcdf6c754a82dd88853b', None),
    (r'F:\mb-security-progress32-peer-20261019', '44abeaf864b4a52865703723e294ca4964d54516', None),
    (r'F:\mb-security-export-headers-peer-20261019', '2d703ddbe682c62c3fe895597ed68ae07ead627d', None),
    (r'F:\mb-r25-qa-ui-20261019', '2c8ee350aaa8d0d95b5c6346dc355b3efc3d0040', None),
    (r'F:\mb-r25-qa-ui-after-20261019', '2b686b9fb66f246be60800450e81850fe271e4ca', None),
    (r'F:\mb-r25-progress32-20261019', 'bd0501cdfbad1e48d483718b66e31bb65559f05e', None),
    (r'F:\mb-r25-progress-ui-20261019', '8dc91899c894a83fd0adb9ea0b2969d406b72ece', '809eab28'),
    (r'F:\mb-r25-privacy-headers-20261019', '2002959122f142162192a122fad7ba2cafbb12b1', None),
    (r'F:\mb-r25-table-layout-20261019', 'ef9dca7aa7d7008def92a5ec64b12f4585798fd7', None),
    (r'F:\mb-mfa31-contract-clock-20261019', '9abdabf5e1e7c2aa6b2c005cee15068a6ef9b9cb', None),
]
for location, commit, prior in imports:
    wt = Path(location)
    assert git(wt, 'rev-parse', commit).decode().strip() == commit
    parent = git(wt, 'rev-parse', prior or commit+'^').decode().strip()
    paths = git(wt, 'diff', '--name-only', '--diff-filter=AM', '-z', parent, commit, '--', RUN.as_posix()).decode().split('\0')[:-1]
    assert paths
    for name in paths:
        blob = git(wt, 'show', commit+':'+name)
        raw = (wt/name).read_bytes()
        if name.startswith(EV.as_posix()+'/'):
            assert raw == blob, ('evidence RAW differs from Git', name)
        remember(name, blob, {'kind': 'git-blob', 'source_commit': commit, 'source_base': parent,
                            'source_raw_sha256': digest(raw), 'raw_equals_git': raw == blob})

direct = [
    (r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\runtime31-c538-runtime72-diagnostic-public-20261019',
     '9dcfaa184e678f3280943816c90358a91c466c7e9235f49c60fa71b397a74151', '95480b218f7ee5af183f789fc0404ceb05f5b2df815559cf028c125978d298ad'),
    (r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\qa-runtime31-c538-acl-independent-public-20261019',
     'c52e2b217dc0bb2736f57df2439bb1eeda47905d971033207970199072d793c2', '5ba1974d43ac2232140f1686c2e7c6cca7abbef7a89b6ebb442461e5d5e5c794'),
    (r'F:\mb-qa-bootstrap-log-20261019\docs\implementation\20261018-evolution\evidence\qa-bootstrap-outcome-logging-independent-20261019',
     '5ffb29fd0497d4d53fdc5672c3ac0a3ae50b5dcb3ca00a7cb2446f2ecb40f5e3', 'a83d02aca01efb99f72a86411b58e8badc7e5e7999b45fdde3951ef110ab6314'),
    (r'F:\mb-qa-current31-clock-20261019\docs\implementation\20261018-evolution\evidence\qa-current31-fixture-clock-focal-independent-20261019',
     '1fe72ca867cf89a04c905308a154ba3702e2140ea0517fb637106b6808de045e', '04e41002cafe8dc9c5daf4b8a2f1fbb0469486064a98e9c390e328a16160924b'),
    (r'F:\mb-qa-current31-clock-20261019\docs\implementation\20261018-evolution\evidence\qa-current31-fixture-clock-pg34-independent-20261019',
     '8194be19ecb17a1f206ad4e9f9c41c901899624aefd009cd62b5232f3b1c69bf', 'e0a93fe15d7b6603b34060e02ae2648103f3d6277f8d56a65508174edf98d50b'),
]
for location, manifest_sha, source_sha in direct:
    folder = Path(location)
    assert digest((folder/'manifest.json').read_bytes()) == manifest_sha
    assert digest((folder/'source.json').read_bytes()) == source_sha
    manifest = json.loads((folder/'manifest.json').read_bytes())
    for name, row in manifest.items():
        assert set(row) == {'bytes', 'sha256'}
        path = folder/name
        assert path.resolve().is_relative_to(folder.resolve())
        blob = path.read_bytes()
        assert len(blob) == row['bytes'] and digest(blob) == row['sha256'], path
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            name = (EV/folder.name/path.relative_to(folder)).as_posix()
            remember(name, path.read_bytes(), {'kind': 'pinned-producer', 'manifest_sha256': manifest_sha,
                                              'source_sha256': source_sha})

prepared = EV/'prepared-wave125-20261019'
extras = {'driver.py': Path(__file__).read_bytes()}
for prefix in ['metodobase-r25-backend-compose-20261019', 'metodobase-r25-ui-compose-20261019',
               'metodobase-r25-focal-fixes-compose-20261019', 'metodobase-mfa31-runtime-terminal-compose-20261019']:
    folder = TMP/prefix
    assert folder.is_dir(), folder
    for path in sorted(folder.iterdir()):
        assert path.is_file()
        extras[prefix+'/'+path.name] = path.read_bytes()
for prefix in ['metodobase-mfa31-runtime-terminal-context-20261019', 'metodobase-mfa31-runtime-logging-context-20261019']:
    for name in ['driver.py', 'manifest.json']:
        extras[prefix+'/'+name] = (TMP/prefix/name).read_bytes()
for name in ['driver.py', 'receipt.json', 'shutdown.stderr.raw.log', 'shutdown.stdout.raw.log']:
    extras['vm-memory-handoff/'+name] = (TMP/'metodobase-vm-memory-handoff-20261019'/name).read_bytes()
extras['runtime-logging/source-context-freeze.json'] = (TMP/'metodobase-mfa31-runtime-logging-validation-20261019/source-context-freeze.json').read_bytes()
extras['ci-clock-preflight/review.json'] = (TMP/'metodobase-mfa31-fixture-clock-ci-preflight-20261019/review.json').read_bytes()
for name, blob in extras.items():
    remember((prepared/name).as_posix(), blob, {'kind': 'root-preparation'})
remember((prepared/'.gitattributes').as_posix(), b'* -text\n', {'kind': 'raw-attributes'})
payload = (json.dumps({'base': BASE, 'scope': 'Evidence import only; MAIN product remains schema30',
                       'git_sources': imports, 'producer_sources': direct, 'imports': ledger}, ensure_ascii=False, indent=2)+'\n').encode()
remember((prepared/'import-ledger.json').as_posix(), payload, {'kind': 'root-import-ledger'})
manifest = {Path(name).relative_to(prepared).as_posix(): {'bytes': len(blob), 'sha256': digest(blob)}
            for name, blob in contents.items() if Path(name).is_relative_to(prepared)}
remember((prepared/'manifest.json').as_posix(), (json.dumps(manifest, indent=2)+'\n').encode(), {'kind': 'root-manifest'})
# All authentication and scanning above precedes the first mutation.
for name, blob in sorted(contents.items(), key=lambda item: (Path(item[0]).name != '.gitattributes', item[0])):
    path = ROOT/name
    if path.exists():
        assert path.read_bytes() == blob, ('existing closed evidence differs', name)
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(blob)
receipt = {'base': BASE, 'files': {name: {'bytes': len(blob), 'sha256': digest(blob)} for name, blob in contents.items()}}
out = TMP/'metodobase-checkpoint125-import-result.json'
assert not out.exists()
out.write_bytes((json.dumps(receipt, indent=2)+'\n').encode())
print(json.dumps({'files': len(contents), 'import_provenance_rows': len(ledger), 'bytes': sum(map(len, contents.values())), 'receipt': str(out)}))
