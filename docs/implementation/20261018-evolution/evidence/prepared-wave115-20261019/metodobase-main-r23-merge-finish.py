from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-main-r23-merge-finish-20261019');out.mkdir(exist_ok=False)
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
head=git('rev-parse','HEAD').decode().strip();assert head=='3643c3ee361abecba4d32ae98c1b87da99fb9d77'
before='937950229e44543568db5a4d2e271689a44fc8b5';incoming='57335e5b4bcba3c76c97d47e481b526fb52874a6'
assert git('config','--local','--get','core.longpaths').strip()==b'true'
assert not git('status','--porcelain','--untracked-files=no')
assert git('show','-s','--format=%P','HEAD').decode().strip().split()==[before,incoming]
preview=(out.parent/'metodobase-main-r23-merge-longpaths-20261019/preview.txt').read_text().splitlines()[0]
assert git('rev-parse','HEAD^{tree}').decode().strip()==preview
reg='docs/implementation/20261018-evolution/TRAZABILIDAD.json'
def criteria(blob):return {r['id']:{n:r[n] for n in ['fuente','seccion','problema','criterio_exacto']} for r in json.loads(blob)['requisitos']}
assert criteria(git('show',before+':'+reg))==criteria((root/reg).read_bytes())
targets={}
for path in sorted((root/'web/database/alembic/schema_targets').glob('*.json')):
    name=path.relative_to(root).as_posix();blob=git('show','HEAD:'+name)
    assert blob==git('show',before+':'+name)
    assert git('hash-object',name).strip()==git('rev-parse','HEAD:'+name).strip()
    targets[name]={'Git_blob_sha256':hashlib.sha256(blob).hexdigest(),'working_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
role='web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py'
assert git('show',before+':'+role)==git('show','HEAD:'+role)
sys.path.insert(0,str(root));from tests.isolation import prepare_environment
prepare_environment(discard_inherited=True)
from web.database.schema_control import expected_head
assert expected_head()=='20261019_personal_history_index'
receipt={'head':head,'before':before,'incoming':incoming,'tree':preview,'schema_head':expected_head(),'criteria_exact':len(criteria((root/reg).read_bytes())),'schema_targets_byte_exact_Git':targets,'c4_unchanged_Git':True,'tracked_status_clean':True,'local_core_longpaths':'true; owned execution clone only, previously no local value observed; normal status now clean','preserved_attempts':['metodobase-main-r23-merge-20261019','metodobase-main-r23-merge-longpaths-20261019','metodobase-main-r23-merge-complete-20261019'],'harness_correction':'Previous completion stopped comparing CRLF working schema source with LF Git blob. This completion compares prior/current Git blobs byte exactly and verifies filtered working hash equals current Git object; immutable evidence was not normalized. Successful merge preceded both completion attempts. No merge repeated.','scope':'Current composed broad regression pending; no Actions/Linux/image/provider/SLO claim.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k!='schema_targets_byte_exact_Git'}))
