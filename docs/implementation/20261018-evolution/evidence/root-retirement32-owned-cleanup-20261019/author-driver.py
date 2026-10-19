from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path(r'F:\mb-retirement32-owned-cleanup-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-retirement32-cleanup-author-20261019')
base = '219f89a5ee0196061fea5b67e36ae07daf7f4316'
peer = '6147f9300989f4115cf8d270025a3805926d32b1'
ev = 'docs/implementation/20261018-evolution/evidence/security-progress-retirement-independent-20261019/'
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, indent=2) + '\n').encode()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.autocrlf=false', *args], cwd=root)
assert not out.exists() and git('rev-parse', 'HEAD').decode().strip() == base
canary = git('show', peer + ':' + ev + 'independent-faults.py')
assert sha(canary) == '1002b027643932e0579eb5cf46b264ec46f129aea9f0f4346be0b579f7bd757a'
test = root / 'tests/test_progress_retirement_cleanup.py'
assert not test.exists()
test.write_bytes(canary)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'route-before.GitLF.py').write_bytes(git('show', base + ':web/routes/progress_retirement.py'))

def photo():
    names = [path for stem in ['web', 'api', 'core', 'config', 'tests'] for path in (root / stem).rglob('*.py') if '__pycache__' not in path.parts]
    return {'sources': {path.relative_to(root).as_posix(): sha(path.read_bytes()) for path in sorted(names)},
        'packages': sorted((dist.metadata['Name'], dist.version) for dist in importlib.metadata.distributions()),
        'python': sha(Path(sys.executable).read_bytes()), 'base_python': sha(Path(sys._base_executable).read_bytes())}

before = photo()
assert len(before['packages']) == 89
(out / 'before.json').write_bytes(enc(before))
pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(out / 'pip-before.RAW.log').write_bytes(pip.stdout + pip.stderr)
assert pip.returncode == 0
child = '''from pathlib import Path
import os,sys
root=Path(sys.argv[1]);out=Path(sys.argv[2]);os.chdir(root);sys.path.insert(0,str(root))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
import pytest
raise SystemExit(pytest.main(['tests/test_progress_retirement_cleanup.py','-q','--tb=short','--basetemp='+str(out/'pytest-run'),'--junitxml='+str(out/'results.xml'),'-o','cache_dir='+str(out/'cache')]))
'''
(out / 'child.py').write_bytes(child.encode())
result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(out / 'child.py'), str(root), str(out)], cwd=root,
    env=dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1'), capture_output=True, timeout=600)
(out / 'stdout.private.RAW.log').write_bytes(result.stdout)
(out / 'stderr.private.RAW.log').write_bytes(result.stderr)
after = photo()
(out / 'after.json').write_bytes(enc(after))
pip2 = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(out / 'pip-after.RAW.log').write_bytes(pip2.stdout + pip2.stderr)
cases = [{'case': node.get('classname') + '::' + node.get('name'), 'outcome': next((kind for kind in ['error', 'failure', 'skipped'] if node.find(kind) is not None), 'passed')} for node in ET.parse(out / 'results.xml').findall('.//testcase')]
summary = {'base': base, 'exit': result.returncode, 'cases': cases, 'sources': len(before['sources']), 'packages': len(before['packages']),
    'sources_packages_python_exact': before == after, 'pip_before': pip.returncode, 'pip_after': pip2.returncode,
    'same_peer_canary_bytes': sha(test.read_bytes()), 'scope': 'Six maintained SQLite fault cases only; PG independent replay remains required. Private runner directory ACL at creation not attested.'}
(out / 'summary.json').write_bytes(enc(summary))
print(json.dumps({'exit': result.returncode, 'cases': len(cases), 'outcomes': {kind: sum(row['outcome'] == kind for row in cases) for kind in ['passed', 'failure', 'error', 'skipped']}, 'quiet': before == after}))
assert result.returncode == 0 and len(cases) == 6 and all(row['outcome'] == 'passed' for row in cases)
assert before == after and pip2.returncode == 0
