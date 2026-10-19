"""Publish explicit immutable static candidate evidence, preserving native failures."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('F:/mb-expat-call-visibility-20261019')
HERE = Path(__file__).resolve().parent
DIAG = HERE.parent / 'expat-sec10-de69-native-diagnostic-20261019'
TARGET = Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/expat-sec10-call-visibility-author-20261019')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
HEAD = '72c44a1834d7bd9803b4b8846c6c87e85a53bfd3'
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert not git('status', '--porcelain').strip()
source = json.loads((HERE / 'source.json').read_bytes())
assert source['source'] == HEAD and source['offline_tests'] == 41
assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in source['source_sha256_before_after'].items())
assert not TARGET.exists()
for parent in TARGET.absolute().parents:
    if parent.exists():
        assert parent.is_dir() and not parent.is_symlink() and parent.resolve() == parent.absolute()
        assert not (getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400)
TARGET.mkdir()
(TARGET / '.gitattributes').write_bytes(b'* -text\n')
files = {
    'source.json': HERE / 'source.json',
    'preparation-and-preserved-regression.json': HERE / 'preparation-and-preserved-regression.json',
    'tests41.raw.xml': HERE / 'frozen-tests41.xml',
    'tests41.raw.stdout.log': HERE / 'frozen-tests41.stdout.log',
    'tests41.raw.stderr.log': HERE / 'frozen-tests41.stderr.log',
    'quality.stdout.log': HERE / 'frozen-quality.stdout.log',
    'pip-check.stdout.log': HERE / 'frozen-pip-check.stdout.log',
    'first36-tests.stdout.log': HERE / 'offline-tests.stdout.log',
    'fixture-initial-error-transcript.txt': HERE / 'fixture-generation-initial-error-transcript.txt',
    'preimage/DE69-rebuild_pyexpat.py.raw': HERE / 'preimage-DE69-rebuild_pyexpat.py.raw',
    'drivers/frozen_offline_driver.py': HERE / 'frozen_offline_driver.py',
    'drivers/seal_static.py': HERE / 'seal_static.py',
    'diagnostic-inputs/REVIEW.md': DIAG / 'REVIEW.md',
    'diagnostic-inputs/call-flags-capture-source.json': DIAG / 'call-flags-capture-source.json',
    'diagnostic-inputs/compiler-source-capture-source.json': DIAG / 'compiler-source-capture-source.json',
    'diagnostic-inputs/namespace-comparison-source.json': DIAG / 'namespace-comparison-source.json',
}
for name in source['changed_files'] + ['runtime-source/expat-sec10/source-pins.json', 'runtime-source/expat-sec10/13c5f63.patch']:
    files['candidate/' + name] = ROOT / name
records = []
# These exact offline inputs contain no live credentials. Scan structured/log
# publications for actual signed opaque/JWT and CSRF forms as an extra guard.
opaque = re.compile(rb'(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]{20,})?(?![A-Za-z0-9_-])')
csrf = re.compile(rb'(?<![A-Za-z0-9_.-])[0-9]{9,13}\.[a-f0-9]{64}\.[a-f0-9]{64}(?![A-Za-z0-9_.-])')
for name, path in files.items():
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    if name.endswith(('.json', '.xml', '.log')):
        assert not opaque.search(raw) and not csrf.search(raw)
    target = TARGET / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    records.append({'path': name, 'original_path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
(TARGET / 'candidate/delta-DE69.patch').write_bytes(git('diff', '--binary', source['parent'], HEAD))
summary = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source': HEAD, 'parent': source['parent'],
    'status': 'Frozen static candidate; SEC review required before coordinated rebuild. No repaired native artifact or runtime acceptance.',
    'findings_in_scope': ['OPS12 empty argv trace caused by spawn vs call', 'OPS13 extra ELF exports caused by missing base hidden visibility'],
    'preserved_previous_findings': ['OPS08', 'OPS09', 'OPS10'],
    'changed_files': source['changed_files'], 'offline_tests': 41, 'Ruff_exit': 0, 'pip_check_exit': 0,
    'source_files_quiet': 749, 'lock_files_quiet': 12, 'package_name_version_entries_quiet': 89,
    'diagnostic_files_quiet': 66, 'diagnostic_source_sha256': source['original_diagnostic_source_sha256'],
    'diagnostic_manifest_sha256': source['original_diagnostic_manifest_sha256'],
    'PSF_source_sha256': source['PSF_archive_sha256'], 'inputs31_unchanged': True,
    'CAPI_config_namespace_versions_patch_and_pins_unchanged': True,
    'trace_contract': 'Record self.call argv and delegate unchanged; require four actual compile calls and one link before publishing future provenance. Offline checks mock effects and are not real compiler argv evidence.',
    'visibility_contract': 'Select only -fvisibility=hidden from two exact-base module flag variables; authenticate installed Makefile; do not replay PGO/LTO or assert full historical reproduction.',
    'export_contract': 'Future nm defined exports must equal exact original [PyInit_pyexpat]; new gate rejects preserved measured DE69 list93.',
    'limits': source['limits'], 'files': records}
(TARGET / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
manifest = {}
for path in sorted(TARGET.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        raw = path.read_bytes()
        manifest[path.relative_to(TARGET).as_posix()] = {'bytes': len(raw), 'sha256': sha(raw)}
raw = (json.dumps(manifest, indent=2) + '\n').encode()
(TARGET / 'manifest.json').write_bytes(raw)
print(json.dumps({'path': str(TARGET), 'files': len(manifest) + 1, 'source_sha256': sha((TARGET / 'source.json').read_bytes()),
                  'summary_sha256': sha((TARGET / 'summary.json').read_bytes()), 'manifest_sha256': sha(raw)}))
