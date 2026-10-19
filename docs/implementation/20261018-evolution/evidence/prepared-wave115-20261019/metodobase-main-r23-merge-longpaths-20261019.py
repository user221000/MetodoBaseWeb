"""Integrate reviewed follow-up/session/CI while retaining exact historical targets."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-main-r23-merge-longpaths-20261019');out.mkdir(exist_ok=False)
git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=root,**k)
before=git('rev-parse','HEAD',text=True).strip();incoming='57335e5b4bcba3c76c97d47e481b526fb52874a6'
assert before=='937950229e44543568db5a4d2e271689a44fc8b5' and not git('status','--porcelain','--untracked-files=no')
registry=root/'docs/implementation/20261018-evolution/TRAZABILIDAD.json'
def criteria():return {r['id']:{n:r[n] for n in ['fuente','seccion','problema','criterio_exacto']} for r in json.loads(registry.read_bytes())['requisitos']}
old=criteria();assert len(old)==108
targets={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'web/database/alembic/schema_targets').glob('*.json'))}
role='web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py';old_role=git('show','HEAD:'+role)
preview=git('merge-tree','--write-tree','--messages','HEAD',incoming,text=True);expected=preview.splitlines()[0];assert len(expected)==40;(out/'preview.txt').write_bytes(preview.encode())
result=subprocess.run(['git','-c','core.longpaths=true','merge','--no-ff',incoming,'-m','Integrate independently reviewed followup facts, session expiry and CI30'],cwd=root,capture_output=True)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode(errors='replace')
assert criteria()==old and git('show','HEAD:'+role)==old_role
assert git('rev-parse','HEAD^{tree}',text=True).strip()==expected and git('show','-s','--format=%P','HEAD',text=True).strip().split()==[before,incoming]
for name,digest in targets.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
assert not git('status','--porcelain','--untracked-files=no')
sys.path.insert(0,str(root));from tests.isolation import prepare_environment
prepare_environment(discard_inherited=True)
from web.database.schema_control import expected_head
assert expected_head()=='20261019_personal_history_index'
receipt={'before':before,'incoming':incoming,'head':git('rev-parse','HEAD',text=True).strip(),'tree':expected,'schema_head':expected_head(),'criteria_exact':108,'Git_longpaths_per_command_only':True,'schema_targets_byte_exact':len(targets),'c4_unchanged':True,'scope':'Local reviewed R23 partial and session/CI integration. No new DDL, Actions, image, provider or SLO. Current composed broad regression remains pending; avoid attributing prior MAIN30 gate to this source.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
