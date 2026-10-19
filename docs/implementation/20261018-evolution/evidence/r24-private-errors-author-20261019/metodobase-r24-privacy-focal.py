from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path(r'F:\mb-r24-invalidated-controls-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r24-privacy-focal-20261019');out.mkdir(exist_ok=False)
paths=['web/middleware/security_headers.py','tests/test_diary_private_headers.py']
photo=lambda:{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
before=photo();args=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests/test_diary_private_headers.py','tests/test_history_headers_followup.py','tests/test_recovery_method_headers.py','tests/test_security_middleware.py','-q','--tb=short','--junitxml='+str(out/'junit.xml')]
result=subprocess.run(args,cwd=root,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180,check=False)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
xml=ET.fromstring((out/'junit.xml').read_bytes());report={'exit':result.returncode,'cases':len(xml.findall('.//testcase')),'failures':len(xml.findall('.//failure')),'errors':len(xml.findall('.//error')),'skips':len(xml.findall('.//skipped')),'source_quiet':before==photo(),'sources':before,'command':args,'scope':'Maintained diary policy/fallback boundaries plus prior history/recovery/security-middleware regression; no PostgreSQL/browser/network.'}
(out/'receipt.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report));assert result.returncode==0 and before==photo()
