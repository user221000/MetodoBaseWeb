"""Authenticate scoped peer reviews and preserve the bounded legacy diagnostic."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-execution-20261018')
EV = ROOT / 'docs/implementation/20261018-evolution/evidence'
TMP = Path(r'C:\Users\Consu\AppData\Local\Temp')
DEST = EV / 'mfa31-refinements-and-legacy-prepared-20261019'
SHA = lambda b: hashlib.sha256(b).hexdigest()


def sensitive(blob):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])', blob):
        start = match.start()
        if start >= 30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}', blob[start-30:start]):
            return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+', blob))


reviews = {
    'security-mfa31-full-independent-20261019': '1003e35ed656c7090bd06551db9756d7e413717535fbc5b5eb4c72f32735f50d',
    'security-mfa31-alias-primary-independent-20261019': 'bd83ad84910cfd2eb9d0dfaaefff566513132161ae266f278e8661ff7c7f337f',
    'security-mfa31-pg-independent-20261019': '25ade8a282b7937034adfbbe985b833d11e9012d09f077ad7b96cf5515399fbd',
    'security-mfa31-canonical-final-independent-20261019': '6836e3a3d5d560c3f3873d78f25cabb0e60febbe2af4992eb0061e1332f989e8',
    'security-mfa31-composition-static-independent-20261019': '8224d3f6a93b8dee2aef611a3e5d06d81df1a96d259a020272172887b9ed08e8',
}
authenticated = {}
for prefix, digest in reviews.items():
    folder = EV / prefix
    source = folder / 'source.json'
    assert SHA(source.read_bytes()) == digest, prefix
    document = json.loads(source.read_bytes())
    paths = {source}
    for row in document['files']:
        path = folder / row['file']
        assert path.resolve().is_relative_to(folder.resolve())
        blob = path.read_bytes()
        assert SHA(blob) == row['sha256'] and not sensitive(blob), path.name
        if 'bytes' in row:
            assert len(blob) == row['bytes']
        assert path.suffix.lower() != '.zip', 'New expanded ZIP review required'
        paths.add(path)
    assert not sensitive(source.read_bytes())
    assert (folder / '.gitattributes').read_bytes() == b'* -text\n'
    assert paths == {p for p in folder.rglob('*') if p.is_file()}
    authenticated[prefix] = {'source_sha256': digest, 'files': len(paths)}

diag = TMP / 'metodobase-mfa31-legacy-contract-diagnostic-20261019'
summary = json.loads((diag / 'summary.private.json').read_bytes())
assert summary['head'] == '913cb66061ac754ad09344fc24e8f769b5722997'
assert summary['counts'] == {'passed': 72, 'failure': 20, 'error': 0, 'skipped': 0}
assert summary['maxfail'] == 20 and summary['cases'] == 92
assert summary['source_packages_quiet'] and summary['source_files'] == 663 and summary['packages'] == 89
before = (diag / 'before.json').read_bytes()
assert before == (diag / 'after.json').read_bytes()
raw_paths = sorted(p for p in diag.iterdir() if p.is_file())
archive = TMP / 'metodobase-mfa31-legacy-contract-diagnostic-raw-private-20261019.zip'
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
    for path in raw_paths:
        output.write(path, path.name)
with zipfile.ZipFile(archive) as retained:
    assert set(retained.namelist()) == {p.name for p in raw_paths}
    for path in raw_paths:
        assert retained.read(path.name) == path.read_bytes()

DEST.mkdir(exist_ok=False)
(DEST / '.gitattributes').write_bytes(b'* -text\n')


def capture(path, name):
    blob = path.read_bytes()
    assert not sensitive(blob), path.name
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)


capture(Path(__file__), 'prepare.py')
capture(TMP / 'metodobase-mfa31-compose-refinements.py', 'composition/driver.py')
composition = TMP / 'metodobase-mfa31-compose-refinements-20261019'
for path in sorted(composition.iterdir()):
    assert path.is_file()
    capture(path, 'composition/' + path.name)
capture(TMP / 'metodobase-mfa31-legacy-contract-diagnostic.py', 'legacy/driver.py')
capture(diag / 'summary.private.json', 'legacy/summary.json')
capture(diag / 'before.json', 'legacy/before.json')
capture(diag / 'after.json', 'legacy/after.json')
receipt = {
    'authenticated_peer_reviews': authenticated,
    'backend_acceptance': 'Scoped security acceptance on440; PG4 belongs to original56 only; static composition review on913; no UI/restore/provider/ASVS/AAL2 acceptance from these reviews.',
    'legacy_diagnostic': 'Bounded initial diagnostic on913, stopped at20failures. All20 are team invitation contract cases; no fixture or product cause inferred yet. It is not a full regression or acceptance. Original business assertions must be preserved while adopting legitimate MFA enrollment and exact grants.',
    'raw_private_archive': {'path': str(archive), 'sha256': SHA(archive.read_bytes()), 'bytes': archive.stat().st_size,
        'files': {p.name: {'bytes': p.stat().st_size, 'sha256': SHA(p.read_bytes())} for p in raw_paths}},
    'public_projection': 'Only structured case identities/results, inventories and drivers are public. Original XML/logs remain private and unchanged. Public summary was already value-free; no result rewriting or deletion.',
    'product_changed': False,
}
(DEST / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
manifest = {'files': {p.relative_to(DEST).as_posix(): {'bytes': p.stat().st_size, 'sha256': SHA(p.read_bytes())}
                      for p in sorted(DEST.rglob('*')) if p.is_file()}}
(DEST / 'manifest.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode())
print(json.dumps({'reviews': len(authenticated), 'review_files': sum(x['files'] for x in authenticated.values()),
                  'prepared_files': len(manifest['files']) + 1,
                  'manifest_sha256': SHA((DEST / 'manifest.json').read_bytes()), 'product_changed': False}))
