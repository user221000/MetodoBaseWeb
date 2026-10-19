"""Execute frozen frontend command bodies on Windows, with one declared chmod adaptation."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path('F:/mb-mfa-ci31-20261019')
OUT = Path(__file__).resolve().parent / 'frontend-windows-command-bodies'
OUT.mkdir(exist_ok=False)
sys.path.insert(0, str(ROOT))
from tests.ci_mfa31.workflow import expected_workflow
from tests.run_reviewed_ci30 import trusted_baseline

trusted_baseline()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == 'ed4a3be11fb1e921962182812362b515afd8885a'
assert not git('status', '--porcelain').strip()
names = [n.decode() for n in git('ls-files', '-z').split(b'\0') if n and not n.startswith(b'docs/')]
photo = lambda: {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
before = photo()
workflow = expected_workflow()
steps = workflow['jobs']['frontend-contracts']['steps']
generated, modules = set(), []
for step in steps:
    for line in step.get('run', '').splitlines():
        if line.startswith('node tests/') and ' > ' in line:
            command, filename = line.split(' > ', 1)
            modules.append((command, filename))
            generated.add(filename)
        if line.startswith('python tests/e2e/normalize_followup_report.py '):
            generated.add(shlex.split(line)[3])
assert len(modules) == 32
assert all(Path(name).name == name and not (ROOT / name).exists() for name in generated)
env = dict(os.environ, RUNNER_TEMP=(OUT / 'runner').as_posix(), GITHUB_WORKSPACE=ROOT.as_posix())
env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + 'C:/Program Files/nodejs' + os.pathsep + env.get('PATH', '')
records, adaptations = [], []
for index, step in enumerate(steps):
    if 'run' not in step:
        continue
    block = step['run']
    if os.name == 'nt' and block.startswith('install -d -m 700 "$RUNNER_TEMP/frontend-private"\n'):
        (OUT / 'runner/frontend-private').mkdir(parents=True, exist_ok=True)
        block = block.split('\n', 1)[1]
        adaptations.append({'step': index, 'scope': 'Windows command-body probe precreated only its synthetic VM log folder. POSIX chmod700, Linux and Actions are not demonstrated.'})
    script = OUT / ('step-' + str(index) + '.sh')
    script.write_bytes(('set -euo pipefail\n' + block).encode())
    result = subprocess.run(['C:/Program Files/Git/bin/bash.exe', script.as_posix()], cwd=ROOT, env=env,
                            capture_output=True, timeout=120)
    (OUT / ('step-' + str(index) + '.private.stdout.log')).write_bytes(result.stdout)
    (OUT / ('step-' + str(index) + '.private.stderr.log')).write_bytes(result.stderr)
    records.append({'step': index, 'name': step.get('name'), 'exit': result.returncode,
                    'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest()})
    assert result.returncode == 0, records[-1]
rows = []
for command, filename in modules:
    report = json.loads((ROOT / filename).read_bytes())
    cases = report.get('results', report.get('checks'))
    assert isinstance(cases, list) and cases
    total = report.get('total', len(cases))
    passed = report.get('passed', sum(not isinstance(case, dict) or case.get('passed', True) is True for case in cases))
    assert type(total) is int and total == passed == len(cases)
    rows.append({'module': command, 'report': filename, 'passed': passed, 'total': total})
assert sum(row['total'] for row in rows) == 519
legacy = json.loads((ROOT / 'personal-diary-controller.json').read_bytes())
snapshot = json.loads((ROOT / 'daily-plan-snapshot-current31.json').read_bytes())
legacy_names = {row['case'] for row in legacy['results']}
snapshot_names = {row['case'] for row in snapshot['results']}
assert len(legacy_names) == 18 and len(snapshot_names) == 25 and legacy_names < snapshot_names
assert len(snapshot_names - legacy_names) == 7
rawdir = OUT / 'raw'
rawdir.mkdir()
manifest = []
for name in sorted(generated):
    source, target = ROOT / name, rawdir / name
    assert source.is_file() and not source.is_symlink()
    assert source.resolve().parent == ROOT.resolve() and target.absolute().parent == rawdir.absolute()
    raw = source.read_bytes()
    manifest.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    source.replace(target)
assert before == photo() and not git('status', '--porcelain').strip()
receipt = {'source': 'ed4a3be11fb1e921962182812362b515afd8885a', 'modules': rows,
    'module_count': len(rows), 'assertion_executions': sum(row['total'] for row in rows),
    'unique_criteria_claim': False, 'snapshot': {'passed': 25, 'legacy_replayed': 18, 'new': 7},
    'tracked_non_evidence_files_quiet': len(names), 'records': records, 'raw_reports': manifest,
    'Windows_only_prelude_adaptations': adaptations,
    'scope': 'Actual Node VM command bodies and their maintained report gates. No browser, HTTP, PG, image, Linux permission or Actions execution.'}
(OUT / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps({'modules': len(rows), 'executions': 519, 'snapshot25': True, 'source_quiet': True}))
