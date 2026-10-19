from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

root = Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
run = root / 'docs/implementation/20261018-evolution'
ev = run / 'evidence'
base = '1be3b671b106bee6447ea47377d2596fde12d0b1'
candidate = '2273616eb218adfdd30680e111da50a4599a8c53'
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.autocrlf=false', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == base and not git('diff', '--cached', '--name-only')
receipt = json.loads((tmp / 'metodobase-checkpoint128-prepare-result.json').read_bytes())
assert receipt['base'] == base and receipt['candidate'] == candidate
names = sorted(receipt['files'])
for name, meta in receipt['files'].items():
    blob = (root / name).read_bytes()
    assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256'], name
for name in receipt['source_paths']:
    assert (root / name).read_bytes() == git('show', candidate + ':' + name), name
definition = next(n for n in ast.parse((tmp / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
data = json.loads((run / 'TRAZABILIDAD.json').read_bytes())
fields = ['fuente', 'seccion', 'problema', 'criterio_exacto']
criteria = lambda value: {row['id']: {field: row[field] for field in fields} for row in value['requisitos']}
before = criteria(data)
assert len(before) == 126
notes = {
    'R02': 'Integración local32 de la fuente227, sin desplegar. SEC17 Google permanece en implementación33 y revisión pendiente; no se considera cerrada la asociación por correo.',
    'R05': 'MAIN incorpora fuentes revisadas31/32. Las dos regresiones completas y cobertura siguen atribuidas sólo a de506/esquema31; no se trasladan a32. CI vigente31 es histórico y requiere evolución coherente para33. Triage root del informe gitleaks original:31.282 ubicaciones checksum candidatas y282 pendientes; Seguridad las revisa independientemente, sin cambio de scanner ni allowlist. No hay un nuevo escaneo global verde.',
    'R12': 'MFA31 y consumidor vigente se integran junto a32 con blobs de227 exactos. ParentOFF continúa denegando la sesión general; el retiro separado sólo concede autoridad limitada sobre eventos propios tras primaria y factor frescos.',
    'R19': 'QA independiente en219:45VM+8SSR+8HTTP,13grupos Chrome/9capturas,0axe/overflow/pageerrors.8HTTP idénticos repetidos en227 tras delta único _execute. Chrome permanece atribuido219; móduloASTfuera_execute exacto.344fuentes runtime/89metadata/binarios/drivers quietos,pips0; servidor/listener y9generaciones Node/Chrome propios ausentes.',
    'R25': 'Código32 integrado localmente desde227, con lector/mediciones/export/consentimientos/UI y retiro freshproof. SEC18 revisado independientemente:79SQLite/30PG PASS, mismos75/26IDs originales+4controles por dialecto. Los cuatro rojos originales quedan verdes con checkout0 antes de cleanup del harness. Si invalidate también falla antes de liberar sigue checkout1/503/contextorestaurado: límite explícito, no garantía universal.3UUID PG cerradas sin sesiones/FORCE y ausencia fresca. CI/regresión amplia32 e imagen final pendientes.',
    'R31': 'Retiro público conectado y revisado acotadamente; no cierra recuperación Google-only/lostallfactor, retención, borrado ni controles globales. Mantiene límites, CAS, factor fresco, estados409/503 veraces y ausencia de tokens/storage nuevos. No se expande sesión general ni se atribuye explotación al fallo compuesto de recursos.',
    'R32': 'MFA31 revisado se integra con32, incluidos MAX_SV/fixtures/privacy y UI. Google33 aún aislado: issuer/sub, verificador de producción, enlace/desenlace y UI en curso; aceptación de alertas/custodia/proveedores/recuperación total sigue pendiente.',
    'SEC18': 'Corrección227 integrada: close de Session nueva en finally e invalidate sólo si falla close, sin dispose global ni retag ambiental. Inversa de route a219 exacta. Autor6SQLite, peer79SQLite/30PG, QA8HTTP idénticos; modelos de invalidate imposible antes/después documentados sin ocultar checkout1 en fallo irrecuperable.'}
refs = {
    'R05': ['root-gitleaks-checksum-triage-prepared-20261019/summary.json'],
    'R19': ['qa-retirement32-review219-20261019/review.json', 'qa-retirement32-review227-20261019/review.json'],
    'R25': ['security-retirement-owned-cleanup-independent-20261019/source.json', 'qa-retirement32-review219-20261019/review.json', 'qa-retirement32-review227-20261019/review.json'],
    'R31': ['qa-retirement32-review227-20261019/review.json'],
    'SEC18': ['root-retirement32-owned-cleanup-20261019/source.json', 'security-retirement-owned-cleanup-independent-20261019/source.json', 'qa-retirement32-review227-20261019/review.json']}
for row in data['requisitos']:
    if row['id'] in notes:
        row['observaciones'].append('Checkpoint128: ' + notes[row['id']])
        if row['id'] != 'SEC18' and candidate not in row['commits']:
            row['commits'].append(candidate)
    for ref in refs.get(row['id'], []):
        assert (ev / ref).is_file(), ref
        if 'evidence/' + ref not in row['evidencia']:
            row['evidencia'].append('evidence/' + ref)
    if row['id'] == 'SEC18':
        row['implementacion'] = 'en_revision'
        row['validacion'] = 'verificado'
        row['commits'] += [candidate, '67743467c13b657f947a9a93310d0b49582a3752']
        row['cambios'].append('Fallback de invalidación local de la nueva Session integrado con revisión independiente; no se afirma liberar una conexión cuando también su invalidación falla antes de liberar.')
assert criteria(data) == before
(run / 'TRAZABILIDAD.json').write_bytes(enc(data))
(run / 'ESTADO.md').write_text('''# Estado de implementación

Checkpoint128 local: MAIN incorpora esquema32 desde la candidata revisada2273616. Se conservan126 requisitos,92 originales y34 nuevos, con126 criterios exactos. Free:10 clientes activos,1plan por cliente al día y10totales por gimnasio al día; desktop soportado. Workspace de referencia intacto. Sin push,PR,despliegue,cargos ni comunicaciones reales.

La integración conecta MFA31, mediciones/progreso32, lector con consentimiento explícito, octava sección de exportación y retiro público con primaria+factor nuevos por operación. Cada fuente integrada coincide byte a byte con227; Dockerfile y locks no cambian. La misma fuente local aún requiere CI y regresión amplia vigente, imagen y matriz común; no se trasladan los resultados amplios31 a32. [Equivalencia](evidence/prepared-wave128-20261019/source-equivalence.json).

Retiro: QA219 cerró45VM,8SSR y8HTTP propios,13grupos Chrome y9capturas sin fallos axe/overflow/JS. Los mismos8HTTP pasaron227; Chrome se atribuye sólo219 y se documenta el delta único _execute. Seguridad227:79SQLite y30PG PASS, casos originales75/26 intactos y4controles nuevos por dialecto. El modelo original libera checkout; si también invalidate falla antes de liberar persiste checkout1,503/contexto restaurado, límite explícito. Tres UUID PG y todos los procesos propios del browser cerrados. [QA](evidence/qa-retirement32-review227-20261019/review.json), [Seguridad](evidence/security-retirement-owned-cleanup-independent-20261019/source.json).

Histórico31de506: serial y n2 cerraron3056PASS+1skipWindows exacto por modo; cobertura crítica serial100%. Estas pruebas no representan toda la integración32. Imagen31f74 conserva sello parcial y VM propia apagada; el próximo artefacto corresponde a la fuente final revisada33.

SEC17 Google permanece en implementación33: asociación issuer/sub, alta nueva vacía sin adoptar cuentas por correo, enlace/desenlace explícitos, verificador de producción y consumidor UI. Sus revisiones y composición siguen pendientes. Google-only con sub histórico desconocido y pérdida total de factores no se dan por recuperados.

Gitleaks sigue sin aceptación global: del informe original se prepararon31.282 clasificaciones candidatas de checksum y282 ubicaciones pendientes; Seguridad revisa por ubicación y con falsificación adversarial. No cambian scanner ni exclusiones. Checksums derivados GitLF→CRLF no son RAW de una ejecución reconstruida. [Triage preparado](evidence/root-gitleaks-checksum-triage-prepared-20261019/summary.json).

Siguiente acción: completar/revisar33 y su UI, componer con esta integración, evolucionar CI vigente sin borrar fixtures históricos, ejecutar regresión y preparar el artefacto final. Continuar pendientes de roadmap sin inventar decisiones comerciales, participantes, proveedores reales ni producción. [Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''', encoding='utf8')
(run / 'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint128 integra localmente esquema32 desde2273616 con fuentes exactas y126 criterios conservados. MFA/progreso/consentimientos/exportación/retiro conectados; revisión focal de retiro:79SQLite/30PG y8HTTP, con browser219 separado. CI/regresión amplia vigente, artefacto final y Google33 siguen pendientes. [Estado](ESTADO.md), [registro](TRAZABILIDAD.md).

Histórico31:3056PASS+1skipWindows serial y n2, cobertura crítica100%; imagenf74parcial. Gitleaks todavía sin aceptación global:31.282 checksum candidatos/282pendientes en revisión independiente, sin nuevo scan verde. Free10clientes/1plancliente/día/10totalgym/día; desktop soportado. No publicación ni despliegue.
''', encoding='utf8')
sections = {
    'CAMBIOS.md': 'Integración local real desde227: MFA31, progreso/mediciones32, lector y consentimientos, exportación y UI/retiro público. Fuentes y tests de la candidata se copian exactamente; control/evidencias históricos de MAIN se conservan. No se altera Dockerfile ni locks. El retiro invalida sólo su Session nueva ante close fallido; el resto del módulo y servicio permanecen exactos. Google33 no se integra todavía.',
    'VALIDACION.md': notes['R19'] + ' ' + notes['R25'] + ' ' + notes['R05'],
    'DECISIONES.md': 'Integrar código local revisado con estado en revisión sin exigir despliegue o proveedor live para autorizar cambios reversibles. Preservar semántica exacta por hashes; no atribuir Chrome219 ni broads31 al nuevo árbol completo. CI31 es histórico hasta su evolución33; mantener fixtures/targets22–32 intactos y añadir actuales33. Clasificaciones de checksum siguen pendientes de revisión independiente; no introducir excepciones de directorio o normalizar RAW para ocultar findings.',
    'RIESGOS.md': 'MAIN es candidata local32, todavía sin regresión/CI/artefacto común vigente. SEC17 Google pendiente y las limitaciones de recuperación total/legacy Google siguen abiertas. SEC18 tiene aceptación focal, pero ninguna implementación puede prometer checkout0 si también falla invalidate antes de liberar. Gitleaks no está globalmente verde. Política de retención/países, objetivos SLO, entrevistas y validación profesional real siguen pendientes de datos/autorización aplicable.'}
for name, text in sections.items():
    with (run / name).open('ab') as handle:
        handle.write(('\n\n## Checkpoint128\n\n' + text + '\n').encode())
subprocess.run([sys.executable, '-X', 'utf8', '-B', 'scripts/implementation_registry.py', '--render', '--check'], cwd=root, check=True, capture_output=True)
assert criteria(json.loads((run / 'TRAZABILIDAD.json').read_bytes())) == before
seal = ev / 'checkpoint128-seal-receipt-20261019'
assert not seal.exists()
seal.mkdir()
(seal / '.gitattributes').write_bytes(b'* -text\n')
(seal / 'driver.py').write_bytes(Path(__file__).read_bytes())
(seal / 'receipt.json').write_bytes(enc({'base': base, 'candidate': candidate, 'registry': 126, 'previous_criteria_exact': 126, 'new_ids': [],
    'main_schema_after': 32, 'source_paths': receipt['source_paths'], 'source_equivalence_exact': True,
    'files': {name: receipt['files'][name] for name in names}}))
names += [path.relative_to(root).as_posix() for path in seal.iterdir() if path.is_file()]
docs = [(run / name).relative_to(root).as_posix() for name in ['ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'TRAZABILIDAD.json', 'TRAZABILIDAD.md']]
for name in names:
    scan((root / name).read_bytes(), name)
for offset in range(0, len(names), 25):
    git('add', '-f', '--', *names[offset:offset + 25])
git('add', '--', *docs)
for name in names:
    assert git('show', ':' + name) == (root / name).read_bytes(), name
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names + docs)
for name in receipt['source_paths']:
    assert git('show', ':' + name) == git('show', candidate + ':' + name)
git('diff', '--cached', '--check', '--', *docs, *[name for name in receipt['source_paths'] if not name.startswith('tests/ci_mfa31/')])
old_tree = receipt['before_Git_tree']
new_tree = {}
for row in git('ls-tree', '-r', '-z', git('write-tree').decode().strip()).split(b'\0'):
    if row:
        meta, name = row.split(b'\t', 1)
        new_tree[name.decode()] = meta.decode()
changed = set(names + docs)
assert set(new_tree) == set(old_tree) | changed
assert all(new_tree[name] == meta for name, meta in old_tree.items() if name not in changed)
assert not git('diff', '--cached', '--name-only', '--', 'Dockerfile', 'requirements_web.lock', 'requirements_web-windows.lock', 'requirements-test.lock')
subprocess.run(['git', '-c', 'core.autocrlf=false', 'commit', '-m', 'Integrate reviewed MFA and progress32 with public consent retirement'], cwd=root, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
print(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), 'registry': 126, 'criteria_exact': 126, 'source_paths': len(receipt['source_paths']), 'authenticated_files': len(names), 'main_schema': 32, 'other_Git_entries_exact': len(set(old_tree) - changed)}))
