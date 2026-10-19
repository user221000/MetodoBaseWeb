"""Preserve original fixture-origin failure; rerun identical assertions in correct isolated29 origin."""
import shutil
import time
import xml.etree.ElementTree as ET
from qa_core_support import *

TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-r12-core29-independent-20261019')
TEMP.mkdir(exist_ok=False)
source=OUT/'test_r12_core29_review.py';target=TEMP/source.name
shutil.copyfile(source,target)
assert target.read_bytes()==source.read_bytes()
save('own-origin-harness-correction.json',{'original_result':'own-result.json','original_log':'own-original.log',
     'original_driver_sha256':sha(source.read_bytes()),'temp_driver_sha256':sha(target.read_bytes()),
     'assertions_changed':False,'cause':'An evidence test under MAIN loaded ancestor MAIN conftest, overriding29 worktree imports with28 modules before fixture verification.',
     'correction':'Exact driver copied to owned Temp outside any repository; explicit frozen29 rootdir/config/importlib; module path guard before every criterion.',
     'failed_attempt_cleanup':'own_lab finally closed its UUID migration generator on setup error; first observer did not see a fixture that never yielded, so zero observed names is not an independent absence proof for that attempt.'})
before=photo('own-isolated-before')
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
            'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
started=time.monotonic()
with (OUT/'own-isolated-original.log').open('xb') as stream:
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(OUT/'launch_pg_tests_isolated_v2.py'),'own-isolated'],
                          cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
after=photo('own-isolated-after')
tree=ET.parse(OUT/'own-isolated.xml').getroot();cases=tree.findall('.//testcase')
counts={'collected':len(cases),'failed':len(tree.findall('.//failure')),'errors':len(tree.findall('.//error')),
        'skipped':len(tree.findall('.//skipped'))}
counts['passed']=len(cases)-sum(counts[key] for key in ['failed','errors','skipped'])
receipt=json.loads((OUT/'own-isolated-owned-database-receipt.json').read_text(encoding='utf8'))
save('own-isolated-result.json',{'head':HEAD,'exit':result.returncode,'seconds':time.monotonic()-started,'counts':counts,
                      'source_and_package_stable':before==after,'sources':len(before['sources']),'packages':89,
                      'driver_sha256':sha(source.read_bytes()),'exact_temp_copy':target.read_bytes()==source.read_bytes(),
                      'owned_database_receipt':receipt,'scope':'Independent SQL22 only. No API/broad/performance or restore29 acceptance.'})
print(json.dumps({'exit':result.returncode,'counts':counts,'stable':before==after,
                  'owned_databases':receipt.get('observed_database_count'),'owned_absence':receipt.get('all_exact_owned_names_absent')}))
assert before==after and result.returncode==0 and counts=={'collected':22,'failed':0,'errors':0,'skipped':0,'passed':22}
assert receipt['observed_database_count']==1 and receipt['all_exact_owned_names_absent']
