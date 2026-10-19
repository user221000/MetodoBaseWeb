from pathlib import Path
import hashlib, importlib.metadata, json, os, subprocess, sys, time
ROOT=Path(r'F:\mb-r25-qa-ui-20261019')
PHASE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r25-qa-ui-20261019')
PUBLIC=ROOT/'docs/implementation/20261018-evolution/evidence/qa-r25-ui-independent-20261019'
NODE=Path(r'C:\Program Files\nodejs\node.exe')
CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
def write(path,raw):
    with path.open('xb') as stream:stream.write(raw)
def dump(path,data):write(path,(json.dumps(data,indent=2)+'\n').encode())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def photo():
    paths=git('ls-files','-z').decode().split('\0')[:-1]
    return {'head':git('rev-parse','HEAD').decode().strip(),
            'tracked_status':git('status','--porcelain','--untracked-files=no').decode(),
            'tracked_raw_sha256':{name:SHA((ROOT/name).read_bytes()) for name in paths},
            'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions() if d.metadata['Name']),
            'binaries':{str(p):SHA(p.read_bytes()) for p in (Path(sys.executable),NODE,CHROME)}}
PHASE.mkdir(exist_ok=False);PUBLIC.mkdir(exist_ok=False)
write(PUBLIC/'.gitattributes',b'* -text\n')
before=photo();dump(PHASE/'before.private.json',before)
assert before['head']=='b7f8e129251dfd5216f811ba77d0b6183ca76735' and not before['tracked_status']
results=[]
for name in ['progreso_datos','progreso_controlador','progreso_operacion','progreso_vista','progreso_wire','progreso_api','progreso_respuestas','progreso_paginas','progress_export']:
    start=time.monotonic();result=subprocess.run([str(NODE),str(ROOT/('tests/e2e/'+name+'.cjs'))],cwd=ROOT,capture_output=True,timeout=120)
    write(PHASE/(name+'.stdout.json'),result.stdout);write(PHASE/(name+'.stderr.log'),result.stderr)
    data=json.loads(result.stdout)
    results.append({'driver':name,'exit':result.returncode,'seconds':time.monotonic()-start,'passed':data.get('passed'),'total':data.get('total'),'output_sha256':SHA(result.stdout)})
    write(PUBLIC/(name+'.json'),result.stdout)
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','-q','tests/test_progress_ui_pages.py','tests/test_personal_progress_http.py','tests/test_qa_progress32_independent.py','--junitxml='+str(PHASE/'http-results.xml')]
start=time.monotonic();result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=900)
write(PHASE/'http.stdout.log',result.stdout);write(PHASE/'http.stderr.log',result.stderr)
results.append({'driver':'SSR2+author HTTP+independent HTTP','exit':result.returncode,'seconds':time.monotonic()-start})
after=photo();dump(PHASE/'after.private.json',after)
assert before==after,'Source, package metadata or binary changed during checks'
dump(PUBLIC/'phase-one-summary.json',{'head':before['head'],'checks':results,'quiet_source_files':len(before['tracked_raw_sha256']),
    'quiet_distribution_metadata':len(before['packages']),'source_packages_binaries_equal':True,
    'scope':'Nine maintained VM drivers use synthetic DOM/fetch and overlap author cases. SSR+actual HTTP use migrated SQLite32, real factories and real registration/login; inherited offline email/explicit lost-ACK seam are doubles. No Chrome/PG/axe claim here.'})
write(PUBLIC/'independent-test.py',(ROOT/'tests/test_qa_progress32_independent.py').read_bytes())
write(PUBLIC/'phase-one-driver.py',Path(__file__).read_bytes())
print(json.dumps({'phase_one_completed':True,'results':results,'quiet_sources':len(before['tracked_raw_sha256'])}))
