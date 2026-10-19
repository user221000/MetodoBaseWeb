from pathlib import Path
import hashlib
import json
import subprocess

repo=Path(r'F:\mb-mfa31-compose-20261019')
root=Path(r'F:\mb-mfa31-reviewed-common-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-reviewed-common-compose-20261019')
base='6a75d096ea3d63d9e78c76d33b7e243160b23364'
clock='d0121919e6207dd76bbb8c0c9bff5966c6930d3f'
logging='4740fa235170ded9596927c9ea261a9d7998122e'
git=lambda *args,cwd=repo:subprocess.check_output(['git','--no-replace-objects',*args],cwd=cwd)
sha=lambda data:hashlib.sha256(data).hexdigest()
assert not root.exists() and not out.exists()
assert git('rev-parse','HEAD').decode().strip()==base
assert not git('status','--porcelain','--untracked-files=no')
def inventory(ref):
    result={}
    for row in git('ls-tree','-r','-z',ref).split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1);result[name.decode()]=meta.decode()
    return result
before=inventory(base)
proof='docs/implementation/20261018-evolution/evidence/'
expected={clock:{'tests/ci_mfa31/current_link_fixtures.py','tests/mfa31_contract_client.py',
    'tests/test_current_mfa31_fixture_clock.py','tests/test_mfa31_contract_clock.py','tests/test_mfa31_contract_clock_keyword.py'},
    logging:{'alembic.ini','tests/test_bootstrap_outcome_logging.py'}}
changes={}
for ref,allowed in expected.items():
    subprocess.run(['git','merge-base','--is-ancestor',base,ref],cwd=repo,check=True,capture_output=True)
    names=set(git('diff','--name-only','-z',base,ref).decode().split('\0')[:-1])
    assert {name for name in names if not name.startswith(proof)}==allowed
    changes[ref]=sorted(names)
assert not set(changes[clock])&set(changes[logging])
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'before.json').write_bytes((json.dumps({'base':base,'Git_tree_entries':before},indent=2)+'\n').encode())
def run(label,command,cwd):
    result=subprocess.run(command,cwd=cwd,capture_output=True)
    (out/(label+'.stdout.raw.log')).write_bytes(result.stdout)
    (out/(label+'.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode==0,label
run('worktree',['git','-c','core.autocrlf=false','worktree','add','-b','implementation/mfa31-reviewed-common-20261019',str(root),base],repo)
run('merge-clock',['git','merge','--ff-only',clock],root)
run('merge-logging',['git','merge','--no-edit',logging],root)
head=git('rev-parse','HEAD',cwd=root).decode().strip()
after=inventory(head);altered=set().union(*map(set,changes.values()))
assert set(after)==set(before)|altered
assert all(after[name]==meta for name,meta in before.items() if name not in altered)
for ref,names in changes.items():
    for name in names:
        assert git('show',head+':'+name)==git('show',ref+':'+name),name
assert git('rev-parse','HEAD').decode().strip()==base
assert not git('status','--porcelain','--untracked-files=no')
assert not git('status','--porcelain','--untracked-files=no',cwd=root)
receipt={'base':base,'head':head,'exact_changes_by_source':changes,
    'other_Git_tree_entries_exact':len(set(before)-altered),
    'production_change_only':['alembic.ini'],'schema31_application_sources_unchanged':True,
    'scope':'Isolated preparation only. Independent peer of d012 remains required before broad runs. No schema32 or runtime image attribution.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({key:value for key,value in receipt.items() if key!='exact_changes_by_source'}))
