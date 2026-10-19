import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root=Path('F:/mb-r12-full29-20261019')
temp=Path('C:/Users/Consu/AppData/Local/Temp')
ev=root/'docs/implementation/20261018-evolution/evidence/r12-composed-page-headers-20261019'
ev.mkdir(exist_ok=False)
(ev/'.gitattributes').write_bytes(b'* -text\n')
before=temp/'metodobase-r12-http-before-page-composition-20261019.py'
after=root/'tests/integration_client_link_http.py'
source=after.read_text(encoding='utf-8')
element="    ('/auth/accept-client-link','post'),\n"
block="    if path=='/auth/accept-client-link' and method=='get':\n        assert response.status_code==200\n    else:\n        assert response.status_code in {404,405}\n"
assert source.count(element)==source.count(block)==1
inverse=source.replace(element,'').replace(block,'    assert response.status_code in {404,405}\n')
assert ast.dump(ast.parse(inverse),include_attributes=False)==ast.dump(ast.parse(before.read_text(encoding='utf-8')),include_attributes=False)
shutil.copyfile(before,ev/'http-test-before-page.py')
for label,name in [('before354','metodobase-r12-composition29-root-gates-20261019'),('after28','metodobase-r12-composed-page-focal-20261019')]:
    shutil.copytree(temp/name,ev/label)
for name in ['metodobase-r12-composition29-root-gates-20261019.py','metodobase-r12-composed-page-focal-20261019.py','metodobase-history30-final-base-test-20261019.py']:
    shutil.copyfile(temp/name,ev/name)
shutil.copyfile(__file__,ev/'package-driver.py')
(ev/'review.json').write_bytes((json.dumps({'scope':'Test-only composition update; mounted acceptance page returns200 instead of backend-only404. Four POST-page wrong-method criteria added; all previous privacy/CSP checks retained.','AST_other_than_one_expected_status_and_one_new_parameter_element_unchanged':True,'before':{'cases':354,'passed':348,'failed':4,'known_SQLite_PG_only_skips':2},'after_focal':{'cases':28,'passed':28,'failed':0,'skipped':0},'all_sources_and_packages_quiet':True,'runtime_unchanged':'b8d0b8fe86188486084cc7178703477fa70ad7b3','SEC500scope':'Independent actual500review separate; not claimed fixed by these tests.'},indent=2)+'\n').encode())
sources=['tests/integration_client_link_http.py']
subprocess.run(['git','-c','core.autocrlf=true','add','--',*sources],cwd=root,check=True,capture_output=True)
proofs=sorted(p.relative_to(root).as_posix() for p in ev.rglob('*') if p.is_file())
for offset in range(0,len(proofs),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*proofs[offset:offset+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',ev.relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
buffer=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(':'+name+'\n' for name in proofs).encode());cursor=0
for name in proofs:
    end=buffer.index(b'\n',cursor);parts=buffer[cursor:end].split();assert parts[1]==b'blob';size=int(parts[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(root/name).read_bytes();cursor+=size+1
assert cursor==len(buffer)
subprocess.run(['git','diff','--cached','--check','--',*sources],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Verify private headers after mounting the R12 acceptance page'],cwd=root,check=True,stdout=subprocess.DEVNULL)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'RAW_Git_exact':len(proofs),'product_changed':False}))
