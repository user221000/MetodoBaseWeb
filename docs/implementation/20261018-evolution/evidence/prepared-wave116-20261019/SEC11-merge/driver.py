from pathlib import Path
import hashlib,json,subprocess
root=Path(r'F:\MetodoBaseWeb-execution-20261018');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-main-sec11-merge-20261019');out.mkdir(exist_ok=False)
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
before='47c68bc540a048a90ef5f7ac75ec35d204cca96c';incoming='5316644608a09632a9997c25d50b1da3486ffc1b'
assert git('rev-parse','HEAD',text=True).strip()==before and not git('status','--porcelain','--untracked-files=no')
preview=git('merge-tree','--write-tree','--messages','HEAD',incoming,text=True);tree=preview.splitlines()[0];assert len(tree)==40;(out/'preview.txt').write_bytes(preview.encode())
reg='docs/implementation/20261018-evolution/TRAZABILIDAD.json';old=git('show','HEAD:'+reg)
historical=[p.relative_to(root).as_posix() for p in sorted((root/'web/database/alembic/schema_targets').glob('*.json'))]+['web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py']
pins={name:git('show','HEAD:'+name) for name in historical}
result=subprocess.run(['git','merge','--no-ff',incoming,'-m','Integrate independently reviewed portal return validation before provider circuit'],cwd=root,capture_output=True)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr);assert result.returncode==0
assert git('rev-parse','HEAD^{tree}',text=True).strip()==tree
assert git('show','-s','--format=%P','HEAD',text=True).strip().split()==[before,incoming]
assert git('show','HEAD:'+reg)==old
for name,blob in pins.items():assert git('show','HEAD:'+name)==blob,name
sources=['web/services/return_paths.py','web/services/stripe_service.py','tests/test_billing_return_paths.py']
for name in sources:assert git('show','HEAD:'+name)==git('show',incoming+':'+name),name
assert not git('status','--porcelain','--untracked-files=no')
receipt={'before':before,'incoming':incoming,'head':git('rev-parse','HEAD',text=True).strip(),'tree':tree,'source_Git_exact':{name:hashlib.sha256(git('show','HEAD:'+name)).hexdigest() for name in sources},'historical_schema_Git_exact':len(pins),'ledger_bytes_unchanged':True,'independent_root':'11samecriteria green, before8invalidred+3validgreen','independent_security':'e48b9ca574fb818bff377fabb4ed851d3406d3a52f6f05dcfbd6beb44581cbd3; same11 plus5own, wrapper/circuit/4HTTP both factories; no MFA grants attributed to this parent','scope':'Local merge only; full composed regression pending. No provider/network/charges or MFA31 integration.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
