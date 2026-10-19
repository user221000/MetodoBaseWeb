"""Sync draft30 to restore-stable29; execute new real migration/query gates."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path('F:/mb-hidx-20261019')
TEMP=Path('C:/Users/Consu/AppData/Local/Temp')
OUT=TEMP/'metodobase-history30-final-base-test-20261019'
OUT.mkdir(exist_ok=False)
sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
sha=lambda raw:hashlib.sha256(raw).hexdigest()
from web.database.alembic.history_index_contract_v1 import expected_history_index
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head.startswith('aa9c3b8')
directory=ROOT/'web/database/alembic/schema_targets'
sync=[]
for dialect in ['sqlite','postgresql']:
    previous=directory/('20261019_client_account_links_'+dialect+'.json')
    target=directory/('20261019_personal_history_index_'+dialect+'.json')
    previous_data=json.loads(previous.read_bytes())
    old=json.loads(target.read_bytes())
    (OUT/target.name).write_bytes(target.read_bytes())
    before_index=[item for item in old['signature']['tables']['planes_generados']['indexes'] if item['name']=='ix_planes_gym_cliente_history']
    assert len(before_index)==1
    old_without=json.loads(json.dumps(old))
    del old_without['history_order_index']
    old_without['signature']['tables']['planes_generados']['indexes']=[item for item in old_without['signature']['tables']['planes_generados']['indexes'] if item['name']!='ix_planes_gym_cliente_history']
    pre_cast=json.loads(subprocess.check_output(['git','show','1aacbcb5e9d0a1ba0b2a08d5c3650e4bd9ff7ce6:'+previous.relative_to(ROOT).as_posix()],cwd=ROOT))
    assert old_without==pre_cast
    new=json.loads(json.dumps(previous_data))
    new['signature']['tables']['planes_generados']['indexes'].extend(before_index)
    new['signature']['tables']['planes_generados']['indexes'].sort(key=lambda row:row['name'])
    new['history_order_index']=expected_history_index(dialect)
    target.write_bytes((json.dumps(new,indent=2,ensure_ascii=False)+'\n').encode())
    sync.append({'dialect':dialect,'predecessor_sha256':sha(previous.read_bytes()),'new_draft_sha256':sha(target.read_bytes()),'single_new_index_and_physical_contract_only':True})
(OUT/'target-sync.json').write_bytes((json.dumps(sync,indent=2)+'\n').encode())
paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')[:-1]
paths=sorted(set(name for name in paths if not name.startswith(('docs/','dist/','build/')) and (ROOT/name).is_file()))
def photo():return {name:sha((ROOT/name).read_bytes()) for name in paths}
def packages():return sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda row:row['name'].lower())
before=photo();before_packages=packages()
(OUT/'before-source.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
(OUT/'before-packages.json').write_bytes((json.dumps(before_packages,indent=2)+'\n').encode())
pip_before=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'before-pip.log').write_bytes(pip_before.stdout+pip_before.stderr)
assert pip_before.returncode==0
env=os.environ.copy()
private=json.loads((TEMP/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:env[key]=private[key]
env['METODOBASE_HISTORY_ORDERED_PROOF_DIR']=str(OUT)
arguments=[sys.executable,'-X','utf8','tests/run_isolated.py',
    'tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py',
    '-q','--junitxml='+str(OUT/'tests.xml')]
started=time.monotonic()
with (OUT/'tests.log').open('wb') as log:
    result=subprocess.run(arguments,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=420)
seconds=time.monotonic()-started
after=photo();after_packages=packages()
(OUT/'after-source.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
(OUT/'after-packages.json').write_bytes((json.dumps(after_packages,indent=2)+'\n').encode())
pip_after=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'after-pip.log').write_bytes(pip_after.stdout+pip_after.stderr)
assert before==after and before_packages==after_packages and pip_after.returncode==0
tree=ET.parse(OUT/'tests.xml')
cases=list(tree.iter('testcase'))
summary={'source_head':head,'predecessor_cast_commit':'6ec3f04fab18d21f28c63bb864a9398f23e5dcce',
    'exit_code':result.returncode,'runner_seconds':seconds,'cases':len(cases),
    'failures':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),
    'sources_including_new_files':len(paths),'sources_stable':before==after,'effective_packages':len(before_packages),'packages_stable':before_packages==after_packages,
    'pip_checks_zero':pip_before.returncode==pip_after.returncode==0,
    'proof':'Actual SQLite and owned synthetic PostgreSQL with real restricted role for history SQL. No latency/SLO, API29 acceptance or MAIN integration claim.'}
(OUT/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary))
raise SystemExit(result.returncode)
