"""Complete the staged checkpoint after correcting prose EOF whitespace only."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root=Path('F:/MetodoBaseWeb-execution-20261018')
run=root/'docs/implementation/20261018-evolution'
ev=run/'evidence'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
data=json.loads((run/'TRAZABILIDAD.json').read_text(encoding='utf-8'))
prior=json.loads(subprocess.check_output(['git','show','HEAD:docs/implementation/20261018-evolution/TRAZABILIDAD.json'],cwd=root))
original={r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in prior['requisitos']}
for row in data['requisitos']:
    assert {k:row[k] for k in original[row['id']]}==original[row['id']]
    if row['id']=='R12':row['observaciones'].append('Seguridad independiente canónica ad712:21propios,18verdes y3rojos reales (OWNER fuente conteam_gym_idnoNULL;parentOWNER receptor conteam_gym_idnoNULL;proofGUCNULLantesCOMMITpermiteOWNERown). Núcleo rechazado,fixV2enautoría;sinincidenteHTTP/producciónatribuido. QA55replayy22propiosverdes no cierranesos3defectos.')
(run/'TRAZABILIDAD.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ['ESTADO.md','VALIDACION.md','RIESGOS.md']:
    p=run/name
    content=p.read_text(encoding='utf-8').rstrip()
    content+='\n\nR12 canónico ad712 sigue aislado y fue rechazado por tres negativos PG independientes: permisos de lectura tras cambiar pertenencia de un OWNER fuente o de un OWNER padre, y comprobación diferida con prueba GUC nula antes del commit. Seguridad conserva 18 positivos y esos tres rojos; backend prepara V2. Los 55 casos reutilizados y 22 propios de QA verdes no cierran estos defectos. Sin fuga HTTP ni incidente productivo atribuidos.\n'
    p.write_text(content,encoding='utf-8')
subprocess.run(['C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True)
driver=ev/'checkpoint106-commit-recovery.py';assert not driver.exists();shutil.copyfile(__file__,driver)
receipt=ev/'checkpoint106-commit-recovery.json';assert not receipt.exists()
receipt.write_text(json.dumps({'prep_erratum':'First checkpoint106 helper reached a prose-only extra blank line at VALIDACION.md EOF and stopped before committing. The failed helper remains RAW as checkpoint106-driver.py. Corrected only new prose EOF and appended current three R12 security negatives; original proof bytes/manifests unchanged.','registry':104,'source_problem_exact_criteria_preserved':104,'no_product_changes':True},indent=2)+'\n',encoding='utf-8')
subprocess.run(['git','-c','core.autocrlf=false','add','--',driver.relative_to(root).as_posix(),receipt.relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
folders=['history-pg200-independent-20261019','sec08-linux-independent-20261019','desktop31215-build66-20261019','history-index-probes-root-20261019']
raw=[ev/'checkpoint106-root-review.json',ev/'checkpoint106-driver.py',ev/'checkpoint106-raw-preservation.json',driver,receipt]
for name in folders:raw.extend(p for p in (ev/name).rglob('*') if p.is_file())
names=sorted(p.relative_to(root).as_posix() for p in raw)
buffer=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(':'+n+'\n' for n in names).encode())
position=0
for name in names:
    end=buffer.index(b'\n',position);header=buffer[position:end].split();assert header[1]==b'blob'
    size=int(header[2]);blob=buffer[end+1:end+1+size];position=end+size+2
    assert blob==(root/name).read_bytes(),name
assert position==len(buffer)
docs=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','VALIDACION.md','CAMBIOS.md','CARGA_LOCAL.md','RIESGOS.md','ENTREGA.md']
docpaths=[(run/name).relative_to(root).as_posix() for name in docs]
subprocess.run(['git','diff','--check','--',*docpaths],cwd=root,check=True)
subprocess.run(['git','add','--',*docpaths],cwd=root,check=True,capture_output=True)
staged=set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1])
assert staged==set(names+docpaths)
subprocess.run(['git','commit','-m','docs: checkpoint106 records PG200, security review and rebuilt desktop'],cwd=root,check=True,capture_output=True)
print(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'new_raw_files':len(names),'all_raw_index_identical':True,'registry':104,'R12_core29_accepted':False}))
