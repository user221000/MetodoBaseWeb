from pathlib import Path
import hashlib,importlib.metadata,json,subprocess,sys,time
ROOT=Path(r'F:\mb-retirement32-public-qa-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
PHASE=TEMP/'metodobase-retirement32-qa-http-v2-20261019';OUT=ROOT/'docs/implementation/20261018-evolution/evidence/qa-retirement32-http-v2-independent-20261019'
HEAD='219f89a5ee0196061fea5b67e36ae07daf7f4316';NODE=Path(r'C:\Program Files\nodejs\node.exe');CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
def dump(path,value):
    with path.open('x',encoding='utf8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def photo():
    entries=subprocess.check_output(['git','ls-files','--stage','-z','--','web','api','core','config','db_bootstrap.py'],cwd=ROOT).decode().split('\0')[:-1]
    raw_hashes={};git_equal=True
    for entry in entries:
        info,name=entry.split('\t');mode,oid,stage=info.split(' ');assert mode in {'100644','100755'} and stage=='0'
        raw=(ROOT/name).read_bytes();raw_hashes[name]=SHA(raw)
        git_equal=git_equal and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
    return {'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'tracked_status':subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True),
        'runtime_raw_sha256':raw_hashes,'runtime_RAW_equals_index_GitLF':git_equal,
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions() if d.metadata['Name']),
        'binaries':{str(p):SHA(p.read_bytes()) for p in (Path(sys.executable),NODE,CHROME)},
        'owned_test_SHA256':SHA((ROOT/'tests/test_qa_retirement32_public.py').read_bytes()),
        'pip_check':subprocess.run([sys.executable,'-m','pip','check'],capture_output=True).returncode}
PHASE.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False);(OUT/'.gitattributes').write_bytes(b'* -text\n')
assert (ROOT/'tests/test_qa_retirement32_public.py').read_bytes()==(TEMP/'metodobase-retirement32-qa-http-v2.py').read_bytes()
wire=ROOT/'docs/implementation/20261018-evolution/evidence/backend-progress32-retirement-20261019/wire-v1.md'
assert SHA(wire.read_bytes())=='5b6de9c0ecbb9bdf070a1ef6831d5f22f2ac11bddf32c54f3787b99d315bc706'
before=photo();dump(PHASE/'before.private.json',before);assert before['head']==HEAD and not before['tracked_status'] and before['runtime_RAW_equals_index_GitLF'] and before['pip_check']==0
vm=[]
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','-q','tests/test_qa_retirement32_public.py','--junitxml='+str(PHASE/'results.xml')]
start=time.monotonic();result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600)
(PHASE/'stdout.private.log').write_bytes(result.stdout);(PHASE/'stderr.private.log').write_bytes(result.stderr)
after=photo();dump(PHASE/'after.private.json',after);assert before==after
import xml.etree.ElementTree as ET
cases=[{'class':row.get('classname'),'name':row.get('name'),'failed':row.find('failure') is not None,'error':row.find('error') is not None,'skipped':row.find('skipped') is not None} for row in ET.parse(PHASE/'results.xml').iter('testcase')]
dump(OUT/'summary.json',{'source_head':HEAD,'exit':result.returncode,'seconds':time.monotonic()-start,'VM':vm,'HTTP_SSR_cases':cases,
    'runtime_sources_quiet':len(before['runtime_raw_sha256']),'distribution_metadata_quiet':len(before['packages']),'runtime_RAW_equals_GitLF':True,'source_pkg_bin_test_equal':True,'pip_checks':[before['pip_check'],after['pip_check']],
    'scope':'Own8 HTTP criteria=4 across both actual factories, real migrated SQLite32 and real MFA-protected team invitation/acceptance/link/consent/parent-OFF genealogy. No bearer mint/auth override/create_all/stamp/limiter reset. Own COMMIT-ACK seam alone, no retained-Session rollback/close tuple injection.This run repeats only the8 own HTTP cases after correcting the incidental-CSRF and creation-factory harness assumptions. Prior8 SSR/45VM results remain separate, unchanged source. No PG/provider/production/SLO claim.'})
(OUT/'owned-test.py').write_bytes((ROOT/'tests/test_qa_retirement32_public.py').read_bytes());(OUT/'driver.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'exit':result.returncode,'VM':vm,'passed_HTTP_SSR':sum(not(c['failed'] or c['error'] or c['skipped']) for c in cases),'total_HTTP_SSR':len(cases),'runtime_sources':len(before['runtime_raw_sha256'])}))
sys.exit(result.returncode)
