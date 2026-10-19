"""Seal only this UI source/proof. No product imports, services or network."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path.cwd()
PREFIX = Path('docs/implementation/20261018-evolution/evidence/progress-retirement-ui')
FOLDER = ROOT / PREFIX
BASE = '345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
PRODUCTS = ['web/routes/pages.py', 'web/templates/login_usuario.html', 'web/templates/login_gym.html', 'web/templates/usuario_perfil.html', 'web/templates/retiro_consentimientos.html', 'web/static/css/retiro-consentimientos.css', 'web/static/js/retiro-consentimientos.js', 'web/static/js/retiro-consentimientos-pagina.js']
TESTS = ['tests/test_progress_retirement_ui.py', 'tests/test_progress_retirement_ui_contract.py', 'tests/e2e/progress_retirement.cjs', 'tests/e2e/progress_retirement_dom.cjs']
DOCS = ['docs/implementation/20261018-evolution/RETIRO_CONSENTIMIENTOS_UI.md']
PROTECTED = ['web/static/js/api.js', 'web/static/js/mfa-ui.js', 'web/static/js/mfa-login.js', 'web/templates/mfa_account_partial.html', 'web/templates/mfa_login_partial.html', 'web/static/js/usuario-diario.js', 'web/static/js/usuario-plan-operacion.js', 'web/static/js/usuario-privacidad.js', 'web/static/js/plan-publicacion-consumo.js', 'web/static/js/plan-diario-ui.js', 'web/static/js/plan-diario-datos.js']


def sha(value):
    return hashlib.sha256(value).hexdigest()


def git(*args, cwd=ROOT):
    return subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.longpaths=true', *args], cwd=cwd, check=True, capture_output=True).stdout


assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert set(git('diff', '--cached', '--name-only').decode().splitlines()) == set(PRODUCTS)
assert not git('diff', '--name-only').strip(), 'Stage exactly the frozen product first'
before = json.loads((FOLDER / 'before-source.json').read_text(encoding='utf8'))
canary = json.loads((FOLDER / 'before-canary.json').read_text(encoding='utf8'))
assert sha((ROOT / TESTS[0]).read_bytes()) == canary['assertions_sha256']
patch = git('diff', '--cached', '--binary', '--', *PRODUCTS)
(FOLDER / 'change.patch').write_bytes(patch)
inverse_root = Path(tempfile.mkdtemp(prefix='metodobase-retirement-ui-inverse-'))
for name in PRODUCTS:
    destination = inverse_root / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, destination)
git('apply', '--reverse', '--whitespace=nowarn', str(FOLDER / 'change.patch'), cwd=inverse_root)
recovered = {}
for name in PRODUCTS:
    if name in before['preimages']:
        content = (inverse_root / name).read_bytes()
        assert content == (FOLDER / 'before' / name).read_bytes()
        assert sha(content) == before['preimages'][name]['raw']
        recovered[name] = sha(content)
    else:
        assert not (inverse_root / name).exists()
protected = {}
for name in PROTECTED:
    content = (ROOT / name).read_bytes()
    assert content == git('show', BASE + ':' + name), name
    protected[name] = sha(content)
sources = {}
for name in PRODUCTS + TESTS + DOCS:
    raw = (ROOT / name).read_bytes()
    lf = raw.replace(b'\r\n', b'\n')
    if name in PRODUCTS:
        assert lf == git('show', ':' + name)
    sources[name] = {'raw_sha256': sha(raw), 'git_lf_sha256': sha(lf), 'bytes': len(raw)}
archive = FOLDER / 'source-raw.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
    for name in PRODUCTS + TESTS + DOCS:
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 19, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        zipped.writestr(info, (ROOT / name).read_bytes())
with zipfile.ZipFile(archive) as zipped:
    assert zipped.testzip() is None
    for name in PRODUCTS + TESTS + DOCS:
        assert sha(zipped.read(name)) == sources[name]['raw_sha256']
tool_root = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1')
tool_hash = sha((tool_root / 'gitleaks.exe').read_bytes())
tool_zip_hash = sha((tool_root / 'gitleaks.zip').read_bytes())
assert tool_hash == '17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c'
assert tool_zip_hash + '  gitleaks_8.30.1_windows_x64.zip' in (tool_root / 'checksums.txt').read_text(encoding='utf8')
with zipfile.ZipFile(tool_root / 'gitleaks.zip') as zipped:
    assert sha(zipped.read('gitleaks.exe')) == tool_hash
assert subprocess.run([str(tool_root / 'gitleaks.exe'), 'version'], capture_output=True, check=True, text=True).stdout.strip() == '8.30.1'
results = {}
for name, passed, total in [('vm-ready.json', 36, 36), ('dom-ready.json', 9, 9)]:
    report = json.loads((FOLDER / name).read_text(encoding='utf8'))
    assert report['passed'] == passed and report['total'] == total
    results[name] = {'passed': passed, 'total': total, 'scope': report['scope']}
proofs = {file.relative_to(ROOT).as_posix(): sha(file.read_bytes()) for file in sorted(FOLDER.rglob('*')) if file.is_file() and file.name not in {'freeze.json', 'secret-scan.json'}}
freeze = {'base': BASE, 'wire_sha256': before['wire_sha256'], 'sources': sources, 'protected_unchanged': protected, 'inverse': {'method': 'git apply --reverse only on a separate temporary copy; exact RAW comparison and new-file absence', 'directory': str(inverse_root), 'recovered': recovered, 'new_files_removed': True}, 'source_raw_zip_sha256': sha(archive.read_bytes()), 'tests': results, 'ssr_final': {'passed': 8, 'proof': (PREFIX / 'ssr-ready.xml').as_posix(), 'scope': 'Actual public SSR in both synthetic factories, not withdrawal API acceptance'}, 'tool': {'gitleaks': str(tool_root / 'gitleaks.exe'), 'version': '8.30.1', 'exe_sha256': tool_hash, 'zip_sha256': tool_zip_hash, 'checksum_and_zip_entry_verified': True}, 'node_sha256': sha(Path('C:/Program Files/nodejs/node.exe').read_bytes()), 'proofs': proofs, 'classification': 'First-party code, synthetic VM proofs, public source hashes and local tool paths. No real credentials, tokens, seeds, recovery kits, grants, contacts or health data.', 'limits': ['No Chrome/axe/PG or purpose-only API execution', 'Backend wire is contractual, not accepted runtime', 'Middleware first-party/all-status policy is a separate backend composition', 'Scanner output is generated after this immutable source seal and excludes itself by the existing runner contract']}
(FOLDER / 'freeze.json').write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({'products': len(PRODUCTS), 'tests': len(TESTS), 'protected_unchanged': len(protected), 'proofs': len(proofs), 'inverse': True, 'zip_verified': True, 'freeze_sha256': sha((FOLDER / 'freeze.json').read_bytes())}))
