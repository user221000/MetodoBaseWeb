"""Check the exact authenticated extra input and retain all original source and guards."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

root=Path(r'F:\mb-expat-clinic-input-20261019')
archive=Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\sca-native-triage31-20261019\primary\Python-3.12.15.tar.xz')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-clinic-verification-20261019')
base='d60d259c6d853483290efb65fa2d33ec14840207'
helper='runtime-source/expat-sec10/rebuild_pyexpat.py'
pins='runtime-source/expat-sec10/source-pins.json'
contract='runtime-source/expat-sec10/CONTRATO.md'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base
assert set(git('diff','--name-only','-z').decode().split('\0')[:-1])=={helper,pins,contract}
assert not git('diff','--cached','--name-only')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
old=git('show',base+':'+helper);new=(root/helper).read_bytes()
(out/'builder-before.GitLF.py').write_bytes(old)
(out/'builder-after.RAW.py').write_bytes(new)
oldlock=json.loads(git('show',base+':'+pins));lock=json.loads((root/pins).read_bytes())
oldns={'__file__':str(root/helper),'__name__':'old_guard_review'}
newns={'__file__':str(root/helper),'__name__':'new_guard_review'}
exec(compile(old,helper,'exec'),oldns)
exec(compile(new,helper,'exec'),newns)
before=oldns['source_files'](archive,oldlock)
after=newns['source_files'](archive,lock)
rows=[]
def check(name,condition):
    assert condition,name
    rows.append({'case':name,'passed':True})
check('Original30 retained exact, one authenticated header added',len(before)==30 and len(after)==31 and all(after[n]==b for n,b in before.items()) and set(after)-set(before)=={'Modules/clinic/pyexpat.c.h'})
check('Known native include now resolves inside selected source',b'#include "clinic/pyexpat.c.h"' in after['Modules/pyexpat.c'] and len(after['Modules/clinic/pyexpat.c.h'])==29204 and sha(after['Modules/clinic/pyexpat.c.h'])=='5e730198b2e3b644a96b411d5e594654d23146110b880a6ee9961fc919d90acb')
check('Every previous pin remains exact',set(lock)-set(oldlock)=={'clinic_header_sha256'} and all(lock[k]==v for k,v in oldlock.items()))
normalized=new.decode().replace('\r\n','\n')
inverse=normalized.replace("'Modules/pyexpat.c','Modules/clinic/pyexpat.c.h'","'Modules/pyexpat.c'").replace('len(selected)==31','len(selected)==30').replace("    assert digest(selected['Modules/clinic/pyexpat.c.h'])==lock['clinic_header_sha256'],'Unexpected Argument Clinic header'\n",'')
check('Three helper edits invert to exact parent GitLF',inverse.encode()==old)
for name in ['backport','build','main']:
    def function(blob):return next(n for n in ast.parse(blob).body if isinstance(n,ast.FunctionDef) and n.name==name)
    check('Unchanged full AST '+name,ast.dump(function(old),include_attributes=False)==ast.dump(function(new),include_attributes=False))
bad=dict(lock,clinic_header_sha256='0'*64)
try:newns['source_files'](archive,bad)
except AssertionError:check('Wrong extra-header pin rejected',True)
else:raise AssertionError('Incorrect header digest accepted')
bad=dict(lock,psf_source_sha256='0'*64)
try:newns['source_files'](archive,bad)
except AssertionError:check('Wrong PSF archive pin rejected',True)
else:raise AssertionError('Incorrect archive digest accepted')
prepared=newns['prepare'](archive,out/'prepared',lock)
check('Preparation changes only original upstream xmlparse backport',prepared['changed_source_files']==['Modules/expat/xmlparse.c'] and prepared['before']['Modules/clinic/pyexpat.c.h']==prepared['after']['Modules/clinic/pyexpat.c.h']==lock['clinic_header_sha256'])
patch=(root/'runtime-source/expat-sec10/13c5f63.patch').read_bytes()
try:newns['backport'](before['Modules/expat/xmlparse.c'],patch+b'\n',lock)
except AssertionError:check('Changed patch bytes rejected',True)
else:raise AssertionError('Changed backport accepted')
subprocess.run(['git','diff','--check'],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',helper,pins,contract],cwd=root,check=True,capture_output=True)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])=={helper,pins,contract}
subprocess.run(['git','commit','-m','Include authenticated Argument Clinic input in the pyexpat build'],cwd=root,check=True,capture_output=True)
receipt={'base':base,'head':git('rev-parse','HEAD').decode().strip(),'checks':rows,'checks_passed':len(rows),
 'original_sources_exact':30,'selected_sources':31,'archive_sha256':lock['psf_source_sha256'],
 'header_sha256':lock['clinic_header_sha256'],'header_bytes':29204,
 'Docker_locks_tar_patch_compiler_build_import_tests_changed':False,
 'builder_before_GitLF_sha256':sha(old),'builder_after_RAW_sha256':sha(new),
 'prepared_source_record_sha256':sha((out/'prepared/source-preparation.json').read_bytes()),
 'scope':'Root author offline selection/backport checks only. Native D60 failure remains; no compiler/import/ELF/linkage/runtime acceptance. Independent Security and native rebuild required.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps(receipt))
