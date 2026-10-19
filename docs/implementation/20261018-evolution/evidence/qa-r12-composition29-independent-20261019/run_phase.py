"""Execute one frozen composition phase once and preserve original outputs."""
import time
import xml.etree.ElementTree as ET
from support import *
mode=sys.argv[1];expected={'backend147':(147,2,4),'restore1':(1,0,2),'UI10':(10,0,0)}[mode]
phase=TEMP/mode;phase.mkdir(exist_ok=False)
before=photo(mode+'-before')
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
            'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
clock=time.monotonic()
with (phase/'tests.log').open('xb') as stream:
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(OUT/'launch.py'),mode],cwd=ROOT,env=environment,
                         stdout=stream,stderr=subprocess.STDOUT,timeout=480)
elapsed=time.monotonic()-clock
after=photo(mode+'-after')
tree=ET.parse(phase/'tests.xml').getroot();cases=tree.findall('.//testcase')
counts={'collected':len(cases),'failed':len(tree.findall('.//failure')),'errors':len(tree.findall('.//error')),'skipped':len(tree.findall('.//skipped'))}
counts['passed']=counts['collected']-counts['failed']-counts['errors']-counts['skipped']
skips=[{'class':case.attrib['classname'],'name':case.attrib['name'],'reason':case.find('skipped').attrib.get('message')} for case in cases if case.find('skipped') is not None]
absence=json.loads((phase/'owned-absence.json').read_bytes())
outputs=[publish(path,mode+'-'+path.name) for path in sorted(phase.iterdir()) if path.is_file()]
save(mode+'-result.json',{'head':HEAD,'exit':result.returncode,'runner_seconds':elapsed,'counts':counts,'skips':skips,
   'full_sources_helpers_packages_stable':before==after,'source_count':before['source_count'],'helper_count':before['helper_count'],'packages':89,
   'owned_absence':absence,'public_outputs':outputs,'scope':'Current29 composition only. No index30, new500/outer-rate-header security acceptance or browser/performance approval from this phase.'})
print(json.dumps({'phase':mode,'exit':result.returncode,'counts':counts,'sources':before['source_count'],
                  'helpers':before['helper_count'],'stable':before==after,'owned_count':absence['count'],'owned_absent':absence['all_owned_absent']}))
assert result.returncode==0 and counts==dict(collected=expected[0],failed=0,errors=0,skipped=expected[1],passed=expected[0]-expected[1])
if mode=='backend147':
    assert {value['name'] for value in skips}=={'test_two_processes_consume_one_proof_once_under_restricted_role[sqlite]',
                    'test_session_revoked_between_proof_lookup_and_account_lock_cannot_accept[sqlite]'}
assert before==after and absence['count']==expected[2] and absence['all_owned_absent']
