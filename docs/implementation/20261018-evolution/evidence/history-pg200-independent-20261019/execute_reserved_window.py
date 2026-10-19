"""Execute only the explicitly authorized history200 resource window, preserve all preparation."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime,timezone

ROOT=Path(r'F:/MetodoBaseWeb-execution-20261018');OUT=Path(__file__).resolve().parent
HEAD='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
WINDOW=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-history200-resource-window-20261019T1112.json')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
RUN=OUT/'run-66d9dec-20261019T1112'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def photo(label):
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert not git('status','--porcelain','--untracked-files=no').decode().strip()
    names=[n for n in git('ls-files','-z').decode().split('\0') if n and not n.startswith('docs/')]
    sources={n:sha(ROOT/n) for n in sorted(names)}
    packages=sorted([p.metadata['Name'],p.version] for p in importlib.metadata.distributions());assert len(packages)==89
    pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,encoding='utf8',timeout=30)
    with (OUT/(label+'-pip.log')).open('x',encoding='utf8') as f:f.write(pip.stdout+pip.stderr)
    assert pip.returncode==0
    value={'head':HEAD,'sources':sources,'source_count':len(sources),'packages':packages,'package_count':89,'pip_check_exit':0,
        'python':platform.python_version(),'driver_sha256':sha(OUT/'run_history200.py')}
    save(label+'-photo.json',value);return value

assert sha(OUT/'run_history200.py')=='4592fb1782e6d19ee1ff61f65d59eb63583313e3d109875ae29a13c5082dca10'
prep=json.loads((OUT/'preparation-manifest.json').read_text(encoding='utf8'))
assert all(sha(OUT/n)==digest for n,digest in prep['files'].items())
window=json.loads(WINDOW.read_text(encoding='utf8'))
assert window['approved'] is True and window['phase']=='history200' and window['expected_head']==HEAD
assert datetime.fromisoformat(window['expires_utc'])>datetime.now(timezone.utc)
assert window['driver_sha256']==sha(OUT/'run_history200.py')
before=photo('execution-before')
prepared=json.loads((OUT/'preparation-environment.json').read_text(encoding='utf8'))
assert before['packages']==prepared['packages']
assert all(before['sources'][name]==digest for name,digest in prepared['sources'].items()
           if name.startswith(('web/','api/','core/','config/')))
delta=git('diff','--name-only',prepared['head_at_preparation'],HEAD).decode().splitlines()
save('execution-head-addendum.json',{'preparation_head':prepared['head_at_preparation'],'execution_head':HEAD,
    'nondocument_changes_since_preparation':[n for n in delta if not n.startswith('docs/')],
    'saas_runtime_bytes_identical_to_preparation':True,'preparation_manifest_sha256':sha(OUT/'preparation-manifest.json'),
    'preparation_files_verified':len(prep['files']),'window_file':str(WINDOW),'window_sha256':sha(WINDOW),
    'window_expires_utc':window['expires_utc'],'explicit_root_ack_received':True,
    'private_configuration':'Only the approved driver child consumes private env.json; not read or serialized by this orchestrator'})
env=os.environ.copy()
for name in ['METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_PG_BIN',
             'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    env.pop(name,None)
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
command=[sys.executable,'-X','utf8',str(OUT/'run_history200.py'),'--private-env',str(PRIVATE),'--output',str(RUN),
    '--requests','100','--seconds','30','--window-file',str(WINDOW),'--expected-head',HEAD]
started=time.monotonic()
save('execution-command.json',{'command':command,'started_utc':datetime.now(timezone.utc).isoformat(),
    'allowed_measured_http':200,'excluded_controls':'auth readiness attempts and exactly1 history warmup; enumerate original report',
    'no_other_scenario_allowed':True})
with (OUT/'execution-original.log').open('xb') as f:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240)
after=photo('execution-after')
save('execution-process-result.json',{'exit':result.returncode,'seconds':time.monotonic()-started,
    'source_and_package_photos_identical':before==after,'original_log':'execution-original.log','run_directory':str(RUN),
    'raw_report_exists':(RUN/'report.json').is_file()})
assert before==after
print(json.dumps({'exit':result.returncode,'source_count':len(before['sources']),'packages':89,
    'run_directory':str(RUN),'source_and_packages_unchanged':True}))
sys.exit(result.returncode)
