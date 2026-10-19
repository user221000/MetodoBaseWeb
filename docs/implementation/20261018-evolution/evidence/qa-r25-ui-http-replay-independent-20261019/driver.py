from pathlib import Path
import hashlib,importlib.metadata,json,subprocess,sys,time
ROOT=Path(r'F:\mb-r25-qa-ui-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
PHASE=TEMP/'metodobase-r25-qa-ui-http-replay-20261019'
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/qa-r25-ui-http-replay-independent-20261019'
TEST=ROOT/'tests/test_qa_progress32_independent.py'
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
def dump(path,data):
    with path.open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2);stream.write('\n')
def photo():
    names=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','db_bootstrap.py'],cwd=ROOT).decode().split('\0')[:-1]
    return {'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'tracked_status':subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True),
        'runtime_raw_sha256':{name:SHA((ROOT/name).read_bytes()) for name in names},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions() if d.metadata['Name']),
        'test_sha256':SHA(TEST.read_bytes()),'python_sha256':SHA(Path(sys.executable).read_bytes())}
PHASE.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False);(OUT/'.gitattributes').write_bytes(b'* -text\n')
before=photo();dump(PHASE/'before.private.json',before)
assert before['head']=='b7f8e129251dfd5216f811ba77d0b6183ca76735' and not before['tracked_status']
start=time.monotonic();result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py','-q','tests/test_qa_progress32_independent.py','--junitxml='+str(PHASE/'results.xml')],cwd=ROOT,capture_output=True,timeout=300)
(PHASE/'stdout.log').write_bytes(result.stdout);(PHASE/'stderr.log').write_bytes(result.stderr)
after=photo();dump(PHASE/'after.private.json',after);assert before==after
import xml.etree.ElementTree as ET
cases=[{'class':row.get('classname'),'name':row.get('name'),'failed':row.find('failure') is not None,'error':row.find('error') is not None,'skipped':row.find('skipped') is not None} for row in ET.parse(PHASE/'results.xml').iter('testcase')]
summary={'source_head':before['head'],'exit':result.returncode,'seconds':time.monotonic()-start,'cases':cases,'runtime_sources_quiet':len(before['runtime_raw_sha256']),
    'distribution_metadata_quiet':len(before['packages']),'test_python_source_metadata_equal':True,
    'initial_harness_reds':'Six initial reds were three mistaken expectations across both factories: 402 documented plan-required, completion object with empty items, and no-store with max-age=0. Only these new harness expectations changed; original test bytes and XML/log retained in phase one. No product or historical test edit.',
    'scope':'12 independent controls, real registration/login/factories/migrated SQLite32. Only offline email and named uncertain COMMIT ACK seam are doubles. No Chrome/PG/SLO claim.'}
dump(OUT/'summary.json',summary);(OUT/'independent-test.py').write_bytes(TEST.read_bytes());(OUT/'driver.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'exit':result.returncode,'passed':sum(not(c['failed'] or c['error'] or c['skipped']) for c in cases),'total':len(cases)}))
sys.exit(result.returncode)
