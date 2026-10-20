"""Finite VM replays with owner-only RAW and public counters, no application startup."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import tempfile

ROOT = Path.cwd()
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/notifications36-bootstrap-20261020'
NODE = Path('C:/Program Files/nodejs/node.exe')
SCANNER = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1/gitleaks.exe')
TESTS = ['tests/e2e/notifications36_bootstrap.cjs', 'tests/e2e/notifications36_state.cjs',
    'tests/e2e/notifications36_dom.cjs', 'tests/e2e/notifications36_nav.cjs']
EXPECTED = [8, 19, 8, 9]

def sha(value):
    return hashlib.sha256(value).hexdigest()

before = json.loads((OUT / 'before-source.json').read_text())
red = json.loads((OUT / 'red-frozen.json').read_text())
assert sha((ROOT / red['driver']).read_bytes()) == red['driver_sha256']
product = ROOT / 'web/static/js/notifications36.js'
old = (OUT / 'notifications36-before.js').read_bytes()
old_default = b'function mount(element,{api=root.Api.notifications36}={})'
new_default = b'function mount(element,{api=Api.notifications36}={})'
assert old.count(old_default) == 1
assert product.read_bytes() == old.replace(old_default, new_default, 1)

def photo():
    files = {row['file']: sha((ROOT / row['file']).read_bytes()) for row in before['sources']}
    files[red['driver']] = sha((ROOT / red['driver']).read_bytes())
    packages = sorted((item.metadata['Name'], item.version)
        for item in importlib.metadata.distributions())
    node_locks = {}
    for name in ['tests/e2e/package.json', 'tests/e2e/package-lock.json']:
        node_locks[name] = sha((ROOT / name).read_bytes())
    return {'files': files, 'python_metadata_count': len(packages),
        'python_metadata_sha256': sha(json.dumps(packages).encode()),
        'node_binary_sha256': sha(NODE.read_bytes()), 'node_locks': node_locks}

initial = photo()
for entry in before['sources']:
    if entry['file'] != 'web/static/js/notifications36.js':
        assert initial['files'][entry['file']] == entry['raw_sha256']
private = Path(tempfile.mkdtemp(prefix='metodobase-notifications-bootstrap-raw-'))
identity = subprocess.run(['whoami'], capture_output=True, check=True).stdout.decode().strip()
subprocess.run(['icacls', str(private), '/inheritance:r', '/grant:r',
    identity + ':(OI)(CI)F', '/Q'], check=True, capture_output=True)
raw = private / 'raw'
raw.mkdir()
rows = []
for number, (name, expected) in enumerate(zip(TESTS, EXPECTED)):
    result = subprocess.run([str(NODE), name], cwd=ROOT, capture_output=True)
    (raw / f'{number}.stdout').write_bytes(result.stdout)
    (raw / f'{number}.stderr').write_bytes(result.stderr)
    report = json.loads(result.stdout)
    rows.append({'file': name, 'exit': result.returncode,
        'passed': report.get('passed'), 'total': report.get('total'),
        'stdout_sha256': sha(result.stdout), 'stdout_bytes': len(result.stdout),
        'stderr_sha256': sha(result.stderr), 'stderr_bytes': len(result.stderr)})
    assert result.returncode == 0 and report['passed'] == report['total'] == expected

assert sha(SCANNER.read_bytes()) == '17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c'
version = subprocess.run([str(SCANNER), 'version'], capture_output=True, check=True).stdout.decode().strip()
assert version == '8.30.1'
scan_command = [str(SCANNER), 'dir', '--config', str(ROOT / '.gitleaks.toml'),
    '--report-format', 'json', '--report-path', str(private / 'raw-scan.json'),
    '--redact', '--no-banner', str(raw)]
scan = subprocess.run(scan_command, capture_output=True)
assert scan.returncode in (0, 1)
findings = json.loads((private / 'raw-scan.json').read_text())
final = photo()
assert final == initial
report = {'scope': 'One-line default mount fix; actual Api/controller in VM and typed response/DOM doubles only',
    'new_canary': {'before': {'bootstrap_red': 6, 'api_shape_green': 2}, 'after': 8,
        'frozen_driver_sha256': red['driver_sha256'], 'assertions_unchanged': True},
    'replays': rows, 'total_passed_after': sum(row['passed'] for row in rows),
    'private_raw': {'directory': str(private), 'owner_only_dacl_applied_before_payload': True,
        'scanner_version': version, 'scanner_exit': scan.returncode, 'findings': len(findings),
        'report_sha256': sha((private / 'raw-scan.json').read_bytes())},
    'quiet': {'selected_source_files': len(initial['files']), 'python_metadata_count': initial['python_metadata_count'],
        'python_metadata_sha256': initial['python_metadata_sha256'], 'node_binary_sha256': initial['node_binary_sha256'],
        'node_locks': initial['node_locks'], 'before_equals_after': True},
    'one_line_product_delta_verified': True,
    'limits': ['No Chrome, SQL, app server, actual cookie, HTTP/API37 or provider acceptance',
        'The three maintained suites do not replace the new default-mount canary',
        'Global secret gate and R27 remain open; no allowlist or shared dependency changes']}
target = OUT / 'after-aggregate.json'
assert not target.exists()
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'passed': report['total_passed_after'], 'counts': [row['passed'] for row in rows],
    'python_metadata': initial['python_metadata_count'], 'source_quiet': True,
    'raw_scan_exit': scan.returncode, 'raw_findings': len(findings),
    'aggregate_sha256': sha(target.read_bytes())}))
