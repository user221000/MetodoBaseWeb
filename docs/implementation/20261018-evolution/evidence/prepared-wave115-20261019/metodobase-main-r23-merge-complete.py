from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-main-r23-merge-complete-20261019');out.mkdir(exist_ok=False)
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
head=git('rev-parse','HEAD').decode().strip()
assert head=='3643c3ee361abecba4d32ae98c1b87da99fb9d77'
previous=subprocess.run(['git','config','--local','--get','core.longpaths'],cwd=root,capture_output=True)
normal=git('status','--porcelain','--untracked-files=no')
assert not git('-c','core.longpaths=true','status','--porcelain','--untracked-files=no')
subprocess.run(['git','config','--local','core.longpaths','true'],cwd=root,check=True)
assert not git('status','--porcelain','--untracked-files=no')
before='937950229e44543568db5a4d2e271689a44fc8b5';incoming='57335e5b4bcba3c76c97d47e481b526fb52874a6'
assert git('show','-s','--format=%P','HEAD').decode().strip().split()==[before,incoming]
preview=(out.parent/'metodobase-main-r23-merge-longpaths-20261019/preview.txt').read_text().splitlines()[0]
assert git('rev-parse','HEAD^{tree}').decode().strip()==preview
reg='docs/implementation/20261018-evolution/TRAZABILIDAD.json'
def criteria(blob):return {r['id']:{n:r[n] for n in ['fuente','seccion','problema','criterio_exacto']} for r in json.loads(blob)['requisitos']}
assert criteria(git('show',before+':'+reg))==criteria((root/reg).read_bytes())
targets={}
for path in sorted((root/'web/database/alembic/schema_targets').glob('*.json')):
    name=path.relative_to(root).as_posix();assert path.read_bytes()==git('show',before+':'+name)
    targets[name]=hashlib.sha256(path.read_bytes()).hexdigest()
role='web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py'
assert git('show',before+':'+role)==(root/role).read_bytes()
sys.path.insert(0,str(root));from tests.isolation import prepare_environment
prepare_environment(discard_inherited=True)
from web.database.schema_control import expected_head
assert expected_head()=='20261019_personal_history_index'
receipt={'head':head,'before':before,'incoming':incoming,'tree':preview,'schema_head':expected_head(),'criteria_exact':len(criteria((root/reg).read_bytes())),'schema_targets_byte_exact':targets,'c4_unchanged':True,'tracked_status_clean':True,'local_core_longpaths':{'prior_exit':previous.returncode,'prior_stdout':previous.stdout.decode(),'new':'true','prior_false_status':normal.decode(),'scope':'Only owned execution clone local configuration; original workspace unchanged'},'preserved_attempts':['metodobase-main-r23-merge-20261019','metodobase-main-r23-merge-longpaths-20261019'],'scope':'Successful merge already existed before this completion. No second merge. Prior wrapper stopped at Windows long-path stat false positive. Broad composed regression still pending; no Actions/Linux/image/provider claim.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k not in ['schema_targets_byte_exact','local_core_longpaths']}))
