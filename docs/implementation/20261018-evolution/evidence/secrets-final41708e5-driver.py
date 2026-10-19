import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import tomllib

root = Path('F:/mbscan41708e5-a')
out = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-secrets-final41708e5-attempt2-20261019')
out.mkdir(exist_ok=False)
head = '41708e59622d1128c421d1975e3c6dbc16a6f008'
sha = lambda b: hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, check=True).stdout
assert git('rev-parse', 'HEAD').decode().strip() == head
assert not git('status', '--porcelain', '--untracked-files=normal')
original = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-secrets-c28-proposals-context-20261019/with-historical-literals-PROPOSAL.toml').read_bytes()
configuration = (root / '.gitleaks.toml').read_bytes()
assert sha(original) == 'd3b17d6bcc20a0acbe88ea2f9314ca241a45cd4eb856decf2585bab09cea68dc'
assert configuration == git('show', head + ':.gitleaks.toml')
assert original.replace(b'\r\n', b'\n') == configuration.replace(b'\r\n', b'\n')
assert tomllib.loads(original.decode()) == tomllib.loads(configuration.decode())
tool = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1/gitleaks.exe')
assert sha(tool.read_bytes()) == '17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c'
started = time.monotonic()
run = subprocess.run([sys.executable, 'scripts/scan_secrets.py', '--gitleaks', str(tool),
                      '--report', str(out / 'raw-sanitized-report.json')], cwd=root,
                     capture_output=True, timeout=170)
(out / 'scan.log').write_bytes(run.stdout + run.stderr)
elapsed = time.monotonic() - started
raw = json.loads((out / 'raw-sanitized-report.json').read_text(encoding='utf-8'))
summary = {'source_commit': head, 'tree_oid': git('rev-parse', head + '^{tree}').decode().strip(),
           'exit': run.returncode, 'seconds': elapsed, 'source_file_count': len(raw['files']),
           'source_inventory_sha256': sha(json.dumps(raw['files'], sort_keys=True, separators=(',', ':')).encode()),
           'raw_finding_count': raw['raw_finding_count'], 'classified_finding_count': raw['classified_finding_count'],
           'remaining_finding_count': raw['remaining_finding_count'], 'source_stable': raw['source_stable'],
           'changed_files': raw['changed_files'], 'findings': raw['findings'],
           'classified_findings': raw['classified_findings'], 'tool': raw['tool'], 'version': raw['version'],
           'binary_sha256': raw['binary_sha256'], 'configuration_raw_sha256': sha(configuration),
           'reviewed_configuration_raw_sha256': sha(original), 'toml_semantics_and_lf_bytes_equal': True,
           'wrapper_sha256': sha((root / 'scripts/scan_secrets.py').read_bytes()),
           'scope': raw['scope'], 'tracked_and_untracked_status_after': git('status', '--porcelain', '--untracked-files=normal').decode(),
           'raw_report_retained_outside_deliverable': str(out / 'raw-sanitized-report.json'),
           'artifacts': {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: summary[k] for k in ['source_commit', 'exit', 'source_file_count', 'raw_finding_count',
      'classified_finding_count', 'remaining_finding_count', 'source_stable', 'seconds']}))
