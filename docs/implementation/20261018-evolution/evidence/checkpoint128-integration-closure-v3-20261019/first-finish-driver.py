from pathlib import Path
import hashlib
import json
import subprocess

root = Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
run = root / 'docs/implementation/20261018-evolution'
base = '1be3b671b106bee6447ea47377d2596fde12d0b1'
candidate = '2273616eb218adfdd30680e111da50a4599a8c53'
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.autocrlf=false', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == base
receipt = json.loads((tmp / 'metodobase-checkpoint128-prepare-result.json').read_bytes())
for name, meta in receipt['files'].items():
    blob = (root / name).read_bytes()
    assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256']
for name in receipt['source_paths']:
    assert git('show', ':' + name) == (root / name).read_bytes() == git('show', candidate + ':' + name)
fields = ['fuente', 'seccion', 'problema', 'criterio_exacto']
criteria = lambda value: {row['id']: {field: row[field] for field in fields} for row in value['requisitos']}
assert criteria(json.loads((run / 'TRAZABILIDAD.json').read_bytes())) == criteria(json.loads(git('show', base + ':docs/implementation/20261018-evolution/TRAZABILIDAD.json')))
docs = [(run / name).relative_to(root).as_posix() for name in ['ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'TRAZABILIDAD.json', 'TRAZABILIDAD.md']]
names = sorted(receipt['files']) + [path.relative_to(root).as_posix() for path in (run / 'evidence/checkpoint128-seal-receipt-20261019').iterdir() if path.is_file()]
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names + docs)
subprocess.run(['git', '-c', 'core.autocrlf=true', 'add', '--', *docs], cwd=root, check=True, capture_output=True)
for name in docs:
    assert git('show', ':' + name) == (root / name).read_bytes().replace(b'\r\n', b'\n')
check_paths = docs + [name for name in receipt['source_paths'] if not name.startswith('tests/ci_mfa31/')]
check = subprocess.run(['git', '-c', 'core.autocrlf=false', 'diff', '--cached', '--check', '--', *check_paths], cwd=root, capture_output=True)
assert check.returncode == 0, {'diagnostic_bytes': len(check.stdout), 'diagnostic_sha256': sha(check.stdout), 'stderr_bytes': len(check.stderr)}
folder = run / 'evidence/checkpoint128-integration-closure-20261019'
assert not folder.exists()
folder.mkdir()
(folder / '.gitattributes').write_bytes(b'* -text\n')
(folder / 'driver.py').write_bytes(Path(__file__).read_bytes())
(folder / 'receipt.json').write_bytes(enc({'base': base, 'source': candidate, 'source_paths_exact': len(receipt['source_paths']), 'criteria_exact': 126,
    'erratum': 'The first control stage preserved Windows CRLF in the eight editable control Markdown/JSON files because its Git helper forced core.autocrlf=false. The source whitespace gate rejected their complete-line CRs. This successor restages only those eight control files with explicit normal text conversion and verifies every staged byte equals working bytes with CRLF-to-LF. All product/test/RAW producer bytes remain exact. Initial driver and seal remain unchanged.',
    'source_and_control_whitespace_gate': 'PASS', 'raw_proof_whitespace_is_not_normalized': True,
    'scope': 'Reviewed local schema32 integration, not a new runtime test or production deployment.'}))
extra = [path.relative_to(root).as_posix() for path in folder.iterdir() if path.is_file()]
git('add', '-f', '--', *extra)
names += extra
for name in names:
    assert git('show', ':' + name) == (root / name).read_bytes()
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names + docs)
new_tree = {}
for row in git('ls-tree', '-r', '-z', git('write-tree').decode().strip()).split(b'\0'):
    if row:
        meta, name = row.split(b'\t', 1)
        new_tree[name.decode()] = meta.decode()
old_tree = receipt['before_Git_tree']
changed = set(names + docs)
assert set(new_tree) == set(old_tree) | changed
assert all(new_tree[name] == meta for name, meta in old_tree.items() if name not in changed)
assert not git('diff', '--cached', '--name-only', '--', 'Dockerfile', 'requirements_web.lock', 'requirements_web-windows.lock', 'requirements-test.lock')
subprocess.run(['git', '-c', 'core.autocrlf=false', 'commit', '-m', 'Integrate reviewed MFA and progress32 with public consent retirement'], cwd=root, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
result = {'head': git('rev-parse', 'HEAD').decode().strip(), 'registry': 126, 'criteria_exact': 126, 'source_paths': len(receipt['source_paths']), 'authenticated_files': len(names), 'main_schema': 32, 'other_Git_entries_exact': len(set(old_tree) - changed)}
(tmp / 'metodobase-checkpoint128-result.json').write_bytes(enc(result))
print(json.dumps(result))
