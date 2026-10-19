"""Seal independent R12 acceptance, static container review and rejected emitter."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence'
BASE='fb19c0d441bfafa9ed758d2cf7dbb78c629e58b7'
sha=lambda value:hashlib.sha256(value).hexdigest()
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=ROOT,**kw)
read=lambda path:json.loads(path.read_bytes())
def write(path,value):path.write_bytes(value.encode('utf8'))
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
raw=set()
def authenticate(directory,filename,digest,key):
    path=EV/directory/filename;assert sha(path.read_bytes())==digest
    value=read(path);entries=value[key]
    if isinstance(entries,dict):entries=[{'file':name,'sha256':detail if isinstance(detail,str) else detail['sha256']} for name,detail in entries.items()]
    for entry in entries:
        target=path.parent/entry['file'];blob=target.read_bytes();assert sha(blob)==entry['sha256'],target
        if 'bytes' in entry:assert len(blob)==entry['bytes']
        raw.add(target)
    raw.add(path)
    attrs=path.parent/'.gitattributes'
    if attrs.exists():assert attrs.read_bytes().replace(b'\r\n',b'\n')==b'* -text\n'
    else:attrs.write_bytes(b'* -text\n')
    raw.add(attrs)
    return value
qa=authenticate('qa-r12-composition29-independent-20261019','final-manifest.json','f601ae684c82fbf5f03bd568e39a52c51f9e344aa6e69e0a6d7f9b6c98bb3afb','files')
assert qa['file_count']==291 and qa['summary_sha256']=='a8ca0e4a1f84bd1fc8609cd6d392377b64d362b3fbddac58bf5772e03d1419af'
summary=EV/'qa-r12-composition29-independent-20261019/final-summary.json';assert sha(summary.read_bytes())==qa['summary_sha256'];raw.add(summary)
authenticate('security-r12-controls-independent-20261019','source.json','9fed14440d04fce7d8712cd2886c98fc53c273418c66967b09523de474d0df0f','published_files_sha256')
authenticate('linux-container-libpq-sec09-prepared-20261019','evidence-manifest.json','ecfd599f4d328bed856519fee8618f19643d97e66fbcd4c4c64540c470db00e6','files')
authenticate('sec09-container-static-independent-20261019','source.json','f251c1ec0a155cde7aecfbfb03506f0143b336402a08e10cc0ca10916257b9d2','files')
authenticate('security-session-emitter-independent-20261019','source.json','0fd128daf9a38d81e9a23fadf01afba295b736dcf4425e9f40487125d06802cd','files')
ci=EV/'qa-ci29-phase1-independent-20261019'
for name in ['source-authentication.json','checker-empty-mutant.py','runner-fake-mutant.py','archive-before-review.json','archive-owned-replacement-setup.json']:
    raw.add(ci/name)
for name in ['checker-empty-result.json','runner-fake-result.json','vm5-result.json']:
    result=read(ci/name);raw.add(ci/name)
    for entry in result['public_outputs']:
        target=ci/entry['public_file'];assert sha(target.read_bytes())==entry['public_sha256'];raw.add(target)
attrs=ci/'.gitattributes'
if attrs.exists():assert attrs.read_bytes().replace(b'\r\n',b'\n')==b'* -text\n'
else:attrs.write_bytes(b'* -text\n')
raw.add(attrs)
data=read(RUN/'TRAZABILIDAD.json');criteria={row['id']:{key:row[key] for key in ['fuente','seccion','problema','criterio_exacto']} for row in data['requisitos']};assert len(criteria)==106
notes={
 'R12':('La composición ec029 fue aceptada por QA: los 16 criterios originales de Chrome/HTTP/PostgreSQL29 pasan con pool real20/10 y API sin dobles; tres canarios de interferencia también pasan. Seguridad acepta31/31 controles. El cambio sigue aislado hasta cerrar CI29; no se relabelan los rojos939 ni los errores de harness como verdes.', ['qa-r12-composition29-independent-20261019/final-summary.json','security-r12-controls-independent-20261019/source.json']),
 'UX-07':('Aceptación independiente del recorrido completo16: invitación explícita, CAS, cuatro comidas, PDF exacto, exportación7, revocación y preservación de cuentas/perfiles. Semillas de menú/PDF son sintéticas; sólo se dobla correo privado local. No se acredita entrega real ni generación del worker.', ['qa-r12-composition29-independent-20261019/final-summary.json']),
 'UX-18':('Los mismos tres canarios pasan tras ec029; QA completa16/16 con PostgreSQL real y Seguridad31/31. Interferencia corregida en candidato aislado, pendiente de integrar junto con CI29. El consumidor privacy permanece dueño de sus controles.', ['qa-r12-composition29-independent-20261019/final-summary.json','security-r12-controls-independent-20261019/source.json']),
 'R13':('UX-18 aceptado de forma independiente en ec029. Nuevo emisor de revisión e8ca8be rechazado: tres expiraciones de A podían redirigir una recuperación síncrona de B;7/10 propios,11/11 autor y74/74 transporte intactos. Se conserva el rechazo y se exige nuevo fix/replay, sin integrar e8.', ['security-r12-controls-independent-20261019/source.json','security-session-emitter-independent-20261019/source.json']),
 'R31':('Exportación real de siete colecciones y conservación de perfiles aceptadas en16/16; pruebas de privacidad y controles31/31. Fences de sesión generales siguen abiertos: e8ca8be falla tres continuaciones obsoletas tras recuperar otra cuenta; no hay fuga ni envío de DTO B demostrado en ese hallazgo.', ['qa-r12-composition29-independent-20261019/final-summary.json','security-session-emitter-independent-20261019/source.json']),
 'R34':('El pool20/10 permitió E2E; no demuestra ausencia de deadlock bajo pool1. Waiter observado auth/me→subscription_guard._get_gym_plan→checkout, holder desconocido y aún sin instrumentar. Índice30/120 sigue aislado.', ['qa-r12-composition29-independent-20261019/final-summary.json']),
 'R18':('d038f1c sustituye psycopg2-binary por build de la misma versión contra libpq/OpenSSL Debian. Autor29 controles estáticos y Seguridad27/27; sólo delta de cinco fuentes aceptado para composición. No hay build/linkage/arranque ni SCA nuevo;71IDs OS y13 coincidencias CNA permanecen abiertos.', ['linux-container-libpq-sec09-prepared-20261019/evidence-manifest.json','sec09-container-static-independent-20261019/source.json']),
 'SEC09':('Preparado sourcebuild d038f1c con locks exclusivos del contenedor y pins APT; fuentes Windows/web intactas.27/27 controles independientes estáticos. Faltan firmaAPT durante build, imagen, linkage y SCA de runtime y entorno build; no se cierra vulnerabilidad por la revisión estática.', ['sec09-container-static-independent-20261019/source.json']),
 'QA11':('CI1 sigue rechazado: QA reprodujo checker vacío y runner falso aceptados por el verificador, además de sustitución Git replace-ref y omisión por atributos externos en el archivo histórico. Fix de integridad1dc separado con4 unit verdes; reparación del archivo y replay independiente pendientes. CI2 incluye recorrido real y18VM/300 ejecuciones; no Actions acreditado.', ['qa-ci29-phase1-independent-20261019/checker-empty-result.json','qa-ci29-phase1-independent-20261019/runner-fake-result.json','qa-ci29-phase1-independent-20261019/archive-before-review.json'])
}
for row in data['requisitos']:
    if row['id'] in notes:
        note,files=notes[row['id']];row['observaciones'].append('Checkpoint110: '+note)
        for name in files:
            if 'evidence/'+name not in row['evidencia']:row['evidencia'].append('evidence/'+name)
    if row['id']=='UX-18':
        row['validacion']='verificado';row['revisor']='QA:16/16 navegadorPG y3/3 canarios. Seguridad:31/31 controles, fuente ec029; integración aún pendiente.'
        row['pruebas'].append('Aceptación independiente:16/16 navegador real,3/3 mismos canarios;31/31 controles de Seguridad. No aceptación de CI29 ni del emisor e8.')
    assert {key:row[key] for key in criteria[row['id']]}==criteria[row['id']]
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write(RUN/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint110 local:106 registros y92 IDs originales; criterios exactos conservados. El original F:/MetodoBaseWeb-main permanece intacto. Rama implementation/20261018-execution, base daa25efbf51d154710bad625025b345fa9ec9252. Sin push, PR, despliegue, cargos o comunicaciones reales.

MAIN conserva esquema28 y la reparación de c4 aceptada por Seguridad: la migración no crea ni concede permisos a un rol global. Mantiene políticas, lineage, ACL previos y34 contratos. Falta reconstruir y arrancar Linux con el arreglo.

La composición R12 con ec029 pasó los16 criterios reales de Chrome/HTTP/PostgreSQL29 y los tres canarios de controles de QA. Seguridad acepta31/31. Incluye exportación de siete colecciones, revocación, PDF exacto y preservación de cuentas/perfiles. Menú/PDF son semillas sintéticas y el único doble es transporte privado de correo. Los rojos939 y los replays de harness se conservan. [Aceptación y límites](evidence/qa-r12-composition29-independent-20261019/final-summary.json).

CI29 sigue aislado y rechazado hasta reparar los bypass que QA reprodujo en checker/runner y en el archivo Git histórico. La corrección de integridad1dc tiene cuatro unit verdes; la del archivo se prepara aparte. CI2 conserva las restauraciones originales, añade el navegador real y exige18 módulos JavaScript. Los18 módulos y sus parsers pasaron300 ejecuciones;279 criterios únicos por21 escenarios heredados repetidos. No se acredita Actions ni el nuevo orquestador portátil por esos resultados.

El emisor síncrono e8ca8be no se integra: Seguridad reprodujo tres redirects obsoletos durante recuperación de otra cuenta. Sus10 controles dieron7 verdes/3 rojos;11 del autor y74 de transporte permanecen verdes. Se exige corrección posterior sobre los mismos negativos. [Rechazo](evidence/security-session-emitter-independent-20261019/source.json).

Índice30/6ea aceptado por QA120/120, aún aislado hasta29/CI. Las observaciones de51/52/51/51/51 filas pertenecen a su corpus1000; no son p95/SLO ni cota universal. El timeout pool1 sigue abierto: waiter conocido, holder desconocido. Pool20/10 sólo acredita el recorrido E2E.

Linux99c continúa rojo42501 antes de crear web. Sus173 archivos, rollback y cierre están preservados; QEMU/red/proxies/SSH cerrados y PG55484 apagado con propiedad verificada. d038f1c prepara build de psycopg2 contra librerías Debian:29 controles de autor y27 independientes estáticos aceptados. Falta imagen, firmaAPT, linkage, arranque y SCA;71 IDs OS y13 coincidencias CNA siguen abiertos. [Revisión estática](evidence/sec09-container-static-independent-20261019/source.json).

La regresión amplia aceptada sigue en a753b2c:2360 verdes y una omisión conocida Windows, serie y dos workers. No se atribuye a29/30/c4 nuevo. Scan final de secretos de la fuente actual pendiente. Desktop soportado; su bundle3.12.15 tiene93 controles independientes, sin instalación/firma ni revisión exhaustiva de DLL.

Free:10 clientes activos, un plan por cliente al día y10 planes totales por gimnasio al día. MensualesFree20/Standard100/Gym+Clínica0 ilimitado; individualStarter1/Pro5/79MXN permanece separado.

Siguiente: aceptar CI29 y componer29, luego30; reconstruir Linux y probar su arranque real. Continúan los criterios restantes de producto, privacidad y operación. No se inventan pilotos humanos ni dictámenes. [Registro completo](TRAZABILIDAD.md).
''')
write(RUN/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint110;106 registros y92 IDs originales. MAIN conserva esquema28 con reparación c4 aceptada. La composición R12 aislada con ec029 pasó16/16 criterios de navegadorPG,3/3 canarios y31/31 controles de Seguridad; CI29 aún rechaza bypass pendientes del archivo histórico. Índice30 aceptado120, todavía aislado.

El emisor e8 se rechazó por tres continuaciones obsoletas. d038 sólo tiene aceptación estática del arreglo de librerías; imagen, arranque y SCA pendientes. No entrega final ni despliegue. Free:10 clientes, un plan por cliente al día y10 planes totales por gimnasio al día; soporte desktop conservado.

Ver [estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md) y [registro](TRAZABILIDAD.md). La evidencia de fuentes anteriores no se presenta como aprobación de la versión actual.
''')
append={
 'VALIDACION.md':'QA ec029 completa16/16 Chrome/HTTP/PostgreSQL29 con pool real20/10,3/3 mismos canarios y15 UUID propios ausentes al cierre. Seguridad31/31 controles. No nuevo Node300 de QA: QA original17 reportes sumaba297 ejecuciones/276 únicos y tres canarios se repitieron aparte. Root CI2 sí ejecutó18 módulos/300 con sus parsers, evidencia aislada en preparación. La fase939 rechazada, errores de harness y replays siguen intactos. d038 sólo estática29 autor/27 Seguridad; emisor e8 rechazado7/10, autor11 ytransporte74 intactos.',
 'CAMBIOS.md':'Se preservan aceptaciones R12ec y del delta estático d038; no se integra código29/30 ni emisor en este checkpoint. Se actualiza sólo validación UX-18 respecto del candidato aceptado; criterios exactos106 intactos. CI1 tiene dos bypass de ejecutables y dos de archivo histórico reproducidos por QA; correcciones aisladas requieren replay independiente.',
 'RIESGOS.md':'CI29 no se acepta con checker vacío, runner falso, replace-ref o export-ignore que suplanten la fuente histórica. Los pins del ejecutable corrigen sólo el primer grupo; verificar árbol/blobs del archivo sigue pendiente. Emisor e8: expiración antigua puede redirigir una recuperación B síncrona; sin fuga o DTO B enviado demostrado. R34 pool1 continúa sin holder identificado. d038 estático no cierra71 IDs OS/13 coincidencias CNA, ni acredita imagen o producción.',
 'DECISIONES.md':'Se acepta el recorrido R12ec dentro de su alcance independiente, manteniendo integración condicionada a CI29 correcto. El emisor e8 permanece aislado hasta corregir los mismos tres negativos de Seguridad. Se mantienen separados evidencia estática de contenedor, build real, linkage, firmaAPT y SCA; incluir entorno build y componentes vendorizados en su análisis.'}
for name,note in append.items():
    with (RUN/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 110\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
assert {row['id']:{key:row[key] for key in criteria[row['id']]} for row in read(RUN/'TRAZABILIDAD.json')['requisitos']}==criteria
driver=EV/'checkpoint110-driver.py';receipt=EV/'checkpoint110-review.json';assert not driver.exists() and not receipt.exists()
shutil.copyfile(__file__,driver);raw.add(driver)
write(receipt,json.dumps({'base':BASE,'registry_count':106,'criteria_exact':True,'product_code_changed':False,'evidence_files':{path.relative_to(ROOT).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
docs=[(RUN/name).relative_to(ROOT).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
names=sorted(path.relative_to(ROOT).as_posix() for path in raw)
for index in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[index:index+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[index:index+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names).encode());cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name;cursor+=size+1
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert cursor==len(buffer) and changed.issubset(set(names+docs)) and set(docs).issubset(changed)
subprocess.run(['git','commit','-m','Seal independent R12 browser acceptance and bounded security reviews'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'raw_blobs_authenticated':len(names),'changed_files':len(changed),'registry':106}))
