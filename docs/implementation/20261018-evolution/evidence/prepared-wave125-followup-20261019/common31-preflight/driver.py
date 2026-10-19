from pathlib import Path
import ast
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys

root=Path(r'F:\mb-mfa31-reviewed-common-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-reviewed-common-preflight-20261019')
head='de506b6077ba055587f02e7d839387e7f5c56f84'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
sha=lambda blob:hashlib.sha256(blob).hexdigest()
assert not out.exists() and git('rev-parse','HEAD').decode().strip()==head
assert not git('status','--porcelain','--untracked-files=no')
names=git('ls-files','-z').decode().split('\0')[:-1]
def photo():
    return {'files':{name:sha((root/name).read_bytes()) for name in names},
            'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
            'python_sha256':sha(Path(sys.executable).read_bytes())}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
before=photo();(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT']:env.pop(key,None)
def run(label,args):
    result=subprocess.run([sys.executable,'-X','utf8','-B',*args],cwd=root,env=env,capture_output=True,timeout=180)
    (out/(label+'.stdout.raw.log')).write_bytes(result.stdout)
    (out/(label+'.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode==0,label
run('pip-before',['-m','pip','check'])
run('checker',['tests/verify_mfa31_ci.py','--output',str(out/'wiring'),'--verify-only'])
run('parser',['tests/run_isolated.py','tests/test_mfa31_ci_trust.py','-q','--tb=short','--junitxml='+str(out/'parser.xml')])
run('pip-after',['-m','pip','check'])
after=photo();assert before==after
(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
report=json.loads((out/'wiring/review.json').read_bytes())
import xml.etree.ElementTree as ET
cases=ET.parse(out/'parser.xml').findall('.//testcase')
assert cases and all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases)
result={'head':head,'workflow_canaries':len(report['workflow_canaries']),
        'PG_required_nodeids':report['current']['required_full_current_PG_nodeids'],'immutable_helpers':report['immutable_helpers'],
        'parser_cases':len(cases),'sources':len(names),'packages':len(before['packages']),
        'source_packages_python_quiet':True,'pip_before_after':[0,0],
        'scope':'Offline static wiring plus maintained parser canaries; not Actions, PG, browser, runtime or broad acceptance'}
assert result['workflow_canaries']==145 and result['PG_required_nodeids']==173 and result['immutable_helpers']==23
(out/'summary.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(result))
