"""Compose frozen CI only in the isolated candidate before its independent acceptance."""
from pathlib import Path
import hashlib
import json
import subprocess

root=Path(r'F:\mb-mfa31-compose-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci31-compose-20261019')
base='4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae'
incoming='e0c3f8b6d7a812c2b46d73748d56da72782c9f04'
git=lambda *args,**kw:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root,**kw)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
names=git('diff','--name-only','-z',base,incoming).decode().split('\0')[:-1]
assert len(names)==33 and all(n.startswith('tests/') or n=='.github/workflows/ci.yml' for n in names)
baseline=json.loads(git('show',incoming+':tests/ci_mfa31/baseline.json'))
for name,digest in baseline['helpers23_sha256'].items():
    assert git('show',base+':'+name)==git('show',incoming+':'+name)
    assert hashlib.sha256(git('show',base+':'+name)).hexdigest()==digest
assert hashlib.sha256(git('show',incoming+':tests/ci_mfa31/current-report-nodeids.json')).hexdigest()=='1a4b9e09110d226cf9777fd3d6824692c2136c6b5e65785ce196585c5b43f860'
expected=git('merge-tree','--write-tree',base,incoming).decode().strip()
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
result=subprocess.run(['git','merge','--no-commit','--no-ff',incoming],cwd=root,capture_output=True)
(out/'merge.stdout.raw.log').write_bytes(result.stdout)
(out/'merge.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode==0 and git('write-tree').decode().strip()==expected
staged=git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]
assert set(staged)==set(names)
for name in names:assert git('show',':'+name)==git('show',incoming+':'+name),name
subprocess.run(['git','diff','--cached','--check','--',*names],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Compose historical and current MFA31 CI for independent acceptance'],cwd=root,check=True,capture_output=True)
receipt={'before':base,'incoming':incoming,'head':git('rev-parse','HEAD').decode().strip(),
 'automatic_merge_tree_exact':True,'conflicts':0,'changed_CI_test_files':33,'product_changed':False,
 'historical_helpers_Git_bytes_exact':23,'scope':'Prepared isolated composition only; independent CI review/current173 PG/broad regression/image/Actions pending.',
 'files':{n:hashlib.sha256(git('show','HEAD:'+n)).hexdigest() for n in names}}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps(receipt))
