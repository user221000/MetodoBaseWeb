from pathlib import Path
import hashlib,importlib.metadata,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');OUT=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-portal-root-before-20261019');OUT.mkdir(exist_ok=False)
test=Path(__file__).with_name('test_metodobase_portal_return_boundary.py');shutil.copyfile(test,OUT/test.name)
sha=lambda b:hashlib.sha256(b).hexdigest()
names=['web/services/stripe_service.py','web/routes/billing.py','tests/run_isolated.py','tests/isolation.py','web/settings.py','web/database/models.py']
def photo():return {'files':{n:sha((ROOT/n).read_bytes()) for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py',str(test),'--noconftest','-q','--tb=short','--junitxml='+str(OUT/'result.xml')],cwd=ROOT,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=90,check=False)
(OUT/'stdout.log').write_bytes(result.stdout);(OUT/'stderr.log').write_bytes(result.stderr)
root=ET.fromstring((OUT/'result.xml').read_bytes());cases=root.findall('.//testcase');after=photo()
report={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'exit':result.returncode,'cases':len(cases),'failures':len(root.findall('.//failure')),'errors':len(root.findall('.//error')),'skips':len(root.findall('.//skipped')),'source_packages_quiet':before==after,'before':before,'after':after,'scope':'Pure real service body via inspect.unwrap, fake typed query return and actual Stripe SDK port replaced by a recording function. No auth/HTTP/RLS/database connection/network/payment or decorator retry acceptance.'}
(OUT/'receipt.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items() if k not in {'before','after'}}))
assert result.returncode==1 and len(cases)==11 and len(root.findall('.//failure'))==8 and not root.findall('.//error') and not root.findall('.//skipped') and before==after
