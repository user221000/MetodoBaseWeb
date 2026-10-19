from pathlib import Path
import hashlib
import json
import subprocess

root=Path(r'F:\mb-mfa31-compose-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-compose-ci-ed4-20261019')
before='bd34893c4b6f806041b0cc6b7f156e9286886748'
reviewed='ed4a3be11fb1e921962182812362b515afd8885a'
parent='e0c3f8b6d7a812c2b46d73748d56da72782c9f04'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==before
assert not git('status','--porcelain','--untracked-files=no')
changed=git('diff','--name-only','-z',parent,reviewed).decode().split('\0')[:-1]
assert len(changed)==11
assert all(n.startswith('tests/') or n=='.github/workflows/ci.yml' for n in changed)
tracked=git('ls-files','-z').decode().split('\0')[:-1]
products=[n for n in tracked if not n.startswith(('tests/','.github/','docs/implementation/'))]
sha=lambda b:hashlib.sha256(b).hexdigest()
snapshot={n:sha(git('show',before+':'+n)) for n in products}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'before.json').write_bytes((json.dumps({'head':before,'reviewed':reviewed,'changed':changed,'products':snapshot},indent=2)+'\n').encode())
result=subprocess.run(['git','merge','--no-edit',reviewed],cwd=root,capture_output=True)
(out/'merge.stdout.raw.log').write_bytes(result.stdout);(out/'merge.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode==0
head=git('rev-parse','HEAD').decode().strip()
assert not git('status','--porcelain','--untracked-files=no')
assert all(sha(git('show',head+':'+n))==digest for n,digest in snapshot.items())
assert all(git('show',head+':'+n)==git('show',reviewed+':'+n) for n in changed)
assert git('show',before+':tests/ci_mfa31/current-report-nodeids.json')==git('show',head+':tests/ci_mfa31/current-report-nodeids.json')
summary={'head':head,'base':before,'reviewed_CI_commit':reviewed,'CI_files':len(changed),'product_files_exact':len(products),
 'current_173_nodeids_exact':True,'new_execution_claim':False,'independent_contract_and_PostgreSQL_results':'QA on exact ed4 sources; closed raw proof pending seal.'}
(out/'receipt.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary))
