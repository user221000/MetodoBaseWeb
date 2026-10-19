"""Record the failed runtime, reviewed bootstrap repair and rejected UI phase."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path('F:/MetodoBaseWeb-execution-20261018');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence'
BASE='5d0e668157f956a4d3ebc785ff3c7ee81fe59664'
sha=lambda value:hashlib.sha256(value).hexdigest()
def git(*args,**kw):return subprocess.check_output(['git',*args],cwd=ROOT,**kw)
def read(path):return json.loads(path.read_bytes())
def write(path,text):path.write_bytes(text.encode('utf8'))
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
runtime=EV/'linux-runtime28-native-20261019/runtime-red-frozen'
qa=EV/'qa-r12-composition29-independent-20261019'
sec=EV/'security-migrator-role-independent-20261019'
assert sha((runtime/'evidence-manifest.json').read_bytes())=='e5e6cbc71cb38a0525f4958bc6d87fa84fe573486fdd3700dc1fdd287c9622d9'
assert sha((qa/'phase939-blocked-manifest.json').read_bytes())=='55beef76a9d1eb6222eb5c7fcb8929b344cc6aff99c0ecfc0607f7392760de7c'
assert sha((qa/'phase939-blocked-summary.json').read_bytes())=='7ed666831d1ad47a018cfb3d7cca088c48ad4648564c418d521259b6a40cf627'
assert sha((sec/'source.json').read_bytes())=='b81fb5afd4611a38e00522c745a9def583a1ef930e4f9e20285833aafad07b27'
raw=set()
manifest=read(runtime/'evidence-manifest.json');assert len(manifest['files'])==manifest['file_count']==173
for row in manifest['files']:
    path=runtime/row['file'];blob=path.read_bytes();assert len(blob)==row['bytes'] and sha(blob)==row['sha256'],path
    raw.add(path)
raw.add(runtime/'evidence-manifest.json')
manifest=read(qa/'phase939-blocked-manifest.json');assert len(manifest['files'])==manifest['file_count']==204
for name,digest in manifest['files'].items():
    path=qa/name;assert sha(path.read_bytes())==digest,name;raw.add(path)
raw.update([qa/'phase939-blocked-manifest.json',qa/'phase939-blocked-summary.json'])
for name,digest in read(sec/'source.json')['published_files_sha256'].items():
    path=sec/name;assert sha(path.read_bytes())==digest,name;raw.add(path)
raw.add(sec/'source.json')
author=Path('F:/mb-r12-ui-fix29-20261019/docs/implementation/20261018-evolution')
destination=EV/'r12-controls-author-20261019';assert not destination.exists()
shutil.copytree(author/'evidence/r12-controls-author-20261019',destination)
assert sha((destination/'freeze.json').read_bytes())=='fe83315f63b8d2af2c874cf265caf21314038591871535ad21706c6670a8d778'
manifest=read(destination/'evidence-manifest.json');assert len(manifest['files'])==manifest['file_count']
for name,detail in manifest['files'].items():
    path=destination/name;blob=path.read_bytes();assert len(blob)==detail['bytes'] and sha(blob)==detail['sha256'];raw.add(path)
raw.add(destination/'evidence-manifest.json')
shutil.copyfile(author/'R12_CONTROLES_INDEPENDIENTES.md',RUN/'R12_CONTROLES_INDEPENDIENTES.md')
for directory in [runtime,qa,sec,destination]:
    attrs=directory/'.gitattributes'
    if attrs.exists():assert attrs.read_bytes().replace(b'\r\n',b'\n')==b'* -text\n'
    else:attrs.write_bytes(b'* -text\n')
    raw.add(attrs)
data=read(RUN/'TRAZABILIDAD.json');old={r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in data['requisitos']}
assert len(old)==105 and 'UX-18' not in old
notes={
 'R03':('Reparaciónhistóricac4 integrada5d0e668 trasSEC:11regresionesoriginales+2propiasverdes. Sólo se retiranCREATEROLE/GRANTglobales;34contratosinmutables. Migra conownerNOCREATEROLE sin crearrolglobal y conservaACLexistentes. Imagen99c anterior siguefallida42501;replayLinuxcorregidopendiente.', ['security-migrator-role-independent-20261019/source.json','linux-runtime28-native-20261019/runtime-red-frozen/evidence-manifest.json']),
 'R04':('El migrador deja deprovisionarrolcluster-global; grantsruntimeexternosexplícitos. SEC confirmaRLS/DDL/SETROLEnegativos ypreservaACLheredadas; noaceptaciónLinuxnueva.', ['security-migrator-role-independent-20261019/source.json']),
 'OPS01':('FalloLinux42501 originalconrollbackpublic0 archivado;delta5d0e668 aceptadonativoPG13 y34contratosiguales. 55484apagadoordenadamenteporSEC, propiedad/HBA/catálogoglobalrevalidados. Faltaimagenconfixyarranque.', ['linux-runtime28-native-20261019/runtime-red-frozen/evidence-manifest.json','security-migrator-role-independent-20261019/source.json']),
 'OPS02':('Provisionamientodelrolruntimepermaneceexterno, sinCREATEROLEmigrador;losACLyaexistentesnopurgados. Ambosrolesrestringidos/comportamientoRLS verificadosen13casosindependientes.', ['security-migrator-role-independent-20261019/source.json']),
 'R12':('FaseQA939 rechazada:HTTP28/28,restore29poblado1,UI10,Node297ejecuciones/276criteriosúnicos. Backend147:144verdes+2skipsSQLitePG-only+1errorlauncherspawn;replaydelcasoverdeaparte. NavegadorrealPG/defaultpool20/10:7verdes,criterio8exportdisabledrojo,9–16noalcanzados. Fixec029 aisladoycongelado,3canariosafter/16regresionesautorverdes;QA/SECafterpendientes.', ['qa-r12-composition29-independent-20261019/phase939-blocked-summary.json','r12-controls-author-20261019/freeze.json']),
 'UX-07':('Vínculo/fragmento/publicaciónCAS/menú/PDFexacto alcanzadosenChromePGreal;exportaciónbloqueadaencriterio8porinterferenciacontroles,UX-18nuevo. Nohayaceptaciónderecorridocompleto.', ['qa-r12-composition29-independent-20261019/phase939-blocked-summary.json']),
 'R13':('NuevoUX-18:VinculosUIcaptura/restaura disabled global ypisaprivacyconcurrente. Fixec029 usaownedControls explícitosporconsumidor;main noesfrontera porqueincluyeexport. 2rojosoriginales+1control→3verdesautor,16assertsexistentesintactas. Replayindependienteaúnenprogreso.', ['r12-controls-author-20261019/freeze.json']),
 'R31':('Exportacióndesiete coleccionesAPIverificada;suacciónUIaúnfallóenrecorridoreal porcontroldeshabilitado. Fixec029noalteraprivacycontroller;supropiociclodevidaseconserva. No cerrarprivacidadnirecorridoporpruebasAPIaisladas.', ['qa-r12-composition29-independent-20261019/phase939-blocked-summary.json','r12-controls-author-20261019/freeze.json']),
 'R34':('QAobservótimeoutbajopool1 enGETauthme→subscriptionguard._get_gym_plan(db)→checkout;dueñodelaprimeraconexióndesconocido,noinstrumentado. Replaypool20/10sóloE2E,nocierraadquisiciónanidada/deadlock/capacidad. Índice30aceptado120sigueaislado.', ['qa-r12-composition29-independent-20261019/phase939-blocked-summary.json']),
 'R18':('Runtime99c fallóantesdeweb;scopeLinuxnetwork/nsSCRM/productionSettingspreservado173archivos. Noarranque/readiness/unsetMIGRATORdemostrados. C4corregidonativo13;sourcebuildpsycopg2contraDebianparcheadoenpreparación,SEC09/71OSsiguenabiertos.', ['linux-runtime28-native-20261019/runtime-red-frozen/evidence-manifest.json','security-migrator-role-independent-20261019/source.json']),
 'OPS07':('QEMU/red/proxies/SSHcerrados;IPv4restauradosemánticamente,IPv6sólofilter/builtinsvacíosinicializados. PG55484transferidoyluegoapagadoSECconpropiedadverificada. NoigualdadbyteabyteIPv6niaceptaciónruntimecorregido.', ['linux-runtime28-native-20261019/runtime-red-frozen/evidence-manifest.json','security-migrator-role-independent-20261019/source.json'])
}
for row in data['requisitos']:
    if row['id'] in notes:
        text,files=notes[row['id']];row['observaciones'].append('Checkpoint109: '+text)
        for name in files:
            value='evidence/'+name
            if value not in row['evidencia']:row['evidencia'].append(value)
    if row['id'] in ['R03','R04','OPS01','OPS02'] and BASE not in row['commits']:row['commits'].append(BASE)
    assert {k:row[k] for k in old[row['id']]}==old[row['id']]
data['requisitos'].append({'id':'UX-18','identificador_original':'UX-18','fuente':'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md',
 'seccion':'Interferencia de controles entre vínculos y exportación','problema':'VinculosUI939 captura y restaura disabled de todos los controles del documento y puede sobrescribir la habilitación concurrente de exportación; QAChrome/PGreal deja privacy-start deshabilitado y no puede completar el criterio8 del recorridoR12.',
 'criterio_exacto':'Cada consumidor de vínculos sólo bloquea, restaura e invalida los controles propios, incluidos dinámicos; no modifica controles, foco o estados del consumidor de exportación u otros componentes. Preservar fences de sesión, permisos y recuperación de acciones inciertas. Los mismos negativos de interferencia deben fallar antes y pasar después; las regresiones existentes y el recorrido real de16criterios deben completarse con revisión independiente.',
 'prioridad':'P1','responsable':'Frontend y QA','tareas':['R12','R13','R31'],'dependencias':[],
 'estado':'en_revision','implementacion':'en_revision','validacion':'en_curso','despliegue':'no_desplegado','entorno':'local',
 'cambios':['Fixec029 aislado requiereownedControls explícitos en los tres consumidores; no selector global ni frontera main.'],
 'commits':['ec0291aec82db6f9fcd007fb0736e2797440f91b'],
 'pruebas':['Antesindependiente:2rojos+1control. Autorafter:3verdes y16regresionesintactas,6syntax. ReplayChrome16yseguridadafterpendientes.'],
 'evidencia':['evidence/qa-r12-composition29-independent-20261019/phase939-blocked-summary.json','evidence/qa-r12-composition29-independent-20261019/phase939-blocked-manifest.json','evidence/r12-controls-author-20261019/freeze.json'],
 'documentacion':['NUEVOS_HALLAZGOS.md','R12_CONTROLES_INDEPENDIENTES.md'],
 'revisor':'QA reprodujo fallo939; QA/seguridad revisanec029 aislado.','bloqueo':None,
 'observaciones':['Corrección no integrada enMAIN, que permaneceesquema28. Noaceptación delrecorrido29 completo.']})
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
with (RUN/'NUEVOS_HALLAZGOS.md').open('ab') as stream:stream.write(('''
## UX-18 — Interferencia de controles entre vínculos y exportación

En939, VinculosUI guarda/restaura disabled de todos los controles del documento. La exportación, dentro del mismo main, se inicializa concurrentemente y su botón puede volver a quedar deshabilitado. QAChrome/PGreal pasó siete criterios y falló el octavo por ese botón;9–16 no se alcanzaron. Se conservan fuentes, capturas y [fase rechazada](evidence/qa-r12-composition29-independent-20261019/phase939-blocked-summary.json).

El fixec029 aislado exige una colección ownedControls por consumidor para operación e invalidación; evita interferir con exportación. Los mismos tres canarios dan2rojos/1control antes y3verdes después en el ensayo del autor;16 regresiones existentes pasan sin alterar aserciones. Falta aceptación independiente y replay real16. [Contrato y límites](R12_CONTROLES_INDEPENDIENTES.md). PrioridadP1, responsable frontend/QA, registroUX-18.
''').encode())
write(RUN/'ESTADO.md','''# Estado de ejecución 20261018-evolution

Checkpoint109 local en curso:106 registros,92 IDs originales y105 criterios previos intactos. NuevoUX-18. Original F:/MetodoBaseWeb-main conservado; rama implementation/20261018-execution, base daa25efbf51d154710bad625025b345fa9ec9252. Sin push, PR, despliegue, cargos o comunicaciones reales.

MAIN sigue en esquema28. Integra ahora5d0e668: la migración histórica deja de crear o conceder permisos a un rol global; mantiene políticas, lineage y34contratos. Seguridad aceptó11 regresiones intactas+2propias;reprodujo42501antes y verificórollback. Se conserva aprovisionamiento externo del rolruntime y ACL heredadas. Falta reconstrucción/arranqueLinuxcorregido. [Revisión](evidence/security-migrator-role-independent-20261019/source.json).

R12/939 aún rechazado por QA. Restore29poblado1, páginas10, HTTPpropios28 yNode17:297ejecuciones/276criteriosúnicos (21exportrepetidas). Backend147 tuvo144verdes/2skips conocidos/1errorlauncher, luego replay focalverde. NavegadorPGreal/defaultpool20/10:7verdes,criterio8exportdisabledrojo,9–16noalcanzados. NuevoUX-18;fixec029 aislado,4JSownedControls por consumidor. Autor3canarios+16regresionesverdes; QA/SECafter en curso. CI29 se prepara aisladamente:26reportsPG,20mutantes,55parser,27procesosinertes,7trust y2restores28 reales;noActions ni navegadorCI acreditados. [Fase rechazada](evidence/qa-r12-composition29-independent-20261019/phase939-blocked-summary.json), [fix](R12_CONTROLES_INDEPENDIENTES.md).

Índice30/6ea aceptado por QA120/120 sin omisiones, aún aislado hasta29/CI. Observaciones de51/52/51/51/51filas son del corpus1000, sin p95/SLO o cota universal. La observaciónpool1 deQA retiene dueño desconocido de la primera conexión;pool20/10 no demuestra ausencia de deadlock. [Aceptación30](evidence/history-index30-independent-20261019/final-summary.json).

Linux99c de fuentebc365c1: producciónSettings y red acotada se ejecutaron, pero migración falló42501 y web jamás se creó. El diario previo private_stdin_sent=false se conserva con errata: los logs sí demuestran ejecución de Settings/Alembic. No se aceptan readiness, marcador28 o ausenciaMIGRATOR en workers.173 archivos congelados registran origen, red roja/corrección, rollback, cierre y continuidad. QEMU/red/proxies/SSH cerrados;PG55484transferido y después apagadoSEC con propiedad,HBA/catálogo verificados. [Evidencia](evidence/linux-runtime28-native-20261019/runtime-red-frozen/README.md).

R18/SEC09:55PyPI/OSV0,87OS/164entradas/71IDs abiertos;811ELF reales. OpenSSL3.5.8vendorizado depsycopg2 coincide por versión con13registrosCNA;alcanzabilidad pendiente. Se prepara buildcontainer contra libpq/OpenSSLDebianparcheados;sin imagen nueva ni excepción. Desktop3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3 tiene93 controles independientes de bundle/payload, sin instalación/firma ni revisión exhaustiva deDLL.

Regresión amplia aceptada sigue en a753b2c:2360verdes/1omisiónWindows,serie+n2;no se atribuye a29/30/c4nuevo. Scan final de secretos de fuente actual pendiente. Free:10clientes activos,1plan/cliente/día y10planes totales/gym/día;mensualesFree20/Standard100/Gym+Clínica0ilimitado;individualStarter1/Pro5/79MXN separado. Desktopsoportado.

Siguiente: QA/SEC del fixUX-18,CI29ycomposiciónaceptada;integrar29ydespués30. ReconstruirLinux con c4/componentes corregidos y validar arranque real;continuar demáscriterios de producto, privacidad y operación. Dictámenes/pilotos humanos permanecen precisos ysin inventar aprobación. [Registro](TRAZABILIDAD.md).
''')
write(RUN/'ENTREGA.md','''# Entrega candidata en curso

Checkpoint109 local;106registros/92IDs originales. No entrega final ni despliegue. MAIN conserva esquema28 e integra5d0e668,c4 reparado tras13controles independientesPG y34contratos intactos; falta imagenLinux corregida.

R12/939 no aceptado:7criterios navegadorverdes,8exportdisabledrojo,9–16 pendientes. Fixec029 aislado tiene3canarios+16regresionesautorverdes y revisión QA/SECen curso. Restore29/API yNode tienen evidencia acotada; CI29 todavía aislado. Índice30 aceptado120, no integrado. Linux99c anterior permanece rojo42501 antesdeweb,71IDsOS ySEC09abiertos. Desktop3.12.15 aceptado sólo en93controles bundle/payload, sin instalación/firma.

Free:10clientes,1plan/cliente/día y10planes/gym/día;desktopconservado. Ver [estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md), [registro](TRAZABILIDAD.md). No se relabelan las pruebas anteriores como aprobación de la versión actual.
''')
append={
 'VALIDACION.md':'Se autentican173 archivosLinuxoriginales,204filesfaseQA939rechazada y revisión migrador13verdes(11originales+2propios). NativePGno acreditaLinuxcorregido. Backend147 se describe144pass/1harnesserror/2skips+replay1, no ejecuciónúnicaverde. Restore29poblado1/UI10/HTTP28/Node297ejecuciones276únicos separados. Browser939:7pass,1fail,8noalcanzados;fixec029autor3+16verdes,sintaxis6,fuentecerrada. TodoslosRAW/derivados mantienen suclasificación;manifiestos yGitblobs verificados byteabyte.',
 'CAMBIOS.md':'Integrado5d0e668:c4 elimina únicamenteCREATEROLE/GRANTglobales para permitir dueño de esquemaNOCREATEROLE;políticas/función/revisiones/targets yACLprevios sin cambio. Repairhistórico justificado porque una revisión posterior no puede superar el fallo previo. FixUIec029 permanece separado deMAIN yse registraUX-18. No27/29/30retargeting para ocultar históricos.',
 'RIESGOS.md':'UX-18/P1 bloquea exportaciónUI en flujoR12 por interferencia deestado disabled;mitigaciónownedControls yreplay16independiente en curso. R34pool1:waiterGETauthme checkout,holderdesconocido;no atribuir causa ni cerrarlo conpool20. C4fix nativoaceptado, Linuxcorregidopendiente;ACLheredados sepreservan ynosepurgaunrolglobal sin alcanceaplicable. SEC09/71OSsiguenabiertos. 55484apagado y recursos propioscerradosconidentidadverificada.',
 'DECISIONES.md':'Se integra únicamenteelc4aceptado13, sin ampliar privilegios ni precrearrolglobal. Se rechaza aceptaciónR12completa peseaAPI/restoreverdes porfalloUIrealcriterio8. Fixec029debe superar mismos16+3 yrevisiónSEC;scopeexplicito decontroles, no main. Elhistórico28enCI correconfuenteGit66fijada, sin editaraserciones/modelofalso. Node297son ejecuciones y276criteriosúnicos,21exportrepetidas.'}
for name,text in append.items():
    with (RUN/name).open('ab') as stream:stream.write(('\n\n## Checkpoint 109\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
assert {r['id']:{k:r[k] for k in old[r['id']]} for r in read(RUN/'TRAZABILIDAD.json')['requisitos'] if r['id'] in old}==old
driver=EV/'checkpoint109-driver.py';receipt=EV/'checkpoint109-review.json';assert not driver.exists() and not receipt.exists()
shutil.copyfile(__file__,driver);raw.add(driver)
write(receipt,json.dumps({'base':BASE,'registry_count':106,'new_id':'UX-18','previous105_criteria_exact':True,'only_product_change_already_integrated':'5d0e668 c4 exclusive repair','evidence_closed_explicit_paths_only':True,'files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
docs=[(RUN/name).relative_to(ROOT).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md','R12_CONTROLES_INDEPENDIENTES.md']]
names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
for index in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[index:index+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[index:index+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
assert not git('diff','--cached','--check','--',*docs,stderr=subprocess.STDOUT)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names).encode());cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buffer) and set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','commit','-m','Record runtime role repair acceptance and rejected R12 browser phase'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'proof_blobs_byte_exact':len(names),'control_docs':len(docs),'registry':106}))
