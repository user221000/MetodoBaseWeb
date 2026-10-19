"""Seal merged29 regression and independent bounded acceptances without changing criteria."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence'
BASE='e250d56a5be5c950167b682d49991d29a8dbaa62';TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
sha=lambda value:hashlib.sha256(value).hexdigest()
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=ROOT,**kw)
read=lambda path:json.loads(path.read_bytes())
def write(path,value):path.write_bytes(value.encode('utf8'))
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
raw=set()
def authenticate(directory,filename,digest,key):
    path=EV/directory/filename;assert sha(path.read_bytes())==digest,path
    entries=read(path)[key]
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
authenticate('qa-ci29-phase1-independent-20261019','final-manifest.json','a8a60638564be49f6403af5fcf3e833c6087e7dfa46df42f78180b40e076007c','files')
authenticate('qa-history30-restore-independent-20261019','final-manifest.json','9c61cb6c7274ca332155289a4fd88449aecdc36630aa42ee8809ab58f8e9b67c','files')
authenticate('security-session-expiry-independent-20261019','source.json','16de663f9d5643e461582944af0e281b5a027d1f7b1c1a9baf221b420e4c9341','files')
authenticate('security-r23-followup-independent-20261019','source.json','321630b4390fc2e5bb0ef2134d9230acdd1931964d0e9d0d2662e07876287d93','files')
reg=TEMP/'metodobase-main29-regression-first-20261019';summary=read(reg/'summary.private.json')
assert summary['head']==BASE and summary['sources_packages_stable'] and summary['coverage_exit']==summary['pip_exit']==0
assert len(summary['results'])==2
for result in summary['results']:
    assert result['exit']==0 and result['cases']==2465 and not result['failures'] and len(result['skips'])==1
    assert result['skips'][0]['case']=='test_symlink_cannot_redirect_a_private_document'
dest=EV/'main29-regression-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
allow=['before.json','after.json','before-pip.log','after-pip.log','serial.xml','shuffle.xml','serial-summary.json','shuffle-summary.json','coverage.xml','coverage.json','coverage-check.stdout.log','coverage-check.stderr.log']
secret=re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+')
classification=[]
for name in allow+['serial.stdout.private.log','serial.stderr.private.log','shuffle.stdout.private.log','shuffle.stderr.private.log']:
    source=reg/name;blob=source.read_bytes();matches=list(secret.finditer(blob))
    classification.append({'file':name,'bytes':len(blob),'sha256':sha(blob),'credential_pattern_matches':len(matches),'published':not matches})
    if not matches:shutil.copyfile(source,dest/name.replace('.private',''))
write(dest/'summary.json',json.dumps(summary,indent=2)+'\n');write(dest/'publication-classification.json',json.dumps(classification,indent=2)+'\n')
shutil.copyfile(TEMP/'metodobase-main29-regression.py',dest/'driver.py')
merge=EV/'main29-merge-20261019';merge.mkdir(exist_ok=False);(merge/'.gitattributes').write_bytes(b'* -text\n')
for source in sorted((TEMP/'metodobase-main29-merge-20261019').iterdir()):
    if source.is_file():assert not secret.search(source.read_bytes());shutil.copyfile(source,merge/source.name)
shutil.copyfile(TEMP/'metodobase-main29-merge.py',merge/'driver.py')
for directory in [dest,merge]:
    files={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(directory.iterdir()) if p.is_file()}
    write(directory/'manifest.json',json.dumps({'files':files},indent=2)+'\n');raw.update(directory.iterdir())
data=read(RUN/'TRAZABILIDAD.json');criteria={row['id']:{key:row[key] for key in ['fuente','seccion','problema','criterio_exacto']} for row in data['requisitos']};assert len(criteria)==106
notes={
 'R12':('R12/ec029 y CI29/fd63620 integrados en e250. QA independiente acepta recorrido16/16, controles y CI completo sin los bypass anteriores; regresión actual29:2464 verdes+1 omisión Windows en serie/cobertura y n2/orden aleatorio.30 aún aislado.',['main29-merge-20261019/manifest.json','main29-regression-20261019/summary.json','qa-ci29-phase1-independent-20261019/final-summary.json']),
 'UX-07':('Vínculo/publicación/exportación7 y preservación de perfiles de ec029 integrados; evidencia real16/16 pertenece a esa fuente29. Nueva adaptación30 requiere revisión independiente.',['main29-merge-20261019/manifest.json']),
 'UX-18':('Corrección de propiedad de controles ec029 integrada;16/16 recorrido,3/3 canarios y31/31 Seguridad preservados.',['main29-merge-20261019/manifest.json']),
 'QA11':('CI29 aceptado independientemente: fixes de trust/archivo/composición con268 archivos autenticados. Verificador histórico exacto rechaza suplantación de checker/runner, replace-ref y omisiones de archivo. Sin Actions ni nuevo Chrome independiente del manager.',['qa-ci29-phase1-independent-20261019/final-summary.json']),
 'R05':('MAIN29 actual:2464pass+1skip Windows en cada modo serial/cobertura y n2 shuffle. Los55 canarios de reports,27 probes inertes y26 reports de CI29 son evidencia local separada, no servicios reales.',['main29-regression-20261019/summary.json','qa-ci29-phase1-independent-20261019/final-summary.json']),
 'R34':('Índice30 sigue aislado; restore30 aceptado por QA:1 nodo,8 controles propios y1 focal SQLite. R34 pool1 mantiene holder desconocido. No SLO por los resultados funcionales.',['qa-history30-restore-independent-20261019/final-summary.json']),
 'R08':('Restore30 aislado preserva48 assertions anteriores+13 nuevas; QA real1/1+8canarios,2 UUID eliminados/ausencia comprobada. No restore de producción ni imagen30.',['qa-history30-restore-independent-20261019/final-summary.json']),
 'R13':('e8+9eb corrige las mismas tres expiraciones obsoletas de sesión; Seguridad acepta102/102 focales. Sigue aislado y requiere composición. El rechazo e8 queda intacto.',['security-session-expiry-independent-20261019/source.json']),
 'R31':('Emisor+fix9eb aceptado focal por Seguridad102/102; aislado. R23 readonly aceptado acotado sin nuevos datos sensibles; faltan criterios de privacidad generales.',['security-session-expiry-independent-20261019/source.json','security-r23-followup-independent-20261019/source.json']),
 'R23':('Dashboard readonly bcd aceptado por Seguridad20 controles propios+20VM autor, condicionado a fix de expiración9eb. Aislado: sin responsables persistidos, eventos atribuibles ni resultados clínicos/causales inventados; R23 parcial.',['security-r23-followup-independent-20261019/source.json'])
}
for row in data['requisitos']:
    if row['id'] in notes:
        note,files=notes[row['id']];row['observaciones'].append('Checkpoint111: '+note)
        for name in files:
            if 'evidence/'+name not in row['evidencia']:row['evidencia'].append('evidence/'+name)
    if row['id']=='UX-18':
        row['estado']=row['implementacion']=row['validacion']='verificado';row['commits'].append(BASE)
        row['revisor']='QA16/16+3canarios y Seguridad31/31, fuente ec029 integrada en e250; local.'
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write(RUN/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint111 local:106 registros,92 IDs originales y criterios exactos conservados. MAIN integra esquema29 en e250d56a5be5c950167b682d49991d29a8dbaa62, con ancestry real fd63620 y reparación c4 que no crea/concede un rol global. Original F:/MetodoBaseWeb-main intacto. Sin push, PR, despliegue, cargos o comunicaciones reales.

R12/ec029 está integrado: QA16/16 Chrome/HTTP/PostgreSQL29,3 canarios y Seguridad31/31. Exportación7, CAS, revocación y perfiles conservados. Menú/PDF son semillas sintéticas; correo sólo transporte privado de prueba. CI29 fue aceptado independientemente tras reparar checker/runner y archivo histórico;268 archivos finales autenticados. Conserva los rechazos y controles anteriores. [QA CI29](evidence/qa-ci29-phase1-independent-20261019/final-summary.json).

Regresión amplia de MAIN29:2464pass+1 omisión conocida por permisos symlink de Windows en cada modo serial/cobertura y dos workers con shuffle. Cobertura de los tres módulos exigidos:100% líneas/ramas y gate aprobado.6087 archivos y89 paquetes estables; pip check0. No se atribuye a30, Linux ni Actions. [Evidencia](evidence/main29-regression-20261019/summary.json).

Índice30/6ea continúa aislado con QA120/120 previo. El restore30 y target histórico29 tienen aceptación independiente:1 restore PG,8 canarios y1 SQLite focal,48 asserts anteriores+13 preservados y dos UUID ausentes. Root ejecutó además el guard29 y restore29 sin cambios desde su archivo Git exacto bajo composición30. Navegador30 del autor:16/16 y finalizador0; primer rechazo y corrección de semilla conservados, revisión independiente en curso. CI30 pendiente.

Emisor e8+fix9eb aceptados focalmente por Seguridad102/102, todavía aislados. R23 readonly aceptado acotado20 controles propios+20VM; faltan responsables persistidos/eventos atribuibles y composición. No se cierra R23 por una pantalla. [Seguridad](evidence/security-r23-followup-independent-20261019/source.json).

Linux99c conserva rojo42501 antes de web. QEMU, red/proxies/SSH y PG55484 están cerrados. d038 sourcebuild/libpq tiene revisión estática29 autor/27 Seguridad; af548 añade retirada de pip/ensurepip, aún sin build real.71 IDs OS permanecen abiertos; triage de librerías y vendorizados en curso. Falta imagen exacta, linkage, SCA runtime/build y arranque ProductionSettings/MIGRATOR unset/readiness. R34 pool1: waiter conocido, holder aún desconocido; pool20/10 no cierra ese riesgo.

Free:10 clientes activos,1 plan por cliente/día y10 planes totales por gimnasio/día. Mensuales Free20/Standard100/Gym+Clínica0 ilimitado; individualStarter1/Pro5/79MXN separado. Desktop soportado; bundle3.12.15 tiene93 controles independientes, sin instalación/firma ni examen exhaustivo de DLL.

Siguiente: cerrar revisión del navegador30 y CI30, integrar30; componer R23/expiración y reconstruir Linux. Continúa el alcance restante de producto/privacidad/operación; pilotos humanos y dictámenes requieren evidencia real. [Registro](TRAZABILIDAD.md).
''')
write(RUN/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint111:106 registros y92 IDs originales. MAIN esquema29, merge e250d56a5be5c950167b682d49991d29a8dbaa62. R12 y CI29 integrados tras QA/Seguridad independientes. Regresión actual:2464pass+1 omisión Windows por modo, serial/cobertura y n2 shuffle; gate de cobertura aprobado.

Índice/restore30 aceptados en sus alcances aislados; navegador30 y CI30 pendientes de aceptación/composición. R23 y fix de expiración tienen aceptación focal aislada, R23 parcial. Linux sigue pendiente de imagen/arranque/SCA; no entrega final ni despliegue. Desktop soportado. Free10 clientes,1 plan/cliente/día y10 totales/gimnasio/día.

Ver [estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md) y [registro](TRAZABILIDAD.md). Evidencia anterior no acredita una fuente posterior.
''')
for name,note in {
 'VALIDACION.md':'MAIN29 e250:2464pass+1skip Windows conocido en serial/cobertura(686.25s) y n2/shuffle(284.328s);6087 fuentes/89 paquetes estables,pip0. Gate tres módulos100% líneas/ramas. CI29 QA final268 archivos autenticados, aceptación acotada local. Restore30 QA1+8 propios+1 SQLite; no Chrome/Actions/SLO por esos resultados.',
 'CAMBIOS.md':'Se integra29/CI29 con ancestry fd real, los16 targets históricos antiguos y c4 conservados. Se sella regresión de la misma fuente integrada. UX-18 pasa a verificado local tras integración y revisiones;106 criterios exactos intactos.30/R23/emisor/Docker nuevos siguen aislados.',
 'RIESGOS.md':'Los bypass CI29 anteriores están corregidos y aceptados independientemente; rechazos conservados. CI30 aún pendiente. e8+9eb tiene aceptación focal, no composición. R23 parcial y readonly. Linux imagen/SCA/ProductionSettings/readiness pendiente; no inferir cierre71IDs de triage estático. Pool1 holder desconocido sigue abierto.',
 'DECISIONES.md':'Integrar29/CI aceptado preservando su commit real como ancestor para archivar el runtime histórico sin falsear markers. Conservar restore29 exacto bajo30 y añadir restore30 en lugar de reemplazar assertions. Evidencia RAW no se normaliza; fuente/prosa usa representación Git LF documentada.'}.items():
    with (RUN/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 111\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
assert {row['id']:{key:row[key] for key in criteria[row['id']]} for row in read(RUN/'TRAZABILIDAD.json')['requisitos']}==criteria
driver=EV/'checkpoint111-driver.py';receipt=EV/'checkpoint111-review.json';assert not driver.exists() and not receipt.exists()
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
subprocess.run(['git','commit','-m','Integrate schema29 evidence and seal current serial and parallel regression'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'raw_blobs_authenticated':len(names),'changed_files':len(changed),'registry':106,'broad_per_mode':2464,'known_windows_skip_per_mode':1}))
