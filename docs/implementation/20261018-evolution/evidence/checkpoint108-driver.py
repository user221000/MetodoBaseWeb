"""Record closed independent reviews and native discovery; no product changes."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path('F:/MetodoBaseWeb-execution-20261018')
RUN=ROOT/'docs/implementation/20261018-evolution'
EV=RUN/'evidence'
BASE='a40d5dffe1d77760416dbe9ffaa51d3dfa6a0088'
sha=lambda data:hashlib.sha256(data).hexdigest()
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=ROOT,**kwargs)
def write(path,value):path.write_bytes(value.encode('utf8'))
def read(path):return json.loads(path.read_bytes())
assert git('rev-parse','HEAD',text=True).strip()==BASE
assert not git('status','--porcelain','--untracked-files=no')
qa=EV/'history-index30-independent-20261019'
sec=EV/'security-r12-api29-independent-20261019'
lin=EV/'linux-runtime28-native-20261019'
assert sha((qa/'final-summary.json').read_bytes())=='4610fd112f049fea094284d7b5b27d4f51ace4bc30b0f3d118df57030cd8dcd5'
assert sha((qa/'final-manifest.json').read_bytes())=='612e69277d82af9a5bcc00d97c7e9dfb0b70a5e6b8c1b9d5bcfb96d779a6f124'
assert sha((sec/'source.json').read_bytes())=='a6d30c16ab925379b09e45159760e2ce656236b8193eaa6253c1a31875bbdc72'
assert sha((lin/'native/native.json').read_bytes())=='9cbf93d511d52a80272f9d5525058062f282202934c2dc6e26aa8347d774eaec'
assert sha((lin/'native-openssl-sec09/comparison.json').read_bytes())=='6b4eee768acde03c3d30712247509a2b89c6b2769d74378e9c603afe25f1127e'
assert sha((lin/'native-openssl-sec09/evidence-manifest.json').read_bytes())=='9b35765886380a8bd9295c4d39285bdc04c16b4e2bc9bee3fd9d177850295797'
assert sha((lin/'symlink-gate/junit.xml').read_bytes())=='c64833be2a024322c503509c51c0e15ae2784a8e438851a3774a01fb6214702f'
for directory,manifest in [(qa,'final-manifest.json'),(lin/'native-openssl-sec09','evidence-manifest.json')]:
    data=read(directory/manifest)
    assert len(data['files'])==data['file_count']
    for name,detail in data['files'].items():
        blob=(directory/name).read_bytes()
        assert len(blob)==detail['bytes'] and sha(blob)==detail['sha256'],name
for name,digest in read(sec/'source.json')['published_files_sha256'].items():
    assert sha((sec/name).read_bytes())==digest,name
for name,detail in read(lin/'native/summary.json')['artifacts'].items():
    blob=(lin/'native'/name).read_bytes()
    assert len(blob)==detail['bytes'] and sha(blob)==detail['sha256'],name
raw=[]
for directory in [qa,sec,lin/'native',lin/'native-openssl-sec09',lin/'symlink-gate']:
    files=sorted(p for p in directory.rglob('*') if p.is_file())
    assert not (directory/'.gitattributes').exists()
    write(directory/'.gitattributes','* -text\n')
    raw.extend(files+[directory/'.gitattributes'])
drivers=lin/'executed-drivers'
for name in ['native_probe.py','run_native_probe.py','prepare_pytest_tools.py','prepare_symlink_gate.py','run_symlink_gate.py']:
    assert (drivers/name).is_file()
    raw.append(drivers/name)
assert sha((drivers/'native_probe.py').read_bytes())==read(lin/'native/summary.json')['probe_sha256']
assert not (drivers/'.gitattributes').exists()
write(drivers/'.gitattributes','* -text\n');raw.append(drivers/'.gitattributes')
data=read(RUN/'TRAZABILIDAD.json')
old={r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in data['requisitos']}
assert len(old)==104 and 'SEC09' not in old
notes={
 'R12':('API72 y composición939 aceptados por seguridad sólo en el alcance API/errores:40 HTTP propios (20SQLite/20PG restringido),1 guard de origen y26 controles finales. Se conservan500,429/503 y correlación rojos previos. Raíz148/148 focal verde; QA independiente de restore/HTTP/UI29 sigue en curso; no integración29.', ['security-r12-api29-independent-20261019/source.json']),
 'UX-07':('Los tres consumidores y exportación de siete colecciones están compuestos aisladamente en939. Falta completar QA de recorridos reales, restauración y navegador sin dobles de API; no se acredita entrega de correo real.', ['security-r12-api29-independent-20261019/source.json']),
 'R34':('QA independiente acepta30/6ea:112 regresiones en una ejecución verde más8 propias,120/120 sin omisiones. Verifica índices físicos, drift, rollback con filasR12 y lectura mixta con NULL. Observaciones de trabajo51/52/51/51/51 limitadas al corpus1000, sin mejora HTTP/p95/SLO demostrada. Sigue aislado hasta29/CI.', ['history-index30-independent-20261019/final-summary.json']),
 'R18':('Inventario real de imagen99c:811ELF/87paquetesOS; psycopg2-binary carga OpenSSL3.5.8 vendorizado. Trece registros CNA primarios incluyen esa versión en rango afectado:SEC09 abierto, alcanzabilidad pendiente. No sumar con71IDsOS ni atribuirlos a PyPI55/OSV0. Linuxsí disponible medianteQEMU; falta corregir componentes y validar startup/regresión.', ['linux-runtime28-native-20261019/native/summary.json','linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json']),
 'SEC08':('Inventario nativo completo de imagen99c distingue OpenSSL Debian/_ssl, cryptography4.0.3 ypsyco3.5.8. Se abreSEC09 separado para componente vendorizado; los backports Debian no actualizan ese ELF.', ['linux-runtime28-native-20261019/native/native.json','linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json']),
 'QA-10':('El inventario nativo detecta superficie fuera de la SCA de distribucionesPyPI;SEC09 requiere corrección y nueva evidencia por artefacto. Gate realLinuxsymlink1/1 sin skip; no startup ni suiteLinux completa.', ['linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json','linux-runtime28-native-20261019/symlink-gate/summary.json']),
 'OPS07':('Imagen99c conserva71IDsOS abiertos y nueva coincidencia por versión de OpenSSL vendorizadoSEC09. No excepción ni imagen corregida. Gate realLinux de symlink1/1; runtime falló42501 al crear rolglobal histórico y se conserva antes de corregir.', ['linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json','linux-runtime28-native-20261019/symlink-gate/summary.json']),
 'R07':('GateLinux realtest_symlink_cannot_redirect_a_private_document:1/1 sin skip contra dos módulos exactos en imagen99c, con --noconftest para excluir fixtureglobalDB ajena al unit. No representa arranquePG ni revisión de permisos de toda la imagen.', ['linux-runtime28-native-20261019/symlink-gate/summary.json']),
 'R03':('EnsayoLinux conSettingsproduction y migratorNOSUPER/NOCREATEROLE encuentra fallo real42501:revisiónc4 intentaCREATEROLEmetodobase_app en instancia fresca. Rollback sin tablas/alembic/rolglobal; producto sinstartup aceptado. Backend prepara delta mínimo sin elevar permisos ni precrear rol para ocultarlo.', ['linux-runtime28-native-20261019/native/summary.json']),
 'OPS01':('Nuevo ensayoLinux descubre dependencia histórica no autorizada deCREATEROLE. Corrección y regresión con migrador restringido/globalroleausente en preparación; no basta el ensayo previo con administradorPG.', ['linux-runtime28-native-20261019/native/summary.json'])
}
for row in data['requisitos']:
    if row['id'] in notes:
        text,files=notes[row['id']]
        row['observaciones'].append('Checkpoint108: '+text)
        for name in files:
            value='evidence/'+name
            if value not in row['evidencia']:row['evidencia'].append(value)
    if row['id']=='R18':row['bloqueo']=None
    assert {k:row[k] for k in old[row['id']]}==old[row['id']]
data['requisitos'].append({
 'id':'SEC09','identificador_original':'SEC09','fuente':'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md',
 'seccion':'OpenSSL vendorizado de psycopg2 fuera de la cobertura Debian y PyPI',
 'problema':'La imagen99c carga libssl/libcryptoOpenSSL3.5.8 del wheelpsycopg2-binary;trece registros CNA primarios incluyen esa versión en el rango3.5.0 a anterior3.5.9. Los backports Debian y OSV de distribucionesPyPI no cubren ese binario.',
 'criterio_exacto':'Preservar inventario ELF y avisos primarios por componente/artefacto; evaluar condiciones y alcanzabilidad sin afirmar explotación sólo por versión; corregir la biblioteca efectiva desde fuente mantenida con procedencia y hashes fijados, sin ignorar avisos ni alterar locksdesktop arbitrariamente; reconstruir imagen, comprobar enlaces/versiones/SBOM/SCA y regresiones PostgreSQL/runtime bajo rol restringido, con revisión independiente. Mantener separados los identificadores de componentes Debian y vendorizados.',
 'prioridad':'P1','responsable':'Operación y seguridad','tareas':['R18','R31','R21'],'dependencias':[],
 'estado':'en_curso','implementacion':'en_curso','validacion':'en_curso','despliegue':'no_desplegado','entorno':'local',
 'cambios':[],'commits':[],
 'pruebas':['Inventario nativo real imagen99c:811ELF/87paquetesOS;13JSONCNA verificados y comparación reproducible. Sin exploit ni corrección aceptada.'],
 'evidencia':['evidence/linux-runtime28-native-20261019/native/native.json','evidence/linux-runtime28-native-20261019/native-openssl-sec09/comparison.json','evidence/linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json'],
 'documentacion':['NUEVOS_HALLAZGOS.md','RIESGOS.md','VALIDACION.md'],
 'revisor':'Coordinación autentica evidencia; revisión independiente de corrección pendiente.','bloqueo':None,
 'observaciones':['No equivale a13 rutas explotables ni se suma aritméticamente a71identificadoresOS. PyPI55/OSV0 conserva su alcance propio.']})
assert len(data['requisitos'])==105
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
with (RUN/'NUEVOS_HALLAZGOS.md').open('ab') as stream:stream.write(('''
## SEC09 — OpenSSL vendorizado de psycopg2 fuera de la cobertura Debian y PyPI

La imagen `99c846bd28b0` carga OpenSSL 3.5.8 del wheel psycopg2-binary, separado de `_ssl` Debian con backports y de cryptography 4.0.3. Trece [registros primarios CNA](evidence/linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json) incluyen 3.5.8 en su rango afectado. El [inventario ELF](evidence/linux-runtime28-native-20261019/native/native.json) identifica rutas, hashes y enlaces efectivos. No se ha demostrado explotación; condiciones de API, protocolo, arquitectura y compilación requieren evaluación por aviso. Los 71 IDs OS y el resultado OSV de 55 distribuciones PyPI mantienen su alcance separado.

Cierre: corregir el componente efectivo con procedencia fijada; reconstruir, inventariar y revisar SBOM/SCA, PostgreSQL y arranque con rol restringido, con aceptación independiente. No hay excepción de riesgo ni imagen corregida aceptada. Responsable: operación y seguridad. Estado: en curso; ver registro SEC09.
''').encode('utf8'))
write(RUN/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint 108: implementación local en curso; 105 registros, con los 92 IDs originales y los criterios de los 104 registros anteriores intactos. Se añade SEC09. Original F:/MetodoBaseWeb-main conservado. Rama implementation/20261018-execution en F:/MetodoBaseWeb-execution-20261018, base daa25efbf51d154710bad625025b345fa9ec9252. Sin push, PR, despliegue, cargos o comunicaciones reales.

MAIN continúa en esquema 28 con recuperación, historial paginado y landing. Regresión amplia independiente en a753b2c: 2360 pruebas aprobadas y una omisión conocida de Windows, tanto en serie como n2 mezclado. Esa ejecución no acredita esquema29/30 ni arranque Linux. CI52af400 y correcciones Docker hasta66d9dec integrados. [Validación](VALIDACION.md), [registro](TRAZABILIDAD.md).

R12 está compuesto en la rama aislada9397569: núcleoV2, casts29 para restore, API y tres consumidores, exportación de siete colecciones y CAS de publicación por ID y versión. Seguridad acepta41 controles API propios y26 finales de cabeceras/correlación, con fallos previos preservados. Focal raíz148/148 verde; QA de HTTP, restauración poblada y navegador real sigue en curso. Aún falta CI29, aceptación completa e integración. [Revisión](evidence/security-r12-api29-independent-20261019/source.json).

R34: índice30 y lector mixto fechado/NULL en6ea19e6 aceptados por QA independiente:112 regresiones en una ejecución verde más8 propias,120/120 sin omisiones. Incluye drift físico y rollback con filasR12. En corpus1000 se observaron51/52/51/51/51 filas según cursor; no acredita p95/SLO ni límite universal del planificador. Sigue aislado hasta completar29 y CI. [Aceptación](evidence/history-index30-independent-20261019/final-summary.json).

Linux: imagen99c de fuentebc365c1, QEMU propio2vCPU/2GiB. Python3.12.15/pip26.2.1;55PyPI conOSV0 y87OS con164 entradas/71 IDs abiertos. Inventario real811ELF descubre OpenSSL3.5.8 de psycopg2-binary:13 registros CNA coinciden por versión, SEC09 abierto, alcanzabilidad pendiente. Debian con backports no actualiza ese ELF. GateLinux real de symlink1/1 sin skip. El migrador conSettingsproduction falló42501 al intentar crear el rol global histórico; rollback completo, sin startup aceptado. Se prepara corrección sin ampliar privilegios. [Inventario](evidence/linux-runtime28-native-20261019/native/summary.json), [SEC09](evidence/linux-runtime28-native-20261019/native-openssl-sec09/README.md).

Desktop soportado: artefactos66d9dec con Python3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3. QA aceptó93 controles del bundle/ZIP/payload Inno y1215 archivos exactos. ZIP4966896c/Setup5651f418 preservados fuera deGit; sin ejecutar instalador, upgrade, uninstall, firma o revisión exhaustiva de DLL. [Aceptación](evidence/desktop31215-independent-20261019/final-summary.json).

Free confirmado:10 clientes activos,1 plan por cliente al día y10 planes totales diarios por gimnasio. Mensuales existentes Free20/Standard100/Gym+Clínica0 ilimitado; individual Starter1/Pro5 y79MXN separado. Sin inventar impuestos, gracia, dispositivos, retención o precios.

PGQA17.11 loopback55483 mantiene sus recursos previos sin mutación ajena. NuevoPG55484 aisladoSCRAM propio sirve para reproducir el fallo de bootstrap; su cierre se verifica por propiedad. R21 cubre fuente41708e5/3028 archivos, no el scan exacto final pendiente. Continúan los demás criterios del registro y los dictámenes/pilotos humanos sin inventar validación.

Siguiente: completar QA y CI29; integrar29 y después30 aceptado; corregir bootstrap y componente nativo Linux, reconstruir y verificar runtime; continuar los demás criterios de producto, privacidad y operación. Cada hito conserva fuente, entorno y límites propios.
''')
write(RUN/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint108 local, sin despliegue. MAIN permanece en esquema28;105 registros,92 IDs originales preservados. No es entrega final de todo el alcance.

La regresión amplia aceptada sigue siendo2360 verdes/1 omisiónWindows en a753b2c, serie y n2. Desktop3.12.15 tiene93 controles independientes de bundle/payload aceptados, sin instalación ni firma. R12/9397569 tiene revisión de seguridad41+26 controles y focal raíz148 verdes; faltan QA de restore/HTTP/navegador real, CI29 e integración. Índice30/6ea19e6 tiene120 controles independientes verdes, aislado hasta29/CI.

Imagen Linux99c conserva71 IDsOS abiertos y el hallazgo SEC09 sobreOpenSSL3.5.8 vendorizado. El gate symlinkLinux pasa1/1; el arranque de producto no se acepta: migración histórica falla42501 bajo migradorNOCREATEROLE. Se conserva rollback y se prepara corrección sin elevar permisos. No hay excepción de riesgo.

Free:10 clientes,1 plan por cliente/día y10 planes totales/gym/día; desktop conservado. Ver [estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md) y [registro](TRAZABILIDAD.md). Los bloqueos técnicos y validaciones externas restantes no se presentan como resueltos.
''')
append={
 'VALIDACION.md':'''Checkpoint108 autentica QA30:120/120 verdes,14UUID cerrados,4580fuentes+7helpers/89paquetes estables. SeguridadR12:41 controlesAPI propios y26 finales,4933fuentes finales estables,UUID cerrado; los rojos de cabeceras y correlación permanecen. No agrega esos resultados como una ejecución única ni acredita restore/UI. InventarioLinux811ELF,13CNA primarios y symlink1/1 se guardan por fase; runtime42501 sigue fallido. El empaquetado verifica cada manifiesto y cada blobRAW contra Git; los informes públicos saneados conservan esa clasificación original.''',
 'CAMBIOS.md':'''Checkpoint108 sólo incorpora evidencia/documentación: aceptación independiente del índice30 aún aislado; revisión API29 y reparaciones de cabeceras/correlación en939 aún aisladas; inventario nativo y gate symlink de imagen99c. Nuevo SEC09 sobreOpenSSL vendorizado. No cambia producto enMAIN. Se registra el fallo real debootstrapCREATEROLE sin reinterpretar los ensayos anteriores con administrador.''',
 'RIESGOS.md':'''SEC09/P1, operación y seguridad: OpenSSL3.5.8 depsycopg2-binary coincide con13 rangosCNA; Debianpatch no lo cubre. Impacto condicionado por API/protocolo/arquitectura/compilación, explotación no demostrada. Mitigación en curso: componente mantenido con procedencia y reconstrucción/SCA/regresión independiente; no excepción. R03/OPS01:bootstrap histórico exigeCREATEROLE pese a contrato migradorrestringido; reproducciónLinux42501 y rollback completo. Se corrige código, sin elevar permisos. R18 ya dispone LinuxQEMU operativo: se elimina el bloqueo obsoleto de falta dehost; quedan componentes/startup y gateOS abiertos.''',
 'DECISIONES.md':'''Checkpoint108 mantiene esquema28MAIN hasta cerrar composición29 y después30. Se acepta30 sólo en alcance índice/lector/migración120, sin SLO. Se acepta seguridadAPI939 sólo en alcance41+26; no sustituyeQA deUI/restore. SEC09 exige evaluar/corregir el ELF efectivo, separado deOS/PyPI. El falloCREATEROLE se corregirá en producto; no se precreará rol ni ampliará el migrador para ocultarlo. Se preserva soporte desktop y decisiones comercialesFree ya respondidas.'''
}
for name,text in append.items():
    with (RUN/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 108\n\n'+text+'\n').encode('utf8'))
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
assert {r['id']:{k:r[k] for k in old[r['id']]} for r in read(RUN/'TRAZABILIDAD.json')['requisitos'] if r['id'] in old}==old
proof=EV/'checkpoint108-review.json';driver=EV/'checkpoint108-driver.py'
assert not proof.exists() and not driver.exists()
shutil.copyfile(__file__,driver)
raw.append(driver)
write(proof,json.dumps({'base':BASE,'new_registry_id':'SEC09','registry_count':105,'prior104_exact_criteria_preserved':True,'product_changes':False,'public_review_artifacts_keep_original_RAW_or_sanitized_classification':True,'closed_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in raw}},ensure_ascii=False,indent=2)+'\n')
raw.append(proof)
docs=[(RUN/name).relative_to(ROOT).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md']]
names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
for index in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[index:index+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[index:index+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
assert not git('diff','--cached','--check','--',*docs,stderr=subprocess.STDOUT)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names).encode())
cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);parts=buffer[cursor:end].split();assert parts[1]==b'blob'
    size=int(parts[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name
    cursor+=size+1
assert cursor==len(buffer)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','commit','-m','Record independent R12 and index30 reviews plus native OpenSSL discovery'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'proof_blobs_byte_identical':len(names),'prose_docs':len(docs),'registry':105,'product_changes':False}))
