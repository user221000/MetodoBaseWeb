"""Small, feature-only source/inverse/scan receipt; never copy a repository or a runtime."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path.cwd().resolve()
BASE = '2273616eb218adfdd30680e111da50a4599a8c53'
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/google-link-ui'
PRODUCTS = ['web/routes/pages.py', 'web/static/js/api.js', 'web/static/js/mfa-login.js',
    'web/templates/configuracion.html', 'web/templates/login_gym.html',
    'web/templates/login_usuario.html', 'web/templates/usuario_perfil.html',
    'web/templates/cuenta_google.html', 'web/static/css/google-vinculo.css',
    'web/static/js/google-vinculo.js', 'web/static/js/google-vinculo-pagina.js']
TESTS = ['tests/test_google_link_ui.py', 'tests/test_google_link_ui_contract.py',
    'tests/e2e/google_link_api.cjs', 'tests/e2e/google_link_state.cjs',
    'tests/e2e/google_link_dom.cjs', 'tests/e2e/google_link_login_review.cjs']
DOC = 'docs/implementation/20261018-evolution/GOOGLE_VINCULO_UI.md'
REGRESSIONS = ['tests/e2e/auth_refresh.cjs', 'tests/e2e/auth_refresh_storage.cjs',
    'tests/e2e/auth_refresh_security_review.cjs', 'tests/e2e/auth_refresh_race_review.cjs',
    'tests/e2e/mfa_api.cjs', 'tests/e2e/mfa_state.cjs', 'tests/e2e/mfa_prompt.cjs',
    'tests/e2e/mfa_consumers.cjs']
DEPENDENCIES = ['api/app.py', 'web/main_web.py', 'web/middleware/security_headers.py',
    'web/static/js/mfa-ui.js', 'web/static/js/usuario-diario.js',
    'web/static/js/usuario-privacidad.js', 'web/static/js/usuario-plan-operacion.js',
    'web/static/js/plan-publicacion-consumo.js', 'web/static/js/usuario-progreso.js',
    'web/static/js/retiro-consentimientos.js', 'web/static/js/retiro-consentimientos-pagina.js',
    'web/auth.py', 'web/auth_deps.py',
    'config/settings.py', 'web/database/models.py', 'web/database/engine.py',
    'requirements_web.lock', 'requirements_web-windows.lock',
    'requirements-test.lock', 'requirements-test-windows.lock',
    'tests/run_isolated.py', 'tests/isolation.py', '.gitleaks.toml', 'scripts/scan_secrets.py']

def digest(content):
    return hashlib.sha256(content).hexdigest()

def git(*arguments, cwd=ROOT):
    return subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.longpaths=true',
        *arguments], cwd=cwd, capture_output=True, check=True).stdout

def write(name, value):
    path = OUT / name
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert (OUT / '.gitattributes').read_text().strip() == '* -text'
source_names = PRODUCTS + TESTS + [DOC]
initial = {name: digest((ROOT / name).read_bytes()) for name in source_names}
before = json.loads((OUT / 'before-source.json').read_text(encoding='utf-8'))
for name, expected in before['sources'].items():
    assert digest(git('show', BASE + ':' + name)) == expected['git_lf']
    assert digest((OUT / 'before' / name).read_bytes()) == expected['raw']

# A bounded scan of the 17 product/test sources, not the existing repository or proofs.
scanner = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1/gitleaks.exe')
assert digest(scanner.read_bytes()) == '17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c'
scanner_dir = scanner.parent
archive = scanner_dir / 'gitleaks.zip'
zip_hash = digest(archive.read_bytes())
assert zip_hash == 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e'
assert zip_hash in (scanner_dir / 'checksums.txt').read_text()
with zipfile.ZipFile(archive) as source_zip:
    entries = [name for name in source_zip.namelist() if name.endswith('gitleaks.exe')]
    assert len(entries) == 1
    assert digest(source_zip.read(entries[0])) == digest(scanner.read_bytes())
version = subprocess.run([str(scanner), 'version'], capture_output=True, check=True).stdout.decode().strip()
assert version == '8.30.1'
scan_dir = Path(tempfile.mkdtemp(prefix='metodobase-google-link-source-scan-'))
snapshot = scan_dir / 'source'
for name in PRODUCTS + TESTS:
    target = snapshot / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / name).read_bytes())
scan_command = [str(scanner), 'dir', '--config', str(ROOT / '.gitleaks.toml'),
    '--report-format', 'json', '--report-path', str(scan_dir / 'report-redacted.json'),
    '--redact', '--no-banner', str(snapshot)]
scan = subprocess.run(scan_command, capture_output=True)
assert scan.returncode in (0, 1)
findings = json.loads((scan_dir / 'report-redacted.json').read_text())
safe = [{key: item.get(key) for key in ('RuleID', 'File', 'StartLine', 'EndLine')}
    for item in findings]
write('scan-source-scope.json', {'scope': '17 product/test source files ONLY; no global/proof scan',
    'command': scan_command, 'version': version, 'executable_sha256': digest(scanner.read_bytes()),
    'archive_sha256': zip_hash, 'exit': scan.returncode, 'findings': safe,
    'global_gate': 'Existing global scan remains red, not rerun or reclassified here',
    'source_sha256': {name: initial[name] for name in PRODUCTS + TESTS}})

git('add', '--', *PRODUCTS, *TESTS, DOC)
inverse = git('diff', '--cached', '-R', '--binary', '--no-ext-diff', '--', *PRODUCTS)
(OUT / 'inverse.patch').write_bytes(inverse)
with tempfile.TemporaryDirectory(prefix='metodobase-google-link-inverse-') as temporary:
    reverse_root = Path(temporary)
    for name in PRODUCTS:
        target = reverse_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    git('apply', '--check', str(OUT / 'inverse.patch'), cwd=reverse_root)
    git('apply', str(OUT / 'inverse.patch'), cwd=reverse_root)
    for name in PRODUCTS:
        if name in before['sources']:
            assert (reverse_root / name).read_bytes() == git('show', BASE + ':' + name)
        else:
            assert not (reverse_root / name).exists()

small_zip = OUT / 'tested-source-raw.zip'
with zipfile.ZipFile(small_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
    for name in source_names:
        bundle.writestr(name, (ROOT / name).read_bytes())
with zipfile.ZipFile(small_zip) as bundle:
    assert bundle.testzip() is None
    for name in source_names:
        assert digest(bundle.read(name)) == initial[name]

protected = {}
for name in REGRESSIONS + DEPENDENCIES:
    source = ROOT / name
    if not source.is_file():
        raise FileNotFoundError(name)
    current = source.read_bytes()
    assert current == git('show', BASE + ':' + name), name
    protected[name] = digest(current)
sources = {}
for name in source_names:
    raw = (ROOT / name).read_bytes()
    blob = git('show', ':' + name)
    assert digest(raw) == initial[name]
    sources[name] = {'raw_sha256': digest(raw), 'git_blob_sha256': digest(blob),
        'lf_sha256': digest(blob.replace(b'\r\n', b'\n')), 'raw_bytes': len(raw),
        'raw_crlf_count': raw.count(b'\r\n'), 'git_crlf_count': blob.count(b'\r\n')}
packages = sorted([{'name': item.metadata['Name'], 'version': item.version}
    for item in importlib.metadata.distributions()], key=lambda item: item['name'].lower())
write('source.json', {'base': BASE, 'scope': 'UI only; no API33/provider/browser/PG acceptance',
    'products': PRODUCTS, 'tests': TESTS, 'sources': sources,
    'read_only_dependencies_exact_base': protected, 'python_packages_read_only': packages,
    'test_counts': {'new_node_vm': 49, 'new_ssr': 8, 'historical_transport_vm': 74,
        'historical_mfa_login_vm': 74},
    'inverse': {'sha256': digest(inverse), 'verified_in_owned_temp': True,
        'shared_before_exact': 7, 'new_products_removed': 4},
    'small_raw_archive': {'name': small_zip.name, 'bytes': small_zip.stat().st_size,
        'sha256': digest(small_zip.read_bytes()), 'all_entries_readback_exact': True},
    'secret_classification': 'Only source, hashes, fixed synthetic VM/SSR fixtures; no live credentials, provider claims, subjects, factors, grants, kits or user data captured',
    'resource_scope': 'No Chrome, VM, PG, network/provider, listeners or owned long-running resources started',
    'pending': ['API33 composition and independent reviews', 'Real Google configuration/auth_time',
        'Browser/CSP/320-1440/manual accessibility', 'Global secret scan triage']})
print(json.dumps({'products': len(PRODUCTS), 'tests': len(TESTS), 'source_manifest_sha256':
    digest((OUT / 'source.json').read_bytes()), 'raw_zip_bytes': small_zip.stat().st_size,
    'scoped_source_scan_exit': scan.returncode, 'scoped_source_findings': len(safe)}))
