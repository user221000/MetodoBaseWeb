from pathlib import Path
import hashlib,importlib.metadata,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
root=Path(r'F:\mb-r24-invalidated-controls-20261019');mode=sys.argv[1];assert mode in {'before','after'}
out=Path(r'C:\Users\Consu\AppData\Local\Temp')/('metodobase-r24-privacy-root-'+mode+'-20261019');out.mkdir(exist_ok=False)
source=Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\qa-r24-independent-20261019\failure-privacy-driver.raw')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='999f84c84996de56b2fbbc8aa66a2ed1c585f96cc686ca8cf9724d5ba35b6a22'
test=out/'test_r24_failure_privacy.py';shutil.copyfile(source,test)
def photo():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    return {'sources':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names if name and (root/name).is_file()},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();env={**os.environ,'PYTHONPATH':str(root),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1','R24_FAILURE_OUTPUT':str(out/'proofs')}
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py','--rootdir='+str(root),'--import-mode=importlib',str(test),'-q','--tb=short','--junitxml='+str(out/'junit.xml')],cwd=root,capture_output=True,env=env,timeout=120,check=False)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
xml=ET.fromstring((out/'junit.xml').read_bytes());after=photo()
receipt={'mode':mode,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'middleware_sha':hashlib.sha256((root/'web/middleware/security_headers.py').read_bytes()).hexdigest(),'driver_sha':hashlib.sha256(test.read_bytes()).hexdigest(),'exit':result.returncode,'cases':len(xml.findall('.//testcase')),'failures':len(xml.findall('.//failure')),'errors':len(xml.findall('.//error')),'skips':len(xml.findall('.//skipped')),'sources_quiet':before==after,'before':before,'after':after,'scope':'Same independent QA frozen four HTTP/SQLite criteria; no PostgreSQL/browser/network.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k not in {'before','after'}}))
assert receipt['cases']==4 and receipt['errors']==0 and receipt['skips']==0 and before==after
assert result.returncode==(1 if mode=='before' else 0) and receipt['failures']==(4 if mode=='before' else 0)
