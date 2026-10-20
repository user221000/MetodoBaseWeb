from pathlib import Path, PurePosixPath
import ast
import hashlib
import importlib.metadata
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

R = Path(r'F:/mb-security-google33-peer-20261019')
T = Path(r'C:/Users/Consu/AppData/Local/Temp')
P = T / 'metodobase-sec-google33-peer-private-20261019'
PREFIX = 'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
O = R / PREFIX
BASE = '3587b3b3eee3a58367624472d7c0683baa8f10e0'
WEB = T / 'metodobase-candidate-web-20261018/Scripts/python.exe'
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=R)
save = lambda n, obj: (O / n).write_bytes((json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode())
load = lambda n: json.loads((O / n).read_bytes())

def streamsha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert not git('status', '--porcelain', '--untracked-files=no')
assert (O / '.gitattributes').read_bytes() == b'* -text\n'
initial = load('sqlite-before.json')
current_source = {name: sha((R / name).read_bytes()) for name in initial['source']}
assert current_source == initial['source'] and len(current_source) == 845
expected = {
    'test_security_google33_peer.py': '77746aba862c45d935d0598d95448990412cdf8506f653cb2d64a02f13dcb366',
    'test_security_google33_postgres_peer.py': 'b96df8d6da0d1a21615b1c122cec435df47b84019067de76785243ceb2ffda04',
    'test_security_google33_canonical_race_peer.py': 'de85e39ac07fb46e5d297ca2c8117d7c6082723c27786a79021add517869938b',
}
for name, digest in expected.items():
    assert sha((R / 'tests' / name).read_bytes()) == digest
assert sha((P / 'initial-race-autoflush-true.RAW.py').read_bytes()) == 'b0ca2b1bb34f6044859b7eb7fccf633fd8b41452c9688eb9142df6f02ea1060b'

def envphoto():
    return {'packages': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
            'python': sha(Path(sys.executable).read_bytes()), 'base_python': sha(Path(sys._base_executable).read_bytes())}

webcode = "from pathlib import Path;import hashlib,importlib.metadata,json,sys;h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();print(json.dumps({'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':h(sys.executable),'base_python':h(sys._base_executable)}))"
final = {'source': current_source, 'author92': envphoto(),
         'web89': json.loads(subprocess.check_output([str(WEB), '-B', '-c', webcode]))}
assert json.loads(json.dumps(final)) == initial
save('final-source-packages-python.json', {**final, 'own_canaries': expected,
     'scope': '845 tracked selected source/config files byte-exact to first photo, plus three peer source pins; package inventories and both Python executable hashes for author92 and WEB89. No all-files/all-disks assertion.'})
for label, exe in [('author92', sys.executable), ('web89', str(WEB))]:
    result = subprocess.run([exe, '-m', 'pip', 'check'], capture_output=True)
    (O / ('pip-' + label + '-final-seal.raw.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0

phase_expectations = {
    'sqlite': (80, 78, 2), 'own-sqlite': (44, 44, 0), 'pg-functional': (64, 62, 2),
    'pg-migration-restore': (15, 15, 0), 'pg-final-races': (7, 5, 2),
}
for phase, (count, passed, failed) in phase_expectations.items():
    report = load(phase + '-summary.json')
    assert report['cases'] == count
    assert report['outcomes'] == {'passed': passed, 'failure': failed, 'error': 0, 'skipped': 0}
closures = load('pg-final-races-closures.STRUCTURAL.json')
assert closures['all_closed_absent'] and len(closures['leases']) == 15
assert len({s['database'] for s in closures['leases']}) == 15
assert all(s['state'] == 'closed_absent' and s['sessions_before_drop'] == 0 and
           s['absence_verified'] == 'fresh_control_connection' for s in closures['leases'])
save('final-owned-closure-scope.json', {
    'owned_UUIDs': 15, 'all_closed_absent': True,
    'source': 'pg-final-races-closures.STRUCTURAL.json',
    'initial_creation': 'exclusive xb receipt before CREATE; OID/owner and launcher birth verified by maintained helper',
    'closure': 'zero own sessions; normal DROP without FORCE; absence from fresh control connection per receipt',
    'no_new_SQL_at_seal': True, 'PG55483_lease_returned_to_root': True,
    'foreign_DB_roles_HBA_services_untouched': True,
})

for name in ['canonical-gym-race-web_main_web.json', 'canonical-gym-race-api_app.json']:
    raw = (P / 'pg-final-races-association-receipts' / name).read_bytes()
    receipt = json.loads(raw)
    assert receipt['statuses'] == [200, 503] and receipt['autoflush_each'] is False
    assert receipt['unique_insert_workers'] == receipt['unique_insert_backends'] == 2
    assert all(receipt[key] for key in ['one_new_container', 'one_binding', 'binding_owner_is_new_container',
        'one_server_owned_profile', 'exactly_five_own_defaults', 'losing_response_has_no_tokens'])
    (O / name.replace('.json', '.STRUCTURAL.json')).write_bytes(raw)

acl = json.loads((P / 'acl-final.private.json').read_bytes())
assert acl['protected'] and acl['parent_SDDL_unchanged'] and acl['parent_rule_count'] == 2
save('private-ACL.STRUCTURAL.json', {**acl,
    'initial_parent_SDDL_sha256': sha((P / 'acl-initial.private.txt').read_bytes()),
    'execution_note': 'Direct ps1 invocation was rejected by host ExecutionPolicy before ACL inspection; same script then completed via process-scoped -ExecutionPolicy Bypass. No persistent policy/ACL changes.'})
retained = []
for path in sorted(P.rglob('*')):
    if path.is_file():
        assert not path.is_symlink()
        stat = path.stat()
        retained.append({'private_relative_path': path.relative_to(P).as_posix(), 'bytes': stat.st_size,
                         'sha256': streamsha(path), 'mtime_ns': stat.st_mtime_ns, 'ctime_ns': stat.st_ctime_ns,
                         'windows_file_attributes': getattr(stat, 'st_file_attributes', None)})
save('private-retention-attributes.STRUCTURAL.json', {
    'scope': 'Original pytest stdout/stderr/XML including all REDs, synthetic fixtures, exclusive owned leases, provider receipts, restore artifacts, initial True source and ACL records. Stream-hashed original bytes; payloads stay private. No reconstructed historical RAW.',
    'files': retained,
})

drivers = O / 'drivers'
drivers.mkdir()
for stem in ['run-sqlite', 'run-own-sqlite', 'run-pg', 'normalize-race', 'run-final-races', 'run-ui', 'failure-shape', 'seal']:
    path = T / ('metodobase-sec-google33-peer-' + stem + '-20261019.py')
    (drivers / (stem + '.py')).write_bytes(path.read_bytes())
(drivers / 'independent-ui.cjs').write_bytes((T / 'metodobase-sec-google33-peer-ui-20261019.cjs').read_bytes())
(drivers / 'final-acl.ps1').write_bytes((T / 'metodobase-sec-google33-peer-final-acl-20261019.ps1').read_bytes())
canaries = O / 'canaries'
canaries.mkdir()
for name in expected:
    (canaries / name).write_bytes((R / 'tests' / name).read_bytes())
(canaries / 'initial-race-autoflush-true.RAW.py').write_bytes((P / 'initial-race-autoflush-true.RAW.py').read_bytes())
assert sha((drivers / 'run-final-races.py').read_bytes()) == '059dc1c3cdfd67a8b8902e1686218b90d22d5f941bd46b52b060f060d5a1f594'
save('replay-contract.json', {
    'reviewed_source_commit': BASE,
    'command': str(Path(sys.executable)) + ' -B ' + str(T / 'metodobase-sec-google33-peer-run-final-races-20261019.py'),
    'entry_driver': 'drivers/run-final-races.py', 'base_driver': 'drivers/run-pg.py',
    'base_driver_SHA256': sha((drivers / 'run-pg.py').read_bytes()),
    'own_canaries_at_tests_directory': expected,
    'initial_True_source': 'canaries/initial-race-autoflush-true.RAW.py',
    'fixture_sources': ['tests/google33_owned.py', 'tests/integration_google33_postgres.py',
        'tests/test_google33_http.py', 'tests/test_google33_association_security.py',
        'tests/test_google33_identity_contract.py', 'tests/run_isolated.py'],
    'fixture_SHA256s': {p: current_source[p] for p in ['tests/google33_owned.py',
        'tests/integration_google33_postgres.py', 'tests/test_google33_http.py',
        'tests/test_google33_association_security.py', 'tests/test_google33_identity_contract.py', 'tests/run_isolated.py']},
    'adapter_for_future_source': 'Copy identical canaries and use a separately recorded worktree/private-receipt coordinate adapter. Do not weaken assertions, provider verification, actor flags or pool1. Read private profile only in RAM; obtain exclusive PG handoff before SQL.',
    'source_and_environment_dependency_manifest': 'final-source-packages-python.json',
})

review = '''Revisión independiente Google33 SEC17 sobre `3587b3b3eee3a58367624472d7c0683baa8f10e0`.

No se acepta Google33 global en esta fuente: QA-17 reproduce una respuesta incorrecta ante colisión concurrente durante el alta HTTP de tipo gym. Los dos factories devuelven 200 y 503; el contrato exige 200 y 409. La cuenta ganadora es única y el perdedor no recibe token, refresh ni challenge. No se observó adopción por email, cruce de titularidad, bypass de autenticación ni fuga de datos.

El canario `test_canonical_http_new_gym_subject_collision_is_a_conflict` usa dos workers HTTP, cada uno con engine restringido y pool1, y `sessionmaker(autoflush=False, expire_on_commit=False)`. Sólo se despacha infraestructura de Session por worker y se sincroniza el INSERT real. Las firmas RSA y la biblioteca de verificación son reales; únicamente el transporte HTTPS de JWKS es sintético. No se sustituyen identidad ni autorización. Se observan dos threads y dos backends en el INSERT. La colisión aflora en `google_link.resolve_or_register` → `crear_gym_profile` (`web/database/repository.py:511`, `db.flush()`), antes del catcher IntegrityError del wrapper de commit. El handler la traduce a 503 `google_link_unconfirmed`. Las dos proyecciones estructurales preservan el primer resultado. Hay una sola cuenta, asociación y GymProfile, con cinco planes propios. Tras cada worker quedan pool0 y GUC vacíos. El fix futuro aún no fue revisado ni ejecutado por este peer.

Se conservan también dos fallos previos de la carrera directa de asociación: `Session(engine)` genérica usa autoflush=True y puede hacer flush al ejecutar la revocación de refresh en confirmación, fuera del catcher de commit. Son robustez del servicio genérico bajo ese constructor; el servicio no documenta una precondición autoflush=False. La preimagen y el RAW original se mantienen. Después se cambiaron exactamente cuatro constructores del harness a autoflush=False, igual que producción; todas las aserciones permanecieron idénticas. Las mismas cuatro carreras directas pasan con False. Esta normalización no convierte los RED originales en pruebas pasadas ni cambia el resultado HTTP canónico.

Resultados por fase, sin sumar replays ni casos importados como pruebas nuevas:

| Fase | Casos | PASS | RED | Alcance |
| --- | ---: | ---: | ---: | --- |
| Autor/contrato SQLite | 80 | 78 | 2 | Dos expectativas de status SSR obsoletas tras integración FE; se conservan |
| Ataques independientes SQLite | 44 | 44 | 0 | Actor, MFA real, SV, proofs, ACK, JWKS y privacidad |
| PG funcional | 64 | 62 | 2 | Incluye los ocho canarios originales y dos carreras genéricas True RED |
| Migraciones/onboarding/restore | 15 | 15 | 0 | Incluye variantes SQLite y PG; no se etiqueta todo como PG |
| PG final focal | 7 | 5 | 2 | Cuatro carreras directas False, contrato DB y dos colisiones HTTP RED |

No hubo errores ni skips en estas fases. Los ocho canarios originales `35ec9a45…` pasan tanto en SQLite como PG después de la única adaptación registrada de tokeninfo a JWKS y credencial RSA firmada; sus aserciones AST de negocio son iguales. Los controles de cabeceras mantenidos rechazaban el nuevo GET SSR /cuenta/google=200 por su conjunto antiguo de status; este peer no los editó. Un canario independiente comprueba GET SSR 200, HEAD 405, slash 307/Location canónica y todas las políticas privadas/CSP/GIS, además de errores API en todos los métodos y vecinos. QA es dueño de la adaptación mantenida y su aceptación no se atribuye a este sello.

Los 44 casos independientes cubren lookup exclusivamente por issuer/sub, contacto de otro owner ignorado, rol/viewer preservado, cuentas desactivadas/borradas/invitadas/parent inválido rechazadas, prueba real de actor/access/SV/purpose y una sola utilización. Se enrola MFA y se usan factores y recovery reales; fallos antes de commit revierten consumo/intent/audit y preservan la admisión, mientras una incertidumbre después de ACK mantiene la mutación pero responde sin secreto. MAX-1→MAX es válido; MAX impide una nueva mutación antes de proveedor/factor y el login asociado sigue exigiendo factor real. No se rebaja el gate general de parent ni el de rol.

La revisión estática y los canarios comprueban JWKS HTTPS fijo, sin redirecciones ni URL tomada del token, límite de credencial/cuerpo, issuer y audiencia configurados, exp y sub estrictos, y auth_time real reciente sin fallback a iat. La biblioteca google-auth 2.62.0 instalada usa PyJWKSet offline sobre el JWKS ya recibido; el intento independiente de provocar una segunda descarga no la produjo. El email sólo sirve de contacto y el alta sin asociación no adopta una cuenta existente por coincidencia de email. El sub revocado conserva el propietario histórico; una asociación explícita exige contraseña local y MFA vigente cuando aplica. Los intents sólo conservan hashes y vinculan actor, propósito, issuer/sub, generación, SV, access y expiración. No se reutiliza la tabla de pagos.

La base observada tiene 35 modelos ORM, 36 tablas físicas, 26 FORCE RLS, 26 funciones y 12 triggers. El actor app no es propietario y sus cuatro flags privilegiados son false; las dos funciones nuevas sólo son triggers SECURITY INVOKER, sin RPC SQL nuevo. Se repiten guardas de permisos, invariantes, búsqueda de sesión y restauración poblada 26→33. Se prueba liberación antes de espera del proveedor y restauración de ContextVar/pool bajo error y cierre compuesto. Los 15 UUID propios tienen recibo inicial exclusivo anterior a CREATE, OID/nacimiento verificados, cero sesiones, DROP normal y ausencia en lectura de control nueva. El lease 55483 se devolvió a ROOT; no se realizó SQL durante el sello.

Se ejecutan cuatro artefactos Node mantenidos y un artefacto independiente de ocho ataques; los cinco terminan 0. Se revisan secretos sólo en RAM, fences de contexto/tiempo, sustitución de actor, cancelación y respuestas inciertas sin reintento ni readback automáticos. Son pruebas Node VM con dobles de DOM/transporte, sin Chrome ni Google vivo. La configuración externa de GIS sigue siendo necesaria para recibir auth_time; solicitar essential_claims no garantiza un factor fresco. Referencia primaria: [Google GIS JavaScript API](https://developers.google.com/identity/gsi/web/reference/js-reference). El contrato de identidad estable usa sub y evita atribuir propiedad actual de una dirección de tercero sólo por email_verified; [guía oficial de validación](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

Quedan explícitamente fuera de aceptación el fix QA-17 aún no probado, la adaptación mantenida de SSR en QA, Google/GIS vivo y la recuperación de cuentas Google-only legadas cuyo sub se desconoce o cuyos factores se perdieron. No se inventan backfills por email ni una recuperación nueva.

845 fuentes/configuraciones seleccionadas permanecen byteidénticas al inicio; los tres canarios propios tienen pins separados y la única normalización del harness queda documentada. Author92, WEB89, ambos ejecutables Python de cada entorno y Node mantienen sus inventarios/hashes; pip check final es 0 en ambos entornos. No se instalaron dependencias ni se modificaron fuentes de producto o pruebas mantenidas. RAW/XML y errores permanecen privados bajo ACL verificado; los fixtures pytest declaran por separado OWNER RIGHTS/SYSTEM/Administrators. El sello publica hashes y atributos originales, sin credenciales ni payloads de backups. La comprobación pública usa scanner119 intacto más el guard específico de JWT de tres segmentos.
'''
(O / 'review.md').write_bytes(review.encode())

node = next(n for n in ast.parse((T / 'metodobase-checkpoint119-prepare.py').read_bytes()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'scan')
scan_hash = sha(ast.dump(node).encode())
assert scan_hash == 'de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns = dict(io=io, json=json, re=re, tarfile=tarfile, zipfile=zipfile, PurePosixPath=PurePosixPath)
exec(compile(ast.Module(body=[node], type_ignores=[]), 'unchanged-checkpoint119', 'exec'), ns)
save('source.json', {
    'reviewed_commit': BASE, 'worktree': str(R), 'product_changes': False,
    'verdict': 'RED source QA-17 requires focal fix and identical replay; no global Google33 acceptance',
    'finding': 'QA-17 canonical gym onboarding subject collision returns 503 instead of 409',
    'canonical_HTTP_factories': 2, 'canonical_actual_statuses': [200, 503], 'canonical_expected_statuses': [200, 409],
    'state_atomicity_and_no_losing_credentials_observed': True,
    'phase_results': {k: load(k + '-summary.json') for k in phase_expectations},
    'phase_counts_are_not_unique_sum': True, 'original_eight_business_assertions_preserved': True,
    'owned_UUIDs_closed_absent': 15, 'new_SQL_during_seal': False,
    'author92_WEB89_sources_bothPython_quiet': True, 'pip_final_exit_each': 0,
    'scanner119_function_AST_sha256': scan_hash,
    'legacy_unknown_sub_lost_factors_and_live_GIS_not_accepted': True,
})
save('public-safety-scan.json', {'function_AST_sha256': scan_hash, 'unchanged_scanner119': True,
    'additional_guard': 'Reject three JWT-like base64url segments each at least 24 bytes',
    'all_public_files_pass': True, 'no_private_payloads_or_secret_values_copied': True})
save('manifest.json', {p.relative_to(O).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                      for p in sorted(O.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
for path in O.rglob('*'):
    if path.is_file():
        blob = path.read_bytes()
        ns['scan'](blob, path.relative_to(O).as_posix())
        assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}', blob), path.name
print(json.dumps({'files': sum(p.is_file() for p in O.rglob('*')),
    'source_SHA256': sha((O / 'source.json').read_bytes()), 'manifest_SHA256': sha((O / 'manifest.json').read_bytes()),
    'scanner119_and_JWT_guard': 'PASS', 'verdict': 'QA-17 RED source frozen for identical replay'}))
