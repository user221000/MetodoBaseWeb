"""Exercise the new pinned-source runner with the actual unchanged CI28 restores."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
root=Path('F:/mb-r12-ci29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore-v2-20261019');out.mkdir(exist_ok=False)
configuration=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
names=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1])
names.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')[:-1])
names=sorted(name for name in names if (root/name).is_file())
sha=lambda value:hashlib.sha256(value).hexdigest()
def photo():return {'files':{name:sha((root/name).read_bytes()) for name in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
def save(name,value):(out/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
before=photo();save('before.json',before)
environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:
    environment.pop(key,None)
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    environment[key]=configuration[key]
for phase in ['before']:
    result=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
    (out/(phase+'-pip.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0
started=time.monotonic()
result=subprocess.run([sys.executable,'-X','utf8','tests/run_reviewed_ci28.py','--output',str(out/'runner'),
    '--junitxml='+str(out/'tests.xml')],cwd=root,env=environment,capture_output=True,timeout=270)
(out/'runner.log').write_bytes(result.stdout+result.stderr)
after=photo();save('after.json',after)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'after-pip.log').write_bytes(pip.stdout+pip.stderr)
cases=ET.parse(out/'tests.xml').findall('.//testcase') if (out/'tests.xml').exists() else []
summary={'root_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
         'exit_code':result.returncode,'runner_seconds':time.monotonic()-started,'cases':len(cases),
         'failures':sum(case.find('failure') is not None for case in cases),'errors':sum(case.find('error') is not None for case in cases),
         'skipped':sum(case.find('skipped') is not None for case in cases),'files':len(names),'packages':len(before['packages']),
         'sources_and_packages_stable':before==after,'pip_check_after_zero':pip.returncode==0,
         'scope':'Two unchanged actual restore cases running from pinned66d9dec actual schema28 source through the new runner; no current29 restore claim.'}
save('summary.json',summary);print(json.dumps(summary))
assert result.returncode==0 and len(cases)==2 and not any(case.find(tag) is not None for case in cases for tag in ['failure','error','skipped'])
assert before==after and pip.returncode==0
