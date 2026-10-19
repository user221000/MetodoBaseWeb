"""Seal accepted local reviews and record SEC11 without closing pending runtime work."""
from pathlib import Path
import copy,hashlib,json,re,shutil,subprocess,sys
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence';TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');BASE='3663a360e019880477e558d4ad98ce0ad533ab77'
sha=lambda b:hashlib.sha256(b).hexdigest();read=lambda p:json.loads(p.read_bytes());git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=ROOT,**k)
def write(p,s):p.write_bytes(s.encode('utf8'))
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
raw=set()
def sensitive(blob):
    # Inspect the fixed MAC suffix first. A greedy unbounded payload scan can
    # backtrack quadratically on deliberately oversized negative fixture input.
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        start=match.start()
        if start>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[start-30:start]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob))

def authenticate(directory,name,digest):
    p=EV/directory/name;assert sha(p.read_bytes())==digest,p;entries=read(p)['files']
    if isinstance(entries,dict):entries=[{'path':n,**v} for n,v in entries.items()]
    for row in entries:
        target=p.parent/row['path'];assert target.resolve().is_relative_to(p.parent.resolve());blob=target.read_bytes()
        assert sha(blob)==row['sha256'] and len(blob)==row['bytes'],target;assert not sensitive(blob),target;raw.add(target)
    assert (p.parent/'.gitattributes').read_bytes().replace(b'\r\n',b'\n')==b'* -text\n';raw.add(p)
    checksum=p.parent/'manifest.sha256'
    if name=='manifest.json' and checksum.exists():assert checksum.read_text().split()[0]==digest;raw.add(checksum)
authenticate('qa-r23-ci-independent-20261019','manifest.json','cc77b04a101cca390bb9028bc379f10dd8545d69534745810cdd9b19bf770446')
authenticate('linux-expat-sec10-m2-prepared-20261019','manifest.json','d08274e175279fc0f368bec1494ccc479c7df913c037d2517673c0f0376a0989')
authenticate('security-sec10-m2-independent-20261019','source.json','96f6de1cf20d7c309ce08a97af99f2c04c06a95af2bc6d91b4a8fca1d1e342ce')
authenticate('r35-readiness-20261019','manifest.json','8a345eadd708cdcf1432b9969babf87aa491f7fea68516b65cfc1b5bac6ab762')
dest=EV/'prepared-wave114-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
def capture(source,name,digest=None):
    blob=source.read_bytes();assert not sensitive(blob),source
    if digest:assert sha(blob)==digest,source
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
capture(Path(r'F:\mb-r24-plan-20261019\docs\implementation\20261018-evolution\evidence\r24\final-source.json'),'r24-author-final-source.json','749261abb9a10ad8ae818bee4fbbd39ce93bb6bf76ced549393049ed90a4cbda')
capture(Path(r'F:\mb-mfa31-20261019\docs\implementation\20261018-evolution\evidence\backend-mfa31-wire-contract.md'),'mfa31-wire.md','ad9ed0c62d2b367f6224ff3339998f1621a0537cf9efb5082bcf1d5e032cda2e')
for p in sorted((TEMP/'metodobase-r24-root-quality-20261019').iterdir()):capture(p,'r24-root-quality/'+p.name)
capture(TEMP/'metodobase-r24-root-quality.py','r24-root-quality/driver.py')
for p in sorted((TEMP/'metodobase-portal-root-before-20261019').iterdir()):capture(p,'SEC11-root-before/'+p.name)
capture(TEMP/'metodobase-portal-root-before.py','SEC11-root-before/driver.py')
author=Path(r'F:\mb-mfa31-20261019\docs\implementation\20261018-evolution\evidence\backend-mfa31-author')
capture(author/'portal-port-before.log','SEC11-author-before.log','c4612f98ec23af35f7da4dfe80720cb9d9ad3e35cba02524b75d34a319a4ade1')
capture(author/'portal-port-before.xml','SEC11-author-before.xml','e55ef9c4c527df0f35de9d59bfc5a877044c51d4224d92dc2de734b0dd46f404')
capture(TEMP/'metodobase-r25-contract-draft.json','r25-contract-draft.json');capture(TEMP/'metodobase-r34-contract-next.json','r34-investigation-contract.json')
for p in sorted((TEMP/'metodobase-checkpoint114-scan-repair-20261019').iterdir()):capture(p,'publication-scan-repair/'+p.name)
capture(TEMP/'metodobase-checkpoint114-scan-repair.py','publication-scan-repair/repair-driver.py')
write(dest/'manifest.json',json.dumps({'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2)+'\n');raw.update(p for p in dest.rglob('*') if p.is_file())
attrs=EV/'.gitattributes';original_attrs=attrs.read_bytes();rules=b'.gitattributes -text\n'+b''.join(('checkpoint'+str(n)+'-'+suffix+' -text\n').encode() for n in (111,112,113,114) for suffix in ('driver.py','review.json'))
assert b'checkpoint114-' not in original_attrs;attrs.write_bytes(original_attrs+rules);raw.add(attrs)
data=read(RUN/'TRAZABILIDAD.json');keys=['fuente','seccion','problema','criterio_exacto'];criteria={r['id']:{k:r[k] for k in keys} for r in data['requisitos']};assert len(criteria)==107 and 'SEC11' not in criteria
new=copy.deepcopy(next(r for r in data['requisitos'] if r['id']=='SEC10'))
new.update(id='SEC11',identificador_original='SEC11',seccion='Retorno de portal fuera del origen y validación anterior al circuito',problema="create_portal_session concatena BASE_URL y return_url sin exigir ruta relativa. Con @outside.example.invalid/path el puerto Stripe recibe otro host. Validar dentro del decorador de reintentos también puede clasificar entradas inválidas como fallos del proveedor y abrir el circuito compartido; la corrección debe evitar ambos efectos.",criterio_exacto="Validar el retorno con un helper canónico antes de emitir grants y antes del circuito/puerto Stripe: una sola barra inicial, sin autoridad/esquema, backslash, espacios o controles ASCII/DEL; preservar rutas /usuario y B2B con query/fragmento permitidos. Rechazar antes de cualquier llamada externa; una secuencia de entradas inválidas no abre el circuito ni bloquea una solicitud válida. Verificar ambas factories, contratos previos, cuerpo ligado al grant y origen/URL exactos mediante puertos sintéticos y revisión independiente, sin llamadas o cargos reales.",prioridad='P1',responsable='Backend y seguridad',tareas=['R01','R31','R32'],dependencias=['R01'],estado='en_curso',implementacion='en_curso',validacion='en_curso',cambios=['Reproducido en la preimagen integrada; reparación aislada en preparación, aún sin aceptación independiente.'],commits=[BASE],pruebas=['Root sobre MAIN:8 entradas inválidas rojas+3 rutas válidas verdes,11 casos/0errores/0skips; seis fuentes/89 paquetes quietos. Sólo cuerpo real del servicio y puerto grabador, sin HTTP/DB/red ni aceptación del retry.','Autor:cuatro rojos aislados (dos grants nuevos y dos puertos de servicio). Secuencia de circuito en revisión; sin declarar after global.'],evidencia=['evidence/prepared-wave114-20261019/SEC11-root-before/receipt.json','evidence/prepared-wave114-20261019/SEC11-author-before.xml'],documentacion=['NUEVOS_HALLAZGOS.md','ESTADO.md','RIESGOS.md'],revisor='Coordinación reproduce preimagen; QA/Seguridad del candidato final pendientes.',bloqueo=None,observaciones=['Checkpoint114: nuevo SEC11,107 criterios anteriores exactos preservados. El hallazgo acredita retorno externo por concatenación, sin afirmar SSRF, explotación real o cargo. El commit listado es la preimagen, no un fix integrado.'])
data['requisitos'].append(new)
notes={
'R01':'SEC11 registra retorno fuera de origen:root8rojos/3controles y autor4rojos. Reparación común fuera del circuito en preparación aislada, sin cobros/red ni cierre.',
'R12':'CI de composición R23/expiry aceptado sobre573:87 mantenidas+35 propias,23VM/348mínimos y fresh8 final con metadata30 real; integración pendiente.',
'R23':'QA CI573 aceptado:29reports/33workflow/55+24+12parser/27inert/80Bash/118refs,87mantenidas+35propias+8freshreal. R23 sigue parcial por responsables/eventos persistidos faltantes; no Actions/imagen/SLO.',
'QA11':'CI573 aceptado con fuentes6591/5helpers originales/89paquetes/157Node estables y recursos propios cerrados. Errores de wrappers e inventarios conservados, no fallos de producto ni repetición de VM/Chrome para arreglar informes.',
'R24':'Autoradc80c7 congelado14producto+9tests;31SQLite/2PG/11browser6capturas por scopes. Rootquality5942/89quietos0errores. SEC detecta sólo botón oculto disabledfalse tras invalidar; root9bfa corrige una condición, mismo16 antes11/16→después16/16 y17mantenidas. Revisiones independientes aún en curso, sustituciones/R33/R31 pendientes.',
'R32':'MFA31/WIP con contrato wire estable y17PG causales verdes; lifecycle/ASGI y restore poblado en revisión del autor. Restore detecta deriva CAST en CHECK nuevo, reparación sólo31 en curso. Sin31 integrado ni aceptación QA/SEC/UI.',
'R18':'SEC10M2 7c013f sobrec02 aceptado sólo estático:37+6 propios y22replay/GPG independiente; fuente/patch/CAPI/namespace autenticados. Sin compilación/imports/linkage/imagen/SCA54 ni cierre71OS.',
'SEC10':'M2 backport exacto7c013f aceptado PASS_STATIC_ONLY. Macro Py_BUILD_CORE_MODULE confirmada desde fuente; no cambio requerido. Falta ejecutar compilación, preservación base, linkage/imports/tests y SCA sobre artefacto real.',
'R21':'Se autentican fuentes/preparaciones aisladas y guardas RAW. Cuatro UUID candidatos tras fallo spawn del harness31 siguen sin atribución: no DROP por prefijo/OID; recibos nuevos registran creación y ausencia exactas. No afirmar limpieza global de recursos.',
'R25':'Contrato preliminar de siguiente ola conserva fuentes/fechas/permisos y consentimiento específico sin adoptar cartera ni inventar adherencia. Sólo diseño, sin DDL reservado ni API implementada.',
'R34':'Siguiente investigación preparada para identificar holder real con checkout/checkin y correlación de generación de proceso/solicitud; no experimento nuevo, no SLO ni inferencia de solución por pool20/10.',
'R35':'Evaluación inicial versionada con inventario fuente232 sin los patrones declarados y referencias primarias actuales. Retención de uso y conservación personal separadas; hipótesis online sin caché sanitaria, sin implementación/instalación/beneficio medido. Continúa en curso.'}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint114: '+notes[row['id']])
    if row['id'] in {'R24','R32','R35'}:row['estado']=row['implementacion']=row['validacion']='en_curso'
    if row['id']=='R25':row['estado']='en_curso'
    if row['id'] in {'R18','SEC10'}:
        for ref in ['evidence/linux-expat-sec10-m2-prepared-20261019/manifest.json','evidence/security-sec10-m2-independent-20261019/source.json']:
            if ref not in row['evidencia']:row['evidencia'].append(ref)
    if row['id'] in {'R12','R23','QA11'}:row['evidencia'].append('evidence/qa-r23-ci-independent-20261019/final-summary.json')
    if row['id']=='R35':row['evidencia'].append('evidence/r35-readiness-20261019/manifest.json');row['documentacion'].append('PWA_EVALUACION.md')
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
with (RUN/'NUEVOS_HALLAZGOS.md').open('ab') as stream:stream.write(('\n\n## SEC11: '+new['seccion']+'\n\n'+new['problema']+'\n\nCriterio de cierre: '+new['criterio_exacto']+'\n\nReproducción independiente local de preimagen:8rojos/3controles, sin DB/HTTP/red. Corrección final y revisión pendientes. [Recibo](evidence/prepared-wave114-20261019/SEC11-root-before/receipt.json).\n').encode())
state=(RUN/'ESTADO.md').read_text(encoding='utf8').replace('Checkpoint113 local:107 registros','Checkpoint114 local:108 registros')
state=state.replace('CI adicional R23 en preparación, no integrado aún.','CI adicional R23/573 aceptado por QA:87mantenidas+35propias y8freshreal; merge aún pendiente. [QA](evidence/qa-r23-ci-independent-20261019/final-summary.json).')
state+='\n\nR24 finaladc y fix menor9bfa están aislados en revisión independiente; MFA31/WIP tiene17PG causales pero restore31 mostró deriva de CHECK que se corrige sin cambiar22–30. SEC11 nuevo:retorno de portal fuera del origen, con8rojos/3controles de root; fix separado en preparación. ExpatM2/7c013f aceptado sólo estático37+6+22, sin imagen reparada. R35 tiene [evaluación inicial](PWA_EVALUACION.md), aún sin beneficio medido. Política R31 consultada al usuario y pendiente; no purgas automáticas nuevas.\n'
write(RUN/'ESTADO.md',state)
delivery=(RUN/'ENTREGA.md').read_text(encoding='utf8').replace('Checkpoint113:107 registros','Checkpoint114:108 registros');delivery+='\n\nCI de R23/573 aceptado localmente, aún aislado. R24/9bfa y MFA31 siguen en revisión; SEC11 registrado sin declarar fix integrado. ExpatM2 sólo aceptado estático, no artefacto reparado. R35 evaluación inicial en curso.\n';write(RUN/'ENTREGA.md',delivery)
for name,note in {'VALIDACION.md':'QA CI573:87mantenidas disjuntas+35propias,23VM/348mínimos,19parsers+Node-e4legacy+5normalizers y8freshreal;6591fuentes/5helpers/89pkgs/157Node quietos y recursos propios cerrados. ExpatM2 sólo estático37+6+22/GPG0. R24 rootquality0 sobre5942/89 y fix9bfa16/16+17VM; fuente/browser anteriores se conservan por scope. SEC11 root11:8rojos+3verdes,6fuentes/89pkgs quietos, sin DB/HTTP/red.','CAMBIOS.md':'Se registra SEC11:108 total,107 criterios previos exactos. Se sella aceptación CI573 y M2 estático; no merge de esas fuentes en este checkpoint. R24/MFA31 están aislados, R25 diseño y R35 evaluación inicial explícitos.','RIESGOS.md':'SEC11 retorno fuera de origen y validación dentro de breaker requieren corrección común previa al puerto/circuito. Restore31 tiene deriva CHECK en corrección sólo31;22–30 intactos. Cuatro UUID candidatos de spawn sin atribución no se eliminan. R24 botón oculto se mantiene disabled en9bfa, sin fuga/capacidad demostrada; revisión final pendiente. Expat necesita artefacto real;71OS abiertos.','DECISIONES.md':'Conservar la política de retención pendiente y separar retención de uso R30 de conservación personal R31. No imponer política de caché como bloqueo de un acceso online sin nueva caché; la implementación PWA sigue condicionada a beneficio medido. Validar entradas del portal antes de resiliencia/proveedor. Los recibos de procesos exigen PID+nacimiento+perfil y generación del padre, nunca ParentPID numérico aislado.'}.items():
    with (RUN/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 114\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
current={r['id']:{k:r[k] for k in keys} for r in read(RUN/'TRAZABILIDAD.json')['requisitos']};assert len(current)==108 and {k:current[k] for k in criteria}==criteria
driver=EV/'checkpoint114-driver.py';receipt=EV/'checkpoint114-review.json';shutil.copyfile(__file__,driver);raw.add(driver)
write(receipt,json.dumps({'base':BASE,'registry':108,'previous_criteria_preserved':107,'new_id':'SEC11','product_code_changed':False,'raw_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
docs=[(RUN/n).relative_to(ROOT).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md','PWA_EVALUACION.md']];names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
for i in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[i:i+25]],cwd=ROOT,check=True,capture_output=True);subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[i:i+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
buffer=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1;assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name;cursor+=size+1
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert cursor==len(buffer) and changed==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True);subprocess.run(['git','commit','-m','Seal followup CI review and static Expat candidate; record portal return boundary'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no');print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_authenticated':len(names),'registry':108,'preserved_criteria':107}))
