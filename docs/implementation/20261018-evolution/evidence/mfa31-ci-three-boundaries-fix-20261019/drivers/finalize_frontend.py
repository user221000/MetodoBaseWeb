"""Finish only the receipt for already-executed frontend commands; do not rerun Node."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path('F:/mb-mfa-ci31-20261019')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'frontend-windows-command-bodies'
sys.path.insert(0, str(ROOT))
from tests.ci_mfa31.workflow import expected_workflow
from tests.ci_mfa31.publish import scan

digest = lambda value: hashlib.sha256(value).hexdigest()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == 'ed4a3be11fb1e921962182812362b515afd8885a'
before = json.loads((HERE / 'frozen-source-gates/receipt.json').read_bytes())['source_sha256_before_after']
assert all(digest((ROOT / name).read_bytes()) == sha for name, sha in before.items())
generated, modules, records, adaptations = set(), [], [], []
for index, step in enumerate(expected_workflow()['jobs']['frontend-contracts']['steps']):
    if 'run' not in step:
        continue
    block = step['run']
    if block.startswith('install -d -m 700 "$RUNNER_TEMP/frontend-private"\n'):
        block = block.split('\n', 1)[1]
        adaptations.append({'step': index, 'scope': 'Windows command-body probe precreated only its synthetic VM log folder. POSIX chmod700, Linux and Actions are not demonstrated.'})
    script = OUT / ('step-' + str(index) + '.sh')
    assert script.read_bytes() == ('set -euo pipefail\n' + block).encode()
    stdout = OUT / ('step-' + str(index) + '.private.stdout.log')
    stderr = OUT / ('step-' + str(index) + '.private.stderr.log')
    assert stdout.is_file() and stderr.is_file()
    records.append({'step': index, 'name': step.get('name'), 'exit': 0,
        'exit_evidence': 'Executed frontend_driver.py reached aggregation after its sequential returncode==0 asserts for every step; preserved aggregation-error transcript.',
        'script_sha256': digest(script.read_bytes()), 'stdout_sha256': digest(stdout.read_bytes()),
        'stderr_sha256': digest(stderr.read_bytes())})
    for line in step['run'].splitlines():
        if line.startswith('node tests/') and ' > ' in line:
            command, name = line.split(' > ', 1)
            modules.append((command, name))
            generated.add(name)
        if line.startswith('python tests/e2e/normalize_followup_report.py '):
            generated.add(shlex.split(line)[3])
rows = []
for command, name in modules:
    report = json.loads((ROOT / name).read_bytes())
    cases = next((report[key] for key in ('results', 'checks', 'report') if isinstance(report.get(key), list)), None)
    assert cases and all(not isinstance(case, dict) or case.get('passed', True) is True for case in cases)
    total, passed = report.get('total', len(cases)), report.get('passed', len(cases))
    assert type(total) is int and type(passed) is int and total == passed == len(cases)
    rows.append({'module': command, 'report': name, 'passed': passed, 'total': total})
assert len(rows) == 32 and sum(row['total'] for row in rows) == 519
legacy = json.loads((ROOT / 'personal-diary-controller.json').read_bytes())
snapshot = json.loads((ROOT / 'daily-plan-snapshot-current31.json').read_bytes())
legacy_names, snapshot_names = ({row['case'] for row in value['results']} for value in (legacy, snapshot))
assert len(legacy_names) == 18 and len(snapshot_names) == 25 and legacy_names < snapshot_names
assert len(snapshot_names - legacy_names) == 7
manifest = []
rawdir = OUT / 'raw'
rawdir.mkdir(exist_ok=False)
for name in sorted(generated):
    source, target = ROOT / name, rawdir / name
    assert Path(name).name == name and source.resolve().parent == ROOT.resolve()
    assert target.absolute().parent == rawdir.absolute() and source.is_file() and not source.is_symlink()
    raw = source.read_bytes()
    manifest.append({'path': name, 'bytes': len(raw), 'sha256': digest(raw)})
    source.replace(target)
assert all(digest((ROOT / name).read_bytes()) == sha for name, sha in before.items())
assert not git('status', '--porcelain').strip()
receipt = {'source': 'ed4a3be11fb1e921962182812362b515afd8885a', 'modules': rows,
    'module_count': 32, 'assertion_executions': 519, 'unique_criteria_claim': False,
    'snapshot': {'passed': 25, 'legacy_replayed': 18, 'new': 7}, 'tracked_non_evidence_files_quiet': len(before),
    'records': records, 'raw_reports': manifest, 'Windows_only_prelude_adaptations': adaptations,
    'aggregation_correction': 'First collector omitted report[] legacy shape after all run gates passed. Its source/error retained. This receipt was completed from the same RAW without another test execution.',
    'scope': 'Actual Node VM command bodies and maintained report gates. No browser, HTTP, PG, image, Linux permissions or Actions execution.'}
raw = (json.dumps(receipt, indent=2) + '\n').encode()
scan(raw)
(OUT / 'receipt.json').write_bytes(raw)
print(json.dumps({'modules': 32, 'executions': 519, 'snapshot25': True, 'sources_quiet': True,
                  'receipt_sha256': digest(raw)}))
