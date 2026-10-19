from pathlib import Path
import hashlib
import json
import subprocess

root=Path(r'F:\mb-mfa31-compose-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-compose-r17-20261019')
before='38b906848874171b53dcb2342769ed20618e9ce6'
reviewed='b50058280b9e4989799732b81a8a10292ebaba92'
common='bd34893c4b6f806041b0cc6b7f156e9286886748'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==before and not git('status','--porcelain','--untracked-files=no')
assert not out.exists()
changed=git('diff','--name-only','-z',common,reviewed).decode().split('\0')[:-1]
assert set(changed)=={'api/app.py','web/main_web.py','web/middleware/metrics.py','web/middleware/security_headers.py',
 'web/observability/routes.py','tests/test_saas_observability_contract.py','tests/test_metrics_privacy_review.py'}
inventory={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in git('ls-tree','-r',before).decode().splitlines()}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'before.json').write_bytes((json.dumps({'head':before,'reviewed':reviewed,'changed':changed,'Git_blob_OIDs':inventory},indent=2)+'\n').encode())
run=subprocess.run(['git','merge','--no-edit',reviewed],cwd=root,capture_output=True)
(out/'merge.stdout.raw.log').write_bytes(run.stdout);(out/'merge.stderr.raw.log').write_bytes(run.stderr)
assert run.returncode==0
head=git('rev-parse','HEAD').decode().strip()
after={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in git('ls-tree','-r',head).decode().splitlines()}
assert not git('status','--porcelain','--untracked-files=no')
assert all(after[n]==oid for n,oid in inventory.items() if n not in changed)
assert all(git('show',head+':'+n)==git('show',reviewed+':'+n) for n in changed)
summary={'head':head,'base':before,'reviewed_R17_commit':reviewed,'changed_files_exact':len(changed),
 'other_Git_blobs_exact':len(inventory)-len(set(changed)&set(inventory)),
 'peer':'Independent same24+2 PASS on b500; full composed regression not yet run.',
 'CI_ed4_and_173_nodeids_unchanged':True,'schema':31,'new_execution_claim':False}
(out/'receipt.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary))
