"""Publish explicit closed author evidence; preserve all prior prefixes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path('F:/mb-mfa-ci31-20261019')
HERE = Path(__file__).resolve().parent
TARGET = Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/mfa31-ci-three-boundaries-fix-20261019')
sys.path.insert(0, str(ROOT))
from tests.ci_mfa31.publish import scan
from tests.run_reviewed_ci30 import new_directory

digest = lambda raw: hashlib.sha256(raw).hexdigest()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
head = git('rev-parse', 'HEAD').decode().strip()
assert head == 'ed4a3be11fb1e921962182812362b515afd8885a'
assert not git('status', '--porcelain').strip()
frozen = json.loads((HERE / 'frozen-source-gates/receipt.json').read_bytes())
frontend = json.loads((HERE / 'frontend-windows-command-bodies/receipt.json').read_bytes())
assert frozen['new_tests'] == 205 and frontend['module_count'] == 32 and frontend['assertion_executions'] == 519
assert all(digest((ROOT / name).read_bytes()) == value for name, value in frozen['source_sha256_before_after'].items())
new_directory(TARGET)
(TARGET / '.gitattributes').write_bytes(b'* -text\n')
sources = {
    'REVIEW.md': HERE / 'REVIEW.md',
    'gates/receipt.json': HERE / 'frozen-source-gates/receipt.json',
    'gates/full-review.json': HERE / 'frozen-source-gates/full-review/review.json',
    'gates/trust-projected.xml': HERE / 'frozen-source-gates/trust-projected.xml',
    'frontend/receipt.json': HERE / 'frontend-windows-command-bodies/receipt.json',
    'frontend/snapshot25.raw.json': HERE / 'frontend-windows-command-bodies/raw/daily-plan-snapshot-current31.json',
    'frontend/legacy18.raw.json': HERE / 'frontend-windows-command-bodies/raw/personal-diary-controller.json',
    'frontend/aggregation-error-transcript.txt': HERE / 'frontend-aggregation-error-transcript.txt',
    'qa-inputs.json': HERE / 'qa-inputs.json',
    'mutant/checker-main-false-success.raw.py': HERE / 'frozen-source-gates/main-only-mutant/tests/check_mfa31_reports.py',
    'mutant/authentic-checker.raw.py': ROOT / 'tests/check_mfa31_reports.py',
}
for name in ('frozen_fix_driver.py', 'frontend_driver.py', 'finalize_frontend.py', 'seal_fix.py'):
    sources['drivers/' + name] = HERE / name
for label in ('actual-empty-cli', 'mutant-empty-cli-false-success', 'mutant-full-verifier-rejected-before-import'):
    for channel in ('stdout', 'stderr'):
        sources['mutant/' + label + '.' + channel + '.raw.log'] = HERE / ('frozen-source-gates/' + label + '.private.' + channel + '.log')
for name in frozen['changed_files']:
    sources['source/' + name] = ROOT / name
records = []
for name, source in sources.items():
    assert source.is_file() and not source.is_symlink()
    raw = source.read_bytes()
    if name.endswith(('.json', '.xml', '.log')):
        scan(raw)
    target = TARGET / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    records.append({'path': name, 'original_path': str(source), 'bytes': len(raw), 'sha256': digest(raw)})
patch = git('diff', '--binary', 'e0c3f8b6d7a812c2b46d73748d56da72782c9f04', head)
(TARGET / 'source/delta-e0.patch').write_bytes(patch)
e0 = TARGET.parent / 'mfa31-ci-e0-offline-20261019/manifest.json'
assert digest(e0.read_bytes()) == 'd9e39537dbd89395be3770ca2aec4565e50d94cdf2bfa3627b4a3ce684901feb'
summary = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source': head,
    'parent_e0': 'e0c3f8b6d7a812c2b46d73748d56da72782c9f04',
    'product_equivalent_to': '4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae',
    'status': 'Frozen author offline pass; independent QA and actual current PG/image/browser/Actions pending. No CI31 runtime acceptance.',
    'prior_e0_preserved_manifest_sha256': digest(e0.read_bytes()), 'changed_CI_files': 11,
    'workflow_canaries': 145, 'Bash_syntax_blocks': 115, 'offline_tests': 205,
    'CLI_negative_real_subprocesses': 132, 'positive173_CLI': 1, 'SQL_fragment_mock_cases': 24,
    'main_only_false_success_mutant_rejected_before_import': True, 'missing_role_marker_rejected': True,
    'frontend': {'modules': 32, 'executions': 519, 'unique_criteria_claim': False,
        'snapshot25': {'new': 7, 'legacy_replayed': 18}},
    'preserved': {'helpers': 23, 'locks': 8, 'actual_PG_nodeids_collected_only': 173, 'source_files_quiet': 932,
        'package_name_version_entries_quiet': 89, 'HIST30_full_and_VM348': 'Previous frozen573 receipt; not rerun in this focal fix'},
    'limits': ['No PG, Chrome, Docker, QEMU, image or Actions execution in this phase',
        'SQL witness canaries use mocked results; actual physical flags still require PG/image execution',
        'Windows frontend command bodies adapt only the POSIX chmod700 prelude; Linux permission evidence pending',
        'Initial frontend receipt collector report[] shape error preserved; finalizer consolidates same passed RAW, no rerun',
        'Package inventory is Name/version metadata, not full installed package byte hashes'],
    'files': records}
raw = (json.dumps(summary, indent=2) + '\n').encode()
scan(raw)
(TARGET / 'summary.json').write_bytes(raw)
manifest = []
for path in sorted(TARGET.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        raw = path.read_bytes()
        manifest.append({'path': path.relative_to(TARGET).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)})
raw = (json.dumps({'scope': 'Immutable closed author offline fix evidence, no runtime acceptance', 'files': manifest}, indent=2) + '\n').encode()
(TARGET / 'manifest.json').write_bytes(raw)
print(json.dumps({'path': str(TARGET), 'files': len(manifest) + 1, 'manifest_sha256': digest(raw),
                  'summary_sha256': digest((TARGET / 'summary.json').read_bytes())}))
