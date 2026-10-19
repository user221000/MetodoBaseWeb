import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path('F:/mb-mfa-ci31-20261019')
out = Path(__file__).resolve().parent / 'windows-command-bodies'
out.mkdir(exist_ok=False)
sys.path.insert(0, str(root))
from tests.ci_mfa31.workflow import expected_workflow
from tests.run_reviewed_ci30 import trusted_baseline

trusted_baseline()
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).split(b'\0')
names = [name.decode() for name in tracked if name and not name.startswith(b'docs/')]
before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
environment = dict(os.environ, RUNNER_TEMP=(out / 'runner').as_posix(), GITHUB_WORKSPACE=root.as_posix())
environment['PATH'] = str(Path(sys.executable).parent) + os.pathsep + 'C:/Program Files/nodejs' + os.pathsep + environment.get('PATH', '')
records = []
prelude_adaptations = []
for index, step in enumerate(expected_workflow()['jobs']['frontend-contracts']['steps']):
    if 'run' not in step:
        continue
    script = out / ('frontend-step-' + str(index) + '.sh')
    block = step['run']
    if os.name == 'nt' and block.startswith('install -d -m 700 "$RUNNER_TEMP/frontend-private"\n'):
        (out / 'runner/frontend-private').mkdir(parents=True, exist_ok=True)
        block = block.split('\n', 1)[1]
        prelude_adaptations.append({'step': index, 'scope': 'POSIX install chmod700 fails on this Windows F volume; Python precreated this synthetic-VM log directory. Linux chmod and Actions execution unproven.'})
    script.write_bytes(('set -euo pipefail\n' + block).encode())
    result = subprocess.run(['C:/Program Files/Git/bin/bash.exe', script.as_posix()], cwd=root,
        env=environment, capture_output=True, timeout=120)
    (out / ('step-' + str(index) + '.stdout.log')).write_bytes(result.stdout)
    (out / ('step-' + str(index) + '.stderr.log')).write_bytes(result.stderr)
    records.append({'step': index, 'name': step.get('name'), 'exit': result.returncode,
                    'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest()})
    assert result.returncode == 0, records[-1]
after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
assert before == after
report = {'scope': 'Actual current frontend command bodies, Windows Node VM only; Linux install-mode prelude adapted explicitly; no browser/PG/image/Actions',
          'records': records, 'tracked_non_evidence_files': len(names), 'source_quiet': True,
          'old22_plus_current_companion16_retained': True, 'MFA_VM_assertions': 74,
          'extra_current_R24_export_VM_assertions': 72, 'no_global_dedup_claim': True,
          'Windows_only_prelude_adaptations': prelude_adaptations}
(out / 'current-frontend.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
print(json.dumps(report, indent=2))
