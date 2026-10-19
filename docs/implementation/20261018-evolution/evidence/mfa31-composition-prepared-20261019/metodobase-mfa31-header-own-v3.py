from pathlib import Path
import ast,hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path(r'F:\mb-mfa31-compose-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');out=tmp/'metodobase-mfa31-header-own-v3-20261019';out.mkdir(exist_ok=False)
old=tmp/'test_metodobase_mfa_diary_composed_headers.py';test=tmp/'test_metodobase_mfa_diary_composed_headers_v3.py';sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(old.read_bytes())=='ea0c0e2c14abad65546cbecdb3fde91339a5bb5db921613421b25bc613b656cd'
assert sha(test.read_bytes())=='a278add1ed03112d49b09840fbd0bccae9cfb2285fe46c22b4a6b96b9c9f573b'
asserts=lambda b:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(b)) if isinstance(n,ast.Assert)]
assert asserts(old.read_bytes())==asserts(test.read_bytes())
names=['web/middleware/security_headers.py','tests/isolation.py','tests/run_isolated.py']
def photo():return {'sources':{n:sha((root/n).read_bytes()) for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();assert before['sources']['web/middleware/security_headers.py']=='06de08dabcc871987c63135446186ad53e368c42efbe9de9b13591bc84aa1476'
env={**os.environ,'PYTHONPATH':str(root),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1'}
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py','--noconftest','--rootdir='+str(root),'--import-mode=importlib',str(test),'-q','--tb=short','--junitxml='+str(out/'result.xml')],cwd=root,capture_output=True,env=env,timeout=45,check=False)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr);xml=ET.fromstring((out/'result.xml').read_bytes());after=photo()
receipt={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'exit':result.returncode,'cases':len(xml.findall('.//testcase')),'failures':len(xml.findall('.//failure')),'errors':len(xml.findall('.//error')),'skips':len(xml.findall('.//skipped')),'source_packages_quiet':before==after,'test_sha256':sha(test.read_bytes()),'assert_nodes_exact':len(asserts(old.read_bytes())),'before':before,'after':after,'causality_driver_harness_note':'Original causality script contained an inert conditional hash assertion. This separate real assertion verifies original/refined source digests and AST10 before execution; no source or prior receipt rewritten.','scope':'Eight own fixture-refined composition criteria only. Prior94maintained passed in initial102run; not repeated or reported as a fresh102pass. No product source change, services, PG or browser.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k not in {'before','after'}}));assert result.returncode==0 and receipt['cases']==8 and before==after
