"""Prepare a separate runtime source; do not mutate the running SaaS matrix."""
from pathlib import Path
import json
import subprocess

repo=Path(r'F:\mb-mfa31-compose-20261019');root=Path(r'F:\mb-mfa31-runtime72-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-runtime72-compose-20261019')
base='809eab28c40c112cb6e3c9d8caceebae28683abd';native='72c44a1834d7bd9803b4b8846c6c87e85a53bfd3'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=repo)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
assert not root.exists() and not out.exists()
ancestor=git('merge-base',base,native).decode().strip()
changed=git('diff','--name-only','-z',ancestor,native).decode().split('\0')[:-1]
allowed={'Dockerfile','requirements-container-apt-metadata.lock','requirements-container-build.lock','requirements-container-psycopg.lock','requirements-container.lock',
 'runtime-source/expat-sec10/.gitattributes','runtime-source/expat-sec10/13c5f63.patch','runtime-source/expat-sec10/CONTRATO.md','runtime-source/expat-sec10/rebuild_pyexpat.py','runtime-source/expat-sec10/source-pins.json',
 'tests/fixtures/expat_sec10/.gitattributes','tests/fixtures/expat_sec10/setuptools84-call-source.json','tests/test_expat_sec10_build_contract.py'}
assert len(changed)==33
assert {n for n in changed if not n.startswith('docs/implementation/20261018-evolution/evidence/')}==allowed
inventory={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in git('ls-tree','-r',base).decode().splitlines()}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'before.json').write_bytes((json.dumps({'app_base':base,'native_source':native,'changed':changed,'Git_blob_OIDs':inventory},indent=2)+'\n').encode())
add=subprocess.run(['git','-c','core.autocrlf=false','worktree','add','-b','implementation/mfa31-runtime72-20261019',str(root),base],cwd=repo,capture_output=True)
(out/'worktree.stdout.raw.log').write_bytes(add.stdout);(out/'worktree.stderr.raw.log').write_bytes(add.stderr)
assert add.returncode==0
merge=subprocess.run(['git','merge','--no-edit',native],cwd=root,capture_output=True)
(out/'merge.stdout.raw.log').write_bytes(merge.stdout);(out/'merge.stderr.raw.log').write_bytes(merge.stderr)
assert merge.returncode==0
runtime_git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
head=runtime_git('rev-parse','HEAD').decode().strip()
after={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in runtime_git('ls-tree','-r',head).decode().splitlines()}
assert not runtime_git('status','--porcelain','--untracked-files=no')
assert all(after[n]==oid for n,oid in inventory.items() if n not in changed)
assert all(runtime_git('show',head+':'+n)==git('show',native+':'+n) for n in changed)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
receipt={'head':head,'app_base':base,'native_source':native,'native_changed_paths_exact':33,
 'other_Git_blobs_exact':len(inventory)-len(set(changed)&set(inventory)),
 'running_broad_worktree_unchanged':True,'native_SEC_review':'Separate same-image verification in progress; no acceptance inferred.',
 'runtime_built':False,'scope':'Source preparation in a separate worktree only. No VM mutation or build.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
