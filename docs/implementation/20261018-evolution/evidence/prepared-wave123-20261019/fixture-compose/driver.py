from pathlib import Path
import hashlib
import json
import subprocess

root=Path(r'F:\mb-mfa31-compose-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-compose-fixtures79-20261019')
before='5637b4daed86fa6ce3024c521aafdb6742373b08';reviewed='79dce040a9d79b51c1971bf4a99338a06c2ac659'
common='bd34893c4b6f806041b0cc6b7f156e9286886748'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==before and not git('status','--porcelain','--untracked-files=no')
assert not out.exists()
changed=git('diff','--name-only','-z',common,reviewed).decode().split('\0')[:-1]
testnames={'tests/current_mfa31_publication_fixtures.py','tests/test_current_publication_fixture_review.py','tests/test_identity_security.py','tests/test_publication_diary_consumption.py'}
assert set(n for n in changed if not n.startswith('docs/implementation/20261018-evolution/evidence/backend-mfa31-current-fixtures-20261019/'))==testnames
inventory={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in git('ls-tree','-r',before).decode().splitlines()}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'before.json').write_bytes((json.dumps({'head':before,'reviewed':reviewed,'changed':changed,'Git_blob_OIDs':inventory},indent=2)+'\n').encode())
result=subprocess.run(['git','merge','--no-edit',reviewed],cwd=root,capture_output=True)
(out/'merge.stdout.raw.log').write_bytes(result.stdout);(out/'merge.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode==0
head=git('rev-parse','HEAD').decode().strip()
after={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in git('ls-tree','-r',head).decode().splitlines()}
assert not git('status','--porcelain','--untracked-files=no')
assert all(after[n]==oid for n,oid in inventory.items() if n not in changed)
assert all(git('show',head+':'+n)==git('show',reviewed+':'+n) for n in changed)
receipt={'head':head,'base':before,'reviewed_fixture_commit':reviewed,'test_files_exact':4,
 'other_Git_blobs_exact':len(inventory)-len(set(changed)&set(inventory)),'schema':31,
 'product_CI_R17_and_173_nodeids_unchanged':True,'new_execution_claim':False}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
