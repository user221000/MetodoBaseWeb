"""Serial bounded runs with original private outputs, labeled public copies, full photos."""
import shutil
import time
import xml.etree.ElementTree as ET
from support import *

mode=sys.argv[1];expected={'maintained112':(112,8),'own8':(8,6)}[mode]
source=OUT/'test_history30_review.py';copy=TEMP/source.name
if not copy.exists():shutil.copyfile(source,copy)
assert copy.read_bytes()==source.read_bytes()
phase=TEMP/mode;phase.mkdir(exist_ok=False)
before=photo(mode+'-before')
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
            'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
clock=time.monotonic()
with (phase/'tests.log').open('xb') as stream:
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(OUT/'launch.py'),mode],cwd=ROOT,env=environment,
                          stdout=stream,stderr=subprocess.STDOUT,timeout=420)
elapsed=time.monotonic()-clock
after=photo(mode+'-after')
tree=ET.parse(phase/'tests.xml').getroot();cases=tree.findall('.//testcase')
counts={'collected':len(cases),'failed':len(tree.findall('.//failure')),'errors':len(tree.findall('.//error')),'skipped':len(tree.findall('.//skipped'))}
counts['passed']=counts['collected']-counts['failed']-counts['errors']-counts['skipped']
absence=json.loads((phase/'owned-absence.json').read_bytes())
public=[]
for path in sorted(phase.iterdir()):
    if path.is_file():public.append(publish_raw_or_sanitized(path,mode+'-'+path.name))
save(mode+'-result.json',{'head':HEAD,'exit':result.returncode,'runner_seconds':elapsed,'counts':counts,
     'full_source_helpers_and_packages_stable':before==after,'sources':before['source_count'],'untracked_helpers':before['helper_count'],
     'packages':89,'owned_absence':absence,'public_outputs':public,'exact_temp_driver_sha256':sha(copy.read_bytes()),
     'scope':'Isolated SQLite and UUID PG functional correctness only. No API29 acceptance, HTTP load/p95/SLO, browser, VM or MAIN mutation.'})
print(json.dumps({'phase':mode,'exit':result.returncode,'counts':counts,'sources':before['source_count'],
                  'helpers':before['helper_count'],'stable':before==after,'owned_absent':absence['all_owned_absent'],'owned_count':absence['count']}))
assert result.returncode==0 and counts==dict(collected=expected[0],failed=0,errors=0,skipped=0,passed=expected[0])
assert before==after and absence['all_owned_absent'] and absence['count']==expected[1]
