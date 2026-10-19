"""Run independent22 once; preserve original output even if a criterion is red."""
import time
import xml.etree.ElementTree as ET
from qa_core_support import *

before=photo('own-before')
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
            'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
started=time.monotonic()
with (OUT/'own-original.log').open('xb') as stream:
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(OUT/'launch_pg_tests.py'),'own'],
                          cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
after=photo('own-after')
tree=ET.parse(OUT/'own.xml').getroot();cases=tree.findall('.//testcase')
counts={'collected':len(cases),'failed':len(tree.findall('.//failure')),'errors':len(tree.findall('.//error')),
        'skipped':len(tree.findall('.//skipped'))}
counts['passed']=len(cases)-sum(counts[key] for key in ['failed','errors','skipped'])
receipt=json.loads((OUT/'own-owned-database-receipt.json').read_text(encoding='utf8'))
save('own-result.json',{'head':HEAD,'exit':result.returncode,'seconds':time.monotonic()-started,'counts':counts,
                      'source_and_package_stable':before==after,'sources':len(before['sources']),'packages':89,
                      'owned_database_receipt':receipt,'scope':'Independent SQL22 only. No API/broad/performance or restore29 acceptance.'})
print(json.dumps({'exit':result.returncode,'counts':counts,'stable':before==after,
                  'owned_databases':receipt.get('observed_database_count'),'owned_absence':receipt.get('all_exact_owned_names_absent')}))
assert before==after and result.returncode==0 and counts=={'collected':22,'failed':0,'errors':0,'skipped':0,'passed':22}
assert receipt['observed_database_count']==1 and receipt['all_exact_owned_names_absent']
