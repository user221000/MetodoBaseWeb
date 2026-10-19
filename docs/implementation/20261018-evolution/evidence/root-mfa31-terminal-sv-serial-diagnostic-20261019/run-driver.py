"""Run one frozen current31 phase; original failing diagnostics stay immutable."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root=Path(r'F:\mb-mfa31-compose-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
head=sys.argv[1];mode=sys.argv[2]
assert re.fullmatch('[a-f0-9]{40}',head) and mode in {'serial','parallel'}
out=tmp/('metodobase-mfa31-composed-'+mode+'-terminal-sv-20261019');assert not out.exists()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain','--untracked-files=no')
names=git('ls-files','-z').decode().split('\0')[:-1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def photo():
    return {'files':{name:sha((root/name).read_bytes()) for name in names},
     'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
     'python_sha256':sha(Path(sys.executable).read_bytes())}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
before=photo();(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
pip_before=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-before.raw.log').write_bytes(pip_before.stdout+pip_before.stderr);assert pip_before.returncode==0
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',COVERAGE_FILE=str(out/'.coverage'))
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT']:
    env.pop(key,None)
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests','--ignore=tests/test_login_desktop.py',
 '--ignore=tests/test_desktop_entrypoints.py','-q','--tb=short','--junitxml='+str(out/'results.xml')]
if mode=='serial':command+=['--cov','--cov-report=xml:'+str(out/'coverage.xml'),'--cov-report=json:'+str(out/'coverage.json')]
else:command+=['--shuffle-seed=20261018','-n','2']
start=time.monotonic();timed_out=False
try:result=subprocess.run(command,cwd=root,env=env,capture_output=True,timeout=1800)
except subprocess.TimeoutExpired as error:
    timed_out=True;result=subprocess.CompletedProcess(command,None,error.stdout or b'',error.stderr or b'')
(out/'stdout.private.raw.log').write_bytes(result.stdout);(out/'stderr.private.raw.log').write_bytes(result.stderr)
cases=ET.parse(out/'results.xml').findall('.//testcase') if(out/'results.xml').exists() else []
identity=lambda c:c.get('classname','')+'::'+c.get('name','')
failures=[{'case':identity(c),'kind':kind,'message':c.find(kind).get('message','')} for c in cases for kind in ['failure','error'] if c.find(kind) is not None]
skips=[{'case':identity(c),'message':c.find('skipped').get('message','')} for c in cases if c.find('skipped') is not None]
reference=ET.parse(tmp/'metodobase-mfa31-broad-diagnostic-20261019/serial.xml').findall('.//testcase')
reference_skips=[{'case':identity(c),'message':c.find('skipped').get('message','')} for c in reference if c.find('skipped') is not None]
after=photo();(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
pip_after=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-after.raw.log').write_bytes(pip_after.stdout+pip_after.stderr)
summary={'head':head,'mode':mode,'exit':result.returncode,'timed_out':timed_out,'seconds':time.monotonic()-start,
 'cases':len(cases),'failures':failures,'skips':skips,'known_windows_skip_exact':skips==reference_skips,
 'previous_diagnostic_identities_preserved':{identity(c) for c in reference}.issubset({identity(c) for c in cases}),
 'sources':len(names),'packages':len(before['packages']),'sources_packages_python_exact':before==after,
 'pip_before':pip_before.returncode,'pip_after':pip_after.returncode,
 'scope':'Frozen composed schema31 SaaS suite; no PostgreSQL/Redis/Chrome/Linux/Actions/SLO claim. One exact historical Windows symlink skip remains disclosed.'}
(out/'summary.private.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps({key:summary[key] for key in ['head','mode','exit','timed_out','seconds','cases','known_windows_skip_exact','previous_diagnostic_identities_preserved','sources','packages','sources_packages_python_exact','pip_before','pip_after']}))
print(json.dumps({'failures':len(failures),'skips':len(skips)}))
assert before==after and pip_after.returncode==0
assert result.returncode==0 and not failures and len(cases)>=2598
assert summary['known_windows_skip_exact'] and summary['previous_diagnostic_identities_preserved']
