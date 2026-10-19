"""Seal accepted30 reviews and independently confirmed component findings."""
import copy,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence'
BASE='da0357df229e534c819d8b694fe0fb6c155c31ad';TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
sha=lambda data:hashlib.sha256(data).hexdigest()
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=ROOT,**kw)
read=lambda path:json.loads(path.read_bytes())
def write(path,value):path.write_bytes(value.encode('utf8'))
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
raw=set();parent_attribute_rules=[]
def authenticate(directory,filename,digest):
    path=EV/directory/filename;assert sha(path.read_bytes())==digest,path
    entries=read(path)['files']
    if isinstance(entries,dict):entries=[{'path':name,**(detail if isinstance(detail,dict) else {'sha256':detail})} for name,detail in entries.items()]
    for entry in entries:
        name=entry.get('path',entry.get('file'));assert name
        target=ROOT/name if name.startswith('docs/') else path.parent/name
        assert target.resolve().is_relative_to(path.parent.resolve())
        data=target.read_bytes();assert sha(data)==entry.get('sha256',entry.get('raw_sha256')),target
        if 'bytes' in entry:assert len(data)==entry['bytes']
        raw.add(target)
    attrs=path.parent/'.gitattributes'
    if attrs.exists():assert attrs.read_bytes()==b'* -text\n';raw.add(attrs)
    else:parent_attribute_rules.append(directory+'/** -text\n')
    raw.add(path)
    checksum=path.parent/'manifest.sha256'
    if filename=='manifest.json' and checksum.exists():assert checksum.read_text().split()[0]==digest;raw.add(checksum)
for row in [
 ('qa-member-browser30-independent-20261019','manifest.json','e899d53dff775450af1941a56fa03f59de88156f2c0952b05ea79ff1180b8ae9'),
 ('qa-ci-history30-independent-20261019','manifest.json','c9d3f995006fe5879b4d85911e49f17fbb2fcc20eab871e5fe2576b9f530b2af'),
 ('linux-sca-native31-triage-20261019','manifest.json','0af20498c46c2dcf0b3ea5884f361f0ba4bb70b4afc4dd2aa4f687c3c1b8690a'),
 ('linux-container-runtime-installer-removal-20261019','manifest.json','1bb828b6e231c5f1b6b06a8d847b6b2f2dca8e201d132661b70de59c8de4a73d'),
 ('backend-container-installer-static-review-20261019','freeze.json','cd6cbf607fd161b253b327210b7c2d0b85c21e98eed69a79071b64a7373a3bab'),
 ('linux-container-runtime-installer-scripts-fix32-20261019','manifest.json','06244fc6d718e0bec1895321d30e8b9a067cbe8a0019c265614fdd01888f33ea'),
 ('backend-container-installer-scripts-fix-review-20261019','freeze.json','2e00f09ab242354396d906c3292e8f6989db1ecaffee429856be4c52235f66df'),
 ('security-native31-sca-independent-20261019','source.json','2a93fdbd3e62070b6ce5c918512380d676e8c2b2e43769237573422379472794')]:authenticate(*row)
parent_attrs=EV/'.gitattributes';assert not parent_attrs.exists()
parent_attrs.write_bytes(''.join(parent_attribute_rules).encode());raw.add(parent_attrs)
merge=EV/'main30-merge-20261019';merge.mkdir(exist_ok=False);(merge/'.gitattributes').write_bytes(b'* -text\n')
for path in (TEMP/'metodobase-main30-merge-20261019').iterdir():
    if path.is_file():shutil.copyfile(path,merge/path.name)
shutil.copyfile(TEMP/'metodobase-main30-merge.py',merge/'driver.py');raw.update(merge.iterdir())
data=read(RUN/'TRAZABILIDAD.json');criteria={row['id']:{key:row[key] for key in ['fuente','seccion','problema','criterio_exacto']} for row in data['requisitos']};assert len(criteria)==106 and 'SEC10' not in criteria
new=copy.deepcopy(next(row for row in data['requisitos'] if row['id']=='SEC09'))
new.update(id='SEC10',identificador_original='SEC10',seccion='Expat embebido de CPython3.12.15 y CVE-2026-77214',
 problema='La imagen99c mide pyexpat2.8.5 embebido en CPython3.12.15; el CNA primario incluye<=2.8.5 y el source exacto conserva XML_ParseBuffer sin el fix de capacidad13c5f63. Las guardas observadas de wrappers no acreditan reparar el componente ni descartar todos sus callers.',
 criterio_exacto='Conservar cadena de procedencia PSF/tag/commit/blobs y ELF por artefacto; verificar rango/fix y alcanzabilidad real sin afirmar explotación sólo por versión; aplicar una reparación mantenida y fijada al componente realmente cargado, reconstruir el artefacto, comprobar versión/parche efectivo, SBOM/SCA y regresiones de parsers/runtime con revisión independiente. No sustituir Expat embebido instalando sólo libexpat Debian ni ignorar el aviso; mantener abierto el alcance no ejecutado.',
 prioridad='P1',responsable='Operación y seguridad',tareas=['R18','R31','R21'],dependencias=['R18'],estado='en_curso',implementacion='pendiente',validacion='en_curso',despliegue='no_desplegado',entorno='local',
 cambios=['Hallazgo de componente confirmado independientemente; corrección e imagen nueva pendientes.'],commits=[BASE],
 pruebas=['6 controles estáticos propios de Seguridad;16 CNA primarios actualizados autenticados. Sin PoC, crash, VM o alcance remoto de app probado.'],
 evidencia=['evidence/linux-sca-native31-triage-20261019/manifest.json','evidence/security-native31-sca-independent-20261019/source.json'],
 documentacion=['NUEVOS_HALLAZGOS.md','SCA_COMPONENTES.md','ESTADO.md','RIESGOS.md'],
 revisor='Seguridad independiente confirma componente/procedencia y acota wrappers; no acepta explotación global ni reparación.',bloqueo=None,
 observaciones=['Checkpoint112: primer registroSEC10, sin renumerar los106 previos. La corrección necesita nuevo artefacto real; no se concede excepción de riesgo.'])
data['requisitos'].append(new)
notes={
 'R12':('Navegador current30 aceptado independientemente:50 mantenidas+22 propias+16freshreal/fixture0. CI30 aceptado74+19/full y ahora integrado en da0357; regresión amplia30 pendiente.',['qa-member-browser30-independent-20261019/final-summary.json','qa-ci-history30-independent-20261019/final-summary.json']),
 'QA11':('CI30 final aceptado:28reports/27workflow/55parser29/24parser30/27inert/76Bash/107refs,74focales y19propios; históricos exactos29→28,18targets anteriores intactos.',['qa-ci-history30-independent-20261019/final-summary.json']),
 'R05':('Esquema30/CI30 integrado,5706fuentes en la revisiónCI y5496 en navegador, cada scope exacto conservado; no relabelar regresión29 como30. Nuevo gate amplio30 preparado.',['qa-ci-history30-independent-20261019/final-summary.json']),
 'R34':('Índice30+restore30+navegador30+CI30 integrados en da0357 tras revisiones;51/52/51/51/51 filas del corpus1000 no son SLO/p95/cota universal. Pool1 holder sigue desconocido.',['main30-merge-20261019/receipt.json']),
 'R18':('Triage por componente confirmado:13 CNA OpenSSL por copia, nuevoSEC10 Expat;71 IDs OS permanecen abiertos. Rechazada exclusiónSQLite50812 por faltarv3; fix compartido/sourceDebianu2 conservan riesgo pendiente. Dockerc02 retirada installers aceptada sólo estática tras dos negativoscripts fallidosaf548 y3+6 verdes posteriores.',['security-native31-sca-independent-20261019/source.json','backend-container-installer-scripts-fix-review-20261019/freeze.json']),
 'SEC09':('Sourcebuildd038+runtimecleanupc02 preparados y aceptados sólo estáticos. pip/ensurepip podrían retirarse en imagen nueva, no se acredita eliminación real aún. No build/linkage/SCA nuevo ni cierre71IDs.',['backend-container-installer-scripts-fix-review-20261019/freeze.json','security-native31-sca-independent-20261019/source.json'])
}
for row in data['requisitos']:
    if row['id'] in notes:
        note,files=notes[row['id']];row['observaciones'].append('Checkpoint112: '+note)
        for name in files:
            if 'evidence/'+name not in row['evidencia']:row['evidencia'].append('evidence/'+name)
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
with (RUN/'NUEVOS_HALLAZGOS.md').open('ab') as stream:stream.write(('\n\n## SEC10: Expat embebido de CPython3.12.15 y CVE-2026-77214\n\n'+new['problema']+'\n\nCierre exigido: '+new['criterio_exacto']+'\n\n[Seguridad independiente](evidence/security-native31-sca-independent-20261019/source.json). Sin reparación, explotación remota o dictamen global acreditados.\n').encode())
write(RUN/'SCA_COMPONENTES.md','''# SCA por componente y artefacto

Imagen histórica99c, sin construir un sustituto en este lote. Se conservan164 entradas/71 IDs OS,811 ELF y55 paquetes PyPI con0 avisos en aquel alcance. Estos números no cubren automáticamente librerías embebidas, vendors o build.

Seguridad confirma Expat2.8.5 embebido y la cadena PSF/tag/commit/blobs: XML_ParseBuffer carece del fix13c5f63 de CVE-2026-77214. Los wrappers con buffers acotados no son reparación ni prueba de ausencia global de alcanzabilidad. Se registraSEC10; no se ejecutó PoC ni se afirmó explotación de la app.

SQLite CVE-2026-50812 permanece abierto: faltar apply_v3 no basta, pues el fix afecta sessionApplyOneOp compartido y tiene testapply_v2. FuenteDebian3.46.1-7+deb13u2/patchset/ELF fueron verificados por Seguridad sin afirmar crash/caller. Zlib85091 presenta un desajuste concreto entre rango y versión/implementación observados; no se autoriza excepción ni se cierra27171. Las13 CNA OpenSSL se evalúan por copia: cryptography4.0.3 está en el límite fijo, psycopg3.5.8 en rango y Debian3.5.7u3 tiene su backport documentado.

Dockerd038 prepara libpq de fuente; af548 prepara retirar pip/ensurepip completos. La revisión detectó scripts parent sin validar: antes1/3, c02 después3/3 y seis controles independientes adicionales. Es aceptación estática; no54 paquetes reales, linkage, SCA nuevo o arranque. Se conservan el rechazo y los freezes inmutables. Los vendors del build y wheel ensurepip se inventarían por separado, aunque no lleguen al runtime final.

[Triage](evidence/linux-sca-native31-triage-20261019/REVISION.md), [revisión independiente](evidence/security-native31-sca-independent-20261019/source.json), [fix de rutas](evidence/backend-container-installer-scripts-fix-review-20261019/review.md). Falta corregir componentes aplicables, construir y revisar el artefacto exacto antes de promoverlo.
''')
state=(RUN/'ESTADO.md').read_text(encoding='utf8').replace('Checkpoint111 local:106 registros','Checkpoint112 local:107 registros').replace('MAIN integra esquema29 en e250d56a5be5c950167b682d49991d29a8dbaa62','MAIN integra esquema30 en da0357df229e534c819d8b694fe0fb6c155c31ad')
state=state.replace('Regresión amplia de MAIN29:','Regresión amplia histórica de MAIN29 (e250, no atribuida a30):')
start=state.index('Índice30/6ea continúa aislado');end=state.index('\n\nEmisor e8+fix9eb',start)
state=state[:start]+'''Índice30, restore30, navegador30 y CI30 ya están integrados. QA índice120/120, restore1+8 propios+1 SQLite, navegador50+22 propios+16freshreal/fixture0. CI30 final74+19 propios,28reports/27workflow/55parser29/24parser30/27inert. Históricos29→28 se ejecutan con fuente Git auténtica, sin modificar los18 targets anteriores. Nuevo gate amplio sobre MAIN30 pendiente. [CI30](evidence/qa-ci-history30-independent-20261019/final-summary.json).'''+state[end:]
state=state.replace('71 IDs OS permanecen abiertos; triage de librerías y vendorizados en curso.','71 IDs OS permanecen abiertos; triage independiente sellado y nuevoSEC10 Expat registrado. SQLite50812 no se excluye por faltarv3. c02 corrige dos negativos de scripts y tiene3+6 controles independientes, sólo estáticos.')
state=state.replace('Siguiente: cerrar revisión del navegador30 y CI30, integrar30; componer R23/expiración y reconstruir Linux.','Siguiente: regresión amplia30; componer R23/expiración y reconstruir Linux. MFA31 exclusivo y R24 tienen autores aislados y contratos coordinados; ninguna migración31 está integrada.')
write(RUN/'ESTADO.md',state)
delivery=(RUN/'ENTREGA.md').read_text(encoding='utf8').replace('Checkpoint111:106 registros','Checkpoint112:107 registros').replace('MAIN esquema29, merge e250d56a5be5c950167b682d49991d29a8dbaa62','MAIN esquema30, merge da0357df229e534c819d8b694fe0fb6c155c31ad').replace('Regresión actual:2464pass+1 omisión Windows por modo','Regresión histórica29:2464pass+1 omisión Windows por modo')
delivery=delivery.replace('Índice/restore30 aceptados en sus alcances aislados; navegador30 y CI30 pendientes de aceptación/composición.','Índice/restore/navegador/CI30 aceptados e integrados; regresión amplia30 pendiente. SEC10 Expat registrado;71 IDs OS siguen abiertos. Dockerc02 sólo aceptado estático.')
write(RUN/'ENTREGA.md',delivery)
for name,note in {
 'VALIDACION.md':'QA navegador30:50unit+22propios+16freshreal/fixture0,5496fuentes/5helpers/89paquetes/157Node estables,UUID/Chrome/8798 cerrados. QA CI30:74unit+19propios/full28reports/27workflow/55+24parser/27inert/76Bash/107refs,5706fuentes estables. Merge MAIN30 conserva106criterios y18targets; amplia30 pendiente. Dockerc02 sólo estático3+6;SEC SCA6/6 y16CNA primarias, errata inicial preservada.',
 'CAMBIOS.md':'Se integra30 y CI30 con ancestry29 real. Se registraSEC10 sin renumerar106 previos; total107. Se sella aceptación independiente de navegador/CI30 y triage estático. R23/expiración,MFA31,R24 y Docker nuevos aún no integrados.',
 'RIESGOS.md':'SEC10 Expat2.8.5 embebido sincapacityfix13c5f63; no reparación ni vía remota demostrada. SQLite50812 exclusión v3 rechazada;71 OS siguen abiertos. c02 scriptsparent arreglado sólo estático; build/runtime/SCA efectivo pendiente. Pool1holder desconocido abierto. Regresión30 debe corresponder a merge actual.',
 'DECISIONES.md':'MFA31 reservado exclusivamente a backend; sin migraciones paralelas. R24 usa borrador de compra explícito en RAM, cantidades reales y consumo confirmado como hecho personal mínimo; no define plazo nuevo de conservación ni publica diario al gimnasio. Menús/sustituciones ambiguos no generan cantidades o recomendaciones ficticias. Contratos en trabajo aislado, no aceptación completa R24/R32.'}.items():
    with (RUN/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 112\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
current={row['id']:{key:row[key] for key in criteria[next(iter(criteria))]} for row in read(RUN/'TRAZABILIDAD.json')['requisitos']}
assert len(current)==107 and {key:current[key] for key in criteria}==criteria
driver=EV/'checkpoint112-driver.py';receipt=EV/'checkpoint112-review.json';assert not driver.exists() and not receipt.exists();shutil.copyfile(__file__,driver);raw.add(driver)
write(receipt,json.dumps({'base':BASE,'original_criteria_preserved':106,'registry_count':107,'new_id':'SEC10','raw_attribute_rules_added_outside_immutable_prefixes':parent_attribute_rules,'raw_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
docs=[(RUN/name).relative_to(ROOT).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md','SCA_COMPONENTES.md']]
names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
for i in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[i:i+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[i:i+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names).encode());cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);head=buffer[cursor:end].split();assert head[1]==b'blob';size=int(head[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buffer)
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert changed==set(names+docs)
subprocess.run(['git','commit','-m','Seal accepted30 composition and independent native component triage'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'raw_blobs_authenticated':len(names),'registry':107,'preserved_criteria':106}))
