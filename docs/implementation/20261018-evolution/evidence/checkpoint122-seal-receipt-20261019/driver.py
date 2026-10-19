from pathlib import Path
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

root=Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
run=root/'docs/implementation/20261018-evolution';ev=run/'evidence'
base='150d0f4cd4ceb030d506e906fb65ec681c9a9868'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
manifests=[
 ('qa-mfa-ci31-pg-independent-20261019','cc75427b2a98a51bbe025876e28b0a1f788c5323a07e7f97c57f996d19f5db60'),
 ('security-r17-observability-independent-20261019','0dbaa418da0da7887ea74c131673b3173b59f8807694d4efb2c2490dca01bfc8'),
 ('security-r17-observability-after-independent-20261019','ff3a8f45473bf340ee8c98764965180e1216094643c53278736d527acd8eb4c5'),
 ('root-r17-observability-author-20261019','7f495abbf422ac085eb1c33e17f8da5c50fa81fa7b534a564ad66d9c24ecf851'),
]
raw=set()
for prefix,digest in manifests:
    parent=ev/prefix;manifest=parent/'manifest.json'
    assert sha(manifest.read_bytes())==digest
    document=json.loads(manifest.read_bytes());rows=document.get('files',document)
    if isinstance(rows,dict):rows=[{'path':name,**meta} for name,meta in rows.items()]
    for row in rows:
        assert ('sha256' in row)!=('SHA256' in row)
        path=parent/row.get('path',row.get('file',''))
        assert path.resolve().is_relative_to(parent.resolve())
        blob=path.read_bytes();assert sha(blob)==row.get('sha256',row.get('SHA256'))
        assert 'bytes' not in row or len(blob)==row['bytes']
        scan(blob,path.name);raw.add(path)
    assert (parent/'.gitattributes').read_text(encoding='ascii').strip()=='* -text'
    raw.update([manifest,parent/'.gitattributes'])
for prefix,digest,manifest_digest in [
 ('security-r17-observability-independent-20261019','2a9cd560b578d6aa4eb5ea05132df1e2de4334641442eaf08cd719239a76d6de',manifests[1][1]),
 ('security-r17-observability-after-independent-20261019','f4b945de61111622435131862200d883bf2b1493694e9f920be925c96155120c',manifests[2][1])]:
    path=ev/prefix/'source.json';blob=path.read_bytes()
    assert sha(blob)==digest and json.loads(blob)['manifest_sha256']==manifest_digest
    scan(blob,path.name);raw.add(path)
pg=ev/'qa-mfa-ci31-pg-independent-20261019/phase-summary.json'
assert sha(pg.read_bytes())=='7df513388be356e53cb4f409e373acdc4ab9d2e5914fc2ba71a9b50baecf5834'

prepared=ev/'prepared-wave122-20261019';assert not prepared.exists()
contents={'driver.py':Path(__file__).read_bytes()}
for prefix in ['metodobase-mfa31-compose-ci-ed4-20261019','metodobase-mfa31-compose-r17-20261019']:
    for path in (tmp/prefix).iterdir():
        assert path.is_file();contents[prefix+'/'+path.name]=path.read_bytes()
for name,blob in contents.items():scan(blob,name)
prepared.mkdir();(prepared/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in contents.items():
    path=prepared/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob);raw.add(path)
(prepared/'manifest.json').write_bytes((json.dumps({n:{'bytes':len(b),'sha256':sha(b)} for n,b in contents.items()},indent=2)+'\n').encode())
raw.update([prepared/'manifest.json',prepared/'.gitattributes'])

path=run/'TRAZABILIDAD.json';data=json.loads(path.read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda d:{r['id']:{n:r[n] for n in fields} for r in d['requisitos']}
before=criteria(data);assert len(before)==118 and 'SEC14' not in before
row={'id':'SEC14','identificador_original':'SEC14',
 'fuente':'docs/implementation/20261018-evolution/evidence/security-r17-observability-independent-20261019/source.json',
 'seccion':'Hallazgo nuevo checkpoint122',
 'problema':'Las tres rutas operativas canónicas omiten cabeceras privadas en respuestas405 y errores de lector500; los cuerpos observados permanecen opacos.',
 'criterio_exacto':'Aplicar Cache-Control no-store, Pragma no-cache y Referrer-Policy no-referrer a todos los estados y métodos de /metrics, /alerts y /health/circuits; conservar errores opacos y el comportamiento de rutas vecinas, repetir el mismo before y revisar de forma independiente sin atribuir una fuga no demostrada.',
 'prioridad':'P1','responsable':'Backend y seguridad','tareas':['R17','R19','R31'],
 'dependencias':['R17'],'estado':'en_revision','implementacion':'en_revision','validacion':'en_curso',
 'despliegue':'no_desplegado','entorno':'local','cambios':['b500 amplía únicamente la frontera privada existente a las tres rutas canónicas. Integrado en candidata aislada5637; pendiente regresión común.'],
 'commits':['b50058280b9e4989799732b81a8a10292ebaba92','5637b4daed86fa6ce3024c521aafdb6742373b08'],
 'pruebas':['Mismo driver24:before12verdes/12rojos,después24verdes; mismos2bounds verdes. Autor84focales y replay24, sin sumar solapamientos.'],
 'evidencia':['evidence/security-r17-observability-independent-20261019/source.json','evidence/security-r17-observability-after-independent-20261019/source.json','evidence/root-r17-observability-author-20261019/limitations.json'],
 'documentacion':['ESTADO.md','VALIDACION.md','DECISIONES.md'],'revisor':'Seguridad independiente: aceptación acotada b500','bloqueo':None,
 'observaciones':['Sin fuga demostrada, sin aceptación global u operativa de R17/R31. MAIN mantiene esquema30.']}
data['requisitos'].append(row)
notes={
 'R05':'CIed4:173PostgreSQL aprobados porQAen12comandos ycheckerreal;42UUIDpropias cerradas sinFORCE/kill yausenciafreshconn.33tablas/32modelos/25FORCE/history30;10143fuentes89paquetes/binarios/config/helpersquietos,pips0. CIed4 compuesto38bcon11paths exactos y624productos intactos; noActions niimagen.',
 'R17':'b500 cuenta respuestas/errores500 por ruta declarada y protege operaciones enambasfactories. SEC14before24=12rojos+12controles; mismo24+2afterverde con10145fuentes89paquetes/Pythonquietos. Autor103dirigidas/52freezeinicial/84fix y24replay son fases solapadas. Mergeaislado5637 conserva7blobs exactos yotros10138; falta regresión común/operación distribuida/SLO.',
 'R19':'173PGverdes yR17aceptadoacotado; candidatoaislado5637integraCIed4/R17b500 sin cambios extra. Peer79fixtures Google/publicación en curso; no repetir ni reatribuir PGprevio. Broadfullcomún posterior aún pendiente.',
 'R31':'SEC14 corrige cabeceras405/500 para tres rutas operativas exactas con misma prueba independiente; cuerposopacos antes/después. No define conservación/países ni cierreR31.',
 'R32':'CIed4PG173aprobado ycerrado. IntegraciónaisladaCI38b+R175637; fixture79bajopeer yregresióncomúnpendiente; no despliegue/configreal/avisos/custodia/recuperacióntotal acreditados.',
 'QA-13':'ContratoCIed4 y173PG aprobados independientemente; fuenteCIexacta compuesta38b. NoActions niimagen.',
 'QA-14':'snapshot25 parserreal aceptado y173PG actual verde; siete casos snapshot nuevos se mantienen separados de18replays. No cambio dehistórico.',
 'QA-15':'Rolrestringido obligatorioSQLreal y173PG conrolappfalse/false/false/false nonowner aceptados; sin bypass/rolglobal/kill.',
}
refs={k:['evidence/qa-mfa-ci31-pg-independent-20261019/phase-summary.json'] for k in ['R05','R19','R32','QA-13','QA-14','QA-15']}
refs['R17']=row['evidencia'];refs['R31']=row['evidencia'][:2]
for item in data['requisitos']:
    ident=item['id']
    if ident in notes:item['observaciones'].append('Checkpoint122: '+notes[ident])
    for ref in refs.get(ident,[]):
        if ref not in item['evidencia']:item['evidencia'].append(ref)
assert len(criteria(data))==119 and {k:criteria(data)[k] for k in before}==before
path.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())

paragraphs=(run/'ESTADO.md').read_text(encoding='utf8').split('\n\n')
def replace(prefix,text):
    positions=[i for i,p in enumerate(paragraphs) if p.startswith(prefix)];assert len(positions)==1,prefix
    paragraphs[positions[0]]=text
replace('Checkpoint 121 local.', 'Checkpoint 122 local. El registro conserva 119 requisitos: 92 originales y 27 hallazgos añadidos. Los 118 criterios anteriores permanecen exactos; SEC14 registra las cabeceras privadas ausentes en errores operativos. MAIN sigue en esquema30 y el workspace original permanece intacto. Free: diez clientes activos, un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales.')
replace('La candidata MFA 31 permanece aislada', 'La candidata MFA31 permanece aislada en5637b4daed86fa6ce3024c521aafdb6742373b08. Integra CIed4 y R17b500, con sus blobs revisados exactos. El diagnóstico amplio anterior bd348 se conserva:2381casos=2360aprobados+2fallosGoogle+18errores de preparación+1skipWindows; maxfail20, no aceptación completa. Backend79 adaptó la configuración Google y la fixture local29→31 con58aserciones exactas,54originales y2controles verdes; QA está revisándolo antes de integrarlo. Después corresponde la regresión común completa. [Diagnóstico](evidence/prepared-wave121-20261019/broad31-diagnostic/summary.SANITIZED.json).')
replace('CI e0 queda preservado', 'CIe0 permanece rechazado y preservado. El contrato corregido ed4 ya tiene aceptación independiente y173casos PostgreSQL verdes en12comandos más checker real. QA cerró42UUIDpropias con cero sesiones y ausencia desde conexión nueva, sinFORCE ni terminar backends. Se mantuvieron10143archivos,89paquetes,Python,binariosPG,config yhelpers; pipcheck verde. El merge38b conservó once archivosCI exactos y624productos previos. No acredita Actions,imagen,Redis niChrome. [Contrato](evidence/qa-mfa-ci31-fix-independent-20261019/phase-summary.json), [PostgreSQL173](evidence/qa-mfa-ci31-pg-independent-20261019/phase-summary.json).')
replace('R17 tiene una candidata aparte', 'R17b500 está aceptado de forma acotada e integrado sólo en la candidata aislada5637. Seguridad conservó24casos antes:12verdes y12rojos por cabeceras405/500 ausentes. El mismo driver pasó24después, además de los mismos dos controles de límites; los cuerpos permanecieron opacos, sin fuga demostrada. La corrección modifica únicamente el reconocimiento de las tres rutas canónicas en la frontera privada existente. Autor84focales y replay24 son fases solapadas; los10145archivos y89paquetes permanecieron estables. Falta regresión común y validación operativa; no acredita agregación distribuida, streaming completo niSLO. [Antes](evidence/security-r17-observability-independent-20261019/source.json), [después](evidence/security-r17-observability-after-independent-20261019/source.json), [evidencia de autor y límites](evidence/root-r17-observability-author-20261019/limitations.json).')
replace('Siguiente acción:', 'Siguiente acción: terminar el peer de fixtures79, integrarlo si procede y ejecutar regresión completa de la candidata compuesta. Seguridad revisa la corrección aislada de trazabilidad y visibilidad del compilador antes de reconstruir Linux. Continuar R25 y las capacidades pendientes sin inventar políticas, pilotos ni dictámenes. [Registro](TRAZABILIDAD.md).')
(run/'ESTADO.md').write_text('\n\n'.join(paragraphs),encoding='utf8')
(run/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint122:119requisitos,92originales y118criterios anteriores exactos. MAIN permanece en esquema30; candidata31 aislada5637 integra CIed4 y R17b500.

QA aprobó173casos PostgreSQL en12comandos;42bases propias cerradas sinFORCE. Seguridad aprobó la corrección de cabeceras operativas con el mismo driver24 y dos controles; el before12rojos permanece intacto. Faltan peer79 y regresión completa compuesta.

Linux de69 mantiene brechas reales de traza del compilador y símbolos ELF. El fix nuevo requiere revisión independiente previa a reconstrucción. R25 conserva contrato y reservaDDL32; aún sin producto32.

Free:diez clientes,un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push,PR,despliegue,cargos ni comunicaciones reales. [Estado](ESTADO.md),[registro](TRAZABILIDAD.md),[validación](VALIDACION.md).
''',encoding='utf8')
for name,text in {
 'VALIDACION.md':'QA173PG:12comandos exit0/checker1730;42UUIDcerradas sinFORCE/cero sesiones/ausenciafreshconn. R17mismo24before12rojos→after24verdes, mismos2boundsverdes; autor84 yreplay24 solapados, noPG. Candidataaislada5637 componeCIed4 yR17b500 exactos; peer79 ybroadcomún pendientes.',
 'CAMBIOS.md':'SEC14 añade cabeceras privadas para respuestas de método405 ylector500 de tres rutas operativas exactas. Mergeaislado38b integraCIed4;5637 integraR17b500. MAIN sólo registra evidencia/criterios; no producto31 integrado todavía.',
 'DECISIONES.md':'La aceptación focal R17 no equivale a métricas distribuidas ni SLO. Conservar before12rojos ysame-driver24after, separar replays. No actualizar pinsCI por una cautela sin evidencia: publicación_diary no está en source_modules del mapping; comprobar gate real tras integrar79.',
 'RIESGOS.md':'Pendientes peer79, regresión serial con cobertura y n2 de la composición,imagen común y operacionesMFA. Linux requiere revisar/reconstruir argvreal yvisibilidad antes de aceptación. R25DDL32 aún exclusivo ysinproducto; políticas/países/SLO/pilotos/dictámenes no inventados.',
}.items():
    with(run/name).open('ab') as handle:handle.write(('\n\n## Checkpoint122\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
assert {k:criteria(json.loads(path.read_bytes()))[k] for k in before}==before
seal=ev/'checkpoint122-seal-receipt-20261019';assert not seal.exists()
seal.mkdir();(seal/'.gitattributes').write_bytes(b'* -text\n')
(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
(seal/'receipt.json').write_bytes((json.dumps({'base':base,'registry':119,'previous_criteria_exact':118,'new_ids':['SEC14'],
 'main_product_changed':False,'authenticated_manifests':manifests,
 'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n').encode())
raw.update(p for p in seal.iterdir() if p.is_file())
names=sorted(p.relative_to(root).as_posix() for p in raw)
docs=[(run/name).relative_to(root).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(root/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record independent PG173 and private operational response acceptance'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':119,'previous_criteria_exact':118,'RAW_authenticated':len(names),'main_product_changed':False}))
