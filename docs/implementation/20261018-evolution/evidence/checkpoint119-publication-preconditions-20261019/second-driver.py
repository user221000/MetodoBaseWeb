"""Record independent MFA acceptance, two discoveries and metadata-only native recovery."""
from pathlib import Path
import hashlib
import json
import runpy
import subprocess
import sys

ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018')
RUN=ROOT/'docs/implementation/20261018-evolution'
EV=RUN/'evidence'
BASE='145b9d409e0c94cfd2cb813d47fa7f9d011096fd'
SHA=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args,**kw:subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT,**kw)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
# Reuse only the scanner definition, not the preparation script's executable module.
import ast
source=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-checkpoint119-prepare.py').read_text(encoding='utf8')
tree=ast.parse(source)
scanner=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='scan')
namespace={}
exec('from pathlib import PurePosixPath\nimport re,io,tarfile,zipfile',namespace)
exec(compile(ast.Module(body=[scanner],type_ignores=[]),'reviewed-scanner','exec'),namespace)
scan=namespace['scan']

def rows(document):
    value=document.get('files',document)
    if isinstance(value,list):return value
    assert isinstance(value,dict)
    result=[]
    for name,meta in value.items():
        if isinstance(meta,str):meta={'sha256':meta}
        else:
            meta=dict(meta)
            assert ('sha256' in meta) != ('SHA256' in meta)
            if 'SHA256' in meta:meta['sha256']=meta.pop('SHA256')
        result.append({'path':name,**meta})
    return result

raw=set()
reviews=[
 ('qa-mfa31-composition-independent-20261019','manifest.json','205bf05814cabed5a1248c5a2cb5d36e0b6ca2a358af45a6733ecb1d349c6e1e'),
 ('qa-mfa31-pg-independent-20261019','manifest.json','9881e76ff770b971e48a79f6f939a58b1efde8a45578ff8c1d91fb3e66b25a30'),
 ('qa-mfa31-browser-independent-20261019','manifest.json','123c7e9e809e35eaa3ecceb04d06ed34d9d3303d5657320e7bf409ba98a5df05'),
 ('qa-mfa31-browser-v2-independent-20261019','manifest.json','3e7de8df2c466a6afaec69e2c63e8c6d15871ff0b5d4de5a163531be1c263504'),
 ('qa-mfa31-summary-independent-20261019','before-manifest.json','228c170fc458f82aad24cde20992f35975f23f8f273940538d3b268b8a81cf64'),
 ('qa-mfa31-summary-after-independent-20261019','manifest.json','e1a951ddb1388aa4793d3bc0f51c2c92d4814e2dac8d0ceee951100274467e73'),
 ('qa-mfa31-restore-independent-20261019','manifest.json','79b9f0b5cc870bcde6ac3984f092539a6dd738004c1d430319ebf322d22d98cd'),
 ('security-apt-metadata-refresh-independent-20261019','source.json','3f79e2aa1cf8ca3c50384e37577329a6a59600881421a33fee06adf01c1cfb12'),
 ('prepared-wave119-20261019','manifest.json','936eec3d8e5ad2bf52d63d98a3a6fb231ec4f56fed0b909841a96a60104731b5'),
]

# Transfer two immutable operations proof sets with their exact recorded manifests.
copies=[
 (Path(r'F:\mb-container-apt-refresh-sec10-20261019')/'docs/implementation/20261018-evolution/evidence/apt-metadata-sec10-refresh-20261019','apt-metadata-sec10-refresh-20261019','a92b47cabf8326c7db80315476b39e5bdd2fc64e30c21da46b6d8cdc00b4f5c6'),
 (Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\expat-sec10-m2-native-preimage-20261019'),'expat-sec10-m2-native-preimage-20261019','3ce49e1ce5b90d6eb60e83fc0ba56b4437b87e19ad832978cf462e2ee64e2925'),
]
for parent,prefix,digest in copies:
    manifest=(parent/'manifest.json').read_bytes()
    assert SHA(manifest)==digest
    target=EV/prefix
    existing=target.exists()
    if not existing:
        target.mkdir()
        (target/'.gitattributes').write_bytes(b'* -text\n')
    else:
        assert (target/'.gitattributes').read_bytes()==b'* -text\n'
        assert (target/'manifest.json').read_bytes()==manifest
    for row in rows(json.loads(manifest)):
        name=row.get('path',row.get('file'))
        original=parent/name
        assert original.resolve().is_relative_to(parent.resolve())
        blob=original.read_bytes()
        assert SHA(blob)==row['sha256'] and len(blob)==row['bytes']
        scan(blob,name)
        path=target/name
        path.parent.mkdir(parents=True,exist_ok=True)
        if existing:assert path.read_bytes()==blob
        else:path.write_bytes(blob)
    if not existing:(target/'manifest.json').write_bytes(manifest)
    reviews.append((prefix,'manifest.json',digest))

for prefix,name,digest in reviews:
    parent=EV/prefix
    manifest=parent/name
    assert SHA(manifest.read_bytes())==digest,prefix
    for row in rows(json.loads(manifest.read_bytes())):
        path=parent/row.get('path',row.get('file',''))
        assert path.resolve().is_relative_to(parent.resolve())
        blob=path.read_bytes()
        assert SHA(blob)==row['sha256'] and ('bytes' not in row or len(blob)==row['bytes']),path.name
        scan(blob,path.name)
        raw.add(path)
    attributes=parent/'.gitattributes'
    assert attributes.read_text(encoding='ascii').strip()=='* -text',prefix
    raw.update([manifest,attributes])
    scan(manifest.read_bytes(),manifest.name)

parent=EV/'backend-mfa31-fixture-adoption'
freeze_blob=(parent/'freeze.json').read_bytes()
assert SHA(freeze_blob)=='ff524d818c9da668f6c059d493f23fc6cce4ecb9bc5e278da8c030031ba34d59'
for name,meta in json.loads(freeze_blob)['proof_files'].items():
    path=parent/name
    blob=path.read_bytes()
    assert len(blob)==meta['bytes'] and SHA(blob)==meta['sha256']
    scan(blob,name)
    raw.add(path)
raw.add(parent/'freeze.json')

data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{r['id']:{key:r[key] for key in fields} for r in value['requisitos']}
before=criteria(json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json')))
assert criteria(data)==before and len(before)==110

def new(ident,problem,criterion,priority,tasks,evidence,commits,tests):
    return {'id':ident,'identificador_original':ident,'fuente':'docs/implementation/20261018-evolution/evidence/'+evidence[0],
     'seccion':'Hallazgo nuevo checkpoint119','problema':problem,'criterio_exacto':criterion,'prioridad':priority,
     'responsable':'QA y automatización' if ident.startswith('QA') else 'Frontend y UX/UI',
     'tareas':tasks,'dependencias':tasks,'estado':'en_revision','implementacion':'en_revision','validacion':'en_curso',
     'despliegue':'no_desplegado','entorno':'local','cambios':['Corrección preparada en candidata aislada4a; integración amplia aún pendiente.'],
     'commits':commits,'pruebas':tests,'evidencia':['evidence/'+e for e in evidence],
     'documentacion':['ESTADO.md','DECISIONES.md','VALIDACION.md'],'revisor':'QA independiente; integración por coordinador',
     'bloqueo':None,'observaciones':['No cambia el criterio de ningún identificador anterior.']}

data['requisitos'].append(new('QA-12',
 'La fixture VM histórica del lector R12 omite los módulos acompañantes y el include que R24 carga en la plantilla real; produce tres fallos de infraestructura sobre eea8 y31.',
 'Conservar el histórico y sus fallos originales; demostrar la causa sin modificar producto ni aserciones, ejecutar los 16 contratos con los acompañantes reales sobre31 y un histórico auténtico aceptado, y revisar de forma independiente la adopción y los gates CI.',
 'P1',['R05','R12','R24','QA-08'],['prepared-wave119-20261019/receipt.json','prepared-wave119-20261019/metodobase-member-vm-causality-20261019/receipt.json','prepared-wave119-20261019/metodobase-member-consumers31-final-20261019/summary.json'],
 ['102f75f28dc7ba7688ed24d97d658b7826ab16c4'],['Original eea8 y31:13/16; stubs pasivos sólo causales:16/16. Nueva fixture con módulos reales:16/16; mismos16 callbacks y runner exactos. Peer/CI en curso.']))
data['requisitos'].append(new('UX-19',
 'Tras confirmar un cambio de MFA, la cuenta muestra el resumen anterior de factor/códigos junto al ACK y el nuevo kit, aunque el servidor ya confirmó el cambio.',
 'Retirar el resumen obsoleto después del ACK de confirmación, regeneración o revocación y al cerrar el contexto local; conservar el kit veraz, no consultar ni renovar con la sesión cerrada y preservar una cuenta nueva si cambia durante el renderizado.',
 'P2',['R15','R32'],['qa-mfa31-summary-independent-20261019/factor-truth-and-original-native-DOM.json','qa-mfa31-summary-after-independent-20261019/phase-summary.json','prepared-wave119-20261019/metodobase-mfa31-summary-fix-20261019/receipt.json'],
 ['4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae'],['Mismo canary independiente b704:3 rojos antes y3 verdes después; QA añadió2 cambios reentrantes de cuenta A→B verdes. No se reatribuyen los15grupos de Chrome c669 a4a.']))
assert {r['id']:r for r in data['requisitos']} and len(criteria(data))==112
assert {k:criteria(data)[k] for k in before}==before
notes={
 'R05':'QA-12 registrado: eea8 postR24 conserva13/16 rojos originales; CI31 adopta histórico57335e5 auténtico anterior aR24 (FULL+348VM verdes), conservando23helpers. Current31 añade fixture16con acompañantes reales y gates propios; aún no se declara integración/Actions.',
 'R08':'QA independiente restauró31 poblado sobre4a:1/1verde,61asserts módulo30 y36helper28 preservados mediante inversa completa,32model/33physical/25FORCE y3actores/24hashes de recuperación. DosUUID eliminadas exactas/0sesiones/ausencia desde conexión nueva. NoRPO/RTO de negocio.',
 'R12':'UI revisión propia da343:10VM+4flujosHTTP SQLite; esos mismos4flujos se repiten enPG31 restringido sobrec669. QA-12 afectafixtureVM, sin regresión de producto demostrada; nueva16verde en candidata, peer pendiente.',
 'R13':'QA repitió15grupos mantenidos/12pantallas enChrome nativo c669:0axeAA enbloques,overflow,pageerrors. Primera preparación0Chrome falló por observador; finalSTOPtimeout20s conservado/cleanup exactoPIDbirth; no cierregrácil ni claveMFAafter observada. UX19 posterior sólo3+2VM focales, sin atribuir15a4a.',
 'R15':'UX-19 registrado: resumen deMFA obsoleto enDOM real; dos inserciones en4a lo retiran después de comprobar contexto. Mismo3antesrojo→3verde; QA2reentrantesA→B adicionales verdes. Todavía candidata aislada.',
 'R18':'D60 actualiza únicamente hash InRelease trixie-updates; Seguridad PASS_METADATA_ONLY,7negativos/GPG real,409hojas/3índices/11registros/10closure invariantes. Intento7c falló correctamente por metadata antescompiler; preimagen conservada. Nueva compilación aislada en curso, no aceptaciónruntime54/71OS.',
 'R19':'QA scopes independientes:10VM y4flujos propios, repeticiónPG de esos4, replay15grupos Chrome mantenidos y1restore. No se suman como nuevos los replays; current31 CI/imagen/regresión amplia siguen pendientes.',
 'R21':'Checkpoint119 conserva RAW con atributos existentes LF/CRLF sin normalizarlos, evidencia fallida y nueva por separado; pruebaDAB53blobs exactos. Root174autorDAB no es revisión independiente; primer recuento109vs110 incluía helper y falló antesmerge, corregido sóloámbito.',
 'R32':'QA aceptó composición10VM/4flujos, replayPG4 yChrome15c669, restauración31 poblada4a yUX19focal3+2. BackendDAB174 verdes con MFA real enfixtures, peer encurso. Aún faltanCI31,regresión amplia/imagen,avisos,custodia/rotación/configuración real yprocedimiento legítimo ante pérdida total.',
 'QA-11':'El hallazgo original de confianza enverificadorCI28 permanece separado deQA-12, nuevo fallo por acompañantes omitidos enfixtureVM.',
 'SEC10':'MetadataD60 aceptada sólo para desbloquear compilación M2: firmas ypackagepins invariantes; no ABI/ELF/Expat import/compilación/SCA acreditados por esa aceptación.',
}
refs={
 'R05':['prepared-wave119-20261019/receipt.json'],
 'R08':['qa-mfa31-restore-independent-20261019/phase-summary.json'],
 'R12':['qa-mfa31-composition-independent-20261019/phase-summary.json','qa-mfa31-pg-independent-20261019/phase-summary.json'],
 'R13':['qa-mfa31-browser-v2-independent-20261019/phase-summary.json'],
 'R15':['qa-mfa31-summary-after-independent-20261019/phase-summary.json'],
 'R18':['security-apt-metadata-refresh-independent-20261019/source.json','expat-sec10-m2-native-preimage-20261019/manifest.json'],
 'R19':['qa-mfa31-browser-v2-independent-20261019/phase-summary.json'],
 'R21':['prepared-wave119-20261019/receipt.json'],
 'R32':['qa-mfa31-restore-independent-20261019/phase-summary.json','backend-mfa31-fixture-adoption/freeze.json','qa-mfa31-summary-after-independent-20261019/phase-summary.json'],
 'SEC10':['security-apt-metadata-refresh-independent-20261019/source.json'],
}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint119: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        full='evidence/'+ref
        if full not in row['evidencia']:row['evidencia'].append(full)
(RUN/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
(RUN/'ESTADO.md').write_text('''# Estado de ejecución 20261018-evolution

Checkpoint119 local:112 requisitos, con los92 originales y20 hallazgos añadidos. Los110 criterios anteriores se conservan exactos. MAIN continúa en esquema30 con R12/R23/SEC11/R24 parcial; el workspace original permanece intacto. Free mantiene10clientes,1plan porcliente/día y10planes totales porgimnasio/día. Desktop sigue soportado. No hubo push, PR, despliegue, cargos ni comunicaciones reales.

La candidata aislada MFA31 está en4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae. Seguridad aceptó backend440 con alcance acotado; QA verificó10VM propios y4flujosHTTP SQLite sobre da343 y repitió esos4flujos enPostgreSQL31 restringido sobrec669. Se conservaron fuentes y89paquetes; ambas bases PG quedaron ausentes con0sesiones. [Composición](evidence/qa-mfa31-composition-independent-20261019/phase-summary.json), [PG](evidence/qa-mfa31-pg-independent-20261019/phase-summary.json).

QA repitió15grupos mantenidos enChrome real sobrec669 y revisó12pantallas: sinviolaciones axeAA enlosbloques nuevos, overflow nipageerrors. Conservó la preparación fallida antesChrome y el timeout20s deSTOP del servidor. El cierre final verificó PID, nacimiento, ejecutable y generación antes de señalizar exclusivamente el proceso propio; el puerto8805 quedó cerrado y los procesos ajenos intactos. No se observó el snapshot final de claveMFA enRAM, ni se afirma cierregrácil. [Alcance exacto](evidence/qa-mfa31-browser-v2-independent-20261019/phase-summary.json).

UX-19 surge de esa revisión: el resumen anterior de factor/códigos seguía visible después del ACK. La corrección4a retira ese texto en dos callbacks tras comprobar el contexto efímero. El mismo canary pasó de3rojos a3verdes; QA añadió2casos verdes de cambio de cuenta durante renderizado. Es aceptación focal; los15grupos anteriores no se reatribuyen a4a. [Antes](evidence/qa-mfa31-summary-independent-20261019/factor-truth-and-original-native-DOM.json), [después](evidence/qa-mfa31-summary-after-independent-20261019/phase-summary.json).

QA restauró31 poblado sobre4a:1/1verde, preservando íntegros los61asserts del módulo30 y36del helper28,32modelos/33tablas físicas,25familias FORCE RLS ylas nuevas filasMFA. Las dos bases temporales quedaron eliminadas exactamente y su ausencia fue comprobada desde otra conexión. Esto no define RPO/RTO ni prueba recuperación deproducción. [Restauración](evidence/qa-mfa31-restore-independent-20261019/phase-summary.json).

La adopciónDAB de cinco archivos de tests pasó174/174 con autenticaciónMFA real. Cambia una expectativa404a403 sobre tres casos porla precedencia deliberada de autorización, con comprobaciones adicionales de opacidad/integridad; las demás aserciones se conservan. Está compuesta en2010 y pendiente de peer. QA-12 registra una fixtureVM dellector que no cargaba los acompañantesR24: eea8 y31 dan13/16; los stubs pasivos sólo demostraron causa. La nueva fixture usa los módulos reales y conserva exactamente los16callbacks:16/16verdes del autor, revisión independiente encurso. CI31 ejecuta histórico auténtico57335e5 con FULL+348VM verdes y prepara gates propios para31;23helpers permanecen inmutables. El históricoeea8 y sus rojos no se reescriben.

La amplia de MAIN30 conserva2597aprobadas+1omisión Windows por modo serial/cobertura y dosworkers mezclados; fuentes y89paquetes estables. No acredita31. CI31, regresión amplia actual eimagen común siguen pendientes. MFA también mantiene pendientes avisos por cambio defactor, custodia/rotación yconfiguración real, yprocedimiento legítimo ante pérdida total de factores.

Linux: el intento de compilaciónM2/7c falló correctamente por InRelease actualizado antes del compilador. D60 cambia sólo ese hash; Seguridad validó firmas,409hojas ypaquetes invariantes, con7negativos verdes. Es PASS_METADATA_ONLY. La nueva compilación aislada está encurso; no se atribuye aello aceptación deABI/linkage/runtime54 ni cierre de71IDs OS. QEMU propio permanece abierto exclusivamente para esa ventana; PG55483 quedó libre. [Metadata](evidence/security-apt-metadata-refresh-independent-20261019/source.json), [preimagen](evidence/expat-sec10-m2-native-preimage-20261019/manifest.json).

R23/R24 siguen parciales. R25/R27/R30/R31/R33/R34/R35 conservan las dependencias de producto, consentimiento, políticas yvalidación real documentadas. La consulta de países/conservación yla de volumen/p95 están pendientes; no se activaron purgas ni se inventaron SLO, pilotos o dictámenes. R34 hizo16solicitudes naturales200 sinreproducir el timeout histórico; sigue abierto.

Siguiente acción: cerrar peer defixtures/gatesCI31, integrarlos enla candidata y ejecutar regresión amplia, mientras Operación valida la compilación nativa. Después continuar las capacidades pendientes sin esperar tareas externas independientes. [Registro](TRAZABILIDAD.md).
''',encoding='utf8')
(RUN/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint 119: 112 requisitos. Los 92 originales y los 110 criterios previos permanecen exactos. MAIN sigue en esquema 30, con 2597 aprobadas y una omisión de symlinks en Windows por cada modo: serial con cobertura y dos workers con orden mezclado.

MFA 31 está aislado en 4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae. Tiene aceptación de backend 440 acotada, revisión QA de diez VM y cuatro flujos HTTP y su repetición en PostgreSQL, quince grupos Chrome sobre c669, restauración poblada sobre 4a y corrección UX-19 focal de tres casos y dos adicionales. Los replays no son casos nuevos. Fixtures DAB y CI 31 siguen en revisión e integración; falta la regresión amplia actual y una imagen común.

D60 sólo tiene aceptación de metadata APT. Compilación, ABI, linkage, SCA y los 71 identificadores OS siguen pendientes. Desktop continúa soportado. Free: diez clientes, un plan por cliente al día y diez totales por gimnasio al día.

No es una entrega final. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md), [registro](TRAZABILIDAD.md).
''',encoding='utf8')
appendices={
 'VALIDACION.md':'QA independiente:10VM+4flujosSQLite, replayPG deesos4,15grupos mantenidosChrome/12pantallasc669,1restorepoblado4a yUX19mismo3+2propios. STOPtimeout ypreparaciónfallida preservados; no runtimekeyafter ni cierregrácil. DAB174esautor, peerpendiente. QA-12:13/16original→16causalstubs(sólocausa)→16actualcompanions nueva fixture. D60firmas/7negativos/metadatainvariante, no compilación.',
 'CAMBIOS.md':'MAIN sólo añade documentación/evidencias. Candidata aislada compone5testsDAB en2010, nuevafixturemember31 en102f ydosinserciones UI4a para retirar resumenMFAobsoleto. Unliteral deesperabrowserc669 siguecopyrevisado, sinotrosassertscambiados. SeañadenQA-12yUX-19sinrenumerar.',
 'DECISIONES.md':'HistóricoCI31 cambia justificadamente deeea8postR24(3rojosinfrafixture) a57335e5aceptadoanteriorR24, ambos auténticosypreservados; current31pruebaR24conacompañantesreales. Conservar23helpersinmutables ytodoslos16callbacks. D60aceptaciónmetadatasólo para nueva compilación. LF/CRLF RAWsepreservansinreescritura.',
 'RIESGOS.md':'PersistenCI31/regresiónactual/imagen,avisosMFA/custodia/configuraciónrealypérdidatotaldefactores. UX19tieneaceptaciónfocal, noreplay15posterior. STOPbrowsernoobservócierregrácil/claveRAMafter,limitesexplícitos. QA-12confianzaenfixtureenpeer. D60noacreditaABI/linkage/SCA/71OS. Políticas,pilotos,clínicaySLOrequierenhechos/decisionesreales.',
}
for name,text in appendices.items():
    with(RUN/name).open('ab') as out:out.write(('\n\n## Checkpoint119\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True,capture_output=True)
assert {k:criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))[k] for k in before}==before
seal=EV/'checkpoint119-seal-receipt-20261019'
seal.mkdir(exist_ok=False)
(seal/'.gitattributes').write_bytes(b'* -text\n')
(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt={'base':BASE,'registry':112,'previous_criteria_exact':110,'new_ids':['QA-12','UX-19'],'main_product_changed':False,
 'authenticated_manifests':reviews,'raw_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':SHA(p.read_bytes())} for p in sorted(raw)}}
(seal/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
raw.update(p for p in seal.iterdir() if p.is_file())
names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
docs=[(RUN/n).relative_to(ROOT).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
buffer=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode())
cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob'
    size=int(header[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name
    cursor+=size+1
assert cursor==len(buffer)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record independent MFA restore and UI findings with metadata-only native review'],cwd=ROOT,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':112,'previous_criteria_exact':110,'RAW_authenticated':len(names),'main_product_changed':False}))
