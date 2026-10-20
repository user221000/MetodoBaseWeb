"""Keep the web delivery ledger current without promoting partial gates."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018');D=R/'docs/implementation/20261018-evolution'
O=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint146-20261020')
BASE='6d6b86cbb2598a1fdf9d41eab42c82d51ad00cd1'
git=lambda *a:subprocess.check_output(['git',*a],cwd=R)
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda o:(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode()
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','-uno').strip() and not O.exists()
O.mkdir();data=json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria=lambda d:{r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in d['requisitos']}
old=criteria(data);assert len(old)==147
untracked=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint145-20261020/untracked-before.json').read_bytes())
assert len(untracked)==537 and all(sha((R/p).read_bytes())==h for p,h in untracked.items());(O/'untracked-before.json').write_bytes(enc(untracked))
paragraph=(
 'MAIN local conserva esquema37 y147 requisitos. Integra la receta Docker57 revisada y cuatro archivos de onboarding22, además de las reparaciones previas de cuenta, sesiones, recordatorios y móvil. Los cuatro blobs de onboarding coinciden con89ca/16c y revisión independiente954f:51 resultados propios,19pytest HTTP/SQLite en ambas factories y32VM con API/controller reales y transportes declarados. El dashboard consulta dos hechos propios persistidos, independientes del periodo estadístico, y deja descarga/entrega como acción explícita. Retira la marca compartida de navegador. En perfil personal incompleto muestra el enlace funcional al perfil y oculta acciones cuyos listeners aún no existen; el texto explica los campos requeridos. Los canarios de autor conservan5RED+2controles→7PASS y2RED+1control→3PASS. No se cierra R22: navegador, PostgreSQL focal y evaluación con5dueños/5socios siguen pendientes.\n\n'
 'Docker57 c4d9 integra12 entradas exactas347, tres helpers y cuatro tests, sin cambiar el lock web. El parser reconoce extras y exige contador entero:57web,56 bloques sin adaptador binario y57 distribuciones runtime esperadas con psycopg2 nativo. Seguridad pasa75 seleccionados y verifica firmas offline APT/PSF y preparación acotada de Expat. La autoridad Git portable conserva21 objetos originales y rutas Merkle sin inventar ancestry; autor138PASS y peer25propios, con57 del companion dentro de un caso sin Git/red/procesos. Esa capa portable todavía no está integrada en MAIN. Imagen, inventario realmente instalado, SBOM y SCA actuales siguen pendientes.\n\n'
 'El escaneo real8d6 terminó RED753:53956 alertas,53203 clasificaciones finitas y15096 archivos estables. V4 cubre las11016 ubicaciones antiguas; las753 nuevas están en20 archivos. Seguridad las propone como750 checksums y tres aserciones de identidad del namespace. ROOT comprueba cada preimagen Git, pointer y línea física,750 controles de pointer y80 del clasificador. V5 aislado c60 prepara897 rutas/57038 pins conservando877 registros v4 exactos y el mismo algoritmo salvo tres literales. Su primera selección205 fue167PASS/38 fallos por dos fixtures omitidas del checkout reducido; al materializarlas el módulo pasa50,38 reparados y12 controles repetidos. El parser esperaba38 y se conserva ese error de conteo; la proyección enlaza205 casos distintos aceptados entre fases, sin afirmar una corrida205PASS. El loader V5 real clasifica753 en el replay privado. Peer del artefacto y nuevo escaneo tras integración siguen pendientes; V5 no está activo en MAIN.\n\n'
 'Navegador37 sigue rechazado. V2 conserva15MFA originales PASS y3 nuevos PASS, después un SyntaxError del test al interpretar como JWT un token de dos segmentos. Cerró servidor/procesos/UUID normalmente. V3 corrige sólo ese decoder con canario puro y controles tipados; selecciona18 sin repetir15. Agotó420s sin reporte final, por lo que no hay conteo18 aceptado ni punto exacto observado. El servidor y UUID cerraron normalmente. Un ACK interno, tras verificar HANDLE/PID/nacimiento/exe/argv, terminó únicamente Node propio con125;19 Chrome observados cerraron por pipe, sin terminación directa. Se preservan ajenos, listener8802 cerrado, fuentes1325/92distribuciones/8084instalados/157Node estables y pip0. PG y Chrome quedaron libres; nueva preparación offline añadirá progreso durable por grupo y comprobará el oráculo WebLock sin evadir serialización. Ese ensayo anterior usaba runtime8d6, no acredita el onboarding nuevo.\n\n'
 'CI serial/cobertura847 sigue parcial e inmutable, con producto anterior a onboarding22. Detectó cuatro RED de privacidad Google cuya fixture usa el contrato antiguo tokeninfo/email-only; el runtime requiere firma/JWKS y vínculo persistido. Se preservan los fallos y se prepara companion actual con los mismos criterios500/202. No hay CI global PASS. Node actual pasa13comandos/147ejecuciones más10controles, aparte del inventario legado51/865 obligaciones. Calidad web pasa F821/sintaxis y9 controles del gate; Bandit conserva28 avisos,22 sin baseline vigente, pendientes de revisión finita. La herramienta de calidad81 no tiene pip: sus exit1 no son pip0. Runtime WEB92 permanece separado. PG se prepara como234 criterios de negocio actuales, cinco físicas33 con fuente auténtica y restore37 que conserva75 aserciones históricas; pool6 sólo en la carrera R24 original y pool1 en el resto. No se ejecutó ese nuevo catálogo.\n\n'
 'Los147 criterios, incluidos92 originales, y537 archivos untracked se conservan exactos. Sólo servicio web. Free aprobado:10 clientes,1 plan por cliente al día,10 planes totales diarios por gimnasio; mensual20 sin cambio. Sin push, PR, despliegue, cobros ni envíos reales. Retención, países, SLO y piloto mantienen sus decisiones externas pendientes.')
for row in data['requisitos']:
 ident=row['id']
 if ident=='R22':
  row.update(estado='en_revision',implementacion='en_curso',validacion='en_revision',revisor='Seguridad independiente954f:51 propios; revisión de los cuatro blobs exactos integrados75dc.')
  row['commits'].extend(['16c49f3fa183fc7b82b8ed127fab244ce77d9f22','954f2fe719ae25031704f801d7a2fda8fab04b11','75dc61a25fe315c46473d688dd97bdfbb36f87a7'])
  row['cambios'].append('Guía basada en cliente activo y plan propio no borrado con doble joinid/gym, sin inferir descarga/entrega ni browserflag; siguiente acción personal al perfil mientras faltan campos.')
  row['pruebas'].append('Autor31pytest mixtos,16HTTP afectados repetidos tras estilo y7VM; personal3VM. Peer51=19pytest HTTP/SQLite+32VM, sin PG/Chrome ni5+5humanos.')
  row['evidencia'].extend(['evidence/root-onboarding22-author-20261020/summary.json','evidence/root-onboarding22-personal-author-20261020/summary.json','evidence/security-onboarding22-independent-20261020/result.json'])
  row['documentacion'].append('ONBOARDING22.md')
  row['bloqueo']='Faltan recorridos nativos/PG focal actuales y evaluación externa con5dueños/5socios; no se contacta personas sin autorización aplicable.'
 if ident in {'UX-11','UX-17'}:
  row['observaciones'].append('Checkpoint146: onboarding22 integrado75dc, revisión954f51. Corrige sólo falsa exportación/browserflag y acciones personales inertes/copy3datos; no cierre de todos los criterios ni medición humana.')
  row['evidencia'].append('evidence/security-onboarding22-independent-20261020/result.json')
 if ident=='QA-30':
  row.update(estado='en_revision',implementacion='verificado',validacion='en_revision')
  row['commits'].extend(['34707350afcc810e546cbb668dd63089ec7982ae','23a5bb4637b7443c45342760914ce0887f98e4be','c4d9ba37a377fdc972c242e7b132146a91e45c38'])
  row['evidencia'].append('evidence/security-container37-inputs-independent-20261020/result.json')
  row['pruebas'].append('75 seleccionados de inputs57 PASS; sólo contrato estático/firmas, sin57instalados. Portable21objetos peer25+child57 aparte y aún no integrado.')
  row['bloqueo']='Construcción de imagen actual, inventario instalado57, SBOM/SCA y runtime pendientes; portabilidad revisada aún por integrar.'
 if ident=='QA-29':
  row['observaciones'].append('Checkpoint146: V2 nativo3 grupos nuevos completados/pageErrors[] confirma montaje gimnasio; V3timeout sin report no atribuye18 ni rolpersonal. Los rechazos se conservan; validaciónnativa completa pendiente.')
 if ident in {'R05','QA-01','QA-07','OPS07','R18'}:
  row['observaciones'].append('Checkpoint146: último escaneo real8d6RED753 (53956raw/53203finite/15096files); v5c60aislado897/57038,Root753y205distinctenfases/peerpendiente. Bandit22sinbaseline/nuevoCIseriepárciálcon4REDlegacyGoogle; Docker57inputsintegrados,nuevaimagen/SCApendiente.')
  row['evidencia'].append('evidence/root-main-r05-v4-fullscan-20261020/summary.json')
 if ident in {'R13','R16','R19','R27','R31'}:
  row['observaciones'].append('Checkpoint146: nativeV2REJECTED15MFA+3nuevos/PARSER_SyntaxError,cierre normal; V3REJECTEDtimeout420sinreporte/Nodeowncierre125manualyChromeexitporpipe,UUIDnormal/freshausencia. Nueva preparaciónoffline requiereoráculoWebLock/progressporgrupo; no contar18 ni afirmarruntimeR22.')
assert criteria(data)==old
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
for name in ['VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','NUEVOS_HALLAZGOS.md']:
 path=D/name;assert b'## Checkpoint146' not in path.read_bytes();path.write_bytes(path.read_bytes().rstrip()+('\n\n## Checkpoint146\n\n'+paragraph+'\n').encode())
state=(D/'ESTADO.md').read_text(encoding='utf8');history=state[state.index('## Observaciones históricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint146 local: esquema37 y147 requisitos.\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint146\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
(D/'ONBOARDING22.md').write_bytes(('''# Guía de preparación y siguiente acción

El dashboard obtiene `onboarding.client_registered` y `onboarding.plan_saved` de la consulta autorizada de estadísticas. Ambos valores son booleanos. La consulta usa clientes activos no borrados y planes no borrados asociados por cliente y gimnasio; la ventana de KPIs no altera estos hechos. Consultar no escribe. La autorización previa de estadísticas sigue gobernando el acceso.

La guía confirma dos pasos de preparación. Descargar, compartir y recibir requieren acciones posteriores explícitas; guardar un plan no prueba ninguna de ellas. Un objeto ausente, tipos incorrectos o un plan sin cliente confirmado muestran estado desconocido. La interfaz vuelve a consultar hechos propios al abrir la página y deja de usar la antigua marca compartida de navegador. Los dos canarios mantenidos tienen checkout LF para conservar sus bytes en cada plataforma.

En el portal personal, si faltan campos, la tarjeta conduce a `/mi-perfil`. Los controles cuyos listeners todavía no se instalaron permanecen ocultos. La tarjeta explica completar campos requeridos y revisar restricciones; los controles existentes del perfil, sesión, nutrición y generación conservan sus contratos.

Implementación integrada75dc; cuatro blobs exactos16c/89ca. Autor:31pytest mixtos,16HTTP repetidos sólo tras estilo,7VM de dashboard y3VM de personal. Seguridad954f:19pytest HTTP/SQLite en ambas factories y32VM con API/controller reales y transportes declarados. Los canarios conservan RED y PASS. No se suman las repeticiones como casos nuevos.

Continúan pendientes PostgreSQL focal, navegador/reflow actuales y evaluación con5dueños/5socios. No se introducen clientes demo, eventos analíticos o métricas de activación fabricadas. Esta corrección no constituye cierre humano de R22.
''').encode())
checked=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout);(O/'registry.stderr').write_bytes(checked.stderr);assert checked.returncode==0
proof=D/'evidence/checkpoint146-closure-20261020';proof.mkdir();(proof/'.gitattributes').write_bytes(b'* -text\n');(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt={'base':BASE,'requirements':147,'criteria_exact':147,'original_ids':92,'untracked_preserved':537,'product_changed_here':False,'R22_four_product_blobs_integrated':True,'Docker57_inputs_integrated':True,'active_registry_version':4,'last_actual_scan_remaining':753,'native18_accepted':False,'image_or_CI_global_accepted':False}
(proof/'receipt.json').write_bytes(enc(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
names=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','NUEVOS_HALLAZGOS.md','ONBOARDING22.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/n).relative_to(R).as_posix() for n in names])
git('diff','--cached','--check');assert all(sha((R/p).read_bytes())==h for p,h in untracked.items())
assert all(p.startswith('docs/') for p in git('diff','--cached','--name-only').decode().splitlines())
git('commit','-m','Record integrated web onboarding container57 and the remaining native scanner and CI gates')
assert not git('status','--porcelain','-uno').strip()
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),**receipt}))
