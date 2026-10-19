"""Resume after owned-source checkout had stale newline/stat index entries."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(r'F:\mb-r12-ci29-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-trust-composition-20261019')
paths=['.github/workflows/ci.yml','tests/e2e/member_link_export.cjs','tests/verify_member_links_ci.py']
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=root,**kw)
assert git('rev-parse','HEAD',text=True).strip()=='ce1afda202fd27a3433ba8247d374d8e496cb5b0'
for name in paths:assert (root/name).read_bytes().replace(b'\r\n',b'\n')==git('show','HEAD:'+name)
subprocess.run(['git','-c','core.autocrlf=true','add','--renormalize','--',*paths],cwd=root,check=True,capture_output=True)
assert not git('diff','--cached','--name-only') and not git('status','--porcelain','--untracked-files=no')
cherry=subprocess.run(['git','cherry-pick','1dc87ef5bf181825d9edff2269120de4fa589a66'],cwd=root,capture_output=True)
(out/'cherry-resumed.log').write_bytes(cherry.stdout+cherry.stderr);assert cherry.returncode==0
apply=subprocess.run(['git','apply','--3way',str(out/'owned-ci2.patch')],cwd=root,capture_output=True)
(out/'apply.log').write_bytes(apply.stdout+apply.stderr);assert apply.returncode==0
subprocess.run(['git','restore','--staged','--',*paths],cwd=root,check=True,capture_output=True)
before={name:(out/('owned-before-'+str(index))).read_bytes() for index,name in enumerate(paths)}
for name in paths[:2]:assert (root/name).read_bytes().replace(b'\r\n',b'\n')==before[name].replace(b'\r\n',b'\n')
proof={'parent_head':'ce1afda202fd27a3433ba8247d374d8e496cb5b0','composed_head':git('rev-parse','HEAD',text=True).strip(),'CI2_patch_preserved_sha256':hashlib.sha256((out/'owned-ci2.patch').read_bytes()).hexdigest(),'paths':{name:{'owned_before_RAW':hashlib.sha256(before[name]).hexdigest(),'after_RAW':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in paths},'first_attempt':'Checkout sources matched HEAD after newline normalization but two stale index entries blocked cherry-pick; no CHERRY_PICK_HEAD. Exact bytes authenticated, scoped renormalize restored empty index, resumed successfully.','merge':'CI2 patch reapplied with three-way merge; no uncommitted source was discarded.'}
(out/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps(proof))
