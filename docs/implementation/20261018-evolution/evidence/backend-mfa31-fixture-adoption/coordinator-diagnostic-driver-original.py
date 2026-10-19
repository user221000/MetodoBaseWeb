from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path(r'F:\mb-mfa31-compose-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-legacy-contract-diagnostic-20261019');out.mkdir(exist_ok=False)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='913cb66061ac754ad09344fc24e8f769b5722997' and not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
names=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','src','tests'],cwd=root).decode().split('\0')[:-1]
def photo():return {'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
selected=['tests/test_auth_security.py','tests/test_billing_consolidation.py','tests/test_billing_integrity.py','tests/test_team_invitation_contract.py','tests/test_team_entitlement_review.py','tests/test_security_billing_review.py','tests/test_rbac_permissions.py','tests/test_api_team_plan_storage_review.py']
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py',*selected,'--maxfail=20','-q','--tb=short','--junitxml='+str(out/'result.xml')]
env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1'}
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT']:env.pop(key,None)
started=time.monotonic();timeout=False
try:result=subprocess.run(command,cwd=root,capture_output=True,env=env,timeout=600,check=False)
except subprocess.TimeoutExpired as error:
    timeout=True;result=subprocess.CompletedProcess(command,None,error.stdout or b'',error.stderr or b'')
(out/'stdout.private.log').write_bytes(result.stdout);(out/'stderr.private.log').write_bytes(result.stderr)
xml=ET.fromstring((out/'result.xml').read_bytes()) if (out/'result.xml').exists() else None;cases=xml.findall('.//testcase') if xml is not None else []
rows=[]
for case in cases:
    kind=next((tag for tag in ['failure','error','skipped'] if case.find(tag) is not None),'passed')
    rows.append({'module':case.get('classname'),'case':case.get('name'),'result':kind})
after=photo();(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
summary={'head':head,'exit':result.returncode,'timed_out':timeout,'seconds':time.monotonic()-started,'cases':len(cases),'counts':{tag:sum(r['result']==tag for r in rows) for tag in ['passed','failure','error','skipped']},'rows':rows,'maxfail':20,'selected':selected,'source_packages_quiet':before==after,'source_files':len(names),'packages':len(before['packages']),'scope':'Initial bounded affected legacy-contract diagnostic against isolated current31backend composition, before fixture adaptation or UI composition. Intentional MFA stepup adoption may require legitimate test enrollment/grants, not environment bypass or weaker business assertions. Not full regression/acceptance, no PG/browser/provider.'}
(out/'summary.private.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in summary.items() if k not in {'rows','selected'}}));assert before==after
