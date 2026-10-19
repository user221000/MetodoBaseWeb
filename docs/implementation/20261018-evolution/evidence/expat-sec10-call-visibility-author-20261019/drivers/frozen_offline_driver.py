"""Close static OPS12/13 author checks, without compiling or accessing a VM."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import runpy
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-expat-call-visibility-20261019')
OUT = Path(__file__).resolve().parent
DIAG = Path('F:/MetodoBaseWeb-linux-lab-20261019/evidence/expat-sec10-de69-native-diagnostic-20261019')
HEAD = '72c44a1834d7bd9803b4b8846c6c87e85a53bfd3'
PARENT = 'de69a85e7903f1a7217b054c0edb269dd5560999'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert not git('status', '--porcelain').strip()
changed = git('diff', '--name-only', PARENT, HEAD).decode().splitlines()
assert set(changed) == {'runtime-source/expat-sec10/rebuild_pyexpat.py', 'runtime-source/expat-sec10/CONTRATO.md',
    'tests/test_expat_sec10_build_contract.py', 'tests/fixtures/expat_sec10/.gitattributes',
    'tests/fixtures/expat_sec10/setuptools84-call-source.json'}
names = [n.decode() for n in git('ls-files', '-z').split(b'\0') if n and not n.startswith(b'docs/')]
snapshot = lambda: {name: sha((ROOT / name).read_bytes()) for name in names}
before = snapshot()
packages = lambda: sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())
package_before = packages()
assert len(package_before) == 89
locks = [name for name in names if name.endswith('.lock')]
for name in locks + ['Dockerfile', 'runtime-source/expat-sec10/source-pins.json', 'runtime-source/expat-sec10/13c5f63.patch']:
    assert git('show', HEAD + ':' + name) == git('show', PARENT + ':' + name)
assert sha((DIAG / 'source.json').read_bytes()) == 'ba64804ae9f2ccbcb638d73dfbe68630e295821076f98efaa4dcfdee95502b09'
assert sha((DIAG / 'manifest.json').read_bytes()) == '9a7abd7b4b054144daa059577371507b796b2a2e63344e566a86833fe0c88542'
manifest = json.loads((DIAG / 'manifest.json').read_bytes())
for name, item in manifest.items():
    raw = (DIAG / name).read_bytes()
    assert len(raw) == item['bytes'] and sha(raw) == item['sha256']
fixture = json.loads((ROOT / 'tests/fixtures/expat_sec10/setuptools84-call-source.json').read_bytes())
for name, item in fixture['methods'].items():
    path = 'setuptools/' + item['sourcefile'].split('/setuptools/', 1)[1]
    raw = (DIAG / 'installed-setuptools-source' / path).read_bytes()
    assert sha(raw) == item['module_sha256'] and item['source'] in raw.decode()
records = []


def run(label, args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=90)
    (OUT / (label + '.stdout.log')).write_bytes(result.stdout)
    (OUT / (label + '.stderr.log')).write_bytes(result.stderr)
    records.append({'gate': label, 'exit': result.returncode, 'stdout_sha256': sha(result.stdout),
                    'stderr_sha256': sha(result.stderr)})
    assert result.returncode == 0, label


run('frozen-tests41', [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py',
    'tests/test_expat_sec10_build_contract.py', '-q', '--tb=short', '--junitxml=' + str(OUT / 'frozen-tests41.xml')])
junit = ET.fromstring((OUT / 'frozen-tests41.xml').read_bytes())
assert len(junit.findall('.//testcase')) == 41
assert not any(junit.findall('.//' + tag) for tag in ('failure', 'error', 'skipped'))
run('frozen-quality', [sys.executable, '-X', 'utf8', '-B', 'tests/check_quality.py', 'lint'])
run('frozen-pip-check', [sys.executable, '-B', '-m', 'pip', 'check'])
for name in changed:
    if name.endswith('.py'):
        compile((ROOT / name).read_bytes(), name, 'exec')
helper = runpy.run_path(str(ROOT / 'runtime-source/expat-sec10/rebuild_pyexpat.py'))
preserved = json.loads((DIAG / 'namespace-comparison-source.json').read_bytes())
try:
    helper['require_base_exports'](preserved['exports']['base'], preserved['exports']['new'])
except AssertionError:
    pass
else:
    raise AssertionError('The preserved actual DE69 export regression was accepted')
assert len(preserved['exports']['base']) == 1 and len(preserved['exports']['new']) == 93
preparation = json.loads((OUT / 'preparation-and-preserved-regression.json').read_bytes())
assert preparation['selected31_before_after_identical_to_DE69'] is True
archive = Path(preparation['archive'])
assert sha(archive.read_bytes()) == preparation['archive_sha256_before_after']
assert before == snapshot() and package_before == packages()
for name, item in manifest.items():
    assert sha((DIAG / name).read_bytes()) == item['sha256']
assert not git('status', '--porcelain').strip()
(OUT / 'preimage-DE69-rebuild_pyexpat.py.raw').write_bytes(git('show', PARENT + ':runtime-source/expat-sec10/rebuild_pyexpat.py'))
receipt = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source': HEAD, 'parent': PARENT,
    'scope': 'Windows offline source/mocked-method controls only; no C compiler, linker, native load, Docker, VM, SSH or network execution.',
    'changed_files': changed, 'offline_tests': 41, 'records': records,
    'fixture_methods_match_full_installed_setuptools84_modules': True,
    'original_diagnostic_source_sha256': sha((DIAG / 'source.json').read_bytes()),
    'original_diagnostic_manifest_sha256': sha((DIAG / 'manifest.json').read_bytes()),
    'original_diagnostic_files_quiet': len(manifest), 'actual_preserved_DE69_exports_base': 1,
    'actual_preserved_DE69_exports_failed': 93, 'new_export_gate_rejects_actual_preserved_failure': True,
    'selected31_inputs_and_patch_identical_to_DE69': True, 'PSF_archive_sha256': preparation['archive_sha256_before_after'],
    'source_files_quiet': len(before), 'source_sha256_before_after': before, 'lock_files_unchanged': locks,
    'Dockerfile_pins_source_patch_unchanged': True, 'package_name_version_metadata89_quiet': package_before,
    'python_executable_sha256': sha(Path(sys.executable).read_bytes()),
    'limits': ['No corrected native artifact or final image has been built; OPS12/13 native acceptance pending SEC and coordinated rebuild',
        'Five compiler calls are tested using exact installed method bodies with mocked process/filesystem effects; not a replacement real argv receipt',
        'Only base hidden visibility is selected; historical PGO/LTO and full-command/ELF hash reproducibility are not asserted',
        'SEC10, SEC09, SQLite50812, zlib27171, OS71, runtime imports and SCA remain outside this author static acceptance']}
(OUT / 'source.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps({'source': HEAD, 'tests': 41, 'source_files_quiet': len(before), 'locks_unchanged': len(locks),
                  'diagnostic_files_quiet': len(manifest), 'source_sha256': sha((OUT / 'source.json').read_bytes())}))
