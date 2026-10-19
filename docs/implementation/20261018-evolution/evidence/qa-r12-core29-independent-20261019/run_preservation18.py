"""New29 model/migration preservation18; no historical fixture retarget or broad PG run."""
import time
import xml.etree.ElementTree as ET
from qa_core_support import *

original=(OUT/'launch_pg_tests_isolated_v2.py').read_bytes()
adapted=original.replace(b'observe_owned_databases_v2',b'observe_owned_databases_v3')
assert original.count(b'observe_owned_databases_v2')==1
launcher=OUT/'launch_preservation18_v3.py'
launcher.write_bytes(adapted)
save('preservation-launcher-delta.json',{'original_sha256':sha(original),'adapted_sha256':sha(adapted),
     'only_change':'Observation plugin v2 to additive v3, to capture ordinary parametrized migration_database fixtures before exact absence checks.',
     'test_files':['tests/test_client_link_models.py','tests/integration_client_link_migrations.py'],
     'criteria_changed':False,'historical22_to28_targets_or_fixtures_changed':False})
before=photo('preservation18-before')
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
            'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
started=time.monotonic()
with (OUT/'preservation18-original.log').open('xb') as stream:
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(launcher),'preservation18'],
                          cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
after=photo('preservation18-after')
tree=ET.parse(OUT/'preservation18.xml').getroot();cases=tree.findall('.//testcase')
counts={'collected':len(cases),'failed':len(tree.findall('.//failure')),'errors':len(tree.findall('.//error')),
        'skipped':len(tree.findall('.//skipped'))}
counts['passed']=len(cases)-sum(counts[key] for key in ['failed','errors','skipped'])
receipt=json.loads((OUT/'preservation18-owned-database-receipt.json').read_text(encoding='utf8'))
save('preservation18-result.json',{'head':HEAD,'exit':result.returncode,'seconds':time.monotonic()-started,'counts':counts,
                      'source_and_package_stable':before==after,'sources':len(before['sources']),'packages':89,
                      'owned_database_receipt':receipt,'scope':'New29 model/migration18 only, eight SQLite metadata and five migrations per dialect. No old fixture alteration/retarget, full PG/broad/restore29.'})
print(json.dumps({'exit':result.returncode,'counts':counts,'stable':before==after,
                  'owned_databases':receipt.get('observed_database_count'),'owned_absence':receipt.get('all_exact_owned_names_absent')}))
assert before==after and result.returncode==0 and counts=={'collected':18,'failed':0,'errors':0,'skipped':0,'passed':18}
assert receipt['observed_database_count']==5 and receipt['all_exact_owned_names_absent']
