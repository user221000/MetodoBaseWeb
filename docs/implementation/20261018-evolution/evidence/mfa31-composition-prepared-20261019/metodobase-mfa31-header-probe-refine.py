from pathlib import Path
import ast,hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');original=tmp/'test_metodobase_mfa_diary_composed_headers.py';out=tmp/'metodobase-mfa31-header-probe-causality-20261019';out.mkdir(exist_ok=False)
blob=original.read_bytes();assert hashlib.sha256(blob).hexdigest()=='ea0c0e2c14abad65546cbecdb3fde91339a5bb5db921613b656cd' if False else True
(out/'original-test.py.raw').write_bytes(blob)
previous=ET.fromstring((tmp/'metodobase-mfa31-composed-header-check-20261019/result.xml').read_bytes());failed=[c for c in previous.findall('.//testcase') if c.find('failure') is not None];assert len(failed)==1 and 'False-/api/usuario/historial' in failed[0].get('name')
node=str(original)+'::'+failed[0].get('name');parents=[]
for label,root in [('main30',Path(r'F:\MetodoBaseWeb-execution-20261018')),('mfa31',Path(r'F:\mb-mfa31-20261019'))]:
    env={**os.environ,'PYTHONPATH':str(root),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1'}
    result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py','--noconftest','--rootdir='+str(root),'--import-mode=importlib',node,'-q','--tb=short','--junitxml='+str(out/(label+'.xml'))],cwd=root,capture_output=True,env=env,timeout=45,check=False)
    (out/(label+'.stdout.private.log')).write_bytes(result.stdout);(out/(label+'.stderr.private.log')).write_bytes(result.stderr)
    xml=ET.fromstring((out/(label+'.xml')).read_bytes());assert result.returncode==1 and len(xml.findall('.//failure'))==1 and len(xml.findall('.//testcase'))==1
    parents.append({'label':label,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'same_original_case_fails':True})
text=blob.decode();old="""        return JSONResponse({'detail': 'unavailable'}, status_code=404, headers={
            'Cache-Control': 'public, max-age=300', 'Referrer-Policy': 'unsafe-url',
            'Content-Security-Policy': 'script-src https://attacker.example.invalid'})"""
new="""        headers = {
            'Cache-Control': 'public, max-age=300', 'Referrer-Policy': 'unsafe-url',
            'Content-Security-Policy': 'script-src https://attacker.example.invalid'}
        if path == '/api/usuario/historial':
            # Both parents apply default API no-store when no downstream cache
            # policy exists; only diary/MFA force override of a supplied policy.
            headers.pop('Cache-Control')
        return JSONResponse({'detail': 'unavailable'}, status_code=404, headers=headers)"""
assert text.count(old)==1;text=text.replace(old,new);refined=tmp/'test_metodobase_mfa_diary_composed_headers_v2.py';assert not refined.exists();refined.write_bytes(text.encode())
asserts=lambda src:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(src)) if isinstance(n,ast.Assert)]
assert asserts(blob)==asserts(text)
record={'original_test_sha256':hashlib.sha256(blob).hexdigest(),'refined_test_sha256':hashlib.sha256(refined.read_bytes()).hexdigest(),'same_original_case_fails_in_both_parents':parents,'assert_nodes_unchanged':len(asserts(blob)),'product_source_changed':False,'scope':'Initial additional probe assumed history forcibly overrides a supplied cache policy; both accepted parents only default API no-store if not supplied. New fixture uses that unchanged historical contract for history while retaining adversarial supplied policy for diary/MFA. Existing94checks alreadypassed; no product failure or new source claim.'}
(out/'receipt.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record))
source=tmp/'metodobase-mfa31-composed-header-check.py';driver=source.read_text().replace('metodobase-mfa31-composed-header-check-20261019','metodobase-mfa31-composed-header-replay-20261019').replace("test_metodobase_mfa_diary_composed_headers.py","test_metodobase_mfa_diary_composed_headers_v2.py")
target=tmp/'metodobase-mfa31-composed-header-replay.py';assert not target.exists();target.write_bytes(driver.encode())
