from pathlib import Path
import ast,hashlib,json,subprocess
R=Path(r'F:/mb-security-r05-classifier-peer-20261019');O=R/'docs/implementation/20261018-evolution/evidence/security-r05-registry-independent-20261019'
OLD='17c9b836776d8ebe51b619ab2b552fafab51f4de';NEW='f7b12a71a89de2e35b0035ccef147a673ad50d29';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git',*a],cwd=R)
assert git('rev-parse','HEAD').decode().strip()==OLD and not git('diff','--name-only')
names=git('diff','--name-only',OLD,NEW).decode().splitlines();assert set(names)=={'scripts/reviewed_scan_locations.py','tests/test_secret_scan_reviewed_locations.py'}
proof={}
for name in names:
    a=(R/name).read_bytes();b=git('show',NEW+':'+name)
    assert a==b+b'\n' and ast.dump(ast.parse(a))==ast.dump(ast.parse(b))
    proof[name]={'before_sha256':sha(a),'after_sha256':sha(b),'removed_bytes':1,'removed_only_terminal_LF':True,'AST_exact':True}
for name in ['scripts/scan_secrets.py','scripts/data/reviewed_scan_locations_v1.zip']:
    assert (R/name).read_bytes()==git('show',NEW+':'+name)
git('checkout','--detach',NEW);assert not git('diff','--name-only')
(O/'final-freeze-transition.json').write_bytes((json.dumps({'from':OLD,'to':NEW,'only_two_terminal_LF_removed':proof,'runner_and_dataset_RAW_exact':True},indent=2)+'\n').encode())
print(json.dumps({'final_commit':NEW,'AST_change':False,'runner_dataset_change':False}))
