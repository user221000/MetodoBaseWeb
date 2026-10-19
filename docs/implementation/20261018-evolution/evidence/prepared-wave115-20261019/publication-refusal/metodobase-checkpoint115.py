"""Record integrated R23 and independently reviewed preparations without closing pending work."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');run=root/'docs/implementation/20261018-evolution';ev=run/'evidence';tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
base='3643c3ee361abecba4d32ae98c1b87da99fb9d77';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
def write(path,value):path.write_bytes(value.encode())
assert git('rev-parse','HEAD',text=True).strip()==base and not git('status','--porcelain','--untracked-files=no')
raw=set()
def sensitive(blob):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=match.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob))
def authenticate(folder,name,digest):
    path=ev/folder/name;assert sha(path.read_bytes())==digest
    for row in json.loads(path.read_bytes())['files']:
        target=path.parent/row.get('path',row.get('file',''));assert target.resolve().is_relative_to(path.parent.resolve())
        blob=target.read_bytes();assert len(blob)==row['bytes'] and sha(blob)==row['sha256'],target
        assert not sensitive(blob),target;raw.add(target)
    assert (path.parent/'.gitattributes').read_bytes().replace(b'\r\n',b'\n')==b'* -text\n';raw.add(path)
authenticate('security-r24-independent-20261019','source.json','fc3928d2cb8b0f5ba376d204084aea259f379a9edb800a07f99eb0dbde9fdcb1')
authenticate('qa-r24-independent-20261019','before-fix-manifest.json','f81bfac40691bae01d2b552d46521d518b80f4f72f99838b33e36b722f2fde50')
dest=ev/'prepared-wave115-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
for name in ['metodobase-main-r23-merge-20261019','metodobase-main-r23-merge-longpaths-20261019','metodobase-main-r23-merge-complete-20261019','metodobase-main-r23-merge-finish-20261019','metodobase-portal-root-after-20261019']:
    source=tmp/name;assert source.is_dir()
    for path in source.rglob('*'):
        if not path.is_file():continue
        blob=path.read_bytes();assert not sensitive(blob),path
        target=dest/name/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
for name in ['metodobase-main-r23-merge-longpaths-20261019.py','metodobase-main-r23-merge-complete.py','metodobase-main-r23-merge-finish.py','metodobase-portal-root-after.py']:
    blob=(tmp/name).read_bytes();assert not sensitive(blob);(dest/name).write_bytes(blob)
write(dest/'scope.json',json.dumps({'R23_integrated':base,'SEC11_candidate':'5316644608a09632a9997c25d50b1da3486ffc1b','SEC11_same_independent_criteria':'11/11 after; prior8invalid failures+3valid controls, source89packages quiet; no retry/HTTP/network claim','R24_header_candidate':'4042d77b55b88fb200e7de1cbf41d75adc88d4f3','R24_header_same_QA_driver':'999f84c84996de56b2fbbc8aa66a2ed1c585f96cc686ca8cf9724d5ba35b6a22;4fail before→4pass after;94 maintained, independent final/browser pending','MFA31':'Author restore1/1+DDL10/10 complete, candidate freeze/reviews/UI still pending, not integrated','scope':'No product source changed in checkpoint. Prior broad2491 applies only to its recorded source, current composed broad pending.'},indent=2)+'\n')
write(dest/'manifest.json',json.dumps({'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2)+'\n')
raw.update(p for p in dest.rglob('*') if p.is_file())
data=json.loads((run/'TRAZABILIDAD.json').read_bytes());keys=['fuente','seccion','problema','criterio_exacto'];criteria={r['id']:{k:r[k] for k in keys} for r in data['requisitos']};assert len(criteria)==108
notes={
'R01':'SEC11 candidato531 validación anterior a circuito/puerto:root11criterios idénticos verdes, antes8rojos+3controles. Autor13secuencia sin resets. Candidato aislado, revisión Seguridad secuencia pendiente; sin red/cargos.',
'SEC11':'Candidato531 aislado pasa11criterios root inmutables y autor13secuencia; falta revisión independiente de circuito/grants e integración, sin cierre por cuerpo de servicio solamente.',
'R12':'R23/expiry/CI573 integrado por merge3643;108criterios, targets22–30 y reparaciónc4 conservados. Composición amplia actual pendiente.',
'R23':'R23/expiry/CI573 integrado3643 tras QA y Seguridad; familia readonly y hechos con fecha/fuente. Sigue parcial por responsables/eventos persistidos; no Actions/imagen/SLO.',
'QA11':'MergeR23 3643 verificado: padres/tree/108criterios y targets/c4 exactos. Se conservan intentos Windowslongpaths y comparación CRLFsource-vs-Git; configlocal core.longpaths=true sólo clon propio. Amplia actual pendiente.',
'R24':'Seguridad acotada adc+9bfa:25puros+18HTTP propios, mismoVM16 verde y3visibilidad/inercia. QA9bfa:31SQLite+65Node+2PGmantenidas+1PGpropia concurrencia;4rojos headers y98dirigidas timeout sin éxito atribuido. Fix4042 aislado:driver9994→4 y94headers verdes; QA/freshbrowser final pendientes. SustitucionesR33 no implementadas.',
'R13':'QA R24 detecta404de diario con Referrer-Policy débil;4042 extiende privacidad de familia diario y500opaco,4criterios idénticos y94headers verdes; independiente final pendiente.',
'R14':'R24 consumo desde publicación usaCAS y ownership; QA PG2+canario1 real verificaNOWAIT/revocación/snapshot. Fuente9bfa preservada; nuevo4042 sóloheaders sigue aislado.',
'R31':'Política de países/plazos aún consultada y sin respuesta; no nuevas purgas automáticas. SeguridadR24 acotada aceptada; headersfallos diario se corrigen4042 aislado. Esto no cierra conservación/borrado ni persistencia tokens.',
'R32':'MFA31 autor final:restore1/1 real poblado32tablas/25familias yDDL10/10 verdes, antiguos22–30 intactos yhelper28original conservado; candidato/revisiónQA/SEC/UI/CI31 pendientes, no integrado.'}
refs={'R01':['evidence/prepared-wave115-20261019/metodobase-portal-root-after-20261019/receipt.json'],'SEC11':['evidence/prepared-wave115-20261019/metodobase-portal-root-after-20261019/receipt.json'],'R23':['evidence/prepared-wave115-20261019/metodobase-main-r23-merge-finish-20261019/receipt.json'],'R24':['evidence/security-r24-independent-20261019/source.json','evidence/qa-r24-independent-20261019/before-fix-summary.json'],'R14':['evidence/qa-r24-independent-20261019/before-fix-summary.json'],'R31':['evidence/security-r24-independent-20261019/source.json']}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint115: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        if ref not in row['evidencia']:row['evidencia'].append(ref)
    if row['id'] in {'R12','R23','QA11'} and base not in row['commits']:row['commits'].append(base)
write(run/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write(run/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint115 local:108 registros,92 IDs originales y criterios exactos conservados. MAIN3643c3ee361abecba4d32ae98c1b87da99fb9d77 integra R23/expiración/CI sobre esquema30. Original F:/MetodoBaseWeb-main intacto. Sin push, PR, despliegue, cargos o comunicaciones reales.

R12, índice30 y restore30 están integrados tras revisiones independientes. Targets22–30 y reparaciónc4 que evita roles globales se conservan byte a byte en Git. La última regresión amplia corresponde a6d4e8b4:2491pass+1 omisión Windows por modo serial/cobertura y n2/shuffle;7381fuentes/89paquetes quietos,pip0,cobertura0. La amplia de la composición actual está pendiente. [Amplia30](evidence/main30-regression-20261019/summary.json).

R23 readonly, expiración yCI573 ya están integrados. QA CI:87mantenidas+35propias,23VM/348mínimos y8freshreal sobre573; composición previa53HTTP+50R12unit+2PG+4propias+118Node+8R23+16R12fresh. El foco768 se corrigió y aceptó con el mismo addon3/3. R23 sigue parcial por responsables/eventos persistidos. No se atribuye a Actions/imagen/SLO. [QA](evidence/qa-r23-ci-independent-20261019/final-summary.json). [Merge](evidence/prepared-wave115-20261019/metodobase-main-r23-merge-finish-20261019/receipt.json).

R24 adc+9bfa sigue aislado. Seguridad acepta alcance acotado:25puros+18HTTP propios y16VM. QA conserva31SQLite,65Node,2PGmantenidas y1canario propio de concurrencia. Cuatro404 revelaron política de referencia débil; fix4042 pasa el mismo driver4/4 y94headers/regresiones. QA repite sobre4042 y prepara11freshR24+16freshR12;98dirigidas anteriores agotaron timeout y no se cuentan como éxito. SustitucionesR33, conservaciónR31 y revisión clínica siguen pendientes. [Seguridad](evidence/security-r24-independent-20261019/source.json). [QA preimagen](evidence/qa-r24-independent-20261019/before-fix-summary.json).

SEC11 tiene candidato separado531:root conserva las mismas11pruebas, antes8rojos+3controles y después11verdes; autor13secuencia sin resets. Falta revisión independiente de circuito/grants e integración. Sólo puertos sintéticos, sin red/cargos. [Recibo](evidence/prepared-wave115-20261019/metodobase-portal-root-after-20261019/receipt.json).

MFA31/56e810b está congelado y no está integrado. El autor pasó restore poblado1/1 y DDL10/10 reales,32 tablas/25 familias. Revisión independiente de QA/Seguridad, UI, CI31, avisos de cambio de factor y composición pendientes. Cuatro UUID candidatos del antiguo fallo spawn siguen sin atribución y no se eliminan por prefijo. Las creaciones nuevas tienen recibo inmediato y ausencia posterior.

Linux99c mantiene rojo42501 antes de web; QEMU/red/proxies/SSH y PG55484 están cerrados. Reparaciones Docker c02 y ExpatM2/7c013f aceptadas sólo estáticamente:37+6 controles propios y22 replay/GPG0 para M2. Falta imagen exacta, compilación/imports/linkage/SCA y arranque ProductionSettings/MIGRATOR unset/readiness.71 IDs OS siguen abiertos. SQLite50812 no se excluye por ausencia de v3. R34: waiter conocido, holder aún desconocido.

Free aprobado:10 clientes activos,1 plan/cliente/día y10 planes totales/gimnasio/día. Mensuales Free20/Standard100/Gym+Clínica0 ilimitado; individual Starter1/Pro5/79MXN separado. Desktop soportado; bundle3.12.15 tiene93 controles independientes, sin instalación/firma ni inventario DLL exhaustivo.

Siguiente: aceptar e integrar R24 final y SEC11; ejecutar una amplia sobre su composición. Revisar MFA31 y componer UI/CI con históricos intactos. Reconstruir Linux en ventana coordinada. R25 tiene contrato preliminar; R35 evaluación inicial sin beneficio medido. Política R31 consultada y pendiente; no nuevas purgas. Pilotos, dictámenes y proveedores requieren evidencia real. [Registro](TRAZABILIDAD.md).
''')
write(run/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint115:108 registros y92 IDs originales. MAIN3643c3ee361abecba4d32ae98c1b87da99fb9d77 integra esquema30, R12, R23 readonly, expiración y CI573 tras revisiones independientes. R23 sigue parcial. La amplia anterior2491+1 por modo corresponde a su fuente6d4e8b4; la amplia actual está pendiente.

R24 final4042, SEC11/531 y MFA31/56e810b siguen aislados en revisión/composición. ExpatM2 tiene sólo revisión estática; falta artefacto Linux reparado/arranque/SCA y siguen71 IDs OS abiertos. Desktop soportado. Free10 clientes,1 plan/cliente/día y10 totales/gimnasio/día.

Sin entrega final, push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md) y [registro](TRAZABILIDAD.md). Evidencia anterior no acredita una fuente posterior.
''')
for name,note in {'VALIDACION.md':'R23 merge3643 padres/tree/108criterios/targets22–30/c4 verificados. Configlocal core.longpaths=true resuelve falsoM por ruta larga. Se conservan wrappers fallidos; comparación de sourceCRLF vs GitLF reparada comparando blobs exactos, sin normalizar RAW. SEC11root mismo11criterios verdes contra531; autor13secuencia aún requiere revisión. QA R24preimagen31SQLite+65Node+2PG+1canario y4headersrojos; fix4042 mismo4verde+94mantenidas, independiente final pendiente. SEC R24acotada25puros/18HTTP/16VM.','CAMBIOS.md':'R23/expiración/CI573 integrado3643; no nuevoDDL. Estecheckpoint sólo documentación/evidencia. R24headers4042,SEC11/531 yMFA31 no se atribuyen aMAIN.','RIESGOS.md':'R23 sigue parcial por responsables/eventos persistidos. R24errores404 requieren no-referrer, fix4042 aislado enQA;98dirigidaspreimagen timeout no pasaron. SEC11candidato pendiente revisióncircuito/grants. Restore31 autor verde no sustituye QA/Seguridad. Políticaretención pendiente y71IDsOS abiertos.','DECISIONES.md':'Se configura core.longpaths=true sólo en clon de ejecución propio para preservar rutas de prueba; workspace original no se modifica. Los RAW CRLF se autentican byte por byte y el check whitespace se limita a fuentes/documentos normalizables. No se repiten gates sin nueva preocupación ni se atribuyen a fuentes posteriores.'}.items():
    with (run/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 115\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
current=json.loads((run/'TRAZABILIDAD.json').read_bytes());assert {r['id']:{k:r[k] for k in keys} for r in current['requisitos']}==criteria
attrs=ev/'.gitattributes';assert b'checkpoint115-' not in attrs.read_bytes();attrs.write_bytes(attrs.read_bytes()+b'checkpoint115-driver.py -text\ncheckpoint115-review.json -text\n');raw.add(attrs)
driver=ev/'checkpoint115-driver.py';shutil.copyfile(__file__,driver);raw.add(driver)
receipt=ev/'checkpoint115-review.json';write(receipt,json.dumps({'base':base,'registry':108,'all_criteria_exact':True,'product_changed_in_checkpoint':False,'raw_files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
names=sorted(p.relative_to(root).as_posix() for p in raw);docs=[(run/n).relative_to(root).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for i in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','--',*names[i:i+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
buffer=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1;assert buffer[cursor:cursor+size]==(root/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buffer)
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert changed==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record integrated followup CI and independent diary and portal preparations'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no');print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_authenticated':len(names),'registry':108,'criteria_exact':108}))
