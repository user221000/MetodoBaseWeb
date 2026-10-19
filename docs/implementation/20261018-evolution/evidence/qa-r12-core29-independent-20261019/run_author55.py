"""Reproduce maintained55 once on the isolated canonical freeze, without API/old broad tests."""
import time
import xml.etree.ElementTree as ET
from qa_core_support import *

before=photo('author55-before')
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
            'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
command=[str(PYTHON),'-X','utf8','-B',str(OUT/'launch_pg_tests.py'),'author55']
started=time.monotonic()
with (OUT/'author55-original.log').open('xb') as stream:
    result=subprocess.run(command,cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
after=photo('author55-after')
tree=ET.parse(OUT/'author55.xml').getroot();cases=tree.findall('.//testcase')
counts={'collected':len(cases),'failed':len(tree.findall('.//failure')),'errors':len(tree.findall('.//error')),
        'skipped':len(tree.findall('.//skipped'))}
counts['passed']=len(cases)-sum(counts[key] for key in ['failed','errors','skipped'])
receipt=json.loads((OUT/'author55-owned-database-receipt.json').read_text(encoding='utf8'))
proof={'head':HEAD,'exit':result.returncode,'seconds':time.monotonic()-started,'counts':counts,
       'source_and_package_stable':before==after,'sources':len(before['sources']),'packages':89,
       'owned_database_receipt':receipt,'scope':'55 maintained core criteria only. No API acceptance, historical35 rerun, full migrations/restore/PG/broad or performance claim.'}
save('author55-result.json',proof)
print(json.dumps({'exit':result.returncode,'counts':counts,'sources_stable':before==after,
                  'owned_databases':receipt.get('observed_database_count'),'owned_absence':receipt.get('all_exact_owned_names_absent')}))
assert before==after and result.returncode==0 and counts=={'collected':55,'failed':0,'errors':0,'skipped':0,'passed':55}
assert receipt['observed_database_count']>0 and receipt['all_exact_owned_names_absent']
