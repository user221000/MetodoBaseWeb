"""Diagnose the complete current SaaS suite on the isolated composed MFA31 candidate."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root=Path(r'F:\mb-mfa31-compose-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-broad-diagnostic-20261019')
head='bd34893c4b6f806041b0cc6b7f156e9286886748'
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain','--untracked-files=no')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
names=git('ls-files','-z').decode().split('\0')[:-1]
def photo():
    return {'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
     'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo()
(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'before-pip.raw.log').write_bytes(pip.stdout+pip.stderr)
assert pip.returncode==0
environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',COVERAGE_FILE=str(out/'.coverage'))
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT']:
    environment.pop(key,None)
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests',
 '--ignore=tests/test_login_desktop.py','--ignore=tests/test_desktop_entrypoints.py',
 '-q','--tb=short','--maxfail=20','--cov','--cov-report=xml:'+str(out/'coverage.xml'),
 '--cov-report=json:'+str(out/'coverage.json'),'--junitxml='+str(out/'serial.xml')]
started=time.monotonic()
timed_out=False
try:result=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=1500)
except subprocess.TimeoutExpired as error:
    timed_out=True
    result=subprocess.CompletedProcess(command,None,error.stdout or b'',error.stderr or b'')
(out/'serial.stdout.private.raw.log').write_bytes(result.stdout)
(out/'serial.stderr.private.raw.log').write_bytes(result.stderr)
cases=ET.parse(out/'serial.xml').findall('.//testcase') if(out/'serial.xml').exists() else []
failures=[];skips=[]
for case in cases:
    for tag in ['failure','error','skipped']:
        node=case.find(tag)
        if node is not None:
            row={'module':case.get('classname'),'case':case.get('name'),'kind':tag,'message':node.get('message','')}
            (skips if tag=='skipped' else failures).append(row)
after=photo()
(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'after-pip.raw.log').write_bytes(pip.stdout+pip.stderr)
summary={'head':head,'exit':result.returncode,'timed_out':timed_out,'seconds':time.monotonic()-started,
 'cases':len(cases),'failures':failures,'skips':skips,'source_packages_quiet':before==after,
 'sources':len(names),'packages':len(before['packages']),'pip_exit':pip.returncode,
 'scope':'Initial broad diagnostic with maxfail20 on isolated schema31 and CIe0 source. CI peer is in progress. No PG/Redis/Chrome/Linux/image/Actions/SLO claim.'}
(out/'summary.private.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps({key:summary[key] for key in ['head','exit','timed_out','seconds','cases','source_packages_quiet','sources','packages','pip_exit']}))
print(json.dumps({'failure_count':len(failures),'skip_count':len(skips)}))
assert before==after and pip.returncode==0
