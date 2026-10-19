"""Record the composed broad gate and the independently reproduced MFA parent condition."""
from pathlib import Path
import copy,hashlib,json,re,shutil,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');run=root/'docs/implementation/20261018-evolution';ev=run/'evidence';tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');base='eea8f773fba9b7f92241958139fcefa23b9ee1d4';sha=lambda b:hashlib.sha256(b).hexdigest()
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
    p=ev/prefix/name;assert sha(p.read_bytes())==digest,p;rows=json.loads(p.read_bytes())['files']
    if isinstance(rows,dict):rows=[{'path':name,**meta} for name,meta in rows.items()]
    for row in rows:
        q=p.parent/row.get('path',row.get('file',''));assert q.resolve().is_relative_to(p.parent.resolve());blob=q.read_bytes()
        assert sha(blob)==row['sha256'] and ('bytes' not in row or len(blob)==row['bytes']),q
        assert not sensitive(blob),q;raw.add(q)
    attrs=p.parent/'.gitattributes';assert attrs.read_bytes().replace(b'\r\n',b'\n')==b'* -text\n';raw.update([p,attrs])
authenticate('main-r23-r24-regression-20261019','manifest.json','7d6a1ef7ba7204ebfa3ff5ebf4f88efa4409f3d1d43023239006626e07bf61d7')
authenticate('mfa31-composition-prepared-20261019','manifest.json','8907854972a553581c03ceb124b55247131f826d8ab9b2abc49e9483b10798d9')
authenticate('mfa31-ci-baseline-prepared-20261019','manifest.json','ff51dd8d5e1b7e1b0033ecb6f2f6b7a10e1dd100d7087e98fe5a822d2c6e9624')
authenticate('security-mfa31-initial-independent-20261019','source.json','adfd99dbb69d6ddc82d778f4ac8972e7af9efe6deb60def31a5a7cc61b17b07c')
dest=ev/'prepared-wave117-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
def capture(path,name,digest=None):
    blob=path.read_bytes();assert not sensitive(blob),path
    if digest:assert sha(blob)==digest
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
capture(tmp/'metodobase-mfa31-security-full-20261019/test_parent_scope.py','SEC13-before-test.py','4d0d35179c3ef1bc10f2023a4a6ac67d6310f09d597ddbc6adfaa4a154ed385f')
capture(tmp/'metodobase-mfa31-security-full-20261019/test_full_review.py','MFA31-full20-before-test.py','602069c1a838cf12440250e167742c62f11a40a062fd16226428ac293aacd5f8')
for folder,prefix,digest in [(Path(r'F:\mb-mfa31-keys-fix-20261019'),'backend-mfa31-alias-key-fix','00d19c33f6febaa231bd5f4dda892d5839aad88af045b0d0a367076050578810'),(Path(r'F:\mb-mfa31-primary-privacy-20261019'),'backend-mfa31-primary-privacy','6d9c03dccfcd644de2c0e15c30718a0e6a56d55a24a166b83adcc978739114bf')]:
    capture(folder/'docs/implementation/20261018-evolution/evidence'/prefix/'freeze.json',prefix+'-freeze.json',digest)
write(dest/'SEC13-initial-observation.json',json.dumps({'source':'56e810b3a0518231ba013cab29d68ee0aba0bacd','reporter':'Independent Security agent; root read exact frozen driver and source canonical predicates, no root HTTP replay in this checkpoint','driver_sha256':'4d0d35179c3ef1bc10f2023a4a6ac67d6310f09d597ddbc6adfaa4a154ed385f','cases':6,'factories':2,'passed_controls':4,'failed_pending_parent':2,'scope':'ADMIN enrolled/authenticated legitimately, then parent persisted state is mutated explicitly in synthetic SQLite to pending invitation, team association or soft deletion. R12 canonical_gym false. Pending parent incorrectly permits new step-up grant; other4deny. No legitimate API path introducing this state demonstrated, no invite/email/payment executed. Backend separate fix under review; nonNULLemptystring states also being tested.'},indent=2)+'\n')
write(dest/'manifest.json',json.dumps({'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2)+'\n');raw.update(p for p in dest.rglob('*') if p.is_file())
data=json.loads((run/'TRAZABILIDAD.json').read_bytes());keys=['fuente','seccion','problema','criterio_exacto'];old={r['id']:{k:r[k] for k in keys} for r in data['requisitos']};assert len(old)==109 and 'SEC13' not in old
new=copy.deepcopy(next(r for r in data['requisitos'] if r['id']=='SEC12'))
new.update(id='SEC13',identificador_original='SEC13',seccion='Elegibilidad canónica de actor y propietario al emitir y consumir MFA',problema='MFA31 omite invitation_token del propietario en current_identity y mfa_actions.authorize. Con administrador previamente enrolado/autenticado, un OWNER activo pero con invitación noNULL permite emitir grant aunque canonical_gym de R12 es falso. Los checks truthy tampoco equivalen a IS NULL ante cadenas vacías históricas/ambiguas.',criterio_exacto='Revalidar bajo los mismos locks de cuentas la elegibilidad persistida de actor y propietario canónico al emitir y consumir autorizaciones: activo, sin borrado, invitación estrictamenteNULL y propietario gym/OWNER sin asociación de equipo. Rechazar estados noNULL incluso vacíos sin emitir ni consumir indebidamente grants y preservar el caso legítimo; no ampliar roles o suplir propiedad. Conservar los seis criterios independientes iniciales en ambas factories, cubrir emisión/consumo y estados ambiguos con pruebas propias, revisión independiente posterior y PostgreSQL restringido cuando corresponda. No afirmar que una API legítima crea esos estados ni que se ejecutó una invitación o cargo.',tareas=['R02','R32'],dependencias=['R02','R32'],cambios=['Hallazgo en fuente31 aislada. Backend prepara delta separado tras freezes de clave y privacidad; MAIN30 no incorpora31.'],commits=['56e810b3a0518231ba013cab29d68ee0aba0bacd'],pruebas=['Seguridad:6HTTP/SQLite,2factories×3estados;4controles denegados correctamente y2rojos delpropietario coninvitación noNULL. Driver inmutable4d0d. Matriz nonNULLvacío yconsumo en preparación separada.'],evidencia=['evidence/prepared-wave117-20261019/SEC13-initial-observation.json','evidence/prepared-wave117-20261019/SEC13-before-test.py'],revisor='Seguridad independiente reproduce; delta final y PostgreSQL pendientes.',observaciones=['Checkpoint117:110total;109criterios previos exactos. Estados sintéticos históricos/ambiguos preparados explícitamente; ningún efecto externo ejecutado.'])
data['requisitos'].append(new)
notes={
'R01':'AmpliaMAINeea8 conR23/R24/SEC11 verde2597pass+1skipWindows por modo serial/cov777.079s y n2shuffle384.438s;9542/89quietos,pip0,cobertura0. SEC12aliasfix78d27 autor5replay+12mantenidas reales(APIaliases/Webcanonical yWebalias404), no17unique; independiente posterior pendiente.',
'R02':'NuevoSEC13 padre invitado noNULL emitegrantADMIN en31aislado:4controles/2rojos, ambosfactories. Root/backend confirmancanonR12 IS NULL, no truthy. Reparacióneligibilidad actor/parent bajo locks en preparación separada; no cambiar web.auth global sin repro.',
'R05':'Amplia actualeea8 ambos modos2597+1 verde, casos2492previos únicos preservados íntegros;106casos adicionales. VentanaPG/Chrome liberada tras gate. CI31 sólo contrato/baseline autenticada, no implementada ni ejecutada.',
'QA11':'Amplia serial/cov y n2shuffle actual compuesta verde2597+1por modo y3módulos100%líneas/ramas.9542fuentes/89pkgs quietos,pip0. Se mantiene omisión Windows symlink; Linux debe ejercerla.110registros/109criteriosprevios exactos.',
'R12':'Amplia actual conserva2492caseIDs previos yse integraR24sin perderR23. MFA31 composición46dc sóloaislada; header conflict único resuelto reteniendo ambos padres,94mantenidas+8propiasporfases/harness explícitas, nofresh102global.',
'R23':'Amplia MAINeea8 compuesta conR24/SEC11 verde2597+1cada modo; noCLI/imagen/SLO por esa suite. Responsables/eventos persistidos siguen pendientes.',
'R24':'Amplia compuestaMAINeea8 verde2597+1cada modo, cobertura0yfuentes9542/89quietas. No cierra sustitucionesR33/conservaciónR31 ni valida Linux/Actions/imagen.',
'R31':'PrimaryAPIlogin/Google privacidad deerrores se corrige8b64aislado:20inmutables antes18/2→20green y94autorregresiones, independiente posterior pendiente; sin fuga afirmada. Política países/plazos siguependiente.',
'R32':'Candidato31 aislado:SECinitialadfd rechaza4alias-key;78d27 autorfix5/5+12mantenidas se solapan. Full20propias18green/2erroresheader→8b64autor20/20; parentpendingSEC13 dosrojos/4controles y6crypto/budget/Redis propias verdes. Revisióncompleta,UIHTTP/PG/CI31 yavisoscorreo pendientes. UI fa48edf VM congelada, composiciónpropia incluye46dc/78/8b64sinserviciosaún.',
'SEC12':'78d27 frozen autorfix; mismo5 antes4red/1control→5green y12mantenidas con rutas reales. Aliases sóloapi.app; Webcanónicosverificados yaliases404sinefectos. Sin montar rutas extra ni17criteriosúnicos. Revisión SEC posterior pendiente.',
'R34':'Amplia terminado no es SLO ni capacidad. Diagnósticoholderpool1 listoencolaQA tras backendfree; no nuevo experimentoPG aún.',
'R21':'Composición MFA31 fueraMAIN46dc mantieneprotección diary yMFA deambospadres; único conflictocomprobado contra merge-tree. BaselineCI30 autenticada9542regularfiles/450366072bytes/23helpers, sin materializararchive oafirmarejecución nueva.'}
refs={'R01':['evidence/main-r23-r24-regression-20261019/summary.json'],'R05':['evidence/main-r23-r24-regression-20261019/summary.json','evidence/mfa31-ci-baseline-prepared-20261019/contract.json'],'QA11':['evidence/main-r23-r24-regression-20261019/summary.json'],'R23':['evidence/main-r23-r24-regression-20261019/summary.json'],'R24':['evidence/main-r23-r24-regression-20261019/summary.json'],'R32':['evidence/security-mfa31-initial-independent-20261019/source.json','evidence/mfa31-composition-prepared-20261019/summary.json'],'SEC12':['evidence/prepared-wave117-20261019/backend-mfa31-alias-key-fix-freeze.json']}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint117: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        if ref not in row['evidencia']:row['evidencia'].append(ref)
write(run/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
with (run/'NUEVOS_HALLAZGOS.md').open('ab') as stream:stream.write(('\n\n## SEC13: '+new['seccion']+'\n\n'+new['problema']+'\n\nCriterio: '+new['criterio_exacto']+'\n\nReproducción inicial:4controles+2rojos enambasfactories conestados sintéticos explícitos. [Recibo](evidence/prepared-wave117-20261019/SEC13-initial-observation.json).\n').encode())
write(run/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint117 local:110 registros,92 IDs originales y109 criterios previos exactos. MAINeea8f773fba9b7f92241958139fcefa23b9ee1d4 integra esquema30, R12, R23/expiración/CI573, SEC11 yR24 parcial. Original F:/MetodoBaseWeb-main intacto. Sin push, PR, despliegue, cargos ni comunicaciones reales.

Amplia actual verde sobre esa fuente:2597 aprobadas+1 omisión conocida de symlinks Windows por modo serial/cobertura y dos workers/shuffle. Duraciones777.079s/384.438s, sin SLO. Se conservan los2492 casos previos únicos y106 adicionales;9542 archivos/89 paquetes quietos,pip0 ygate de cobertura0. Los tres módulos exigidos tienen100%líneas/ramas. No es aceptación Linux/Actions/imagen/PG. [Evidencia](evidence/main-r23-r24-regression-20261019/summary.json).

R23 yR24 siguen parciales por responsables/eventos persistidos ypor sustituciones/R33/R31 respectivamente. R24 integrado con25 fuentes exactamente iguales a4042; QA98+21 yfresh11R24+16R12 sobre4042,Seguridad27propias+4HTTP. La fase9bfa conserva31SQLite+65VM+2PG+1canario por fuente. SEC11 retorno/circuito está integrado tras root11 ySeguridad5propios+11replay. Sus grants se revisan con31. [QA R24](evidence/qa-r24-after-privacy-independent-20261019/final-summary.json).

MFA31 sigue aislado. Fuente56e810 autor37fuentes/205proofs,restore1 yDDL10 no equivalen a aceptación. SEC12aliases de pago se corrige78d27:autor mismo5verdes y12mantenidas conrutas reales, revisión posterior pendiente. Privacidad primaryAPI se corrige8b64:autor20inmutables y94dirigidas verdes, posterior pendiente. NuevoSEC13:padre invitado noNULL permitegrantADMIN;4controles/2rojos enambasfactories. Backend alinea actor/parent concanon IS NULL, cubriendo también cadena vacía. NoMFA31 integrado. [Revisión inicial](evidence/security-mfa31-initial-independent-20261019/source.json). [SEC13](evidence/prepared-wave117-20261019/SEC13-initial-observation.json).

Composición31/46dc fueraMAIN conserva las políticas de diario yMFA en el único conflicto. Pasaron94mantenidas enuna tanda y8propias después de corregir supuestos de fixture; no se afirma un fresh102global. UI fa48edf tiene freezeVM ycomposición propia con78/8b64; espera parentfinal para HTTP real. QA/SeguridadPG, browser,CI31, avisos de cambiofactor yconfiguración real pendientes. BaselineCI30 autenticada9542archivos/23helpers sólo preparación, sin nuevaCI ejecutada.

R24 publica proyecciones nuevas autenticadas:4CSRF SSR deQA privados y4 delautor sustituidos sólo enproyección; originales ymanifiestos rechazados conservados. ZIPs de fuente17/25entradas revisados byteexactos. No se reescribieron resultados. [Proyección](evidence/r24-author-private-projection-20261019/projection.json).

Linux99c conserva rojo42501 antesdeweb. QEMU/red/proxies/SSH yPG55484 cerrados. Docker c02/ExpatM2 sólo aceptación estática; falta compilación/imports/linkage/SCA/arranqueProductionSettings/MIGRATORunset/readiness.71 IDsOS abiertos. R34holder espera slotQA yventana coordinada; ampliar pool no acredita solución.

Free:10 clientes activos,1 plan/cliente/día y10 totales/gimnasio/día. MensualesFree20/Standard100/Gym+Clínica0 ilimitado; individualStarter1/Pro5/79MXN separado. Desktop soportado,bundle3.12.15 con93 controles independientes; instalación/firma/inventarioDLL exhaustivo pendientes.

Siguiente:terminar refinamientos yrevisión completaMFA31, componerUI/CI conhistóricos intactos ydiagnosticarR34. ReconstruirLinux enventana acordada ycontinuar producto/privacidad. R25 contrato preliminar; R35 evaluación sinbeneficio medido. PolíticaR31 consultada ypendiente, sin nuevaspurgas. Pilotos/dictámenes/proveedores requieren evidencia real. [Registro](TRAZABILIDAD.md).
''')
write(run/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint117:110 registros y92 IDs originales. MAINeea8f773fba9b7f92241958139fcefa23b9ee1d4 integra esquema30,R12,R23/expiración/CI573,SEC11 yR24 parcial. Amplia actual2597aprobadas+1omisión Windows por modo serial/cobertura y n2/shuffle;9542fuentes/89paquetes quietos,pip0,cobertura0,2492casosprevios íntegros.

MFA31 sigueaislado conrefinamientos dekey/privacidad yparentcanónicoSEC13 en revisión;UI/QA/Seguridad/CI31 pendientes. LinuxExpatM2 sólorevisiónestática,faltaartefacto/arranque/SCA ysiguen71IDsOS abiertos. Desktopsoportado. Free10clientes,1plan/cliente/día y10totales/gimnasio/día.

Sin entrega final,push,PR,despliegue,cargos ni comunicaciones reales. [Estado](ESTADO.md),[validación](VALIDACION.md),[riesgos](RIESGOS.md)y[registro](TRAZABILIDAD.md). Cada evidencia conserva fuente/entorno.
''')
for name,note in {'VALIDACION.md':'Ampliaeea8:serial2597pass+1skipWindows777.079s,shuffle2597pass+1skip384.438s;9542fuentes/89paquetes estables,pip0,cobertura0,2492caseIDs previos exactos más106nuevos cada modo.3módulos100%líneas/ramas. No PG/Redis/Linux/Actions/imagen/SLO. Composición46dc94mantenidas+8propias porfases;1+1rojos de fixture cache preservados y10assertsAST intactos en refinamiento final, sincambioproducto.','CAMBIOS.md':'Se sella gate actualR23/R24/SEC11 yse registraSEC13 de fuente31aislada.78d27key y8b64privacidad están fueraMAIN ypendientes de revisión posterior. No nuevo producto encheckpoint.','RIESGOS.md':'SEC13 parent/actor canónicos de31 requieren invitation_token estrictamenteNULL bajo locks al emitir/consumir.2rojos/4controles, sinacciónexternareal. SEC12fix yprivacidadprimary enrevisión; no aceptarMFA por corregir sólo5o20. Linux71OS,políticaR31,pilotos yconfiguraciónproveedores siguenpendientes.','DECISIONES.md':'CongelarMAINduranteamplia dio9542fuentes/89paquetes exactos. Registrar109criterios previos sincambio ynuevoSEC13. Preservar todoslos intentos deprobeheaders; corregirfixtures contraelcontratoreal deambospadres sin tocar producto ni10aserciones. CI31 usará fuente30 auténtica, no marcadores viejos fabricados desde modelos31.'}.items():
    with (run/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 117\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
current={r['id']:{k:r[k] for k in keys} for r in json.loads((run/'TRAZABILIDAD.json').read_bytes())['requisitos']};assert len(current)==110 and {k:current[k] for k in old}==old
attrs=ev/'.gitattributes';assert b'checkpoint117-' not in attrs.read_bytes();attrs.write_bytes(attrs.read_bytes()+b'checkpoint117-driver.py -text\ncheckpoint117-review.json -text\n');raw.add(attrs)
driver=ev/'checkpoint117-driver.py';shutil.copyfile(__file__,driver);raw.add(driver)
receipt=ev/'checkpoint117-review.json';write(receipt,json.dumps({'base':base,'registry':110,'previous_criteria_exact':109,'new_id':'SEC13','product_changed_in_checkpoint':False,'raw_files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
names=sorted(p.relative_to(root).as_posix() for p in raw);docs=[(run/n).relative_to(root).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md']]
for i in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','--',*names[i:i+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
buf=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buf.index(b'\n',cursor);head=buf[cursor:end].split();assert head[1]==b'blob';size=int(head[2]);cursor=end+1;assert buf[cursor:cursor+size]==(root/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buf) and set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record composed broad regression and MFA parent eligibility finding'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no');print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_authenticated':len(names),'registry':110,'previous_criteria_exact':109}))
