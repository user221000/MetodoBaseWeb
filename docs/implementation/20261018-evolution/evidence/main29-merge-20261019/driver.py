"""Integrate the independently accepted CI29 branch while retaining ancestry."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-main29-merge-20261019');out.mkdir(exist_ok=False)
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=root,**kw)
before=git('rev-parse','HEAD',text=True).strip();incoming='fd636202045efa30b1430f4a9dd8ab287ec76357'
assert before=='5b7e7f78d2555c11157959a031b909700eb3ae02' and not git('status','--porcelain','--untracked-files=no')
registry=root/'docs/implementation/20261018-evolution/TRAZABILIDAD.json'
def criteria():return {row['id']:{name:row[name] for name in ['fuente','seccion','problema','criterio_exacto']} for row in json.loads(registry.read_bytes())['requisitos']}
old=criteria();assert len(old)==106
targets={path.relative_to(root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root/'web/database/alembic/schema_targets').glob('*.json'))}
role='web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py';old_role=git('show','HEAD:'+role)
preview=git('merge-tree','--write-tree','--messages','HEAD',incoming,text=True);expected_tree=preview.splitlines()[0];assert len(expected_tree)==40
merged=subprocess.run(['git','merge','--no-ff',incoming,'-m','Integrate independently reviewed member links and CI29 gates'],cwd=root,capture_output=True)
(out/'merge.stdout.log').write_bytes(merged.stdout);(out/'merge.stderr.log').write_bytes(merged.stderr)
if merged.returncode:
    print(json.dumps({'merge_exit':merged.returncode,'diagnostics':str(out)}));raise SystemExit(merged.returncode)
assert criteria()==old and git('show','HEAD:'+role)==old_role
assert git('rev-parse','HEAD^{tree}',text=True).strip()==expected_tree
assert git('show','-s','--format=%P','HEAD',text=True).strip().split()==[before,incoming]
for name,digest in targets.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
assert not git('status','--porcelain','--untracked-files=no')
sys.path.insert(0,str(root));from tests.isolation import prepare_environment
prepare_environment(discard_inherited=True)
from web.database.schema_control import expected_head
assert expected_head()=='20261019_client_account_links'
receipt={'before':before,'incoming':incoming,'head':git('rev-parse','HEAD',text=True).strip(),'tree':expected_tree,'schema_head':expected_head(),'criteria_exact':106,'old_schema_targets_byte_exact':len(targets),'c4_repair_unchanged':True,'ancestry_preserved_for_historical29':True,'no_push_deploy_or_providers':True,'scope':'Local integration only; broad regression on merged source remains pending.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))
