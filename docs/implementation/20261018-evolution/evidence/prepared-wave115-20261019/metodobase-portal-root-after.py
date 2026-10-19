from pathlib import Path
import hashlib,importlib.metadata,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
root=Path(r'F:\mb-portal-return-sec11-root-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-portal-root-after-20261019');out.mkdir(exist_ok=False)
beforetest=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-portal-root-before-20261019\test_metodobase_portal_return_boundary.py')
test=out/beforetest.name;shutil.copyfile(beforetest,test)
sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','merge-base','--is-ancestor','5316644608a09632a9997c25d50b1da3486ffc1b','HEAD'],cwd=root)==b''
names=['web/services/stripe_service.py','web/services/return_paths.py','web/routes/billing.py','tests/run_isolated.py','tests/isolation.py','web/settings.py','web/database/models.py']
def photo():return {'files':{n:sha((root/n).read_bytes()) for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py',str(test),'--noconftest','-q','--tb=short','--junitxml='+str(out/'result.xml')],cwd=root,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=90,check=False)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
xml=ET.fromstring((out/'result.xml').read_bytes());after=photo()
report={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'test_sha':sha(test.read_bytes()),'same_frozen_before_test':test.read_bytes()==beforetest.read_bytes(),'exit':result.returncode,'cases':len(xml.findall('.//testcase')),'failures':len(xml.findall('.//failure')),'errors':len(xml.findall('.//error')),'skips':len(xml.findall('.//skipped')),'source_packages_quiet':before==after,'before':before,'after':after,'scope':'Same independent11 pure real SDK-port service-body criteria. No auth/HTTP/RLS/network/payment or decorator-retry acceptance. Separate author13 covers sequential circuit behavior.'}
(out/'receipt.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items() if k not in {'before','after'}}))
assert result.returncode==0 and report['cases']==11 and not (report['failures'] or report['errors'] or report['skips']) and before==after
