"""Register QA-18 RED and recovered CI33 PG evidence without product34 imports."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
C=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint132-20261020')
BASE='d8d828e22634e168f1500b8a38805883d768063f'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*args):return subprocess.run(['git',*args],cwd=R,capture_output=True,check=True)
def immutable(data):return {r['id']:{k:r[k] for k in ('fuente','seccion','problema','criterio_exacto')} for r in data['requisitos']}
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
assert not C.exists();C.mkdir()
untracked=git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')[:-1]
preserved={p:sha((R/p).read_bytes()) for p in untracked if (R/p).is_file()}
(C/'untracked-before.json').write_bytes(enc(preserved))
data=json.loads((D/'TRAZABILIDAD.json').read_bytes());prior=immutable(data)
assert len(prior)==127 and 'QA-18' not in prior
imports=[];imported=[]
for ref,prefix,count in [
    ('e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee','security-followup34-independent-20261019',38),
    ('b3d0aaab563fa42ca77e05d65f6c139cb7c3f1d1','qa-ci33-PG240-recovery-independent-20261019',63),
    ('b3d0aaab563fa42ca77e05d65f6c139cb7c3f1d1','qa-ci33-c86-source-binding-independent-20261019',6),
]:
    folder='docs/implementation/20261018-evolution/evidence/'+prefix
    paths=git('ls-tree','-r','--name-only','-z',ref,'--',folder).stdout.decode().split('\0')[:-1]
    assert len(paths)==count
    for p in paths:
        raw=git('show',ref+':'+p).stdout;target=R/p
        if target.exists():assert target.read_bytes()==raw
        else:target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(raw)
        imported.append(p)
    imports.append({'source_commit':ref,'prefix':prefix,'files':count,'RAW_equal_source_Git':True,'product_imported':False})
row={
 'id':'QA-18','identificador_original':'QA-18',
 'fuente':'docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019/source.json',
 'seccion':'Hallazgo nuevo checkpoint132',
 'problema':'El candidato Backend34 devuelve409 followup_busy ante IntegrityError desconocido durante flush y ante SQLITE_ERROR=1 de tabla inexistente cuyo nombre contiene blocked. Falla la clasificación de disponibilidad; no se confirma bypass de autorización, explotación remota ni fuga de datos.',
 'criterio_exacto':'En ambas factories, los mismos canarios HTTP autenticados deben devolver503 followup_unconfirmed para errores de integridad desconocidos y SQLITE_ERROR real de tabla inexistente, con independencia de palabras como blocked en su nombre. Sólo conflictos de constraint, trigger o bloqueo conocidos, identificados mediante códigos y diagnósticos cerrados del driver, pueden producir409; un rollback incierto conserva503. Mantener cabeceras privadas, opacidad, ausencia de ACK y Task/Event parciales, sin retry, readback o adopción automática; una petición explícita posterior al fallo puede aplicar una sola operación. Preservar los controles de bloqueo SQLite real409 y tabla faltante sin ese fragmento503 y repetir las doce canarias originales sin rebajar aserciones.',
 'prioridad':'P2','responsable':'Backend, seguridad y QA',
 'tareas':['R05','R19','R23'],'dependencias':['R02','R03','R23'],
 'estado':'en_curso','implementacion':'en_curso','validacion':'en_curso','despliegue':'no_desplegado','entorno':'local',
 'cambios':['Reproducción independiente sobre80b9 preservada; reparación tipada aislada en curso. No se integra producto34 enMAIN.'],
 'commits':['80b9a44adf4daae160673b4d86a58cb06f809071','e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee'],
 'pruebas':['Canaria propia SHA c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce:12casos,8PASS4RED,0errores/skips. Replay75SQLite del autor PASS, no PostgreSQL34 ejecutado en ese sello.'],
 'evidencia':['evidence/security-followup34-independent-20261019/review.md','evidence/security-followup34-independent-20261019/source.json'],
 'documentacion':['ESTADO.md','VALIDACION.md','NUEVOS_HALLAZGOS.md'],
 'revisor':'Seguridad independiente del autor34; corrección posterior requiere nuevo replay y revisión independiente',
 'bloqueo':None,'observaciones':['Dos hipótesisPG del mismo sello (hint antes de authority y Cliente FOR SHARE sinNOWAIT) siguen sin confirmar; no se presentan como hallazgos demostrados ni se mezclan conQA-18.']}
data['requisitos'].append(row)
pg=('QA recuperó sin rerun los20reportes/240IDs únicos PG33 sobrec86:240PASS0FAIL/error/skip. '
    '52UUID propias ausentes y0sesiones confirmados en conexión nueva tras la pausa; DROP ordinario ysin terminate. '
    '1114fuentes/92distribuciones/8084archivos instalados ybinarios exactos. Los testigos distinguen engine de negocio de15sondeos auxiliares poscaso; no se atribuye su engine al negocio. '
    'Fuentesc86/R05v1; composiciónMAINv2, broad,Chrome,imagen,Linux yActions no demostrados por esta fase.')
for r in data['requisitos']:
    if r['id'] in {'R05','R08','R19','QA-08','QA-10','OPS04','OPS07','QA-17'}:
        r['observaciones'].append('Checkpoint132: '+pg)
        for p in ['evidence/qa-ci33-PG240-recovery-independent-20261019/phase-summary.json','evidence/qa-ci33-c86-source-binding-independent-20261019/full-source-delta82.json']:
            if p not in r['evidencia']:r['evidencia'].append(p)
    if r['id']=='R23':r['observaciones'].append('Checkpoint132: QA-18 confirmado en candidato34,12canarias8PASS4RED; corrección aislada en curso. PG55483 transferido deQA aBackend para target34/22PG/restore34; aún sin aceptación de esos checks.')
assert {k:v for k,v in immutable(data).items() if k!='QA-18'}==prior
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
state=(D/'ESTADO.md').read_text(encoding='utf-8').replace('Checkpoint131 local: esquema33 y127 requisitos (92 originales+35 añadidos).','Checkpoint132 local: esquema33 y128 requisitos (92 originales+36 añadidos).',1)
state=state.replace('Se conservan íntegros los126 criterios previos.','Se conservan íntegros los127 criterios previos.',1)
state+='\nQA recuperó PG33 c86:20reportes/240casos PASS, sin nuevos casos ni rerun.\n52UUID ausentes y0sesiones comprobados tras pausa. Mantienev1 ylas limitaciones\ndel engine auxiliar; integraciónCI ypinv2 en curso. Backend tomaPG55483 para34.\nQA-18 queda abierto:12canarias8PASS4RED sobre80b9; fuente34 sigue aislada.\n[PG recuperado](evidence/qa-ci33-PG240-recovery-independent-20261019/phase-summary.json),\n[QA-18](evidence/security-followup34-independent-20261019/review.md).\n'
(D/'ESTADO.md').write_bytes(state.encode())
(D/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint132:128requisitos y127criterios previos exactos. QA recuperó los240
casos PostgreSQL33 originales c86:todos PASS,sin rerun;52UUID propias ausentes
y0sesiones. CI actual prepara composición conR05v2; broad/browser/imagen siguen
pendientes. MAIN sigue en esquema33. Backend34 tieneQA-18 abierto (8PASS4RED),
PG34,restore34 yUI34 pendientes de revisión integrada. R05sigueRED1.603hallazgos.
R27/R31/R33,imagen ydesktop final continúan. Free10clientes/1plancliente/día/
10totalgym/día ydesktop soportado. Sin publicación odespliegue.
[Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
append={
 'VALIDACION.md':pg+' QA-18: '+row['pruebas'][0],
 'CAMBIOS.md':'Se incorpora sólo evidencia yregistro; ningún producto34 oCIc86 cambiaMAIN en este checkpoint.',
 'RIESGOS.md':row['problema']+' La reproducción deQA-18 permanece abierta hasta corrección yreplay independiente. '+pg,
 'NUEVOS_HALLAZGOS.md':'QA-18 (P2): '+row['problema']+' Criterio: '+row['criterio_exacto'],
}
for name,paragraph in append.items():
    p=D/name;raw=p.read_bytes();assert b'## Checkpoint132' not in raw
    p.write_bytes(raw.rstrip()+b'\n\n## Checkpoint132\n\n'+paragraph.encode()+b'\n')
proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(C/'registry.stdout').write_bytes(proc.stdout);(C/'registry.stderr').write_bytes(proc.stderr)
assert all(sha((R/p).read_bytes())==h for p,h in preserved.items())
proof=D/'evidence/checkpoint132-closure-20261020';proof.mkdir();(proof/'.gitattributes').write_bytes(b'* -text\n')
receipt={'base':BASE,'registry':128,'new_ID':'QA-18','previous_criteria_exact':127,'imports':imports,'preexisting_untracked_files_preserved':len(preserved),'product_changes':[],'SQL34_tests_executed':False,'new_PG33_cases':0,'PG33_cases_recovered':240,'global_acceptance':False}
(proof/'receipt.json').write_bytes(enc(receipt));(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',*imported,proof.relative_to(R).as_posix())
paths=[(D/p).relative_to(R).as_posix() for p in ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md',*append]]
git('-c','core.autocrlf=true','add','--renormalize','--',*paths)
git('diff','--cached','--check')
assert set(git('diff','--cached','--name-only').stdout.decode().splitlines())==set(imported)|set(paths)|{p.relative_to(R).as_posix() for p in proof.iterdir()}
git('commit','-m','Register SQL classification regression and recover exact CI33 PG240 evidence')
assert not git('status','--porcelain','-uno').stdout.strip()
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
