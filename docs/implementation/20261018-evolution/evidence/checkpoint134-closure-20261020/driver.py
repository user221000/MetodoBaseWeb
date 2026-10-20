"""Preserve bounded peer evidence while newer34/35 products remain isolated."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
C=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint134-20261020')
BASE='e006516fe99ec0da65c4a0f563b8c5736e541b50'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*a):return subprocess.run(['git',*a],cwd=R,capture_output=True,check=True)
def immutable(data):return {r['id']:{k:r[k] for k in ('fuente','seccion','problema','criterio_exacto')} for r in data['requisitos']}
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
assert not C.exists();C.mkdir()
data=json.loads((D/'TRAZABILIDAD.json').read_bytes());prior=immutable(data);assert len(prior)==128
untracked=git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')[:-1]
preserved={p:sha((R/p).read_bytes()) for p in untracked if (R/p).is_file()}
(C/'untracked-before.json').write_bytes(enc(preserved))
imports=[];paths=[]
for ref,prefix,count in [
 ('4187a23a33844c6a5b225b34dbce25b0ece4874b','security-followup34-qa18-author-20261019',38),
 ('c6289c7044ec647335e4fd691308fb6ee75df6d2','qa-followup34-sqlfix-peer-independent-20261020',33),
 ('fad3d024dfcbf362e9bc564730bb387e9287cd5c','security-nutrition35-pure-independent-20261019',28),
 ('3a1ba45107301d8769339c6264154d0268fdd9f3','root-nutrition35-profile-author-20261020',6),
]:
    folder='docs/implementation/20261018-evolution/evidence/'+prefix
    names=git('ls-tree','-r','--name-only','-z',ref,'--',folder).stdout.decode().split('\0')[:-1]
    assert len(names)==count
    for name in names:
        target=R/name;raw=git('show',ref+':'+name).stdout
        assert not target.exists()
        target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(raw);paths.append(name)
    imports.append({'source_commit':ref,'prefix':prefix,'files':count,'product_imported':False,'RAW_equal_source_Git':True})
qa=('QA-18: fuente41dc5 aceptada focalmente porQA independiente con la misma canaria original c3a4:12/12PASS, '
    'desde4FAIL/8PASS anteriores, sin modificar asserts. Dieciséis controles propios directos PASS (seisSQLite reales y diezmetadatos sintéticos), '
    'sinPostgreSQL. No cubre la proyecciónUsuario posterior ni aceptación global34; el producto34 aún no está enMAIN.')
nutrition=('Candidato35 fuente55a3 tiene162casosSQLitePASS con perfiles/DTO/persistencia/cuota/PDFreal yguard final; '
    'ambasfactories gimnasio ypersonal sóloSaaS. Contratos anteriores intactos; downgrade no borra declaraciones. '
    'Cambio de restricciones durantePDF deja ceroPlan/READY,reserva liberada yobjetoPENDING explícito para reconciliación. '
    'Un fallo de framing personal404 yla foto parcial inicial137 se preservan; final162 enumera fuentes nuevas. '
    'SECfad3 acepta sólo dominio/constructoresd5:79replay y24propiosPASS,no integración35. '
    'UI ydesktop avanzan enWTpropias;PG35/peerintegrado pendientes,no aprobación clínica ni MAIN/despliegue.')
for row in data['requisitos']:
    if row['id']=='QA-18':
        row['estado']=row['implementacion']=row['validacion']='en_revision'
        row['observaciones'].append('Checkpoint134: '+qa)
        row['commits'].extend(['41dc5ae6e9c02d9b846685428df1fc722aa4cca7','4187a23a33844c6a5b225b34dbce25b0ece4874b','c6289c7044ec647335e4fd691308fb6ee75df6d2'])
        row['evidencia'].extend(['evidence/security-followup34-qa18-author-20261019/source.json','evidence/qa-followup34-sqlfix-peer-independent-20261020/phase-summary.json'])
        row['revisor']='QA independiente acepta clasificación de41dc5; integración34 yproyección posterior pendientes'
    if row['id'] in {'R05','R19','R23'}:row['observaciones'].append('Checkpoint134: '+qa)
    if row['id'] in {'R06','R33','B09','B23','UX-02'}:
        row['observaciones'].append('Checkpoint134: '+nutrition)
        row['commits'].extend(['55a3f4f9b1c1d03937bae78a5cee4f1d1b6379af','3a1ba45107301d8769339c6264154d0268fdd9f3','fad3d024dfcbf362e9bc564730bb387e9287cd5c'])
        row['evidencia'].extend(['evidence/root-nutrition35-profile-author-20261020/review.md','evidence/security-nutrition35-pure-independent-20261019/source.json'])
assert immutable(data)==prior
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
state=(D/'ESTADO.md').read_text(encoding='utf-8').replace('Checkpoint133 local:','Checkpoint134 local:',1)
state=state.replace('la reparación41dc5 tiene replay de autor12PASS yespera revisión independiente.','la reparación41dc5 tiene peerQA12originales+16propiosPASS,sóloSQLite. Proyección posterior e integración34 siguen pendientes.',1)
state+='\nCandidato35 aislado55a3:162SQLitePASS para perfil/cuota/publicación. Revisión\nSEC del dominio/constructoresd5:79+24PASS; no cubre todaAPI35. UI35 ydesktop\ncontinúan;PG35 ypeerintegrado pendientes. Se conserva un objetoPENDING\ncuando cambia el perfil trasPDF; no se afirma ceroefectosdurables.\n[Autor35](evidence/root-nutrition35-profile-author-20261020/review.md),\n[peer puro](evidence/security-nutrition35-pure-independent-20261019/source.json),\n[QA-18 peer](evidence/qa-followup34-sqlfix-peer-independent-20261020/phase-summary.json).\n'
(D/'ESTADO.md').write_bytes(state.encode())
(D/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint134 conserva128requisitos ytodos los criterios. MAIN continúa en33
conCI33/R05v2. QA-18 tienepeerSQLite12+16PASS en41dc5,pendiente integración34
yproyección posterior. Nutrición35 tiene162SQLite deautor ypeer separado del
núcleo puro; UI,desktop,PG35 ypeerintegrado siguen encurso. R05globalRED1603,
R27/R31,pruebas actuales de navegador,broad,imagen ydesktop final abiertos.
Free10clientes/1plancliente/día/10totalgym/día;desktop soportado.
Sin publicación odespliegue. [Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
append={'VALIDACION.md':qa+' '+nutrition,'CAMBIOS.md':'Sólo evidencia/control,sin incorporar aún productos34/35. '+nutrition,'NUEVOS_HALLAZGOS.md':qa}
for name,paragraph in append.items():
    p=D/name;raw=p.read_bytes();assert b'## Checkpoint134' not in raw
    p.write_bytes(raw.rstrip()+b'\n\n## Checkpoint134\n\n'+paragraph.encode()+b'\n')
proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(C/'registry.stdout').write_bytes(proc.stdout);(C/'registry.stderr').write_bytes(proc.stderr)
assert all(sha((R/p).read_bytes())==h for p,h in preserved.items())
proof=D/'evidence/checkpoint134-closure-20261020';proof.mkdir();(proof/'.gitattributes').write_bytes(b'* -text\n')
receipt={'base':BASE,'registry':128,'previous_criteria_exact':128,'imports':imports,'preexisting_untracked_preserved':len(preserved),'product_changes':[],'global34_35_acceptance':False}
(proof/'receipt.json').write_bytes(enc(receipt));(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',*paths,proof.relative_to(R).as_posix())
controls=[(D/name).relative_to(R).as_posix() for name in ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md',*append]]
git('-c','core.autocrlf=true','add','--renormalize','--',*controls)
checked=subprocess.run(['git','diff','--cached','--check'],cwd=R,capture_output=True,check=False)
(C/'whitespace.stdout').write_bytes(checked.stdout);(C/'whitespace.stderr').write_bytes(checked.stderr)
assert checked.returncode==0
git('commit','-m','Preserve independent SQL conflict review and isolated nutrition35 evidence')
assert not git('status','--porcelain','-uno').stdout.strip()
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
