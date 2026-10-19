from pathlib import Path, PurePosixPath
import ast
import hashlib
import importlib.metadata
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(r'F:\mb-security-terminal-sv-peer-20261019')
MAIN = Path(r'F:\MetodoBaseWeb-execution-20261018')
PRIVATE = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-sec15-peer-private-20261019')
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/security-terminal-sv-peer-independent-20261019'
HEAD = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *a: subprocess.check_output(['git', '--no-replace-objects', *a], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert not git('status', '--porcelain', '--untracked-files=no')
assert not PRIVATE.exists() and not OUT.exists()
test = ROOT / 'tests/test_security_terminal_sv_peer.py'
ast.parse(test.read_text(encoding='utf8'))
author = MAIN / 'docs/implementation/20261018-evolution/evidence/root-mfa31-terminal-sv-author-20261019'
assert sha((author / 'manifest.json').read_bytes()) == '5d8220d6623bd585b50319de6afddaebb056bb3128e5cabdb9fa1cc3e66c6d6a'
assert sha((author / 'source.json').read_bytes()) == 'a62f8ef89ba32bba2eb3f705b453f633bf58d8125b676901580fd99b02c3879f'
manifest = json.loads((author / 'manifest.json').read_bytes())
for name, entry in manifest.items():
    data = (author / name).read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], name
for name in ['web/services/mfa_service.py', 'web/static/js/mfa-ui.js', 'tests/test_mfa31_terminal_session_version.py']:
    assert git('show', HEAD + ':' + name) == (author / 'source/after-GitLF' / name).read_bytes(), name

PRIVATE.mkdir()
OUT.mkdir(parents=True)
(OUT / '.gitattributes').write_bytes(b'* -text\n')
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
(OUT / 'test_security_terminal_sv_peer.py').write_bytes(test.read_bytes())
names = sorted(set(git('ls-files', '-z').decode().split('\0')[:-1] + ['tests/test_security_terminal_sv_peer.py']))

def photo():
    return {'files': {n: sha((ROOT / n).read_bytes()) for n in names},
        'packages': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
        'python_sha256': sha(Path(sys.executable).read_bytes())}

def dump(name, data):
    (OUT / name).write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode('utf8'))

before = photo()
dump('before.json', before)
pip_before = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(OUT / 'pip-before.raw.log').write_bytes(pip_before.stdout + pip_before.stderr)
assert pip_before.returncode == 0
command = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py',
 'tests/test_recovery28_review.py::test_last_eligible_session_version_consumes_once_and_next_request_stays_generic',
 'tests/test_mfa31_terminal_session_version.py',
 'tests/test_mfa31_http.py::test_enrollment_login_one_use_and_status_never_repeats_secrets',
 'tests/test_mfa31_http.py::test_recovery_one_use_and_password_reset_does_not_disable_factor',
 'tests/test_security_terminal_sv_peer.py', '-q', '--tb=short', '--junitxml=' + str(PRIVATE / 'results.xml')]
run = subprocess.run(command, cwd=ROOT, env=dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1'),
    capture_output=True, timeout=480)
(PRIVATE / 'stdout.raw.log').write_bytes(run.stdout)
(PRIVATE / 'stderr.raw.log').write_bytes(run.stderr)
cases = ET.parse(PRIVATE / 'results.xml').findall('.//testcase')
structural = [{'classname': c.get('classname'), 'name': c.get('name'),
    'outcome': next((k for k in ['failure', 'error', 'skipped'] if c.find(k) is not None), 'passed')} for c in cases]
dump('cases.STRUCTURAL.json', structural)
after = photo()
dump('after.json', after)
pip_after = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True)
(OUT / 'pip-after.raw.log').write_bytes(pip_after.stdout + pip_after.stderr)
dump('summary.json', {'source_head': HEAD, 'author_primary_files_authenticated': len(manifest),
    'case_count': len(cases), 'same_author_cases': 14, 'own_cases': len(cases) - 14,
    'outcomes': {k: sum(c['outcome'] == k for c in structural) for k in ['passed', 'failure', 'error', 'skipped']},
    'exit': run.returncode, 'source_count': len(names), 'packages': len(before['packages']),
    'sources_packages_python_exact': before == after,
    'pip_before': pip_before.returncode, 'pip_after': pip_after.returncode,
    'scope': 'Independent focal SQLite HTTP/SQL/in-memory corruption canaries; actual password and factor for positive HTTP. No PG, browser, VM, provider or production claim.'})
dump('private-originals.json', {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
    for p in sorted(PRIVATE.iterdir())})
print((OUT / 'summary.json').read_text(encoding='utf8'))
assert before == after and pip_after.returncode == 0
assert run.returncode == 0 and len(cases) == 41
