"""Compose the separately reviewed archive fix with the eight CI2 trust pins."""
from pathlib import Path
import ast,hashlib,json,subprocess
root=Path(r'F:\mb-r12-ci29-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-archive-composition-20261019');out.mkdir(exist_ok=False)
git=lambda *args,**kwargs:subprocess.check_output(['git',*args],cwd=root,**kwargs)
assert git('rev-parse','HEAD',text=True).strip()=='67ae4664ed091f05568f49e366a67d6846d8a728'
assert not git('status','--porcelain','--untracked-files=no')
name='tests/verify_member_links_ci.py';before=git('show','HEAD:'+name)
old=b'ae535aab4f27b0ea2f76da4ef6068129c2a7520326012c77c1142a1a6cea14e6';new=b'58cf6c165d155d13120c3fe2ea50f1fac26960a3456c438418de45a2e040bbed'
base=git('show','1dc87ef5bf181825d9edff2269120de4fa589a66:'+name)
incoming=git('show','98ef40f0604ce730a1757940c4a551dd83f87fa2:'+name)
assert base.count(old)==before.count(old)==1 and incoming==base.replace(old,new)
result=subprocess.run(['git','cherry-pick','98ef40f0604ce730a1757940c4a551dd83f87fa2'],cwd=root,capture_output=True)
(out/'cherry.log').write_bytes(result.stdout+result.stderr)
if result.returncode:
    conflicts=git('diff','--name-only','--diff-filter=U','-z').decode().split('\0')[:-1]
    assert conflicts==[name],conflicts
    (out/'conflicted-verifier.RAW.py').write_bytes((root/name).read_bytes())
    (root/name).write_bytes(before.replace(old,new))
    subprocess.run(['git','-c','core.autocrlf=true','add','--',name],cwd=root,check=True,capture_output=True)
    continued=subprocess.run(['git','cherry-pick','--continue'],cwd=root,capture_output=True)
    (out/'continue.log').write_bytes(continued.stdout+continued.stderr);assert continued.returncode==0
else:
    assert (root/name).read_bytes().replace(b'\r\n',b'\n')==before.replace(old,new)
tree=ast.parse((root/name).read_text(encoding='utf-8-sig'))
pin_node=next(item.value for item in tree.body if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='PINNED_CURRENT_GATES' for target in item.targets));pins=ast.literal_eval(pin_node)
assert len(pins)==8 and pins['tests/run_reviewed_ci28.py']==new.decode()
for path,digest in pins.items():assert hashlib.sha256((root/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,path
assert not git('status','--porcelain','--untracked-files=no')
receipt={'base':'67ae4664ed091f05568f49e366a67d6846d8a728','incoming':'98ef40f0604ce730a1757940c4a551dd83f87fa2','head':git('rev-parse','HEAD',text=True).strip(),'pins':pins,'only_verifier_change':'One runner digest; all six CI2 executable anchors and two original anchors retained.','source_conflict_resolution_inverse_exact':(root/name).read_bytes().replace(b'\r\n',b'\n').replace(new,old)==before}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))
