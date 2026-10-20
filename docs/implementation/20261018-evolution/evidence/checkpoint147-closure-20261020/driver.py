"""Preserve web-only scope and exact criteria while recording real current gates."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018');D=R/'docs/implementation/20261018-evolution'
O=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint147-20261020')
BASE='3c56e5a9262874afb096f5012800054f3fdd2413'
git=lambda *a:subprocess.check_output(['git',*a],cwd=R)
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda o:(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode()
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','-uno').strip() and not O.exists()
O.mkdir();data=json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria=lambda d:{r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in d['requisitos']}
old=criteria(data);assert len(old)==147
untracked=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint146-20261020/untracked-before.json').read_bytes())
assert len(untracked)==537 and all(sha((R/p).read_bytes())==h for p,h in untracked.items());(O/'untracked-before.json').write_bytes(enc(untracked))
paragraph=(
 'MAIN mantiene esquema37 y147 requisitos, exclusivamente del servicio web. El onboarding integrado pasa35/35 pytest mixtos HTTP/SQLite y42/42 comprobaciones Node seleccionadas sobre63c, con1344 fuentes y92 distribuciones estables. Son hechos persistidos propios y estados de interfaz; no acreditan navegador, PostgreSQL ni5dueños/5socios. R22 sigue abierto para esos criterios. El código web conserva los cuatro blobs revisados75dc y las correcciones previas de cuenta, sesiones, recordatorios y móvil.\n\n'
 'La autoridad portable Docker72 ya está integrada c11d:21 objetos Git originales, rutas Merkle y pin del ZIP, sin requerir Git en el companion aislado. Conserva12 entradas Docker57 exactas y el lock web; no se importan workflows todavía. V5 también está activo924e:897 rutas/57038 pins,877 registros anteriores exactos y algoritmo del loader idéntico salvo tres literales. Su peer4ed acepta264 criterios distintos en fases (204 heredados y60 propios), con un semántico750 excluido expresamente del peer y ya revisado por ROOT;261PASS iniciales y37PASS de replay reparan sólo tres fixtures físicas, sin alterar aserciones. Se conservan sus intentos de checkout y framing rechazados. En el MAIN integrado924e pasan347/347 en una sola selección:265 del escáner y82 de portabilidad, sin errores ni skips. Un caso portable ejecuta57 hijos en árbol nuevo sin Git/red/procesos; no se añaden al347. Fuentes1358/Python92/Node estables y Ruff12 módulos PASS. Imagen, inventario instalado57, SBOM y SCA actuales siguen pendientes.\n\n'
 'El nuevo escaneo completo realca09 usa Gitleaks8.30.1 verificado,15244 archivos estables y256.766s:54179 alertas,53956 clasificaciones finitas y223 pendientes, exit1. Resuelve las753 ubicaciones del escaneo8d6; las223 nuevas están en seis archivos de metadatos de cuenta/entorno/receta y requieren revisión por preimagen/pointer/línea antes de clasificarse. No se aprueban por forma ni por texto del scanner. El resultado actual es RED223, no CI o R05 global PASS. El informe completo y mapas permanecen privados protegidos; los históricos RED1603/11016/753 conservan sus fuentes.\n\n'
 'La fase runtime de la suite amplia serial847 terminó4725PASS/60FAIL/1skip Windows,0errors y4786 identidades exactas,3008.04s. Las seis físicas históricas35 no se ejecutaron tras ese rechazo. Conserva41 fallos de framing de fixtures antiguas,14 del contrato antiguo de seguimiento,4 del transporte Google antiguo y uno de expectativa de lookup pre-tenant. Este último pasó status422 y falla sólo al exigir la verificación Bearer en el login público: QA26 la elimina intencionadamente antes de establecer el nuevo sujeto. Se preparan companions explícitos con criterios actuales y originales intactos; no se atribuye retrospectivamente PASS al847. Paralelo y cobertura final actuales siguen pendientes. Calidad web pasa F821/sintaxis y9 controles; Bandit28/22 sin baseline vigente sigue en revisión finita independiente. El entorno de calidad81 no tiene pip y conserva exit1; WEB92 separado conserva pip0.\n\n'
 'Navegador37 continúa rechazado por los intentos V1/V2/V3 preservados. V3 agotó420s sin reporte final y no tiene conteo18 aceptado; Node propio cerró125 bajo ACK por identidad y Chrome salió por pipe, servidor/UUID por cierre normal y ausencia fresca. V4 se prepara offline: canario con API y WebLock reales prueba que B no puede completar antes de liberar el ACK de A, conserva el oráculo legacy RED y3PASS con orden serializado; journal privado fsync tiene8 controles. Se mantiene el producto R31 y se añade un addon R22 de dos actores sintéticos, separado de18. Todavía no se inició SQL/Chrome ni se aceptó all20. PG tiene preparación354 IDs/24 módulos y19 controles, sin SQL; incluye234 criterios legacy37,12 migración37,13 nutrición,29 notificaciones,35 cuenta,30 peer y un restore37. R22 focal adicional y físicas33 auténticas conservan sus gates propios; pool6 sólo en la carrera R24 y pool1 en el resto.\n\n'
 'Los147 criterios, incluidos92 originales, y537 archivos untracked se conservan exactos. Desktop queda fuera de desarrollo, pruebas, instaladores e integración actuales. Los manifiestos históricos con ese nombre usados como fixtures de checksums no son ejecución del producto. Free aprobado:10 clientes,1 plan por cliente al día,10 planes totales diarios por gimnasio y mensual20 sin cambio. Sin push, PR, despliegue, cobros ni envíos reales. Retención, países, SLO y piloto mantienen sus decisiones externas pendientes.')
for row in data['requisitos']:
 ident=row['id']
 if ident=='R22':
  row['commits'].append('bc67207f141eb41e1cfd079ce8cf4256d86f00ce')
  row['pruebas'].append('MAIN63c:35/35 HTTP/SQLite y42/42Node seleccionados; fuente1344/Python92/Node quiet. No PG,Chrome ni5+5 humanos.')
  row['evidencia'].append('evidence/root-main-onboarding22-current-20261020/summary.json')
 if ident in {'UX-11','UX-17'}:
  row['observaciones'].append('Checkpoint147: MAIN63c pasa35HTTP/SQLite+42Node de onboarding; no aceptación PG/nativa/humana. Addon2 sintético preparado separado de18, no ejecutado.')
 if ident in {'R05','QA-01','QA-07','OPS07','R18','QA-30'}:
  row['commits'].extend(['c11d3182580d1c4486099a4991cf3a41663617e8','924e6f6ae96589326ef1b0400c36c37d734b0c59','ca09d2f803bcd1e2b977db7b708fa6559c9b5617','3c56e5a9262874afb096f5012800054f3fdd2413'])
  row['evidencia'].extend(['evidence/root-main-v5-portable-current-20261020/summary.json','evidence/root-main-r05-v5-fullscan-20261020/summary.json'])
  row['observaciones'].append('Checkpoint147: portable21objetos yV5 integrados; actual347/347PASS fuente924e (265scanner+82portable, child57 no sumado). Nuevo scanrealca09 RED223=54179raw/53956finite/15244stable. Serial847runtime4725P/60F/1skip,0E/4786exactos; companions pendientes. Bandit22 revisión independiente; imagen57/SBOM/SCA/paralelo actual pendientes.')
 if ident=='QA-30':
  row['bloqueo']='Portable integrado c11d y347focal PASS; faltan construcción actual, inventario instalado57, SBOM/SCA y runtime de imagen.'
 if ident in {'R13','R16','R19','R27','R31','QA-29'}:
  row['observaciones'].append('Checkpoint147: V4 sólo preparación offline con3 canarios WebLockPASS/oráculo antiguoRED y8controlesjournal; addonR22=2 separado de18, all20 no iniciado. V3timeout sin18aceptados y cierre propio125/Chromepipe/UUIDnormal se conserva. PG354 preparado sinSQL; ningún resultado nativo actual nuevo.')
assert criteria(data)==old
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
for name in ['VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','NUEVOS_HALLAZGOS.md']:
 path=D/name;assert b'## Checkpoint147' not in path.read_bytes();path.write_bytes(path.read_bytes().rstrip()+('\n\n## Checkpoint147\n\n'+paragraph+'\n').encode())
state=(D/'ESTADO.md').read_text(encoding='utf8');history=state[state.index('## Observaciones históricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint147 local: esquema37 y147 requisitos.\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint147\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
onboarding=D/'ONBOARDING22.md';onboarding.write_bytes(onboarding.read_bytes().rstrip()+b'\n\n'+('Aceptación focal actual: MAIN63c pasa35/35pytest mixtos HTTP/SQLite y42/42Node seleccionados, conservados en [la evidencia integrada](evidence/root-main-onboarding22-current-20261020/summary.json). No extiende este resultado a PostgreSQL, navegador ni participantes humanos.\n').encode())
checked=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout);(O/'registry.stderr').write_bytes(checked.stderr);assert checked.returncode==0
proof=D/'evidence/checkpoint147-closure-20261020';proof.mkdir();(proof/'.gitattributes').write_bytes(b'* -text\n');(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt={'base':BASE,'requirements':147,'criteria_exact':147,'original_ids':92,'untracked_preserved':537,'product_changed_here':False,'active_registry_version':5,'last_actual_scan_remaining':223,'integrated_focused_cases':347,'serial_847_failed':60,'native20_accepted':False,'image_or_CI_global_accepted':False}
(proof/'receipt.json').write_bytes(enc(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
names=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','NUEVOS_HALLAZGOS.md','ONBOARDING22.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/n).relative_to(R).as_posix() for n in names])
git('diff','--cached','--check');assert all(sha((R/p).read_bytes())==h for p,h in untracked.items())
assert all(p.startswith('docs/') for p in git('diff','--cached','--name-only').decode().splitlines())
git('commit','-m','Record web-only integrated scanner portability onboarding and the remaining current gates')
assert not git('status','--porcelain','-uno').strip()
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),**receipt}))
