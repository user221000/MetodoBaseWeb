from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

R = Path(r'F:/mb-security-google33-conflict-peer-20261019')
T = Path(r'C:/Users/Consu/AppData/Local/Temp')
P = T / 'metodobase-sec-google33-conflict-peer-private-20261019'
O = R / 'docs/implementation/20261018-evolution/evidence/security-google33-conflict-independent-20261019'
FIX = '8a5e5dc235e96a47488befb743fc02a24b491939'
sha = lambda b: hashlib.sha256(b).hexdigest()
save = lambda n, x: (O / n).write_bytes((json.dumps(x, indent=2, ensure_ascii=False) + '\n').encode())
load = lambda n: json.loads((O / n).read_bytes())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R).decode().strip() == FIX
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=R)
binding = load('frozen-source-binding.json')
for phase, count in [('sqlite', 12), ('pg', 11)]:
    summary = load(phase + '-summary.json')
    assert summary['cases'] == count and summary['exit'] == 0
    assert summary['outcomes'] == {'passed': count, 'failure': 0, 'error': 0, 'skipped': 0}
    assert load(phase + '-before.json') == load(phase + '-after.json')
final = load('pg-after.json')
assert load('sqlite-before.json') == final
for name, digest in final['source'].items():
    assert sha((R / name).read_bytes()) == digest
for name, digest in binding['peer_canaries'].items():
    assert sha((R / 'tests' / name).read_bytes()) == digest
assert load('pg-summary.json')['owned_UUIDs'] == 3 and load('pg-summary.json')['all_closed_absent']
assert len(load('pg-closures.STRUCTURAL.json')['leases']) == 3
for label, exe in [('author92', T / 'metodobase-google33-author-aamidzkr/venv/Scripts/python.exe'),
                   ('web89', T / 'metodobase-candidate-web-20261018/Scripts/python.exe')]:
    check = subprocess.run([str(exe), '-m', 'pip', 'check'], capture_output=True)
    (O / ('pip-' + label + '-after.raw.log')).write_bytes(check.stdout + check.stderr)
    assert check.returncode == 0
for name in ['canonical-gym-race-api_app.json', 'canonical-gym-race-web_main_web.json']:
    raw = (P / 'pg-association-receipts' / name).read_bytes()
    observation = json.loads(raw)
    assert observation['statuses'] == [200, 409] and observation['losing_error_codes'] == ['google_link_conflict']
    assert observation['unique_insert_workers'] == observation['unique_insert_backends'] == 2
    assert all(observation[k] for k in ['one_new_container', 'one_binding', 'binding_owner_is_new_container',
        'one_server_owned_profile', 'exactly_five_own_defaults', 'losing_response_has_no_tokens'])
    (O / name.replace('.json', '.STRUCTURAL.json')).write_bytes(raw)

acl = json.loads((P / 'acl-final.private.json').read_bytes())
assert acl['protected'] and acl['parent_SDDL_unchanged'] and acl['parent_rule_count'] == 2
save('private-ACL.STRUCTURAL.json', {**acl,
    'initial_parent_SDDL_SHA256': sha((P / 'acl-initial.private.txt').read_bytes())})
attributes = []
for path in sorted(P.rglob('*')):
    if path.is_file():
        assert not path.is_symlink()
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        stat = path.stat()
        attributes.append({'private_relative_path': path.relative_to(P).as_posix(), 'bytes': stat.st_size,
            'SHA256': h.hexdigest(), 'mtime_ns': stat.st_mtime_ns, 'ctime_ns': stat.st_ctime_ns,
            'windows_file_attributes': getattr(stat, 'st_file_attributes', None)})
save('private-retention-attributes.STRUCTURAL.json', {
    'scope': 'Original focal stdout/stderr/XML, synthetic fixtures, initial/final ACL, exclusive UUID receipts and structural race observations. Payloads remain private; original bytes stream-hashed, no RAW reconstructed.',
    'files': attributes})

drivers = O / 'drivers'
drivers.mkdir()
for stem in ['prepare', 'run', 'seal']:
    (drivers / (stem + '.py')).write_bytes((T / ('metodobase-sec-google33-conflict-peer-' + stem + '-20261019.py')).read_bytes())
(drivers / 'final-acl.ps1').write_bytes((T / 'metodobase-sec-google33-conflict-peer-final-acl-20261019.ps1').read_bytes())
canaries = O / 'canaries'
canaries.mkdir()
for name in binding['peer_canaries']:
    (canaries / name).write_bytes((R / 'tests' / name).read_bytes())
(canaries / 'maintained-test_google33_conflict_window.py').write_bytes((R / 'tests/test_google33_conflict_window.py').read_bytes())
save('replay-contract.json', {
    'frozen_product_commit': FIX, 'immutable_RED_peer_commit': binding['immutable_RED_peer_commit'],
    'commands': ['python92 -B drivers/run.py sqlite', 'python92 -B drivers/run.py pg'],
    'coordinate_note': 'Driver pins the own WT/private prefix. A future replay records only coordinate changes and installs the byte-identical canaries under tests/; do not change assertions or identity verification. PG requires a fresh exclusive root handoff.',
    'canary_SHA256s': binding['peer_canaries'],
    'fixtures': 'Standard current33 maintained fixtures on frozen product; no compatibility dummy or identity override.',
    'private_profile_values_published': False,
    'owned_UUIDs': 3, 'closed_absent': True, 'PG_lease_returned_after_receipts': True,
})
review = '''Aceptación focal QA-17 sobre `8a5e5dc235e96a47488befb743fc02a24b491939`, base `707b32605c254466982f25a368b046a0445a3f71`. El sello RED anterior `0bf1d0a8c5a3470173faa36b094076843b76dd6f` permanece inmutable. Esta aceptación sólo cierra la clasificación de colisiones de alta/confirmación; no es aceptación global Google33.

Los mismos dos canarios HTTP canónicos ahora observan 200+409 `google_link_conflict`, frente a 200+503 `google_link_unconfirmed` antes. Se conservan byteidénticos los archivos y todas las aserciones de la carrera HTTP, las carreras directas False y la preimagen genérica True. Cada carrera usa dos conexiones restringidas con pool1 y firmas RSA/JWKS verificadas por la biblioteca real; sólo el transporte de Google y la coordinación SQL son sintéticos. No hay Google vivo ni overrides de identidad. Se mantiene una sola cuenta/asociación/GymProfile, cinco planes propios y ningún token/refresh/challenge del perdedor. Las dos observaciones de backends/threads distintos y las políticas de pool/GUC se comprueban con el oráculo original.

El replay PG tiene 11 casos PASS, sin errores ni skips: cuatro carreras directas False, cuatro con los constructores True originales, dos altas HTTP canónicas y el contrato real33. Los cuatro True son una comprobación de robustez del servicio genérico; producción configura False. El caso de dos actores True que antes escapaba como IntegrityError ahora responde conflicto. No se suman estos replays a las pruebas del sello original como casos nuevos.

SQLite focal tiene 12 casos PASS, sin errores ni skips: cuatro del autor para fallo de perfil y rollback normal/incierto, cuatro independientes que fallan en confirm después de escrituras reales, dos controles mantenidos de pérdida de ACK y dos controles independientes de cabeceras SSR/API. En confirm se verifican reversión de binding, consumo del intent, SV, auditoría y revocación de refresh, mientras la admisión duradera permanece. Si rollback no puede confirmar el resultado se conserva 503 sin secretos ni mensajes SQL. La pérdida de ACK continúa produciendo 503 aunque la mutación ya se haya confirmado.

La revisión estática reconstruye el AST completo del módulo anterior al retirar únicamente el helper/import nuevo, desenvolver los dos tails y normalizar el antiguo try del primer flush. El helper sólo captura IntegrityError, exige rollback antes de 409 y propaga el 503 del rollback incierto; no reintenta, consulta al ganador ni adopta por correo. En confirm cubre creación/reactivación, consumo, revocación, auditoría y commit. En alta cubre desde add/primer flush hasta binding/perfil/membresías/identidad/audit/commit. Los gates previos y las funciones start, unlink y cleanup permanecen iguales. De las 845 fuentes seleccionadas del sello RED sólo cambia google_link.py; se añade el test mantenido del autor.

El canario de cabeceras permanece byteidéntico: sólo GET SSR canónico admite 200, HEAD canónico exige 405 y el slash exige 307 con Location exacta. Todas las aserciones de cache/referrer/CSP/GIS, errores API y vecinos se conservan. No se modifica ni se presume la aceptación de la adaptación mantenida de QA.

Se crean sólo tres UUID propios con recibo inicial exclusivo anterior a CREATE, OID/nacimiento verificados, app no owner y cuatro flags privilegiados false, FORCE RLS y pool1. El contrato real mantiene 35 ORM, 36 tablas físicas, 26 FORCE, 26 funciones y 12 triggers, sin RPC nuevo. Cada UUID cierra con cero sesiones, DROP normal y ausencia en otra conexión fresca. El lease55483 se devuelve a ROOT tras esos cierres; no se tocan DB ajenas, roles/HBA ni servicios.

Fuentes seleccionadas, cinco canarios, 92/89 distribuciones y ambos binarios Python de cada entorno permanecen iguales entre fases; pip check antes/después termina 0. No se instalaron dependencias. RAW/XML y sus atributos originales permanecen privados bajo ACL protegido; pytest declara separadamente sus fixtures OWNER RIGHTS/SYSTEM/Administrators. Scanner119 intacto más el guard JWT valida los artefactos publicados. No se ejecutan Chrome, VM, pruebas amplias ni llamadas a Google vivo. Las limitaciones Google-only legado, factores perdidos y configuración GIS externa del sello anterior siguen pendientes.
'''
(O / 'review.md').write_bytes(review.encode())
node = next(n for n in ast.parse((T / 'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
scan_hash = sha(ast.dump(node).encode())
assert scan_hash == 'de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns = dict(io=io, json=json, re=re, tarfile=tarfile, zipfile=zipfile, PurePosixPath=PurePosixPath)
exec(compile(ast.Module(body=[node], type_ignores=[]), 'unchanged-scanner119', 'exec'), ns)
save('source.json', {'reviewed_commit': FIX, 'immutable_RED_peer_commit': binding['immutable_RED_peer_commit'],
    'verdict': 'QA-17 focal acceptance', 'global_Google33_acceptance': False, 'product_changes_by_peer': False,
    'SQLite_cases': 12, 'PG_cases': 11, 'all_passed_no_errors_no_skips': True,
    'old_canonical_and_True_False_canaries_RAW_exact': True, 'own_new_confirm_rollback_cases': 4,
    'all_sources_packages_bothPython_quiet': True, 'pip_before_after_exit_each': 0,
    'owned_UUIDs_closed_absent': 3, 'PG_lease_returned': True, 'scanner119_AST_SHA256': scan_hash})
save('public-safety-scan.json', {'scanner119_AST_SHA256': scan_hash, 'scanner119_unchanged': True,
    'additional_three_segment_JWT_guard': True, 'all_public_files_pass': True})
save('manifest.json', {p.relative_to(O).as_posix(): {'bytes': p.stat().st_size, 'SHA256': sha(p.read_bytes())}
    for p in sorted(O.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
for path in O.rglob('*'):
    if path.is_file():
        raw = path.read_bytes()
        ns['scan'](raw, path.relative_to(O).as_posix())
        assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}', raw), path.name
print(json.dumps({'files': sum(p.is_file() for p in O.rglob('*')),
    'source_SHA256': sha((O / 'source.json').read_bytes()), 'manifest_SHA256': sha((O / 'manifest.json').read_bytes()),
    'verdict': 'QA-17 focal acceptance', 'scanner119_JWTguard': 'PASS'}))
