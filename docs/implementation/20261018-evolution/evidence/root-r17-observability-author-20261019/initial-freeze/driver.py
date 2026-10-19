"""Freeze the six-file R17 candidate and verify its final mounted privacy contract."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

root=Path(r'F:\mb-saas-observability-20261019')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
out=tmp/'metodobase-saas-observability-frozen-20261019'
names=['api/app.py','web/main_web.py','web/middleware/metrics.py','web/observability/routes.py',
       'tests/test_saas_observability_contract.py','tests/test_metrics_privacy_review.py']
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()=='bd34893c4b6f806041b0cc6b7f156e9286886748'
assert set(git('diff','--name-only','-z').decode().split('\0')[:-1])==set(names)-{'web/observability/routes.py','tests/test_saas_observability_contract.py'}
previous=ET.parse(tmp/'metodobase-saas-observability-final-20261019.xml').findall('.//testcase')
assert len(previous)==103 and all(not any(c.find(t) is not None for t in ['failure','error','skipped']) for c in previous)
subprocess.run(['git','diff','--check'],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*names],cwd=root,check=True,capture_output=True)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names)
subprocess.run(['git','commit','-m','Mount private operational metrics in both application factories'],cwd=root,check=True,capture_output=True)
head=git('rev-parse','HEAD').decode().strip()
assert not git('status','--porcelain','--untracked-files=no')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
tracked=git('ls-files','-z').decode().split('\0')[:-1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def photo():
    return {'files':{n:sha((root/n).read_bytes()) for n in tracked},
     'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
     'python_sha256':sha(Path(sys.executable).read_bytes())}
before=photo()
(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
pip_before=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-before.raw.log').write_bytes(pip_before.stdout+pip_before.stderr)
assert pip_before.returncode==0
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests/test_saas_observability_contract.py',
 'tests/test_metrics_privacy_contract.py','tests/test_metrics_privacy_review.py','-q','--tb=short','--junitxml='+str(out/'pytest.xml')]
result=subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=180)
(out/'pytest.stdout.private.raw.log').write_bytes(result.stdout)
(out/'pytest.stderr.private.raw.log').write_bytes(result.stderr)
cases=ET.parse(out/'pytest.xml').findall('.//testcase')
after=photo()
(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
pip_after=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-after.raw.log').write_bytes(pip_after.stdout+pip_after.stderr)
summary={'head':head,'base':'bd34893c4b6f806041b0cc6b7f156e9286886748','exit':result.returncode,
 'cases':len(cases),'failed_or_skipped':sum(any(c.find(t) is not None for t in ['failure','error','skipped']) for c in cases),
 'prior_directed':{'cases':103,'exit':0,'after_style_full_AST_exact':True},
 'sources':len(tracked),'packages':len(before['packages']),'sources_packages_python_exact':before==after,
 'pip_before':pip_before.returncode,'pip_after':pip_after.returncode,
 'scope':'Author real mounted ASGI/factory contract with isolated metadata SQLite, not PostgreSQL/migrations/browser/production/Actions/SLO. METRICS_ENABLED explicitly enabled per test; external alert delivery doubled at API handler boundary. Full response body streaming and distributed aggregation are not measured.',
 'test_adoption':'Historical privacy case ID retained: unhandled-response limitation changed deliberately from0records to1status500 with route-only identity and extra no_identity assertions. No privacy check removed.'}
(out/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary))
assert before==after and result.returncode==0 and summary['failed_or_skipped']==0 and pip_after.returncode==0
