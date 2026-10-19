from pathlib import Path
import hashlib
import json
import subprocess
import sys

tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
source = tmp / 'metodobase-gitleaks-historical-fingerprint-triage.py'
target = tmp / 'metodobase-gitleaks-historical-evidence-triage.py'
assert not target.exists()
blob = source.read_bytes()
text = blob.decode()
replacements = [
    ("previous = tmp / 'metodobase-gitleaks-fingerprint-triage-20261019'", "previous = tmp / 'metodobase-gitleaks-public-artifact-triage-20261019'"),
    ("out = tmp / 'metodobase-gitleaks-historical-fingerprint-triage-20261019'", "out = tmp / 'metodobase-gitleaks-historical-evidence-triage-20261019'"),
    ('assert len(rows) == 25895', 'assert len(rows) == 9015'),
    ("*commits, '--', '.', ':!docs/**'", "*commits, '--', *sorted(wanted)")]
for old, new in replacements:
    assert text.count(old) == 1
    text = text.replace(old, new)
inverse = text
for old, new in reversed(replacements):
    inverse = inverse.replace(new, old)
assert inverse.encode() == blob
target.write_bytes(text.encode())
receipt = {'derived_from': source.name, 'original_sha256': hashlib.sha256(blob).hexdigest(), 'derived_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'replacements': replacements, 'inverse_exact': True, 'scope': 'Read-only checksum derivation from historical evidence blobs. Blob bodies are never written or printed, to avoid reintroducing historic synthetic token/log content. Only checksum/OID/location proof is emitted.'}
(tmp / 'metodobase-gitleaks-historical-evidence-derivation.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(target)], capture_output=True)
print(result.stdout.decode())
if result.returncode:
    print(result.stderr.decode())
raise SystemExit(result.returncode)
