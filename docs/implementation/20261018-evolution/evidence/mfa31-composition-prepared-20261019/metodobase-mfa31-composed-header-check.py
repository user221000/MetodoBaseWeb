from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path(r'F:\mb-mfa31-compose-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-composed-header-check-20261019');out.mkdir(exist_ok=False)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='46dc908dd82edaa369f4d095df5abe7703a60de1'
test=Path(__file__).with_name('test_metodobase_mfa_diary_composed_headers.py')
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
def photo():return {'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();env={**os.environ,'PYTHONPATH':str(root),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1'}
command=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','--rootdir='+str(root),'--import-mode=importlib',str(test),'tests/test_diary_private_headers.py','tests/test_history_headers_followup.py','tests/test_recovery_method_headers.py','tests/test_security_middleware.py','-q','--tb=short','--junitxml='+str(out/'result.xml')]
result=subprocess.run(command,cwd=root,capture_output=True,env=env,timeout=180,check=False)
(out/'stdout.private.log').write_bytes(result.stdout);(out/'stderr.private.log').write_bytes(result.stderr)
xml=ET.fromstring((out/'result.xml').read_bytes());after=photo()
receipt={'head':head,'source_resolution_sha256':hashlib.sha256((root/'web/middleware/security_headers.py').read_bytes()).hexdigest(),'exit':result.returncode,'cases':len(xml.findall('.//testcase')),'failures':len(xml.findall('.//failure')),'errors':len(xml.findall('.//error')),'skips':len(xml.findall('.//skipped')),'source_packages_quiet':before==after,'sources':len(names),'packages':len(before['packages']),'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'before':before,'after':after,'scope':'Eight own composed privacy/fallback/adjacent/CSP criteria plus94maintained regression; isolated candidate only, not full MFA or main acceptance; no PG/browser/providers.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k not in {'before','after'}}));assert result.returncode==0 and receipt['cases']==102 and before==after
