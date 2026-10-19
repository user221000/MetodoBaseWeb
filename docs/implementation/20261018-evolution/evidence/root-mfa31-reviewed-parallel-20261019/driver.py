from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile

tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
root = Path(r'F:\MetodoBaseWeb-execution-20261018')
ev = root / 'docs/implementation/20261018-evolution/evidence'
phase = tmp / 'metodobase-mfa31-reviewed-parallel-20261019'
serial = ev / 'root-mfa31-reviewed-serial-20261019'
target = ev / 'root-mfa31-reviewed-parallel-20261019'
control = tmp / 'metodobase-mfa31-reviewed-parallel-seal-20261019'
private = tmp / 'metodobase-mfa31-reviewed-parallel-private-20261019'
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
assert not target.exists() and not control.exists() and not private.exists()
assert sha((serial / 'manifest.json').read_bytes()) == '7cdb18113d5ae118e8ac6c689a113645dd8c585420e9f0bda088c95ff584cb62'
sm = json.loads((serial / 'manifest.json').read_bytes())
for name, meta in sm.items():
    blob = (serial / name).read_bytes()
    assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256']
summary = json.loads((phase / 'summary.private.json').read_bytes())
assert summary['head'] == 'de506b6077ba055587f02e7d839387e7f5c56f84'
assert summary['mode'] == 'parallel' and summary['exit'] == 0 and not summary['failures'] and not summary['timed_out']
assert summary['cases'] == 3057 and summary['known_windows_skip_exact'] and len(summary['skips']) == 1
assert summary['sources_packages_python_exact'] and summary['pip_before'] == summary['pip_after'] == 0
assert (phase / 'before.json').read_bytes() == (phase / 'after.json').read_bytes()
cases = []
for node in ET.parse(phase / 'results.xml').findall('.//testcase'):
    assert node.find('error') is None and node.find('failure') is None
    cases.append({'case': node.get('classname', '') + '::' + node.get('name', ''), 'outcome': 'skipped' if node.find('skipped') is not None else 'passed'})
assert len(cases) == len({row['case'] for row in cases}) == 3057
assert sorted(cases, key=lambda row: row['case']) == sorted(json.loads((serial / 'all-cases.STRUCTURAL.json').read_bytes()), key=lambda row: row['case'])
preserved = json.loads((phase / 'case-preservation.json').read_bytes())
assert preserved['baseline3047_preserved'] and preserved['current3057_unique']
originals = {path.name: path.read_bytes() for path in phase.iterdir() if path.is_file()}
assert all(Path(name).suffix.lower() not in {'.db', '.env', '.sqlite', '.sqlite3'} for name in originals)
control.mkdir()
acl = (serial / 'archive-acl.ps1').read_text(encoding='utf8')
assert acl.count("$names = @('serial-originals.zip')") == 1
acl = acl.replace("$names = @('serial-originals.zip')", "$names = @('parallel-originals.zip')")
(control / 'archive-acl.ps1').write_bytes(acl.encode())

def protect(mode):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(control / 'archive-acl.ps1'), '-Mode', mode, '-PrivateRoot', str(private)], capture_output=True)
    (control / ('acl-' + mode + '.stdout.raw.log')).write_bytes(result.stdout)
    (control / ('acl-' + mode + '.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode == 0, mode
    return json.loads(result.stdout.decode('utf-8-sig'))

created = protect('create')
verified = protect('verify')
assert verified['verified_before_payload']
archive = private / 'parallel-originals.zip'
assert archive.stat().st_size == 0
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as handle:
    for name, blob in originals.items():
        handle.writestr(name, blob)
with zipfile.ZipFile(archive) as handle:
    assert set(handle.namelist()) == set(originals)
    assert all(handle.read(name) == blob for name, blob in originals.items())
final = protect('final')
assert all((phase / name).read_bytes() == blob for name, blob in originals.items())
definition = next(n for n in ast.parse((tmp / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
blobs = {'.gitattributes': b'* -text\n', 'driver.py': Path(__file__).read_bytes(),
    'summary.STRUCTURAL.json': enc({**{key: value for key, value in summary.items() if key != 'failures'}, 'passed': 3056, 'failure_count': 0, 'error_count': 0}),
    'all-cases.STRUCTURAL.json': enc(cases), 'case-preservation.RAW.json': (phase / 'case-preservation.json').read_bytes(),
    'before.RAW.json': (phase / 'before.json').read_bytes(), 'after.RAW.json': (phase / 'after.json').read_bytes(),
    'pip-before.RAW.log': (phase / 'pip-before.raw.log').read_bytes(), 'pip-after.RAW.log': (phase / 'pip-after.raw.log').read_bytes(),
    'archive-acl.ps1': (control / 'archive-acl.ps1').read_bytes(),
    'source.json': enc({'source': summary['head'], 'status': 'PASS_WEB31_N2_ONLY',
        'private_original_files': {name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in originals.items()},
        'private_archive': {'basename': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive.read_bytes()), 'members': len(originals)},
        'archive_ACL_created_verified_before_payload': verified, 'archive_ACL_final': final,
        'original_files_unchanged': True, 'original_directory_ACL_at_creation_attested': False,
        'serial_manifest_sha256': sha((serial / 'manifest.json').read_bytes()), 'same_3057_case_identities_and_outcomes_as_serial': True,
        'prior_3047_case_preservation': preserved, 'venv_python_hash_before_after': json.loads((phase / 'before.json').read_bytes())['python_sha256'],
        'python_base_executable_hash_not_observed_in_this_phase': True,
        'scope': 'Parallel n2 Windows web31 regression only. Duration is diagnostic, not an SLO. Coverage belongs to the separately sealed serial phase. No PostgreSQL, Redis, Chrome, Linux image, desktop or hosted Actions claim.'})}
for name, blob in blobs.items():
    scan(blob, name)
target.mkdir()
(target / '.gitattributes').write_bytes(blobs.pop('.gitattributes'))
for name, blob in blobs.items():
    with (target / name).open('xb') as handle:
        handle.write(blob)
manifest = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in target.iterdir() if path.is_file()}
(target / 'manifest.json').write_bytes(enc(manifest))
print(json.dumps({'files': len(manifest) + 1, 'source_sha256': sha((target / 'source.json').read_bytes()), 'manifest_sha256': sha((target / 'manifest.json').read_bytes()), 'private_original_files': len(originals)}))
