"""Publish two additive fixture changes without changing any VM assertion."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root=Path('F:/mb-r12-full29-20261019')
temp=Path('C:/Users/Consu/AppData/Local/Temp')
ev=root/'docs/implementation/20261018-evolution/evidence/r12-composed-export-fixture-20261019'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
ev.mkdir(exist_ok=False)
(ev/'.gitattributes').write_bytes(b'* -text\n')
before_fixture=temp/'metodobase-r12-export-fixture-before-20261019.cjs'
before_wrapper=temp/'metodobase-r12-export-wrapper-before-20261019.cjs'
fixture=root/'tests/e2e/personal_export_context.cjs'
wrapper=root/'tests/e2e/member_link_export.cjs'
names_old="'generation_requests','personal_diary'];"
names_new="'generation_requests','personal_diary','member_links'];"
scope_old="coverage:'account_and_persisted_personal_space'"
scope_new="member_links:'active_recipient_metadata_only',coverage:'account_persisted_personal_space_and_active_member_link_metadata'"
actual=fixture.read_text(encoding='utf-8')
assert actual.count(names_new)==actual.count(scope_new)==1
assert actual.replace(names_new,names_old).replace(scope_new,scope_old)==before_fixture.read_text(encoding='utf-8')
removed='replaceOnce("'+names_old+'","'+names_new+'");\nreplaceOnce("'+scope_old+'","'+scope_new+'");\n'
marker="replaceOnce('async function fixture(){'"
actual=wrapper.read_text(encoding='utf-8')
assert actual.count(marker)==1
assert actual.replace(marker,removed+marker)==before_wrapper.read_text(encoding='utf-8')
for label,name in [('before17','metodobase-r12-node-composition29-20261019'),('after2','metodobase-r12-node-export-focal-20261019'),('private500_focal123','metodobase-r12-private500-composition-focal-20261019')]:
    shutil.copytree(temp/name,ev/label)
for source,label in [(before_fixture,'fixture-before.cjs'),(before_wrapper,'wrapper-before.cjs'),(temp/'metodobase-r12-middleware-before-private500-20261019.py','middleware-before-private500.py')]:
    shutil.copyfile(source,ev/label)
for name in ['metodobase-r12-node-composition29-20261019.py','metodobase-r12-node-export-focal-20261019.py','metodobase-r12-private500-composition-focal-20261019.py']:
    shutil.copyfile(temp/name,ev/name)
shutil.copyfile(__file__,ev/'package-driver.py')
review={'kind':'Test-only DTO7 fixture alignment, plus completed root private500 focal evidence',
    'fixture_inverse_matches_before_byte_for_byte_after_EOL':True,'wrapper_inverse_matches_before_byte_for_byte_after_EOL':True,
    'changes_only':['Add seventh dataset name and exact coverage metadata in shared legacy fixture','Remove precisely two in-memory adaptations now redundant from member_link_export wrapper'],
    'all_test_assertions_retained':True,'initial17_node_modules':{'276_green_criteria':True,'old_export21_module_failed_before_case_output':True},
    'after_two_modules':{'legacy_export':21,'member_export':32,'failed':0},
    'current_VM_composition_unique_criteria':297,'single_all_green_17_module_run':False,
    'root_private500_focal':{'passed':123,'failed':0,'skipped':0,'scope':'Exact9d0 runtime; no independent API/browser acceptance'},
    'sources_quiet_each_phase':True,'product_changed_in_this_commit':False}
(ev/'review.json').write_bytes((json.dumps(review,indent=2)+'\n').encode())
sources=[fixture.relative_to(root).as_posix(),wrapper.relative_to(root).as_posix()]
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
subprocess.run(['git','commit','-m','Align legacy export fixtures with the additive seventh dataset'],cwd=root,check=True,stdout=subprocess.DEVNULL)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'proof_blobs_exact':len(proofs),'test_assertions_unchanged':True,'product_changes':False}))
