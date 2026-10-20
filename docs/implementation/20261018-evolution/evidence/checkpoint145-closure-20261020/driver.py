"""Record current web-only integration and two independently reproduced regressions."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
O=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint145-20261020')
BASE='ce090d8083e79a2f8f66f39539cf31cd98461ed0'
git=lambda *a:subprocess.check_output(['git',*a],cwd=R)
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda o:(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode()
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not git('status','--porcelain','-uno').strip() and not O.exists()
O.mkdir()
data=json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria=lambda value:{row['id']:{k:row[k] for k in ['fuente','seccion','problema','criterio_exacto']} for row in value['requisitos']}
old=criteria(data);assert len(old)==145
untracked=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint144-20261020/untracked-before.json').read_bytes())
assert len(untracked)==537 and all(sha((R/p).read_bytes())==h for p,h in untracked.items())
(O/'untracked-before.json').write_bytes(enc(untracked))
spec=importlib.util.spec_from_file_location('ledger',R/'scripts/implementation_registry.py')
ledger=importlib.util.module_from_spec(spec);spec.loader.exec_module(ledger)
rows=[
 ('QA-29','El montaje predeterminado de recordatorios usa window.Api aunque api.js declara una constante léxica Api; la página real falla al iniciar sin una API inyectada.',
  'Montar recordatorios con la API real de scripts clásicos, sin crear window.Api ni inyectar options.api. Cubrir llamada predeterminada, DOMContentLoaded y documento completo para gimnasio y personal, sin escrituras iniciales ni refresh automático. Mantener cancelación por pagehide, fence del epoch y páginas sin widget. Conservar canarias RED, repetirlas tras la corrección y comprobar el recorrido nativo actual sin pageErrors, sin relajar negocio ni contratos de sesión.',
  ['R27','R13','R31'],'Frontend; QA independiente','en_revision','verificado',
  ['9fd6432a491efd5906e52619cce31acac1356192','6f9d8fa4ba5d5cf73fc981b7c76c32fa7b915300','288df221830dbffec6adf20e99c9a675e86ec8f0'],
  ['evidence/notifications36-bootstrap-20261020/source.json','evidence/qa-notifications29-bootstrap-peer-final-20261020/final-summary.json','evidence/qa-native37-initial-rejected-20261020/final-summary.json'],
  'Autor8:6TypeError+2controles antes,8PASS después. QA propios6:4TypeError+2controles antes,6PASS después;19estado+8DOM+9navegación mantenidos. Total50 ejecuciones seleccionadas después, no deduplicación global ni HTTP/Chrome/PG. Nuevo gate nativo pendiente.',
  'QA independiente6f9d; inversión exacta del operando y11 paths protegidos. Native37 original rechazado y cierre manual conservados.'),
 ('QA-30','El parser del lock de contenedor omite google-auth[pyjwt] y su contrato acepta un contador float equivalente al entero; inventario56 no coincide con requisitos realmente instalables.',
  'Reconocer y canonicalizar todos los requisitos fijados, incluidos extras, preservando nombres, versiones y hashes de cada bloque y rechazando duplicados o entradas ambiguas. Derivar el catálogo completo y su distribución nativa explícita; exigir type(count) is int y correspondencia exacta entre nombres/versiones/conteo del contrato. Preservar el candidato56 rechazado y sus controles literales, preparar un companion explícito para el catálogo corregido y exigir revisión independiente. Validar después la imagen realmente construida y su inventario instalado, sin sustituir esa ejecución por el contrato estático.',
  ['R05','R18','QA-07','OPS07'],'Operación; Seguridad independiente','en_curso','en_curso',
  ['c1ef8f05d8e82cbb642eefbf10780023d67cb3b1','d1721191ef0726c59a4e7fd4a580882008fe51b3'],[],
  'Canarias independientes:1RED float56.0 y8controles en candidato56; parser Requirement independiente:2RED+1control,57web/56container/57runtime. Ningún build, instalación, SCA o runtime57 ejecutado.',
  'Seguridad independiente security_browser36; corrección de autor y replay pendientes.')]
for ident,problem,criterion,tasks,owner,state,implementation,commits,evidence,tests,reviewer in rows:
 row=ledger.record(ident,D/'NUEVOS_HALLAZGOS.md','Checkpoint145 '+ident,problem,criterion,'P2')
 row.update(tareas=tasks,responsable=owner,estado=state,implementacion=implementation,validacion='en_revision',commits=commits,evidencia=evidence,
  pruebas=[tests],documentacion=['NUEVOS_HALLAZGOS.md','VALIDACION.md'],revisor=reviewer)
 row['bloqueo']='Recorrido nativo37 actual pendiente.' if ident=='QA-29' else 'Parser/contrato corregidos, revisión y construcción actual pendientes.'
 data['requisitos'].append(row)
paragraph=(
 'El servicio web integra esquema37, seguridad de cuenta y sesiones R31, notificaciones36/UI27, la reparación móvil de tres CSS y el catálogo finito de escaneo v4. El último cambio de producto288df corrige un operando del montaje de recordatorios: usa la constante léxica Api que declara api.js. API, backend y primitivas de sesión permanecen exactos. QA-29 conserva6 canarias del autor y4 propias TypeError antes; después pasan8+6 y36 comprobaciones mantenidas,50 ejecuciones seleccionadas offline. La aceptación nativa sigue pendiente.\n\n'
 'El primer navegador37 sí ejecutó15 grupos MFA originales (11profesionales y4personales), con pageErrors vacíos en ese alcance. La nueva selección18 se detuvo en el primer grupo de recordatorios:0 grupos nuevos completos,Timeout y un TypeError sin stack capturado. El gate combinado33 quedó rechazado y se conserva íntegro. El cierre normal excedió45 segundos: se cerró únicamente el proceso propio verificado, se confirmó cero sesiones, DROP ordinario y ausencia fresca de la UUID. No se afirma normal_server_exit. QA prepara el nuevo freeze con el fix y un observer privado; aún no inició otro PG/Chrome.\n\n'
 'La superposición del menú móvil pasa de16/16RED a16/16PASS con las mismas canarias Chrome geométricas y DOM inerte declarado, sin SQL. Las tres CSS integradascd423 coinciden con autor78aa y revisión3c257; scripts y plantillas no cambian. Esto prueba esa geometría, no accesibilidad completa ni todos los flujos nativos.\n\n'
 'V4 está integrado663d:877 rutas,56285 pins,641 registros v3 exactos y85 sustituciones explícitas cuyo historial se conserva. ROOT verifica11016 ubicaciones antiguas con475 negativos; Seguridad repite11016 positivos,1652 mutaciones de archivo y4 controles de anclaje. La fixture contiene sólo los bytes originales del manifiesto histórico, sin recuperar ni reconstruir auth-guard. Su peer pasa37/37. El primer gate del autor fue157PASS/5fallos de fixture; tras la corrección pasó37/37, y MAINactual pasa162/162. Son pruebas y replay del informe405, no un nuevo escaneo global. El último escaneo real sigue RED11016; el nuevo árbol y la alerta literal de identidad del test bootstrap necesitan escaneo y clasificación finita.\n\n'
 'CI se limita al SaaS y excluye cinco pruebas de licencia offline desktop, además de sus seis módulos explícitos. La ejecución amplia anterior se canceló antes de esos casos; no es un PASS. La colección actual deOps tiene4722 IDs:4716 runtime37 y6 físicas35 separadas; el verificador33 se ejecuta sobre fuente histórica auténtica, sin reconstruir imagen antigua. Serial/cobertura, paralelo, PostgreSQL/Redis/navegador e imagen actual conservan sus gates pendientes. QA-30 documenta que el inventario56 omitía google-auth con extras y aceptaba float: parser independiente deriva57 distribuciones runtime. Se corrige antes de construir; firmas APT/PSF offline no sustituyen imagen, SCA o ejecución.\n\n'
 'El registro conserva145 criterios exactos y añade QA-29 yQA-30:147 IDs, incluidos92 originales. Los537 archivos untracked siguen intactos. Free aprobado:10 clientes,1 plan por cliente al día,10 planes totales diarios por gimnasio; mensual20 sin cambio. Trabajo exclusivo del servicio web. Sin push, PR, despliegue, cobros ni envíos reales. Decisiones externas de retención, países, SLO y piloto siguen abiertas sin repetir consultas.')
for row in data['requisitos']:
 ident=row['id']
 if ident in {'R13','UX-09'}:
  row['observaciones'].append('Checkpoint145:3CSScd423 exactas autor78aa/QA3c257;16geométricosRED→16PASS enChromeDOMinerte/sinSQL;criterioscompletosaccesibilidad/recorridosnativospendientes.')
  row['evidencia'].extend(['evidence/qa-native37-mobile-before-20261020/manifest.json','evidence/qa-native37-mobile-after-20261020/manifest.json'])
 if ident in {'R05','R18','QA-01','QA-07','OPS07'}:
  row['observaciones'].append('Checkpoint145:v4integrado663d,MAIN162PASS/peer11016+1652+4neg/fixturepeer37PASS;últimofullscan405RED11016,nuevoárbolpendiente.QA30conteo56rechazado,57esperadopendienteimagen;noSCAactualPASS.')
  row['evidencia'].extend(['evidence/root-main-r05-v4-current-20261020/summary.json','evidence/security-r05-v4-independent-20261020/manifest.json','evidence/security-r05-v4-fixture-independent-20261020/manifest.json'])
 if ident in {'R27','R31','R16','R19'}:
  row['observaciones'].append('Checkpoint145:native37primer15MFAoriginalesPASS,0/18nuevoscompletos;gate33REJECTEDporbootstrapQA29,fix288df/peer50offlinePASS;replaynativopendiente. Cierremanualtras45stimeout/DROPnormal/ausenciafresca,nonormalexit.')
assert {k:v for k,v in criteria(data).items() if k in old}==old and len(criteria(data))==147
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
for name in ['VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','NUEVOS_HALLAZGOS.md']:
 path=D/name;assert b'## Checkpoint145' not in path.read_bytes()
 text=paragraph
 if name=='NUEVOS_HALLAZGOS.md':text='\n\n'.join('### '+x[0]+'\n\n'+x[1]+'\n\nAceptación: '+x[2] for x in rows)+'\n\n'+paragraph
 path.write_bytes(path.read_bytes().rstrip()+('\n\n## Checkpoint145\n\n'+text+'\n').encode())
state=(D/'ESTADO.md').read_text(encoding='utf8');history=state[state.index('## Observaciones históricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint145 local: esquema37 y147 requisitos.\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint145\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
checked=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout);(O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode==0,checked.stdout.decode(errors='replace')+checked.stderr.decode(errors='replace')
proof=D/'evidence/checkpoint145-closure-20261020';proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt={'base':BASE,'requirements':147,'previous_criteria_exact':145,'original_ids':92,'untracked_preserved':537,
 'product_changed':False,'schema':37,'QA29_offline_selected':50,'QA29_native_pending':True,'QA30_image_pending':True,
 'mobile_geometry_before_red':16,'mobile_geometry_after_pass':16,'current_v4_unit_pass':162,'fresh_scan_accepted':False,
 'scope':'web SaaS only','external_operations':False}
(proof/'receipt.json').write_bytes(enc(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
names=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','NUEVOS_HALLAZGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/n).relative_to(R).as_posix() for n in names])
git('diff','--cached','--check')
assert all(sha((R/p).read_bytes())==h for p,h in untracked.items())
assert all(p.startswith('docs/') for p in git('diff','--cached','--name-only').decode().splitlines())
git('commit','-m','Record web-only mobile scanner and bootstrap integration with remaining release gates')
assert not git('status','--porcelain','-uno').strip()
result={'head':git('rev-parse','HEAD').decode().strip(),**receipt}
(O/'result.json').write_bytes(enc(result));print(json.dumps(result))
