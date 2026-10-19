"""Verify the frozen UI source and scan every proposed new blob before integration."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import re
import subprocess
import zipfile

ROOT = Path(r'F:\mb-mfa31-compose-20261019')
UI = Path(r'F:\mb-mfa-ui31-20261019')
OUT = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa-ui31-compose-preflight-20261019')
BASE = '913cb66061ac754ad09344fc24e8f769b5722997'
INCOMING = '087c807cc777d553f3fe5d28fb2a723758d695a9'
SOURCE = 'docs/implementation/20261018-evolution/evidence/mfa-ui31/source.json'
SHA = lambda b: hashlib.sha256(b).hexdigest()


def git(*args, **kwargs):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, **kwargs)


def sensitive(blob):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])', blob):
        start = match.start()
        if start >= 30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}', blob[start-30:start]):
            return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+', blob))


assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert not git('status', '--porcelain', '--untracked-files=no')
source_blob = git('show', INCOMING + ':' + SOURCE)
assert SHA(source_blob) == '789a5f590c33bb45bb92c13175f9e1f2c5823557f737ad0f3a588b9849e46621'
assert source_blob == (UI / SOURCE).read_bytes()
source = json.loads(source_blob)
expected = {**source['ui_product13'], **source['vm_tests5'], **source['new_test_fixture_sources']}
assert len(source['ui_product13']) == 13 and len(expected) == 24
for name, meta in expected.items():
    blob = git('show', INCOMING + ':' + name)
    assert SHA(blob) == meta['git_lf_sha256']
    assert SHA((UI / name).read_bytes()) == meta['raw_sha256']
names = git('diff', '--name-only', '-z', BASE, INCOMING).decode().split('\0')[:-1]
assert {name for name in names if not name.startswith('docs/')} == set(expected)
queries = ''.join(INCOMING + ':' + name + '\n' for name in names).encode()
raw = git('cat-file', '--batch', input=queries)
cursor = 0
files = {}
findings = []
archives = {}
for name in names:
    end = raw.index(b'\n', cursor)
    header = raw[cursor:end].split()
    assert header[1] == b'blob'
    size = int(header[2])
    cursor = end + 1
    blob = raw[cursor:cursor+size]
    assert len(blob) == size
    cursor += size + 1
    files[name] = {'bytes': size, 'sha256': SHA(blob)}
    if sensitive(blob):
        findings.append({'path': name, 'location': 'blob', 'values_withheld': True})
    if name.lower().endswith('.zip'):
        entries = {}
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                path = PurePosixPath(member.filename)
                assert path.as_posix() == member.filename and not path.is_absolute() and '..' not in path.parts
                assert member.filename not in entries and member.file_size < 5_000_000
                content = archive.read(member)
                assert len(content) == member.file_size
                entries[member.filename] = {'bytes': len(content), 'sha256': SHA(content)}
                if sensitive(content):
                    findings.append({'path': name, 'location': member.filename, 'values_withheld': True})
        archives[name] = entries
assert cursor == len(raw)
for name in ['api/routes/pagos.py', 'web/services/mfa_service.py', 'web/services/mfa_actions.py',
             'web/middleware/security_headers.py', 'web/database/schema_control.py']:
    assert git('show', BASE + ':' + name) == git('show', INCOMING + ':' + name), name
OUT.mkdir(exist_ok=False)
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
report = {'base': BASE, 'incoming': INCOMING, 'source_manifest_sha256': SHA(source_blob),
          'files': files, 'expanded_archives': archives, 'sensitive_findings': findings,
          'values_withheld': True, 'product_test_paths': len(expected),
          'backend5_Git_exact': True, 'status': 'REFUSED' if findings else 'PREFLIGHT_PASS',
          'scope': 'Frozen source and publication scan only; no merge, tests, application, browser, database or provider execution.'}
(OUT / 'receipt.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
print(json.dumps({'status': report['status'], 'changed_files': len(names), 'product_test_paths': len(expected),
                  'ZIPs': len(archives), 'sensitive_findings_metadata': findings,
                  'receipt_sha256': SHA((OUT / 'receipt.json').read_bytes())}))
assert not findings, 'Publication refused; exact finding locations are retained without values'
