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
base = '5b8d06bcb30b1cb9c4e863f120213fc157604014'
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=root)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
enc = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == base and not git('status', '--porcelain', '--untracked-files=no')
definition = next(n for n in ast.parse((tmp / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'preserved-scanner', 'exec'))
receipt = json.loads((tmp / 'metodobase-checkpoint127-import-result.json').read_bytes())
raw = {root / name for name in receipt['files']}
for path in raw:
    meta = receipt['files'][path.relative_to(root).as_posix()]
    blob = path.read_bytes()
    assert len(blob) == meta['bytes'] and sha(blob) == meta['sha256']
    scan(blob, path.name)
data = json.loads((run / 'TRAZABILIDAD.json').read_bytes())
fields = ['fuente', 'seccion', 'problema', 'criterio_exacto']
criteria = lambda value: {row['id']: {field: row[field] for field in fields} for row in value['requisitos']}
before = criteria(data)
assert len(before) == 124
notes = {
    'R02': 'SEC17 confirmado por revisión independiente sobre345:4canarios rojos y4controles verdes en ambas factories, con respuesta válida Google modelada y asociación local por email. No se demuestra bypass criptográfico ni explotación live. Asociación issuer/sub33, enlace explícito con primaria local+factor y alta nueva sin adoptar cuentas están en implementación separada.',
    'R05': 'Serial y n2 de506 cerrados: cada modo3056PASS+1skipWindows exacto,3057IDs únicos y3047anteriores preservados,10208fuentes/89paquetes/Python quietos,pip0/0. Gate real de cobertura serial100%líneas/branches en3módulos críticos. Fullgitleaks de UI:exit1,31566raw,2pins existentes,31564restantes; sólo2nuevos fingerprints metadata verificados FP,31562previos sin clasificar. Scanner119 acotado no equivale a gitleaks global.',
    'R19': 'Dos modos completos de506 PASS con la misma omisión histórica Windows de symlink. Duraciones1358.688s serial/621.156s n2 son diagnósticas, noSLO. No atribuir a estas ejecuciones PostgreSQL/Redis/Chrome/Linux/desktop/Actions ni nueva composición32.',
    'R25': 'Retiro backend congeladofcfb +UIde216 +clocks/loggerde506 compuesto219f89,10332otrasGitentries exactas y todos los cambios RAW=Git productor. Autorbackend SQLite50funcionales y fases superpuestas,PG16=10+4+2; UI36controllerVM+9DOMVM+8SSR, todavía no browser integrado. Seguridadindependiente:SQLite73PASS/2rojos,PG24PASS/2rojos; todos los casos autor pasan. ParentOFF con invitación real permitemetadata/withdraw200 sin habilitarlogin general401. SEC18 retienecheckout bajo commit/rollback/close fallidos simultáneos;503opaco/contextorestaurado se conservan. Delta focal y QA pública en curso.',
    'R31': 'Retiro exige primaria password fresca y factor activo por cada operación/página; Google-only y pérdida total no resueltos. Metadata mínima propia/CAS/latest/appendwithdraw, admisión durable separada, factor+evento+audit en unaACK,503sinretry/readback. HallazgoSEC18 es robustez bajo inyección compuesta, sin evidencia de fuga/bypass/explotación. Registro no cierra derechos globales de privacidad.',
    'R32': 'SEC17 asociaciónGoogle por email confirmada, corrección33 separada en curso sin backfill de sub desde correo. Dos tablas de identidad/intent separadas de pagos; verificador de producción y alta/enlace/desenlace explícitos requieren cierre y revisión. No se amplían login general ni autoridad parental para retiro. Alertas/custodia/proveedores/lostallfactor continúan pendientes.'}
refs = {
    'R02': ['security-google-subject-association-independent-20261019/source.json'],
    'R05': ['root-mfa31-reviewed-serial-20261019/source.json', 'root-mfa31-reviewed-parallel-20261019/source.json', 'progress-retirement-ui/secret-scan-summary.json'],
    'R19': ['root-mfa31-reviewed-serial-20261019/source.json', 'root-mfa31-reviewed-parallel-20261019/source.json'],
    'R25': ['backend-progress32-retirement-20261019/source.json', 'progress-retirement-ui/final-source.json', 'security-progress-retirement-independent-20261019/source.json', 'prepared-wave127-20261019/metodobase-retirement32-common-verified-20261019/receipt.json'],
    'R31': ['security-progress-retirement-independent-20261019/source.json'],
    'R32': ['security-google-subject-association-independent-20261019/source.json']}
for row in data['requisitos']:
    if row['id'] in notes:
        row['observaciones'].append('Checkpoint127: ' + notes[row['id']])
    for name in refs.get(row['id'], []):
        assert (ev / name).is_file(), name
        if 'evidence/' + name not in row['evidencia']:
            row['evidencia'].append('evidence/' + name)

new = [
    ('SEC17', 'security-google-subject-association-independent-20261019',
     'Google login y reautenticación asocian una respuesta válida al usuario local por correo, sin vínculo estable issuer/sub; un correo third-party verificado sin hd no prueba autoridad actual del mailbox.',
     'Asociar Google por issuer/sub persistido y único, sin adopción por coincidencia de correo. Enlazar y desenlazar explícitamente con primaria local fresca y factor existente, intención de un uso ligada a actor, propósito, sujeto, sesión y generación; emitir sólo tras commit confirmado. Mantener alta nueva vacía sin apropiarse de cuentas/pertenencias existentes, verificar tokens en producción, no inventar backfill legacy por email y preservar controles de rol, pertenencia, SV y MFA en ambas factories.',
     'P1', ['R02', 'R12', 'R31', 'R32'], 'en_curso', 'en_curso',
     '8casos independientes:4canarios de asociación fallan y4controles de rechazo pasan; sin proveedor real, bypass de firma ni bypass del segundo factor.', ['fb488e809415fd84c487ec3e2cdca90d987befd3']),
    ('SEC18', 'security-progress-retirement-independent-20261019',
     'La sesión nueva del retiro conserva un checkout si commit, rollback y close fallan antes de liberar recursos y la Session sigue referenciada; la respuesta503 y el ContextVar restaurado permanecen correctos.',
     'Invalidar únicamente la Session nueva del retiro cuando falle su limpieza antes de liberar la conexión; no disponer el pool global ni modificar la Session ambiental. Mantener503 opaco ante incertidumbre, restaurar ContextVar y comprobar con las mismas aserciones SQLite y PostgreSQL pool1 que no queda checkout bajo el modelo compuesto, además de ACK de admisión y cierre fallido tras commit.',
     'P2', ['R17', 'R25', 'R31'], 'en_curso', 'en_curso',
     'SQLite73PASS/2rojos yPG24PASS/2rojos; cero errores/skips. Modelo de inyección a Session, no fallo real de driver observado ni explotación. Dos UUID propias cerradas sin sesiones/FORCE con ausencia fresca.', ['6147f9300989f4115cf8d270025a3805926d32b1'])]
for ident, prefix, problem, criterion, priority, deps, implementation, validation, tests, commits in new:
    data['requisitos'].append({'id': ident, 'identificador_original': ident,
        'fuente': 'docs/implementation/20261018-evolution/evidence/' + prefix + '/source.json',
        'seccion': 'Hallazgo nuevo checkpoint127', 'problema': problem, 'criterio_exacto': criterion,
        'prioridad': priority, 'responsable': 'Backend, seguridad y QA', 'tareas': deps, 'dependencias': deps,
        'estado': 'en_revision', 'implementacion': implementation, 'validacion': validation,
        'despliegue': 'no_desplegado', 'entorno': 'local', 'cambios': ['Hallazgo confirmado acotadamente; corrección y aceptación independiente pendientes.'],
        'commits': commits, 'pruebas': [tests], 'evidencia': ['evidence/' + prefix + '/source.json', 'evidence/' + prefix + '/review.md'],
        'documentacion': ['ESTADO.md', 'VALIDACION.md', 'DECISIONES.md'], 'revisor': 'Seguridad independiente del autor',
        'bloqueo': None, 'observaciones': ['MAIN permanece en esquema30. No atribuir aceptación global ni despliegue.']})
assert len(criteria(data)) == 126 and all(criteria(data)[key] == value for key, value in before.items())
(run / 'TRAZABILIDAD.json').write_bytes(enc(data))
(run / 'ESTADO.md').write_text('''# Estado de implementación

Checkpoint127 local:126 requisitos,92 originales y34 nuevos; los124 criterios anteriores se conservan exactos. Free:10 clientes activos,1plan por cliente al día,10totales por gimnasio al día. Desktop soportado. MAIN sigue en esquema30; candidatas31/32/33 aisladas. Sin push,PR,despliegue,cargos ni mensajes reales.

La candidata31de506 cerró serial y n2:3056PASS y el mismo skipWindows de symlink por modo,3057identidades únicas,3047anteriores preservadas,10208fuentes/89paquetes/Python quietos y pip0/0. El checker real de cobertura serial pasó100%líneas y branches en3módulos críticos. Estos resultados no representan la nueva composición32,PG,Chrome,Linux ni desktop. [Serial](evidence/root-mfa31-reviewed-serial-20261019/source.json), [n2](evidence/root-mfa31-reviewed-parallel-20261019/source.json).

Retiro propio: backendfcfb y UIde216 están congelados; composición219f89 añade clocks/logger revisados y conserva10332otras entradasGit exactas. La preparación detectó conversiónCRLF y luego marcas stat antiguas: se preservan los intentos y el sucesor verifica bytesGit exactos e índice/tree sin cambio. QA pública de ambas factories/navegador está en curso. Seguridad confirmó metadata/withdraw200 con invitación real y parentOFF manteniendo login general401, pero SEC18 retiene checkout bajo fallo compuesto de limpieza; corrección focal y replay pendientes. [Autor](evidence/backend-progress32-retirement-20261019/source.json), [UI](evidence/progress-retirement-ui/final-source.json), [Seguridad](evidence/security-progress-retirement-independent-20261019/source.json).

SEC17 confirma asociación Google por correo sin vínculo issuer/sub:4canarios rojos y4controles verdes, sin explotación live ni bypass criptográfico demostrado. Backend implementa33 con identidad separada, enlace/desenlace explícitos y alta nueva sin adoptar cuentas existentes; sin backfill por email. Su aceptación y composición final siguen pendientes. [Revisión](evidence/security-google-subject-association-independent-20261019/source.json).

Gitleaks global sigue rojo:31564hallazgos restantes;2fingerprints nuevos de metadata fueron verificados como falsos positivos y31562anteriores siguen sin clasificar. No se modifica el scanner ni se amplía allowlist para ocultarlos. La imagen31f74 conserva su sello parcial; el sucesor de observador sólo está preparado y no ejecutado. VM propia apagada.

Siguiente acción: corregir y revisar SEC18, cerrar QA pública del retiro, completar33 con verificador y contratos Google, y componer el código revisado antes de CI, regresión y artefacto final. Continuar alcance pendiente sin atribuir entrevistas, proveedores o producción no observados. [Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''', encoding='utf8')
(run / 'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint127:126 requisitos y124 criterios previos exactos; MAIN esquema30. Serial y n2 aislados31de506:3056PASS+1skipWindows exacto cada uno; cobertura crítica serial100%. Candidata32retiro219f89 compuesta y en QA pública; SEC18 de limpieza requiere corrección y replay. SEC17 Google confirmado; implementación33 y aceptación pendientes. [Estado](ESTADO.md), [trazabilidad](TRAZABILIDAD.md).

Imagen31f74/digestdc8fab52 conserva evidencia parcial de arranque/health/ready y contrato nativo; worker incompleto por criterios del observador errados, sin reescribirlos. Sucesor preparado no ejecutado; siguiente build corresponde a la fuente final revisada. Gitleaks global rojo y clasificación pendiente. Free10clientes/1plancliente/día/10totalgym/día; desktop soportado. No se ha publicado ni desplegado.
''', encoding='utf8')
sections = {
    'VALIDACION.md': notes['R05'] + ' ' + notes['R19'] + ' ' + notes['R25'] + ' ' + notes['R02'],
    'CAMBIOS.md': 'MAIN incorpora sólo control/evidencia. Composición aislada219f89 integra fcfc+UIde216+de506 con bytes exactos; no se atribuyen broads31 a32. UI tiene32paths de evidencia incluidos atributos (31además del archivo de atributos). Dos fallos de preparación del import se corrigieron antes de escribir: manifestGoogle excluye atributos y UI31contaba sin ellos. No cambian producto ni resultados.',
    'DECISIONES.md': 'Mantener alta Google nueva vacía por issuer/sub con contacto no verificado thirdparty/nohd, sin adopción por email ni derechos/perfiles implícitos. Email ya registrado exige vínculo explícito localfresh+MFA; desenlace explícito conserva historial y primaria local utilizable. No backfill de sub desde email. Probar causalidad con ocho casos originales tokeninfo antes de sustituir verificador; proveedor final con JWT firmado y fixtureJWKS sólo por transporte, sin mock de identidad. Nuevo entorno propio, no mutar WEB89 de evidencia. SEC18: invalidar sólo Session nueva si falla limpieza, no pool global.',
    'RIESGOS.md': 'Las migraciones locales reversibles necesarias están autorizadas; inventar identidad Google histórica a partir de email carece de evidencia y no es una migración técnica legítima. SEC17 y SEC18 pendientes de aceptación. Gitleaks global31564remaining:2FPmetadata confirmados/31562previos sin clasificar, no todo falso positivo. Worker31parcial no habilita despliegue. Países,retención,SLO,pilotos,especialista y pérdida total de factores permanecen abiertos.'}
for name, text in sections.items():
    with (run / name).open('ab') as handle:
        handle.write(('\n\n## Checkpoint127\n\n' + text + '\n').encode())
subprocess.run([sys.executable, '-X', 'utf8', '-B', 'scripts/implementation_registry.py', '--render', '--check'], cwd=root, check=True, capture_output=True)
assert all(criteria(json.loads((run / 'TRAZABILIDAD.json').read_bytes()))[key] == value for key, value in before.items())
seal = ev / 'checkpoint127-seal-receipt-20261019'
assert not seal.exists()
seal.mkdir()
(seal / '.gitattributes').write_bytes(b'* -text\n')
(seal / 'driver.py').write_bytes(Path(__file__).read_bytes())
(seal / 'receipt.json').write_bytes(enc({'base': base, 'registry': 126, 'previous_criteria_exact': 124, 'new_ids': ['SEC17', 'SEC18'],
    'main_product_changed': False, 'files': {path.relative_to(root).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in sorted(raw)}}))
raw.update(path for path in seal.iterdir() if path.is_file())
names = sorted(path.relative_to(root).as_posix() for path in raw)
docs = [(run / name).relative_to(root).as_posix() for name in ['ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'TRAZABILIDAD.json', 'TRAZABILIDAD.md']]
for offset in range(0, len(names), 25):
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'add', '-f', '--', *names[offset:offset + 25]], cwd=root, check=True, capture_output=True)
subprocess.run(['git', 'add', '--', *docs], cwd=root, check=True, capture_output=True)
for name in names:
    assert git('show', ':' + name) == (root / name).read_bytes(), name
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names + docs)
subprocess.run(['git', 'diff', '--cached', '--check', '--', *docs], cwd=root, check=True, capture_output=True)
subprocess.run(['git', 'commit', '-m', 'Record complete schema31 regressions and independent Google and retirement findings'], cwd=root, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
print(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), 'registry': 126, 'criteria_exact': 124, 'authenticated_files': len(names), 'main_product_changed': False}))
