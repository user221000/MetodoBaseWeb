from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

root=Path(r'F:\mb-mfa31-terminal-sv-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
phase=sys.argv[1];assert phase in {'before','after'}
out=tmp/('metodobase-mfa31-terminal-sv-'+phase+'-20261019');assert not out.exists()
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()=='809eab28c40c112cb6e3c9d8caceebae28683abd'
names=sorted(set(git('ls-files','-z').decode().split('\0')[:-1]+['tests/test_mfa31_terminal_session_version.py']))
sha=lambda data:hashlib.sha256(data).hexdigest()
def photo():
    return {'files':{name:sha((root/name).read_bytes()) for name in names},
     'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python_sha256':sha(Path(sys.executable).read_bytes())}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
before=photo();(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
pip_before=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-before.raw.log').write_bytes(pip_before.stdout+pip_before.stderr);assert pip_before.returncode==0
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py',
 'tests/test_recovery28_review.py::test_last_eligible_session_version_consumes_once_and_next_request_stays_generic',
 'tests/test_mfa31_terminal_session_version.py',
 'tests/test_mfa31_http.py::test_enrollment_login_one_use_and_status_never_repeats_secrets',
 'tests/test_mfa31_http.py::test_recovery_one_use_and_password_reset_does_not_disable_factor',
 '-q','--tb=short','--junitxml='+str(out/'results.xml')]
run=subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=300)
(out/'stdout.private.raw.log').write_bytes(run.stdout);(out/'stderr.private.raw.log').write_bytes(run.stderr)
cases=ET.parse(out/'results.xml').findall('.//testcase')
after=photo();(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
pip_after=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-after.raw.log').write_bytes(pip_after.stdout+pip_after.stderr)
summary={'phase':phase,'source_base':'809eab28c40c112cb6e3c9d8caceebae28683abd','cases':len(cases),'exit':run.returncode,
 'passed':sum(not any(c.find(kind) is not None for kind in ['failure','error','skipped']) for c in cases),
 'failed':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),
 'skipped':sum(c.find('skipped') is not None for c in cases),'sources':len(names),'packages':len(before['packages']),
 'sources_packages_python_exact':before==after,'pip_before':pip_before.returncode,'pip_after':pip_after.returncode,
 'test_source_sha256':sha((root/'tests/test_mfa31_terminal_session_version.py').read_bytes()),
 'scope':'Author same-driver real password/factor HTTP and SQLite metadata fixtures; no PG/Chrome/provider or minted positive bearer use in new cases.'}
(out/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary));assert before==after and pip_after.returncode==0
if phase=='after':assert run.returncode==0 and summary['passed']==14
