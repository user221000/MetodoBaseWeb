"""Complete checkpoint107 after fixing registry-relative evidence links only."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('F:/MetodoBaseWeb-execution-20261018')
RUN=ROOT/'docs/implementation/20261018-evolution'
EV=RUN/'evidence'
PYTHON='C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe'
BASE='b59c99f04c5bb164ec54a467c866bcca21a9e328'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args,**kwargs):
    return subprocess.check_output(['git',*args],cwd=ROOT,**kwargs)
assert git('rev-parse','HEAD',text=True).strip()==BASE
assert not git('diff','--cached','--name-only')
folders=['desktop31215-independent-20261019','qa-r12-core29-independent-20261019','security-r12-core29-independent-20261019','security-r12-core29-v2-independent-20261019']
expected={'desktop31215-independent-20261019/final-summary.json':'56dff578b1954a3e7c21582597b5082d7ddd6cd41820f7ea7cd4c5afbf76530c','qa-r12-core29-independent-20261019/final-summary.json':'5f9f299e0d6832df92473a16ebe4df8fbe18e3ed277eaedcac2f37901dd8ddb3','security-r12-core29-independent-20261019/source.json':'f02414062e52b8d0bb12475270b4a96a749bc6924bfb0deb0a9abeb70ee6a767','security-r12-core29-v2-independent-20261019/source.json':'5a4a12d5522ed68c845005c2c6b4dae8c63ddccc21090c7a437bacef11cbe543'}
for name,digest in expected.items():assert sha((EV/name).read_bytes())==digest
raw=[]
receipts={}
for name in folders:
    directory=EV/name
    manifest=directory/'final-manifest.json'
    if manifest.exists():
        data=json.loads(manifest.read_bytes())
        assert len(data['files'])==data['file_count']
        for item,detail in data['files'].items():
            content=(directory/item).read_bytes()
            assert len(content)==detail['bytes'] and sha(content)==detail['sha256']
    files=sorted(p for p in directory.rglob('*') if p.is_file())
    assert (directory/'.gitattributes').read_bytes()==b'* -text\n'
    receipts[name]={p.relative_to(directory).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files}
    raw.extend(files)
data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
prior=json.loads(git('show','HEAD:docs/implementation/20261018-evolution/TRAZABILIDAD.json'))
immutable={r['id']:{k:r[k] for k in ('fuente','seccion','problema','criterio_exacto')} for r in prior['requisitos']}
assert len(data['requisitos'])==104
corrected=0
prefix='docs/implementation/20261018-evolution/'
for row in data['requisitos']:
    assert {k:row[k] for k in immutable[row['id']]}==immutable[row['id']]
    for i,reference in enumerate(row['evidencia']):
        if reference.startswith(prefix):
            assert any(reference.startswith(prefix+'evidence/'+folder+'/') for folder in folders)
            row['evidencia'][i]=reference.removeprefix(prefix)
            corrected+=1
assert corrected==11,corrected
(RUN/'TRAZABILIDAD.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
subprocess.run([PYTHON,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
driver=EV/'checkpoint107-driver.py'
recovery=EV/'checkpoint107-recovery.py'
assert not driver.exists() and not recovery.exists()
shutil.copyfile('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint107-20261019.py',driver)
shutil.copyfile(__file__,recovery)
receipt=EV/'checkpoint107-review.json'
assert not receipt.exists()
receipt.write_text(json.dumps({'base_commit':BASE,'kind':'evidence_and_current_prose_only','criteria_preserved':104,'original_RAW_seals':expected,'proof_files_including_coordinator_scoped_attributes':receipts,'erratum':'Initial helper used repository-relative evidence links; registry requires execution-directory-relative links. It stopped before rendering/staging/commit. Corrected only11new links; proof bytes and exact criteria unchanged. Original helper retained.','product_changes':False,'R12_scope':'CoreV2 same21green only; API/restore/casts/integration excluded. V1red and QA95 partial preserved.','desktop_scope':'93checks bundle/ZIP/compiled payload/runtime only; Setup not executed.'},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
raw.extend([driver,recovery,receipt])
docs=[RUN/name for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
names=sorted({p.relative_to(ROOT).as_posix() for p in raw+docs})
for start in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=ROOT,check=True,capture_output=True)
for name in folders:
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',(EV/name).relative_to(ROOT).as_posix()],cwd=ROOT,check=True,capture_output=True)
assert not git('diff','--cached','--check','--',*[p.relative_to(ROOT).as_posix() for p in docs],stderr=subprocess.STDOUT)
raw_names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in raw_names).encode())
cursor=0
for name in raw_names:
    end=buffer.index(b'\n',cursor);parts=buffer[cursor:end].split();assert parts[1]==b'blob'
    size=int(parts[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name
    cursor+=size+1
assert cursor==len(buffer)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names)
subprocess.run(['git','commit','-m','Record desktop93 and independent R12 core V1/V2 reviews'],cwd=ROOT,check=True)
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_git_blobs_byte_identical':len(raw_names),'docs':len(docs),'registry':104,'product_changes':False}))
