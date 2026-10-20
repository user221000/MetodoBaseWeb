"""Record peer SEC19 and frozen browser/notification candidates, web only."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
T = Path('C:/Users/Consu/AppData/Local/Temp')
O = T/'metodobase-checkpoint140-20261020'
BASE = '52d2d30ff0096015a7ca94325bb1da3e6c1f4c6d'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=R, capture_output=True, check=check)


assert git('rev-parse', 'HEAD').stdout.decode().strip() == BASE
assert not git('status', '--porcelain', '-uno').stdout.strip()
assert not O.exists()
O.mkdir()
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria = lambda value: {row['id']: {key: row[key] for key in ('fuente', 'seccion', 'problema', 'criterio_exacto')} for row in value['requisitos']}
old = criteria(data)
assert len(old) == 140
untracked = {path: sha((R/path).read_bytes()) for path in git('ls-files', '--others', '--exclude-standard', '-z').stdout.decode().split('\0') if path and (R/path).is_file()}
assert len(untracked) == 537
(O/'untracked-before.json').write_bytes(encode(untracked))
imports, paths = [], []
for ref, prefix in [
    ('1f964465c0fd7b28d8e9a350d9df94a6ef6ff1ec', 'root-r31-export-companion-20261020'),
    ('8133d8b638b5cc40dcd55cade6b85bc8c8f80e47', 'root-r31-browser-server-author-20261020'),
    ('81ae854759efa1354a2f5183c35a51e08981921f', 'root-r31-mfa-ui-http-20261020'),
    ('439f13544b104001921337f457b0b6bbe6b889bb', 'browser-session31-author-offline-20261020'),
    ('be33fb17cb7a25fdbf8ff4f6a58e46d939301f04', 'qa-r31-export-browser-independent-20261020'),
    ('389500267aefb0221c8785f805ad1dc9123a6fd6', 'qa-sec19-pg35-independent-20261020'),
    ('9248350a38a9432f8da98e9ac58aa9f1d381babf', 'backend-notifications36-author-20261019'),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree', '-r', '--name-only', '-z', ref, '--', folder).stdout.decode().split('\0')[:-1]
    assert names, prefix
    entry = {'producer': ref, 'prefix': prefix, 'files': len(names), 'hashes': {}, 'product_imported': False}
    for path in names:
        raw = git('show', ref+':'+path).stdout
        assert not (R/path).exists(), path
        (R/path).parent.mkdir(parents=True, exist_ok=True)
        (R/path).write_bytes(raw)
        paths.append(path)
        entry['hashes'][path] = sha(raw)
    imports.append(entry)
for ref, names in [
    ('439f13544b104001921337f457b0b6bbe6b889bb', ['SESION_NAVEGADOR_R31_CI_MAP.json', 'SESION_NAVEGADOR_R31_IMPLEMENTACION.md']),
    ('4233a9992abe3b815a2fc487ee20ebb4030e383f', ['SESION_NAVEGADOR_R31_NATIVE_SNAPSHOT.json', 'SESION_NAVEGADOR_R31_NATIVE_CURRENT_MAP.json']),
    ('9248350a38a9432f8da98e9ac58aa9f1d381babf', ['NOTIFICACIONES_R27_CONTRATO36.md', 'NOTIFICACIONES_R27_RUNBOOK.md']),
    ('8a427c310ec9b5ff37983ac9bdff354343be1708', ['SESION_NAVEGADOR_R31_WIRE.json']),
]:
    for name in names:
        path = 'docs/implementation/20261018-evolution/'+name
        assert not (R/path).exists(), path
        (R/path).write_bytes(git('show', ref+':'+path).stdout)
        paths.append(path)
binding = {}
for path in ['web/services/followup_tasks.py', 'web/database/followup_task_repository.py',
             'web/database/models.py', 'web/database/followup_policy.py',
             'tests/test_followup34_lock_projection.py', 'tests/integration_nutrition35_postgres.py',
             'web/database/alembic/schema_targets/20261019_followup_tasks_postgresql.json',
             'web/database/alembic/schema_targets/20261020_nutrition_profile_postgresql.json']:
    raw = git('show', BASE+':'+path).stdout
    assert raw == git('show', '389500267aefb0221c8785f805ad1dc9123a6fd6:'+path).stdout, path
    binding[path] = sha(raw)
for row in data['requisitos']:
    if row['id'] == 'SEC19':
        row['estado'] = row['implementacion'] = row['validacion'] = 'verificado'
        row['bloqueo'] = None
        row['revisor'] = 'QA independiente: misma funci\u00f3n original sin wrapper/aserciones editadas,2/2PG35 en ambasfactories, rol4FALSE/noowner/noMember/FORCE28/pool1. Fuente relevante byteexacta a MAIN35.'
        row['commits'].append('389500267aefb0221c8785f805ad1dc9123a6fd6')
        row['evidencia'].append('evidence/qa-sec19-pg35-independent-20261020/review.json')
        row['pruebas'].append('Checkpoint140:2/2 originalesPGPASS, SQL yORM observados sin nombre/email/hash;38tablas/head35,1UUID cerrada normal0sesiones/ausenciafresca. Sin despliegue.')
        row['observaciones'].append('Checkpoint140: ocho blobs relevantes son exactos entre MAIN35 y el peer3895; se cierra s\u00f3lo SEC19 local, sin cierre globalR19/R31.')
    if row['id'] in {'R31', 'SEC02', 'R10', 'R19', 'R32'}:
        row['observaciones'].append('Checkpoint140: R31joint8878 aislado, producto38frontend byteexactbee yservidor8a;925ejecuciones offline/848labels/865obligaciones, QA108export/49casos+4mutacionesrechazadas, ROOT4MFAUI-HTTP reales ambosfactoriesPASS. SecurityUI yChrome/CI actuales pendientes. No tokensStorage ni credenciales artificiales para adoptar actor. Nativecompanions4233 compilan6/6, sin atribuir casosChrome.')
        row['evidencia'].extend(['evidence/root-r31-mfa-ui-http-20261020/summary.json', 'evidence/qa-r31-export-browser-independent-20261020/phase-summary.json', 'evidence/browser-session31-author-offline-20261020/source.json'])
    if row['id'] in {'R27', 'SEC23', 'QA-24'}:
        row['observaciones'].append('Checkpoint140: candidato36 autor9248350 congelado:109SQLite+5PGDDL+10PGfuncionales+1restore finalPASS,19PGanteriores porfase no reatribuidos,22UUID cerradas normal0sesiones/ausenciafresca.41ORM42physical32FORCE,targetPGafe901/SQLite383d42. Puertos/env\u00edo deshabilitados; QA/SEC/UI e integraci\u00f3nMAIN pendientes. ROOTaa3231 es composici\u00f3n aislada sin gateactual todav\u00eda.')
        row['commits'].append('9248350a38a9432f8da98e9ac58aa9f1d381babf')
        row['evidencia'].append('evidence/backend-notifications36-author-20261019/source.json')
assert criteria(data) == old
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
paragraph = ('MAIN contin\u00faa esquema35 con140 requisitos (92 originales y48 a\u00f1adidos). Sus75 contratos dirigidos conservan su fuente c4f9. SEC19 queda verificado local: QA repite2/2 originales enPG35 restringido, observaSQL/ORM y confirma que no carga contacto ajeno; ocho blobs relevantes son exactos aMAIN. R31joint8878 permanece aislado: servidor106peerPASS, frontend925ejecuciones offline/848labels/865obligaciones; QAexport108ejecuciones/49casos y4mutacionesrechazadas. ROOT pasa4/4MFAUI conHTTP real en ambasfactories. Nuevos companions nativos4233 compilan6/6 sin ejecutarChrome; QA prepara fixtures35 y mantiene leasePG exclusivo paraR31. Seguridad revisa UI y despu\u00e9s36. Notificaciones36 autor9248350:109SQLite+5PGDDL+10PGfuncionales+1restore finalPASS;22BD cerradas normal/ausenciafresca. ROOTaa3231 compone36 aislado, sin atribuirle esos gates ni integrar producto enMAIN. UI36/peer,CI/broad/Chrome/imagen actuales ydespliegue siguen pendientes. R05 global contin\u00faa RED1603 en4f4, sin nuevo escaneo. S\u00f3lo servicio web; desktop fuera del trabajo yentrega.')
for name, content in {
    'VALIDACION.md': paragraph,
    'CAMBIOS.md': paragraph,
    'DECISIONES.md': 'SEC19 s\u00f3lo se cierra tras la repetici\u00f3nPG independiente ybinding exacto aMAIN. Conservar cada gate ligado a su commit;108export no son108casos \u00fanicos. Nuevos companions nativos sustituyen \u00fanicamente framing de sesi\u00f3n/esquema de forma expl\u00edcita; originales permanecen hist\u00f3ricos. No presentar compilaci\u00f3n comoChrome ni aceptaci\u00f3n del proveedor comoentrega. LeasePG exclusivoQA; sin leaseChrome todav\u00eda.',
    'RIESGOS.md': 'R31 UI sensible en revisi\u00f3n independiente; nativos/CI antiguos dependen deStorage yfixtures31/33. Notificaciones36 mantiene puertos cerrados hasta revisi\u00f3nQA/SEC/UI; su tolerancia a incertidumbre nunca prueba env\u00edo o causalidad. Retenci\u00f3n, pa\u00edses, SLO acordado, piloto yrevisi\u00f3n profesional mantienen sus decisiones externas pendientes.'
}.items():
    p = D/name
    assert b'## Checkpoint140' not in p.read_bytes()
    p.write_bytes(p.read_bytes().rstrip()+('\n\n## Checkpoint140\n\n'+content+'\n').encode())
state = (D/'ESTADO.md').read_text(encoding='utf8')
history = state[state.index('## Observaciones hist\u00f3ricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementaci\u00f3n\n\nCheckpoint140 local: esquema35 y140 requisitos.\n\n'+paragraph+'\n\nFree:10 clientes activos,1 plan por cliente al d\u00eda y10 planes totales por gimnasio al d\u00eda. La copia de referencia y537 archivos untracked se preservan; sin push, PR, despliegue, cargos oenv\u00edos.\n\n[Registro](TRAZABILIDAD.md), [validaci\u00f3n](VALIDACION.md).\n\n'+history+'\n## Checkpoint140\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validaci\u00f3n](VALIDACION.md).\n').encode())
proof = D/'evidence/checkpoint140-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
(proof/'imports.json').write_bytes(encode(imports))
(proof/'SEC19-MAIN-source-binding.json').write_bytes(encode(binding))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=R, capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout)
(O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
git('-c', 'core.autocrlf=false', 'add', '-f', '--', *paths, proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json', 'TRAZABILIDAD.md', 'ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md']
git('-c', 'core.autocrlf=true', 'add', '--renormalize', '--', *[(D/name).relative_to(R).as_posix() for name in controls])
check = git('diff', '--cached', '--check', check=False)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cr = set()
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.', line)
    if not match:
        continue
    path, num = match.group(1), int(match.group(2))
    assert path in paths, path
    value = git('show', ':'+path).stdout.split(b'\n')[num-1]
    assert value.endswith(b'\r') and not value[:-1].endswith((b' ', b'\t'))
    cr.add(path)
attrs = git('show', ':.gitattributes').stdout.replace(b'\r\n', b'\n').rstrip(b'\n')+b'\n'
for path in sorted(cr):
    entry = (path+' whitespace=cr-at-eol\n').encode()
    if entry not in attrs:
        attrs += entry
(R/'.gitattributes').write_bytes(attrs)
git('-c', 'core.autocrlf=false', 'add', '--', '.gitattributes')
git('diff', '--cached', '--check')
assert all(sha((R/path).read_bytes()) == digest for path, digest in untracked.items())
assert all(git('show', ':'+path).stdout == (R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') or path == '.gitattributes' for path in git('diff', '--cached', '--name-only').stdout.decode().splitlines())
receipt = {'base': BASE, 'requirements': 140, 'previous_criteria_exact': 140,
    'proof_files_imported': sum(row['files'] for row in imports), 'docs_imported': 7,
    'untracked_preserved': 537, 'product_imported': False, 'MAIN_schema': 35,
    'SEC19_verified_local': True, 'global_acceptance': False, 'CRLF_paths_preserved': sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c', 'core.autocrlf=false', 'add', '-f', '--', proof.relative_to(R).as_posix())
git('diff', '--cached', '--check')
git('commit', '-m', 'Close independent SEC19 and record frozen web browser and notification candidates')
assert not git('status', '--porcelain', '-uno').stdout.strip()
result = {'head': git('rev-parse', 'HEAD').stdout.decode().strip(), **receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
