"""Correct one inactive hidden control; no action/leak resurrection is claimed."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
ROOT=Path(r'F:\mb-r24-invalidated-controls-20261019');EV=ROOT/'docs/implementation/20261018-evolution/evidence/r24-invalidated-controls-author-20261019';EV.mkdir(exist_ok=False);(EV/'.gitattributes').write_bytes(b'* -text\n')
BASE='adc80c7edb6314a7851b9447bccb092a62c142d5';NODE='C:/Program Files/nodejs/node.exe'
TEST=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r24-security-independent-20261019\vm_review_v5.cjs')
sha=lambda b:hashlib.sha256(b).hexdigest();git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=ROOT,**k)
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
assert sha(TEST.read_bytes())=='363fca611fc79aef71d6568edf227870f46111ab4ee91106495b5eb3c1b3409b'
shutil.copyfile(TEST,EV/'independent-frozen-criteria.cjs')
target=ROOT/'web/static/js/plan-publicacion-consumo.js';before=target.read_bytes();(EV/'before.raw.js').write_bytes(before)
assert before.replace(b'\r\n',b'\n')==git('show',BASE+':web/static/js/plan-publicacion-consumo.js')
def run(label,script,expected):
    result=subprocess.run([NODE,str(script)],cwd=ROOT,env={**os.environ,'R24_REVIEW_ROOT':str(ROOT)},capture_output=True,timeout=30,check=False)
    (EV/(label+'.stdout.json')).write_bytes(result.stdout);(EV/(label+'.stderr.log')).write_bytes(result.stderr)
    assert result.returncode==expected,(label,result.stderr.decode(errors='replace'))
    return {'exit':result.returncode,'stdout_sha256':sha(result.stdout)}
old=run('before',TEST,1)
needle=b'discard.disabled=update.busy';replacement=b'discard.disabled=!active||update.busy'
assert before.count(needle)==1;after=before.replace(needle,replacement);target.write_bytes(after);assert after.replace(replacement,needle)==before
new=run('after',TEST,0);maintained=run('maintained17',ROOT/'tests/e2e/daily_plan_controls.cjs',0)
shutil.copyfile(__file__,EV/'driver.py')
data={'base':BASE,'driver_sha256':sha(TEST.read_bytes()),'before':old,'after':new,'maintained17':maintained,'source_raw_before_sha256':sha(before),'source_raw_after_sha256':sha(after),'source_git_lf_after_sha256':sha(after.replace(b'\r\n',b'\n')),'inverse_exact':True,'scope':'Same16 independent controlled-DOM criteria before/after plus maintained17; no browser/HTTP/PG. Five failed predicates require disabled state after invalidation; button was hidden and no capability/leak demonstrated. Fix only retains disabled while inactive. Prior R24 real11 not rerun or relabelled.'}
(EV/'receipt.json').write_bytes((json.dumps(data,indent=2)+'\n').encode());(EV/'freeze.json').write_bytes((json.dumps({'files':{p.name:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(EV.iterdir())}},indent=2)+'\n').encode())
names=sorted(p.relative_to(ROOT).as_posix() for p in EV.iterdir());source=target.relative_to(ROOT).as_posix()
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names],cwd=ROOT,check=True,capture_output=True);subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',source],cwd=ROOT,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
assert git('show',':'+source)==after.replace(b'\r\n',b'\n')
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+[source])
subprocess.run(['git','diff','--cached','--check','--',source],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Keep inactive publication discard control disabled'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain');print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'freeze':sha((EV/'freeze.json').read_bytes()),**data}))
