"""Seal current R24/portal reviews, preserve criteria, and register the MFA alias finding."""
from pathlib import Path
import copy,hashlib,json,re,shutil,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');run=root/'docs/implementation/20261018-evolution';ev=run/'evidence';tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');base='bd3c1ca02840c90490cfa2e89b2b9fd7104e83dc'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
def write(p,s):p.write_bytes(s.encode())
assert git('rev-parse','HEAD',text=True).strip()==base and not git('status','--porcelain','--untracked-files=no')
raw=set()
def sensitive(blob):
    for m in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=m.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob))
def authenticate(prefix,name,digest):
    p=ev/prefix/name;assert sha(p.read_bytes())==digest,p
    for row in json.loads(p.read_bytes())['files']:
        q=p.parent/row.get('path',row.get('file',''));assert q.resolve().is_relative_to(p.parent.resolve());blob=q.read_bytes()
        assert sha(blob)==row['sha256'] and ('bytes' not in row or len(blob)==row['bytes']),q
        assert not sensitive(blob),q;raw.add(q)
    attrs=p.parent/'.gitattributes';assert attrs.read_bytes().replace(b'\r\n',b'\n')==b'* -text\n';raw.update([p,attrs])
authenticate('qa-r24-after-privacy-independent-20261019','manifest.json','b4eadfb70ee939a19e9b6887b8a5f635114063f685118b1cc8ffdf16b9a8b56a')
authenticate('security-sec11-independent-20261019','source.json','e48b9ca574fb818bff377fabb4ed851d3406d3a52f6f05dcfbd6beb44581cbd3')
authenticate('security-r24-private-errors-independent-20261019','source.json','4a709db44b2bd60340e339bbd0ef46da28de1fef089a324b7d267e3a7bf9414b')
dest=ev/'prepared-wave116-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
def capture(path,name,digest=None):
    blob=path.read_bytes();assert not sensitive(blob),path
    if digest:assert sha(blob)==digest
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
for p in (tmp/'metodobase-main-sec11-merge-20261019').iterdir():
    if p.is_file():capture(p,'SEC11-merge/'+p.name)
capture(tmp/'metodobase-main-sec11-merge.py','SEC11-merge/driver.py')
author=Path(r'F:\mb-mfa31-20261019\docs\implementation\20261018-evolution\evidence\backend-mfa31-author')
capture(author/'freeze.json','MFA31-author-freeze.json','59316fe16fdbc1c2ea0c7f27c3fc7ddfa667b776aaa9c4f934f746b00bdfb5b2')
capture(author/'AUTHOR_REPORT.md','MFA31-author-report.md')
capture(tmp/'metodobase-mfa31-security-independent-20261019/test_action_keys.py','SEC12-before-test.py','59f9284b5bda012c9e502ca87b3f598832a115356e6e666c16149a67841c6566')
write(dest/'SEC12-initial-observation.json',json.dumps({'source':'56e810b3a0518231ba013cab29d68ee0aba0bacd','reporter':'Independent Security agent; root read frozen driver, did not rerun it in this checkpoint','driver_sha256':'59f9284b5bda012c9e502ca87b3f598832a115356e6e666c16149a67841c6566','factory':'api.app only in original5','result':'4failures+1canonicalcontrolpass','failed_criteria':['stripealias exact keyA returns403','MPalias exactkeyA returns403','stripealias grantwithoutkey+addedheader reaches syntheticport200','MPalias grantwithoutkey+addedheader reaches syntheticport200'],'scope':'No real provider, charge, factor bypass or RBAC bypass demonstrated. Author fix in a separate worktree; final review pending.'},indent=2)+'\n')
write(dest/'manifest.json',json.dumps({'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2)+'\n');raw.update(p for p in dest.rglob('*') if p.is_file())
data=json.loads((run/'TRAZABILIDAD.json').read_bytes());keys=['fuente','seccion','problema','criterio_exacto'];old={r['id']:{k:r[k] for k in keys} for r in data['requisitos']};assert len(old)==108 and 'SEC12' not in old
new=copy.deepcopy(next(r for r in data['requisitos'] if r['id']=='SEC11'))
new.update(id='SEC12',identificador_original='SEC12',fuente='docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md',seccion='Binding de Idempotency-Key en aliases de pago del candidato MFA31',problema='Los aliases /api/pagos/stripe/session y /api/pagos/mp/preference del candidato56e810 no transmiten Idempotency-Key a step_up ni al servicio. El grant con clave exacta se rechaza y un grant sin clave acepta una cabecera nueva hasta el puerto sintético. El control de checkout canónico sí liga la clave.',criterio_exacto='Leer la misma Idempotency-Key observada por HTTP y transmitirla sin divergencia a la validación/consumo del grant y a la intención durable en ambos aliases, conservando DTO y respuesta legacy. Rechazar clave añadida, retirada o cambiada antes del puerto y sin consumo irreversible indebido; aceptar la clave exacta. Probar ambos proveedores y factories con autenticación/MFA reales y puertos sintéticos; conservar los cinco criterios independientes originales, la revisión independiente posterior y las garantías canónicas previas. No afirmar doblecargo, proveedor real ni bypass del factor.',prioridad='P1',responsable='Backend y seguridad',tareas=['R01','R32'],dependencias=['R01','R32'],estado='en_curso',implementacion='en_curso',validacion='en_curso',cambios=['Hallazgo en candidato aislado31, no en MAIN30. Backend prepara fix separado sin mutar el candidato congelado.'],commits=['56e810b3a0518231ba013cab29d68ee0aba0bacd'],pruebas=['Seguridad:5HTTP/SQLite en api.app,4rojos+1control canónico verde; driver inmutable59f928. Se requiere cobertura equivalente de web.main_web y after independiente.'],evidencia=['evidence/prepared-wave116-20261019/SEC12-initial-observation.json','evidence/prepared-wave116-20261019/SEC12-before-test.py'],documentacion=['NUEVOS_HALLAZGOS.md','ESTADO.md','RIESGOS.md'],revisor='Seguridad independiente reproduce; fix y revisión posterior pendientes.',bloqueo=None,observaciones=['Checkpoint116:109total;108criterios previos exactos. Estecommit es la preimagen aislada, no una corrección integrada.'])
data['requisitos'].append(new)
notes={
'R01':'SEC11/531 integrado por merge5949, fuentes3exactas/21pins históricos yregistro intactos. Root11+Seguridad5propios y11replay aceptan retorno/circuito/4HTTP ambosfactories, sin grantsMFA atribuidos531. NuevoSEC12aliases31 en corrección aislada.',
'SEC11':'Helper/puerto integrado5949 trasroot11+Seguridad5propios+11replay. Revisión secuencia inválidos→válidos sinreset y4HTTP. Grants con exactbody serán revisados en31; no declarados en531.',
'R24':'Integrado bd3c1ca:25fuentes exactas4042 y179RAW/proyecciones seguras; ancestryADC no incorporada por4CSRF deSSR sintético. QAfinal98+21 yfresh11R24+16R12 sobre4042,5987/89/157Node estables y4UUID cerradas. Seguridaddelta27propias+4replay, anterior25puros/18HTTP/16VM preservada. Amplia actual pendiente. Sigueparcial por sustituciones/R33/R31.',
'R12':'QA final4042 freshR12_16 verde/UUIDcerrada, evidencia por fuente exacta. Composición MAIN R24bd3 conR23/CI573 pendiente amplia actual.',
'R13':'Privacidad deerroresdiario4042 integrada enbd3; mismo4HTTP,27controles propiosSEC y94mantenidas author. QA secciónbrowser axe0/overflow0/pageErrors0, sinWCAGglobal.',
'R14':'R24 consumo explícito/publicación/listacompras integrado conCAS yrevocación. MecanismosPG sobre9bfa dosmantenidos+1concurrencia conservadosporfuente, no reatribuidos a4042/MAIN.',
'R31':'CuatroCSRF SSR sintéticosQA se conservaron privados y se publicaronproyecciones seguras nuevas; filtrorechazómanifiesto inicial antesindex. Cuatroautor se saneansóloenproyección nueva, originales/commitsintactoslocales. Política países/plazos siguependiente; no nuevaspurgas ni cierrelegal.',
'R32':'MFA31/56e810 congelado autor37fuentes/205proofs; revisiones independientes activas, UIenVM/composición. SECdetectó4rojos delbindingKeyenaliasesAPI, nuevoSEC12; backendfix separadoenpreparación. Restore31 autor1 yDDL10noequivalen aaceptación. Sin31integrado.',
'QA11':'R23+R24+SEC11 composición localactual lista para amplia serial/cov+n2shuffle; pruebas anteriores se mantienen porfuente.109registros;108criteriosprevios exactos. RecibosRAW/proyecciones autenticadosbyteporbyte.'}
refs={'R01':['evidence/security-sec11-independent-20261019/source.json'],'SEC11':['evidence/security-sec11-independent-20261019/source.json','evidence/prepared-wave116-20261019/SEC11-merge/receipt.json'],'R24':['evidence/qa-r24-after-privacy-independent-20261019/final-summary.json','evidence/security-r24-private-errors-independent-20261019/source.json','evidence/r24-main-source-integration-20261019/receipt.json','evidence/r24-author-private-projection-20261019/manifest.json'],'R31':['evidence/r24-author-private-projection-20261019/projection.json'],'R32':['evidence/prepared-wave116-20261019/MFA31-author-freeze.json','evidence/prepared-wave116-20261019/SEC12-initial-observation.json']}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint116: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        if ref not in row['evidencia']:row['evidencia'].append(ref)
    if row['id']=='SEC11':row['estado']=row['implementacion']=row['validacion']='en_revision'
    if row['id']=='R24':row['commits'].append(base);row['estado']=row['implementacion']='en_curso';row['validacion']='en_revision'
write(run/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
with (run/'NUEVOS_HALLAZGOS.md').open('ab') as stream:stream.write(('\n\n## SEC12: '+new['seccion']+'\n\n'+new['problema']+'\n\nCriterio: '+new['criterio_exacto']+'\n\nReproducción inicial independiente:4rojos+1control en api.app. Candidato31 aislado, sin proveedor/cargo real. [Recibo](evidence/prepared-wave116-20261019/SEC12-initial-observation.json).\n').encode())
write(run/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint116 local:109 registros,92 IDs originales y108 criterios previos exactos. MAINbd3c1ca02840c90490cfa2e89b2b9fd7104e83dc integra esquema30, R12, R23/expiración/CI573, SEC11 yR24 parcial. Original F:/MetodoBaseWeb-main intacto. Sin push, PR, despliegue, cargos ni comunicaciones reales.

R23 readonly yR24 están integrados tras revisión independiente. R23 sigue parcial por responsables/eventos persistidos; R24 por nuevas sustituciones/R33/R31. R24 integra25 fuentes exactamente iguales a4042; QA final98regresiones+21focales yfresh11R24+16R12 en4042, Seguridaddelta27propias+4HTTP. La fase9bfa conserva31SQLite+65VM+2PG+1canario concurrencia por fuente, sin reatribución. [QA R24](evidence/qa-r24-after-privacy-independent-20261019/final-summary.json). [Seguridad](evidence/security-r24-private-errors-independent-20261019/source.json).

La última amplia corresponde a6d4e8b4:2491pass+1 omisión Windows por modo serial/cobertura y n2/shuffle;7381 fuentes/89 paquetes quietos,pip0,cobertura0. La amplia de la composición actual está pendiente y será el siguiente gate. Targets22–30 yreparaciónc4 se conservan. [Amplia anterior](evidence/main30-regression-20261019/summary.json).

SEC11 retorno/circuito está integrado por5949:root11 ySeguridad5propios+11replay, incluidos4HTTP de ambosfactories. Sin red/cargos; el binding de grants se revisa con31 y no se atribuye al padre531. [Seguridad](evidence/security-sec11-independent-20261019/source.json).

MFA31/56e810 está congelado yaislado:autor37fuentes/205proofs, restore poblado1/1 yDDL10/10. QA/Seguridad/UI/CI31 yavisos de cambiofactor pendientes. NuevoSEC12:dos aliases de pago no transmiten Idempotency-Key;4rojos y1control independiente enapi.app. Backend prepara fix separado, conservando el driver yrequiriendoambasfactories. No31 integrado. [Preimagen](evidence/prepared-wave116-20261019/SEC12-initial-observation.json).

R24 usa nuevas proyecciones públicas autenticadas:cuatroCSRF SSR deQA quedaron privados ycuatro delautor sólo se sustituyen enla proyección. Originales ymanifiestos rechazados conservados; el patch selectivo evita traer esa ancestry aMAIN. Los dosZIP de fuente17/25entradas se revisaron yse conservan byte a byte. Ningún resultado se reescribió. [Proyección](evidence/r24-author-private-projection-20261019/projection.json).

Linux99c mantiene rojo42501 antes de web; QEMU/red/proxies/SSH yPG55484 cerrados. Docker c02 yExpatM2/7c013f tienen sólo aceptación estática; falta compilación/imports/linkage/SCA yarranqueProductionSettings/MIGRATORunset/readiness.71 IDsOS abiertos; SQLite50812 no se excluye por ausencia dev3. R34 diagnósticoholder queda encola trasla revisión actual; pool20/10 no es una solución acreditada.

Free aprobado:10clientes activos,1plan/cliente/día y10planes totales/gimnasio/día. MensualesFree20/Standard100/Gym+Clínica0 ilimitado; individualStarter1/Pro5/79MXN separado. Desktopsoportado,bundle3.12.15 con93controles independientes; instalación/firma/inventarioDLL exhaustivo pendientes.

Siguiente:amplia actual, reparar/revisarSEC12, componerMFA31/UI/CI conhistóricos intactos ydiagnosticarR34. Después reconstruirLinux enventana coordinada ycontinuar alcance restante. R25 contrato preliminar; R35 evaluación sinbeneficio medido. PolíticaR31 consultada ypendiente; no nuevaspurgas. Pilotos/dictámenes/proveedores requieren evidencia real. [Registro](TRAZABILIDAD.md).
''')
write(run/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint116:109 registros y92 IDs originales. MAINbd3c1ca02840c90490cfa2e89b2b9fd7104e83dc integra esquema30, R12, R23/expiración/CI573, SEC11 yR24 parcial tras revisiones independientes. La amplia anterior2491+1 por modo corresponde a6d4e8b4; la amplia actual está pendiente.

MFA31/56e810 sigue aislado en revisión ycomposiciónUI/CI; SEC12 registra el fallo de binding de clave enaliases legacy ysu reparación separada. ExpatM2 sólo tiene revisión estática; faltan imagen Linux reparada/arranque/SCA ysiguen71 IDsOS abiertos. Desktop soportado. Free10clientes,1plan/cliente/día y10totales/gimnasio/día.

Sin entrega final, push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md) y[registro](TRAZABILIDAD.md). La evidencia conserva su fuente yentorno.
''')
for name,note in {'VALIDACION.md':'QA4042:98/98 en424.86s,21focales,freshR24_11+R12_16;5987/89/157Node/tools/config quietos y4UUID ausentes. PG9bfa2+1concurrencia y31SQLite/65Node no se reatribuyen. SEC4042 mismo27propios4/27→27/27 y4QAHTTP; SEC5315propios+11rootreplay. Integraciónselectiva bd3:25sourcesGit exactas,179RAW autenticados,21pins esquema/c4 yregistro intactos, ancestryADC excluida. Actualamplia pendiente.','CAMBIOS.md':'SEC11 integrado5949 yR24 parcialbd3 con cabeceras privadas en todoslos errores de diario. Datos propios confirmados sobreviven revocación de fuente; nuevas escrituras se rechazan. Se registraSEC12 candidatoMFA, sin31 integrado. ProyeccionesSSR publican hashesRAW yredacciones puntuales sin modificar originales.','RIESGOS.md':'SEC12:aliases31 no ligan key observada al grant/puerto,4rojos+1control; reparación/revisión pendientes, sin bypassfactor/doblecargo demostrado. R24/R23 siguen parciales. MFA31 authorrestore no sustituye QA/Seguridad/UI/CI.71 IDsOS ypolíticaR31 pendientes.','DECISIONES.md':'Integrar25fuentesR24 mediante patch exacto en commitnuevo, conservando commitsprivadosautor yevitando ancestry que contieneCSRFsintéticos. Proyecciónnueva sustituye sólo4valoresidentificadoscon hashesRAW/públicos; ZIPs fuente se inspeccionan porentrada. No debilitar filtro ni reescribir pruebas/manifiestos cerrados. Priorizar reparaciónSEC12 P1 antes dediagnósticoR34 P2.'}.items():
    with (run/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 116\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
current={r['id']:{k:r[k] for k in keys} for r in json.loads((run/'TRAZABILIDAD.json').read_bytes())['requisitos']};assert len(current)==109 and {k:current[k] for k in old}==old
attrs=ev/'.gitattributes';assert b'checkpoint116-' not in attrs.read_bytes();attrs.write_bytes(attrs.read_bytes()+b'checkpoint116-driver.py -text\ncheckpoint116-review.json -text\n');raw.add(attrs)
driver=ev/'checkpoint116-driver.py';shutil.copyfile(__file__,driver);raw.add(driver)
receipt=ev/'checkpoint116-review.json';write(receipt,json.dumps({'base':base,'registry':109,'previous_criteria_exact':108,'new_id':'SEC12','product_changed_in_checkpoint':False,'raw_files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
names=sorted(p.relative_to(root).as_posix() for p in raw);docs=[(run/n).relative_to(root).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md']]
for i in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','--',*names[i:i+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
buf=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buf.index(b'\n',cursor);head=buf[cursor:end].split();assert head[1]==b'blob';size=int(head[2]);cursor=end+1;assert buf[cursor:cursor+size]==(root/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buf) and set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Seal independent daily plan and portal reviews; record MFA alias key binding finding'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no');print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_authenticated':len(names),'registry':109,'previous_criteria_exact':108}))
