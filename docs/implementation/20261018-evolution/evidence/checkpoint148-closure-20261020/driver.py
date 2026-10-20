"""Keep all exact requirements while recording only verified web progress."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R / 'docs/implementation/20261018-evolution'
T = Path('C:/Users/Consu/AppData/Local/Temp')
O = T / 'metodobase-checkpoint148-20261020'
BASE = '71d5915d667870245b682eef7cddb08abf508d55'
git = lambda *a: subprocess.check_output(['git', *a], cwd=R)
sha = lambda b: hashlib.sha256(b).hexdigest()
enc = lambda o: (json.dumps(o, ensure_ascii=False, indent=2) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == BASE and not git('status', '--porcelain', '-uno').strip() and not O.exists()
O.mkdir()
data = json.loads((D / 'TRAZABILIDAD.json').read_bytes())
criteria = lambda d: {r['id']: {k: r[k] for k in ['fuente', 'seccion', 'problema', 'criterio_exacto']} for r in d['requisitos']}
old = criteria(data)
assert len(old) == 147
untracked = json.loads((T / 'metodobase-checkpoint147-20261020/untracked-before.json').read_bytes())
assert len(untracked) == 537 and all(sha((R / p).read_bytes()) == h for p, h in untracked.items())
(O / 'untracked-before.json').write_bytes(enc(untracked))
paragraph = (
    'Trabajo y entrega exclusivamente del servicio web, esquema37 y147 requisitos (92 originales y55 añadidos), con criterios y537 archivos untracked conservados exactos. Free mantiene10 clientes,1 plan por cliente al día,10 planes totales por gimnasio al día y mensual20 sin cambio. Sin trabajo desktop, push, PR, despliegue, cobros ni envíos reales.\n\n'
    'R22 tiene aceptación nativa focal V5:2/2 grupos sobre PostgreSQL37 y Chrome,8 capturas, cero pageErrors/axe scoped/overflow, finalizador de los dos actores alcanzado, servidor y launcher exit0, una UUID quinta acumulada con DROP normal/cero sesiones/ausencia fresca y14 procesos propios cerrados. Los15 MFA y18 account/notifications previos conservan sus fuentes y límites; no se afirma aceptación combinada actual de35. V4 sigue rechazado pese a completar su driver18: falló addon y cierre45s, finalizador no alcanzado; su recuperación manual permanece explícita. El diagnóstico de cabeceras preserva no-store/referrer general para estadísticas y no-referrer para perfil; sólo se corrigió el helper de prueba, sin cambiar la política de producto.\n\n'
    'La inspección nativa identificó texto estrecho a390px. MAIN962d integra únicamente dos líneas CSS revisadas: el texto dispone de su fila móvil antes de la acción. QA independiente reproduce el defecto390 con el CSS anterior y acepta320/360/390/480/640/641/768/1440,16 geometrías y9 capturas, cero pageErrors/red, cierre normal y entorno estable;641/768/1440 conservan geometría. Es render aislado con fragmentos auténticos y hechos sintéticos declarados, no otro E2E autenticado. PostgreSQL focal35 y evaluación humana5dueños/5socios siguen pendientes.\n\n'
    'V6 está integrado95382:903 rutas/57261 anclajes,897 registros V5 exactos y seis archivos/223 ubicaciones añadidas desde la propuesta semántica revisada. ROOT verifica el artefacto real con223 positivos y54 negativos, sin cambio de algoritmo salvo tres literales; MAIN95382 pasa109/109 seleccionados y Ruff3. El escaneo completo realb0fa conserva15324 archivos estables y usa Gitleaks8.30.1 verificado:54180 alertas,54179 clasificaciones finitas y una pendiente, exit1. Las223 anteriores quedan resueltas. Seguridad recalcula independientemente el checksum nombrado de esa ubicación nueva con1 positivo,15 negativos semánticos y7 de anclaje; su propuesta no activa una excepción. V7 y otro escaneo actual aún pendientes; R05 global sigue abierto/RED1.\n\n'
    'El registro separado Bandit22 queda aprobado sólo para sus fuentes/contexto/30d y dos conjuntos completos de bytes autenticados, con baseline histórico intacto. Ops y su peer contrastan el gate real2c0; en MAIN962d pasan lint/sintaxis/Bandit y9 pruebas negativas con6 controles, además56/56 pytest de consumidor y contrato independiente, sin errores/skips. Bandit1.9.4 conserva28 ocurrencias:6 históricas (5 fingerprints únicos) y22 aprobadas, cero pendientes/errores. Fuente1372,WEB92/tool81/Node157/binarios estables. WEB pip0/0; tool81 carece de pip, sin claim de consistencia pip. Esto no acepta aislamiento compartido, imagen, SCA o CI amplio.\n\n'
    'Serial847 conserva4725PASS/60FAIL/1skip Windows; companions actuales Google/retención pasan70/70 y lookup16/16, sin modificar los originales ni convertir847 en PASS. Ops prepara fases históricas V5peer60/V6autor48 con transporte Git autenticado y n2 actual, sin retarget ni eliminación de criterios. PostgreSQL429 está preparado/coleccionado en29 grupos con26 controles offline, todavía sin SQL; añade35R22,31seguridad y9QA26 a354 previos. La lectura real de VM devolvió guest con3.50GiB libres, memoria/cache72/nonce correctos y apagado QMP normal; no hubo upload/build. Imagen57, inventario instalado, SBOM/SCA, Redis y CI amplio actual siguen pendientes. Retención, países, SLO, piloto, revisión profesional nutricional y custodia/recuperación externa conservan decisiones o participación reales pendientes.')
for row in data['requisitos']:
    ident = row['id']
    if ident in {'R22', 'UX-11', 'UX-17', 'R13', 'UX-09'}:
        row['commits'].extend(['a4382cd0b3652bd14b739f98224a20e94556e3b9', '962d7516d45a95e0a8ce6b2946a1ea070985e944', BASE])
        row['evidencia'].extend(['evidence/qa-native37-v5-r22-final-20261020/final-summary.json', 'evidence/qa-r22-mobile-layout-independent-20261020/final-summary.json'])
        row['observaciones'].append('Checkpoint148: R22V5 dos gruposPG37/ChromePASS con finalizador/cierre normal; CSS390 reparado exactamente2líneas y render aislado8anchuras/16geometríasPASS. No35E2E combinado actual ni5+5 humanos; PGfocal35 pendiente.')
    if ident in {'R05', 'QA-01', 'QA-07', 'OPS07', 'R18', 'QA-30'}:
        row['commits'].extend(['95382f0193857463b6537748bbe16adb857e0b49', 'b0fa556346a0097cd8a4372d586184a100758737', '2e1d255f6d0c68e7697a4532ea54cca4bac40a82', 'a8b41c84c4a875ccebd304327ab72b2ae33a135f', BASE])
        row['evidencia'].extend(['evidence/root-main-v6-current-20261020/summary.json', 'evidence/root-main-r05-v6-fullscan-20261020/summary.json', 'evidence/root-main-quality22-current-20261020/summary.json'])
        row['observaciones'].append('Checkpoint148: V6actual109/109 yROOTartifact223positivos/54negativos. Fullscanb0fa RED1=54180raw/54179finite/15324stable; checksumfinal peerrevisado sinactivarV7. BanditMain962dactual28=6baseline+22approved/0pending,4toolsteps+9neg/6ctrl y56pytestPASS; tool81sinpip/WEB92pip0/0. CI84760FAIL intacto; companions70+16PASS, n2/imagen/SCA pendientes. PG429coleccionado/26controlesoffline sinSQL.')
    if ident == 'QA-30':
        row['bloqueo'] = 'Portable integrado y gates focales PASS; VM preflight lectura/apagado normal. Faltan build actual57, inventario instalado, SBOM/SCA y runtime de imagen.'
    if ident in {'R16', 'R19', 'R27', 'R31', 'QA-29'}:
        row['observaciones'].append('Checkpoint148: V4driver18 completo pero all20REJECTED/finalizador no alcanzado/cierre manual explícito. V5sólo2R22PASS con finalizador/cierre normal y cincoUUID acumuladas. Nuevo35grupos actual sólo preparación offline; no reatribuir15/18 anteriores. PG429aún sinSQL; no imagen/entrega real.')
assert criteria(data) == old
(D / 'TRAZABILIDAD.json').write_bytes(enc(data))
for name in ['VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md']:
    path = D / name
    assert b'## Checkpoint148' not in path.read_bytes()
    path.write_bytes(path.read_bytes().rstrip() + ('\n\n## Checkpoint148\n\n' + paragraph + '\n').encode())
state = (D / 'ESTADO.md').read_text(encoding='utf8')
history = state[state.index('## Observaciones históricas'):]
(D / 'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint148 local: esquema37 y147 requisitos.\n\n' + paragraph + '\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n' + history + '\n## Checkpoint148\n\n' + paragraph + '\n').encode())
(D / 'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n' + paragraph + '\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
onboarding = D / 'ONBOARDING22.md'
text = onboarding.read_text(encoding='utf8')
old_pending = 'Continúan pendientes PostgreSQL focal, navegador/reflow actuales y evaluación con5dueños/5socios.'
assert text.count(old_pending) == 1
text = text.replace(old_pending, 'El gate nativo focal de dos casos y el ajuste móvil posterior tienen aceptación separada registrada en Checkpoint148. Continúan pendientes PostgreSQL focal35, E2E combinado actual y evaluación con5dueños/5socios.')
onboarding.write_bytes((text.rstrip() + '\n\nCheckpoint148: nativo V5 R22 pasa2/2 con8 capturas y cierre/finalizador normales; CSS móvil integrado962d pasa revisión independiente con8 anchuras y16 geometrías de render aislado. No son35 grupos E2E actuales ni validación humana. [Evidencia móvil](evidence/qa-r22-mobile-layout-independent-20261020/final-summary.json).\n').encode())
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=R, capture_output=True)
(O / 'registry.stdout').write_bytes(checked.stdout)
(O / 'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
proof = D / 'evidence/checkpoint148-closure-20261020'
proof.mkdir()
(proof / '.gitattributes').write_bytes(b'* -text\n')
(proof / 'driver.py').write_bytes(Path(__file__).read_bytes())
receipt = {'base': BASE, 'requirements': 147, 'criteria_exact': 147, 'original_ids': 92,
    'untracked_preserved': 537, 'product_changed_here': False, 'active_registry_version': 6,
    'last_actual_scan_remaining': 1, 'Main_quality56': True, 'native_R22_groups': 2,
    'mobile_render_widths': 8, 'PG429_executed': False, 'image_or_CI_global_accepted': False}
(proof / 'receipt.json').write_bytes(enc(receipt))
git('-c', 'core.autocrlf=false', 'add', '-f', '--', proof.relative_to(R).as_posix())
names = ['TRAZABILIDAD.json', 'TRAZABILIDAD.md', 'ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md', 'ONBOARDING22.md']
git('-c', 'core.autocrlf=true', 'add', '--renormalize', '--', *[(D / n).relative_to(R).as_posix() for n in names])
git('diff', '--cached', '--check')
assert all(sha((R / p).read_bytes()) == h for p, h in untracked.items())
assert all(p.startswith('docs/') for p in git('diff', '--cached', '--name-only').decode().splitlines())
git('commit', '-m', 'Record current web quality native onboarding mobile fix and remaining execution gates')
assert not git('status', '--porcelain', '-uno').strip()
print(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), **receipt}))
