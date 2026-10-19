"""Preserve rejected CI gates, their proposed repairs and the native compiler defect."""
from pathlib import Path,PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018')
RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence'
TMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
BASE='9b101f9c690633c6e786f8f963c2c902b2356e96'
SHA=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args,**kw:subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT,**kw)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((TMP/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
native=Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\expat-sec10-d60-native-failed-20261019')
manifest=(native/'manifest.json').read_bytes()
assert SHA(manifest)=='099e43674b96cb6c4d03fd0feeca5d30f9336d962b17ff14828993434057318d'
originals={name:(native/name).read_bytes() for name in json.loads(manifest)}
for name,meta in json.loads(manifest).items():
    assert SHA(originals[name])==meta['sha256'] and len(originals[name])==meta['bytes']
    scan(originals[name],name)
target=EV/native.name
assert not target.exists()
target.mkdir();(target/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in originals.items():
    path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
(target/'manifest.json').write_bytes(manifest)

reviews=[
 ('qa-mfa-ci31-independent-20261019','manifest.json','c95fcafce462c9d4c7fc11f12cf15b8254657756adf0e7a9a195e2d3329a9ddb'),
 ('mfa31-ci-three-boundaries-fix-20261019','manifest.json','5ef44b4b3f10e577d05e05bca9cfc326d2fda866202b52518181119d2420a492'),
 ('security-expat-clinic-independent-20261019','source.json','66f909964f8fa7cc49c4ad26ef55244a6b8399f4b5496d493a82ab5f10a79aa3'),
 ('expat-sec10-d60-native-failed-20261019','manifest.json','099e43674b96cb6c4d03fd0feeca5d30f9336d962b17ff14828993434057318d'),
 ('prepared-wave121-20261019','manifest.json','0f6ecf2ff633b50fe2ee026c71b9568be45d1a7bcdeb56c61c872419089d37b1'),
 ('root-native-provenance-gap-20261019','manifest.json','f5f22357c1192288b063db6f7019c2462b669cbcc6dc544322b202621a927c0b'),
 ('qa-mfa-ci31-fix-independent-20261019','manifest.json','424d82964dbf0dea8f72cd0d26729c8b8f0bef63c9e19546880a4d6107c7606f'),
]
raw=set()
for prefix,name,digest in reviews:
    parent=EV/prefix;source=parent/name
    assert SHA(source.read_bytes())==digest,prefix
    document=json.loads(source.read_bytes());rows=document.get('files',document)
    if isinstance(rows,dict):rows=[{'path':key,**value} for key,value in rows.items()]
    for row in rows:
        assert ('sha256' in row)!=('SHA256' in row)
        path=parent/row.get('path',row.get('file',''));blob=path.read_bytes()
        assert path.resolve().is_relative_to(parent.resolve()) and SHA(blob)==row.get('sha256',row.get('SHA256'))
        assert 'bytes' not in row or len(blob)==row['bytes']
        scan(blob,path.name);raw.add(path)
    assert (parent/'.gitattributes').read_text(encoding='ascii').strip()=='* -text'
    raw.update([source,parent/'.gitattributes'])

data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{r['id']:{key:r[key] for key in fields} for r in value['requisitos']}
before=criteria(json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json')))
assert criteria(data)==before and len(before)==112
discoveries=[
 ('QA-13','El checker CLI de informes actuales puede devolver éxito sin informes y el verificador completo no detecta ese cambio aislado de main.',
  'El CLI auténtico debe rechazar informes vacíos, incompletos o sustituidos; el verificador debe rechazar el mutante main-only return0 antes de aceptar sus resultados, conservando los 173 nodos y la revisión independiente de los mismos negativos.',
  ['R05','R19'], 'qa-mfa-ci31-independent-20261019/cli-and-coverage-review.json','ed4a3be11fb1e921962182812362b515afd8885a'),
 ('QA-14','El workflow actual omite daily_plan_snapshot y sus siete casos nuevos; el histórico anterior a R24 tampoco los ejecuta.',
  'Ejecutar en el CI actual los 25 casos snapshot —siete nuevos y dieciocho repeticiones declaradas— con el módulo original y parser real; rechazar su omisión aunque el workflow y el mapa derivado se modifiquen juntos, sin atribuirlos al histórico anterior.',
  ['R05','R24'], 'qa-mfa-ci31-independent-20261019/cli-and-coverage-review.json','ed4a3be11fb1e921962182812362b515afd8885a'),
 ('QA-15','El marcador de preparación del navegador acepta la ausencia de application_role_restricted_nonowner, pese a exigir un rol restringido.',
  'Todos los marcadores actuales deben aportar un testigo obligatorio true derivado de consultar los cuatro privilegios del rol y la propiedad de la base real; rechazar ausencia, false y sustituciones, con revisión del SQL y de los mismos negativos antes de servicios.',
  ['R04','R05','R19'], 'qa-mfa-ci31-independent-20261019/missing-role-marker-review.json','ed4a3be11fb1e921962182812362b515afd8885a'),
 ('OPS08','El selector de fuentes de pyexpat omite el encabezado Argument Clinic requerido y el build D60 falla al compilar.',
  'Añadir únicamente el encabezado auténtico del mismo tar PSF firmado, fijar su hash y conservar los treinta inputs y el parche anteriores; revisar de forma independiente y compilar el target real con bindings, C API, ELF y linkage comprobados antes de aceptar el artefacto.',
  ['R18','R21','SEC10'], 'expat-sec10-d60-native-failed-20261019/source.json','de69a85e7903f1a7217b054c0edb269dd5560999'),
 ('OPS09','El target nativo compila y ejecuta los seis smoke checks, pero build-provenance registra una lista vacía de argumentos del compilador.',
  'Capturar los argumentos reales de cada compilación y enlace sin cambiar fuentes ni flags para fabricar el testigo; rechazar una traza vacía o incompleta, conservar el artefacto y los diagnósticos previos, y revisar de forma independiente la instrumentación y su resultado nativo.',
  ['R18','R20','R21'], 'root-native-provenance-gap-20261019/receipt.json','de69a85e7903f1a7217b054c0edb269dd5560999'),
]
for ident,problem,criterion,tasks,source,commit in discoveries:
    row={'id':ident,'identificador_original':ident,'fuente':'docs/implementation/20261018-evolution/evidence/'+source,
     'seccion':'Hallazgo nuevo checkpoint121','problema':problem,'criterio_exacto':criterion,'prioridad':'P1',
     'responsable':'Operación y documentación' if ident.startswith('OPS') else 'QA y automatización',
     'tareas':tasks,'dependencias':tasks,'estado':'en_revision','implementacion':'en_revision','validacion':'en_curso',
     'despliegue':'no_desplegado','entorno':'local','cambios':['Corrección aislada preparada; no integrada en MAIN.'],
     'commits':[commit],'pruebas':['Before independiente preservado; la aceptación posterior sigue acotada y pendiente de integración.'],
     'evidencia':['evidence/'+source],'documentacion':['ESTADO.md','VALIDACION.md','DECISIONES.md'],
     'revisor':'Seguridad independiente estática; dinámica pendiente' if ident=='OPS08' else 'QA independiente; replay del fix en curso',
     'bloqueo':None,'observaciones':['No cambia ningún criterio anterior.']}
    if ident=='OPS09':
        row.update(estado='en_curso',implementacion='pendiente',revisor='Seguridad independiente pendiente')
        row['cambios']=['Brecha observada en el target compilado; diagnóstico e instrumentación correctiva pendientes.']
    data['requisitos'].append(row)
assert len(criteria(data))==117 and {k:criteria(data)[k] for k in before}==before
notes={
 'R05':'QA rechazó CIe0 por CLI main-only falso éxito, snapshot omitido y rol opcional: nuevosQA-13/14/15. Autor ed4 corrigió11 archivos CI,205 canarios/FULL145/Bash115 y32VM/519; QA aceptó el contrato con los mismos repros,12 propios/24 fragmentosSQL/snapshot25. Los173PG comenzaron en ventana propia; aún sin resultado. Se conservan173 IDs/23helpers/8locksPython y2Node; no sumar canarios offline comoPG.',
 'R18':'OPS08: D60 falló al compilar por header Clinic omitido. de69 añade sólo header auténtico29204/SHA5e730; root11 ySeguridad21+11/firmaPSF aceptan sólo estática. Target de69 compiló0 yhelper6smokes, pero OPS09 registra compiler_commands vacío: target sin aceptación completa. Operación midió93exports nuevos frente1base; OPS10 reservado mientras cierra su evidencia. No runtime54/OS71/SCA acreditados.',
 'R19':'Contrato CIed4 aceptado por QA separado de173PG en curso. Broad diagnóstico bd348:2381 casos=2360pass/2Googlefail/18publicaciónsetupERROR/1skip;maxfail20,10143fuentes89paquetes quietos,pip0. No veinte defectos de producto. Backend reproduce2Google501 por Settings antiguo y2setup29sin tablasMFA; adaptación local en curso sin modificar asserts.',
 'R25':'Contrato documental a1f9579561c943381f544ae6eaabf1700e82c8b3 yRAW879d093b conservado. Miembro→gym exacto, consentimiento append versionado/revocable, scope/profile/categorías/fecha explícitos, agregados mínimos yretiro sin MFA. DDL32 reservado exclusivamente aR25; ningún producto/DDL/PG32 ejecutado. AccessorSQL requiere revisión de privacidad/seguridad antes de aceptación.',
 'R32':'QA aceptó contrato CIed4 tras corregir3fronteras;173PG en curso, no aceptación adelantada. Broad inicial detuvo20fallos de2módulos:causasfixturales SettingsGoogleantiguo/esquema29 confirmado en4representantes,correcciónaislada sinasserts cambiados. R17 nuevo producto aisladofee219 con52focales103dirigidas deautor, noindependiente.',
 'QA-12':'Fixture16con acompañantes ya aceptada focalmente. QAaceptó contratoCIed4 con snapshot25 añadido (7nuevos+18repeticiones) y3negativoscorregidos;173PG e integración/broad todavía pendientes.',
 'SEC10':'de69 estática aceptada independiente21+11:31inputs ylos30previos exactos; firmaPSF validada. Compilación real llegó0 y6smokes, pero trazaargvvacía OPS09 yvalidaciónELF/linkage/namespace aún diagnósticas; no cierreSEC10.',
}
refs={
 'R05':['qa-mfa-ci31-independent-20261019/phase-summary.json','qa-mfa-ci31-fix-independent-20261019/phase-summary.json'],
 'R18':['security-expat-clinic-independent-20261019/source.json','root-native-provenance-gap-20261019/receipt.json'],
 'R19':['prepared-wave121-20261019/broad31-diagnostic/summary.SANITIZED.json'],
 'R25':['prepared-wave121-20261019/R25/contract.RAW.md'],
 'R32':['prepared-wave121-20261019/broad31-diagnostic/summary.SANITIZED.json','qa-mfa-ci31-fix-independent-20261019/phase-summary.json'],
 'QA-12':['qa-mfa-ci31-fix-independent-20261019/phase-summary.json'],
 'SEC10':['security-expat-clinic-independent-20261019/source.json'],
 'OPS08':['security-expat-clinic-independent-20261019/source.json'],
 'QA-13':['qa-mfa-ci31-fix-independent-20261019/phase-summary.json'],
 'QA-14':['qa-mfa-ci31-fix-independent-20261019/phase-summary.json'],
 'QA-15':['qa-mfa-ci31-fix-independent-20261019/phase-summary.json'],
}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint121: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        full='evidence/'+ref
        if full not in row['evidencia']:row['evidencia'].append(full)
(RUN/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())

paragraphs=(RUN/'ESTADO.md').read_text(encoding='utf8').split('\n\n')
def replace(prefix,value):
    positions=[i for i,p in enumerate(paragraphs) if p.startswith(prefix)]
    assert len(positions)==1,prefix
    paragraphs[positions[0]]=value
replace('Checkpoint 120 local.',
 'Checkpoint 121 local. El registro conserva 117 requisitos: los 92 originales y veinticinco hallazgos añadidos. Los 112 criterios anteriores permanecen exactos. Se añaden QA-13, QA-14, QA-15, OPS08 y OPS09. MAIN sigue en esquema 30; el workspace original permanece intacto. Free mantiene diez clientes activos, un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales.')
replace('La candidata MFA 31 está aislada',
 'La candidata MFA 31 permanece aislada en bd34893c4b6f806041b0cc6b7f156e9286886748, con producto 4a y CI e0. El diagnóstico amplio ejecutó 2381 casos: 2360 aprobados, dos fallos Google, dieciocho errores de preparación de publicación y una omisión de symlink Windows. Se detuvo por maxfail20; no es una regresión completa aceptada. Sus 10143 archivos y 89 paquetes permanecieron estables, con pip check verde. Backend reprodujo los dos Google501 por una configuración antigua y los dos errores representativos de ambas factories por esquema29 sin tablasMFA; la adaptación aislada conserva las 58 aserciones de esos módulos. [Diagnóstico](evidence/prepared-wave121-20261019/broad31-diagnostic/summary.SANITIZED.json).')
replace('CI e0 queda preservado',
 'CI e0 queda preservado y rechazado por tres fronteras: main-only falso éxito sin informes, snapshot25 omitido y testigo de rol opcional. El fix ed4a3be11fb1e921962182812362b515afd8885a cambió once archivos CI y conservó producto 4a, 173 nodos y 23 helpers. Autor: 205 canarios, 145 controles workflow y 32 módulos frontend con 519 ejecuciones. QA aceptó el contrato repitiendo los mismos negativos, doce controles propios, veinticuatro fragmentos SQL y snapshot25 con parser real. Las 173 identidades PG están en ejecución en una ventana propia; no se adelanta su resultado. [Antes](evidence/qa-mfa-ci31-independent-20261019/phase-summary.json), [después](evidence/qa-mfa-ci31-fix-independent-20261019/phase-summary.json).')
replace('Linux: D60 actualiza',
 'Linux: D60 superó metadata APT, pero falló al compilar por omitir el encabezado Argument Clinic. de69 lo añade desde el mismo tar PSF firmado, conservando exactamente los treinta inputs anteriores. Root pasó once controles; Seguridad veintiuno positivos y once negativos, con aceptación sólo estática. El target de69 compiló y ejecutó seis smoke checks, pero OPS09 conserva su lista de argumentos vacía. Operación confirmó además 93 exports frente a uno de la base: OPS10 queda reservado mientras sella evidencia y causa. No hay aceptación completa de artefacto, ELF, linkage, runtime54 ni cierre de los 71 IDs OS. VM propia permanece bajo lease exclusivo para diagnóstico y revisión; sin PG ni proxies. [Fallo D60](evidence/expat-sec10-d60-native-failed-20261019/source.json), [revisión estática](evidence/security-expat-clinic-independent-20261019/source.json), [brecha de procedencia](evidence/root-native-provenance-gap-20261019/receipt.json).')
position=next(i for i,p in enumerate(paragraphs) if p.startswith('R23 y R24 siguen parciales.'))
paragraphs.insert(position,'R17 tiene una candidata aparte fee219929ac2c6a16cc8d8a6bec42cb757245a4e: seis archivos conectan métricas y rutas operativas protegidas a ambas factories. Pasó 103 comprobaciones dirigidas y un freeze focal de 52, con 10145 archivos, 89 paquetes y Python estables. Son resultados de autor sobre ASGI y SQLite de metadata; Seguridad está revisando métodos y errores, autorización y privacidad. No se integra todavía ni acredita métricas distribuidas, streaming completo o un SLO.')
paragraphs.insert(position+1,'R25 sólo tiene contrato documental congelado a1f9579561c943381f544ae6eaabf1700e82c8b3: consentimiento versionado para miembro→gym exacto, selección de perfil, categorías y fechas, agregados mínimos y retiro sin MFA. DDL32 está reservado exclusivamente a ese trabajo; aún no se editó ni ejecutó producto32. El accessor requiere revisión de privacidad y seguridad. [Contrato](evidence/prepared-wave121-20261019/R25/contract.RAW.md).')
(RUN/'ESTADO.md').write_text('\n\n'.join(paragraphs),encoding='utf8')
(RUN/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint 121: 117 requisitos; 92 originales y 112 criterios anteriores intactos. MAIN continúa en esquema 30. MFA 31 sigue aislado y su regresión amplia inicial se detuvo con dos fallos Google y dieciocho errores de preparación, bajo revisión de fixtures.

QA aceptó el contrato CI ed4 tras corregir tres fronteras; las 173 identidades PostgreSQL están en ejecución. R17 fee219 tiene 103 comprobaciones dirigidas y 52 focales de autor, con revisión independiente pendiente.

El target Expat de69 compiló y pasó seis smoke checks, pero mantiene una brecha de argumentos del compilador y una diferencia de exportaciones ELF. No acredita imagen común, runtime54, SCA ni cierre OS. R25 conserva sólo su contrato, sin DDL32 ejecutado.

Free: diez clientes, un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''',encoding='utf8')
for name,text in {
 'VALIDACION.md':'Se preservan el rechazo CIe0 y el contrato ed4 aceptado independientemente: mismos tres negativos,205 canarios offline,145 workflow, snapshot25 y SQL de rol. Los173PG están en curso, no aprobados todavía. Broad bd348:2381=2360pass+2fail+18error+1skip; maxfail20 y fuente/89paquetes quietos. de69 tiene aceptación estática21+11 y target compilado0/6smokes, con compiler argv vacío y superficie ELF diferente aún sin aceptación. R17 es autor103+52, no QA independiente.',
 'CAMBIOS.md':'MAIN sólo registra cinco hallazgos y evidencia. CIed4 repara CLI, snapshot y rol obligatorio; de69 añade un único header auténtico. La candidataR17 monta observabilidad protegida y cuenta errores500 sin guardar detalles. La adaptación de fixtures Google/publicación no altera producto. R25 sigue documental.',
 'DECISIONES.md':'Los canarios offline no son PostgreSQL y los replays no son casos nuevos. Un target compilado no acredita procedencia vacía ni superficie ELF alterada. Preservar D60 rojo y de69 sin reconstruirlo para disfrazar resultados. DDL32 queda reservado a R25; el contrato no autoriza copiar diarios, inferir ingesta ni conclusiones clínicas.',
 'RIESGOS.md':'Pendientes: integración y regresión amplia31,173PG eimagen común; instrumentación argv y exportaciones ELF del target nativo; revisión independiente R17 y aspectos operativos MFA. OPS10 se añadirá con la evidencia nativa cerrada. Continúan políticas, entrevistas/pilotos reales, validación profesional y objetivos de carga sin inventarlos.',
}.items():
    with(RUN/name).open('ab') as out:out.write(('\n\n## Checkpoint 121\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True,capture_output=True)
assert {k:criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))[k] for k in before}==before
seal=EV/'checkpoint121-seal-receipt-20261019';seal.mkdir(exist_ok=False)
(seal/'.gitattributes').write_bytes(b'* -text\n')
(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
(seal/'receipt.json').write_bytes((json.dumps({'base':BASE,'registry':117,'previous_criteria_exact':112,
 'new_ids':[r[0] for r in discoveries],'main_product_changed':False,'authenticated_manifests':reviews,
 'RAW_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':SHA(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n').encode())
raw.update(p for p in seal.iterdir() if p.is_file())
names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
docs=[(RUN/n).relative_to(ROOT).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record CI trust repairs and native compiler findings without premature acceptance'],cwd=ROOT,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':117,'previous_criteria_exact':112,'RAW_authenticated':len(names),'main_product_changed':False}))
