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
run = Path('docs/implementation/20261018-evolution')
ev = run / 'evidence'
base = '1be3b671b106bee6447ea47377d2596fde12d0b1'
candidate = '2273616eb218adfdd30680e111da50a4599a8c53'
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == base and not git('status', '--porcelain', '--untracked-files=no')
ancestor = git('merge-base', base, candidate).decode().strip()
assert ancestor == 'eea8f773fba9b7f92241958139fcefa23b9ee1d4'
assert not git('diff', '--name-only', ancestor, base, '--', '.', ':!docs/implementation/**')
all_names = git('diff', '--name-only', '-z', base, candidate).decode().split('\0')[:-1]
source_names = [name for name in all_names if not name.startswith('docs/implementation/')]
source_names += [str(run / 'MFA_UI_CONTRATO.md').replace('\\', '/')]
assert len(source_names) == len(set(source_names))
assert all(Path(name).parts[0] in {'web', 'api', 'config', 'tests', '.github', 'alembic.ini', 'docs'} for name in source_names)
source = {name: git('show', candidate + ':' + name) for name in source_names}
contents = dict(source)
ledger = []
proof_snapshots = [
    ('2273616eb218adfdd30680e111da50a4599a8c53', '219f89a5ee0196061fea5b67e36ae07daf7f4316', 'root-retirement32-owned-cleanup-20261019', '44df142f8dd1524aeb4d4b4db96841d2242737526684c732e960a3feeebabb37'),
    ('67743467c13b657f947a9a93310d0b49582a3752', candidate, 'security-retirement-owned-cleanup-independent-20261019', '01b16d22c9f51276c2a6ac27fc4d10fe32d53f454a2107ef4ea1ac1cde2a6a6a'),
    ('2b1a2e275abb26c291fb02a7a3e8f5a2e58ce2f5', '219f89a5ee0196061fea5b67e36ae07daf7f4316', 'qa-retirement32-review219-20261019', '0aa731d409dcbc9c152a4ecb2103f9731f067a15f3473decc858ef0461e998e1'),
    ('3c881d1b83b6911babda4018af6540ef91ce8cc7', candidate, 'qa-retirement32-review227-20261019', 'e2de8d00638473eac967da3c65f146b8b4145d43290d206482d3f48e4c2498d9')]
for ref, parent, anchor, manifest_sha in proof_snapshots:
    names = git('diff', '--name-only', '-z', parent, ref, '--', str(ev)).decode().split('\0')[:-1]
    assert names
    assert sha(git('show', ref + ':' + (ev / anchor / 'manifest.json').as_posix())) == manifest_sha
    for name in names:
        blob = git('show', ref + ':' + name)
        assert name not in contents
        contents[name] = blob
        ledger.append({'path': name, 'Git_commit': ref, 'bytes': len(blob), 'sha256': sha(blob)})
prefix = ev / 'root-gitleaks-checksum-triage-prepared-20261019'
phases = ['metodobase-gitleaks-fingerprint-triage-20261019', 'metodobase-gitleaks-historical-fingerprint-triage-20261019', 'metodobase-gitleaks-public-artifact-triage-20261019', 'metodobase-gitleaks-historical-evidence-triage-20261019']
summaries = [json.loads((tmp / phase / 'summary.json').read_bytes()) for phase in phases]
assert summaries[-1]['remaining_unclassified'] == 282
archive = io.BytesIO()
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as handle:
    for phase in phases:
        for path in sorted((tmp / phase).iterdir()):
            if path.is_file():
                handle.writestr(phase + '/' + path.name, path.read_bytes())
contents[(prefix / '.gitattributes').as_posix()] = b'* -text\n'
contents[(prefix / 'sanitized-classification-ledgers.zip').as_posix()] = archive.getvalue()
contents[(prefix / 'summary.json').as_posix()] = enc({'prior_report_sha256': '0e5d0cfc77c1626912beca8c9b39e91fe56464e9e9cc71502947e44288b09352',
    'input_remaining': 31564, 'root_checksum_candidates': 31282, 'remaining_unclassified': 282, 'phases': summaries,
    'scope': 'Prepared root triage only, pending independent review. The original full scanner report is external and unchanged; no new scanner run or changed rule/allowlist. GitLF-to-CRLF checksums are DERIVED, not reconstructed execution RAW. Historical blob bodies never republished.'})
prepared = ev / 'prepared-wave128-20261019'
controls = {'.gitattributes': b'* -text\n', 'driver.py': Path(__file__).read_bytes(),
    'import-ledger.json': enc({'base': base, 'candidate': candidate, 'common_ancestor': ancestor, 'source_paths': source_names, 'proofs': ledger,
        'scope': 'Local schema32 integration candidate, no deployment. Full regressions belong to31 only; independent retirement HTTP/PG/UI scopes remain separate. Google33 not included.'}),
    'source-equivalence.json': enc({'candidate': candidate, 'source_paths': {name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in source.items()},
        'main_source_unchanged_since_common_ancestor': True, 'no_Dockerfile_or_dependency_lock_change': not git('diff', '--name-only', base, candidate, '--', 'Dockerfile', 'requirements_web.lock', 'requirements_web-windows.lock', 'requirements-test.lock')})}
for name in ['metodobase-retirement32-cleanup-commit.py', 'metodobase-retirement32-cleanup-commit-receipt.json', 'metodobase-gitleaks-historical-evidence-prepare.py', 'metodobase-gitleaks-historical-evidence-derivation.json']:
    controls[name] = (tmp / name).read_bytes()
controls['manifest.json'] = enc({name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in controls.items()})
for name, blob in controls.items():
    contents[(prepared / name).as_posix()] = blob
definition = next(n for n in ast.parse((tmp / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
for name, blob in contents.items():
    scan(blob, name)
for name, blob in contents.items():
    if name not in source:
        path = root / name
        if path.exists():
            assert path.read_bytes() == blob, name
out = tmp / 'metodobase-checkpoint128-prepare-result.json'
assert not out.exists()
inventory = {name: meta for meta, name in (row.split(b'\t', 1) for row in git('ls-tree', '-r', '-z', base).split(b'\0') if row)}
for name, blob in sorted(contents.items(), key=lambda item: (Path(item[0]).name != '.gitattributes', item[0])):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if name in source:
        path.write_bytes(blob)
    elif not path.exists():
        with path.open('xb') as handle:
            handle.write(blob)
for name, blob in source.items():
    assert (root / name).read_bytes() == git('show', candidate + ':' + name) == blob
assert not git('diff', '--name-only', '--', *[name for name in ['Dockerfile', 'requirements_web.lock', 'requirements_web-windows.lock', 'requirements-test.lock']])
result = {'base': base, 'candidate': candidate, 'source_paths': source_names, 'files': {name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in contents.items()},
    'before_Git_tree': {name.decode(): meta.decode() for name, meta in inventory.items()}}
out.write_bytes(enc(result))
print(json.dumps({'source_paths': len(source_names), 'proof_and_preparation_paths': len(contents) - len(source_names), 'bytes': sum(map(len, contents.values())), 'candidate': candidate}))
