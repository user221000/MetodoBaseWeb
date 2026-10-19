"""Preserve the owned CI2 patch, compose accepted-source CI1 fix, reapply CI2."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(r'F:\mb-r12-ci29-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-trust-composition-20261019');out.mkdir(exist_ok=False)
paths=['.github/workflows/ci.yml','tests/e2e/member_link_export.cjs','tests/verify_member_links_ci.py']
git=lambda *args,**kwargs:subprocess.check_output(['git',*args],cwd=root,**kwargs)
assert git('rev-parse','HEAD',text=True).strip()=='ce1afda202fd27a3433ba8247d374d8e496cb5b0'
assert set(git('diff','--name-only','-z').decode().split('\0')[:-1])==set(paths)
assert not git('diff','--cached','--name-only')
before={name:(root/name).read_bytes() for name in paths}
for index,name in enumerate(paths):(out/('owned-before-'+str(index))).write_bytes(before[name])
patch=git('diff','--binary','--',*paths);(out/'owned-ci2.patch').write_bytes(patch)
subprocess.run(['git','restore','--source=HEAD','--',*paths],cwd=root,check=True,capture_output=True)
subprocess.run(['git','cherry-pick','1dc87ef5bf181825d9edff2269120de4fa589a66'],cwd=root,check=True,capture_output=True)
result=subprocess.run(['git','apply','--3way',str(out/'owned-ci2.patch')],cwd=root,capture_output=True)
(out/'apply.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
subprocess.run(['git','restore','--staged','--',*paths],cwd=root,check=True,capture_output=True)
for name in paths[:2]:assert (root/name).read_bytes().replace(b'\r\n',b'\n')==before[name].replace(b'\r\n',b'\n')
proof={'parent_head':'ce1afda202fd27a3433ba8247d374d8e496cb5b0','composed_head':git('rev-parse','HEAD',text=True).strip(),'CI2_patch_preserved_sha256':hashlib.sha256(patch).hexdigest(),'paths':{name:{'owned_before_RAW':hashlib.sha256(before[name]).hexdigest(),'after_RAW':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in paths},'merge':'Three-way patch reapplied; workflow/export unchanged under checkout newline normalization; verifier includes independent trust repair plus pending CI2 delta.'}
(out/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps(proof))
