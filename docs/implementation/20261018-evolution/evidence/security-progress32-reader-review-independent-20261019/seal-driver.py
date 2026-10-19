from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

ROOT=Path(r'F:\mb-security-progress32-peer-20261019')
EV=ROOT/'docs/implementation/20261018-evolution/evidence'
OUT=EV/'security-progress32-reader-review-independent-20261019'
TMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
HEAD='bd0501cdfbad1e48d483718b66e31bb65559f05e'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert not OUT.exists()
phases=[EV/'security-progress32-reader-independent-20261019',
    EV/'security-progress32-reader-independent-v2-20261019',EV/'security-progress32-reader-independent-v3-20261019']
summaries=[json.loads((p/'summary.json').read_bytes()) for p in phases]
assert summaries[0]['outcomes']=={'passed':0,'failure':0,'error':22,'skipped':0} and summaries[0]['lease_count']==0
assert summaries[1]['outcomes']=={'passed':20,'failure':2,'error':0,'skipped':0}
assert summaries[2]['outcomes']=={'passed':3,'failure':0,'error':0,'skipped':0}
for s in summaries:
    assert s['sources_packages_python_pg_profile_exact'] and s['packages']==89 and s['pip_before']==s['pip_after']==0
leases=[]
for p in phases[1:]:leases+=json.loads((p/'resource-closure.json').read_bytes())
assert len(leases)==5 and len({l['database'] for l in leases})==5
for l in leases:
    assert l['initial_creation']=='exclusive_xb_before_CREATE' and l['state']=='closed_absent'
    assert l['sessions_before_drop']==0 and l['absence_verified']=='fresh_control_connection'
    assert l['launcher_birth_filetime']==l['launcher_birth_after_CREATE'] and l['server_port']==55483
old=ast.parse((phases[1]/'test_security_progress32_peer.py').read_bytes())
new=ast.parse((phases[2]/'test_security_progress32_peer.py').read_bytes())
functions=lambda tree:{n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
a,b=functions(old),functions(new)
role='test_authority_locks_block_updates_then_changed_source_and_reader_roles_deny_old_scope'
assert a.keys()==b.keys()
for name in a:
    if name!=role:assert ast.dump(a[name])==ast.dump(b[name])
old_asserts=[ast.dump(n) for n in ast.walk(a[role]) if isinstance(n,ast.Assert)]
new_asserts=[ast.dump(n) for n in ast.walk(b[role]) if isinstance(n,ast.Assert)]
assert all(n in new_asserts for n in old_asserts) and len(new_asserts)==len(old_asserts)+1
v2=json.loads((phases[1]/'cases.STRUCTURAL.json').read_bytes())
v3=json.loads((phases[2]/'cases.STRUCTURAL.json').read_bytes())
failed={c['case'] for c in v2 if c['outcome']=='failure'}
assert len(failed)==2 and failed<={c['case'] for c in v3 if c['outcome']=='passed'}
passing={c['case'] for c in v2 if c['outcome']=='passed'}|{c['case'] for c in v3 if c['outcome']=='passed'}
assert len(passing)==23
diag=TMP/'metodobase-sec32-peer-private-v3-20261019/parent-boundary.json'
diagnostic=json.loads(diag.read_bytes())
assert diagnostic['classification']=='DIAGNOSTIC_AUTH_BOUNDARY_ONLY'
assert diagnostic['prior_explicit_consent_http']==200 and diagnostic['withdraw_after_shutdown_http']==401

OUT.mkdir();(OUT/'.gitattributes').write_bytes(b'* -text\n')
(OUT/'seal-driver.py').write_bytes(Path(__file__).read_bytes())
(OUT/'parent-boundary.json').write_bytes(diag.read_bytes())
def dump(path,value):path.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf8'))
dump(OUT/'case-coverage.json',{'unique_cases_with_passing_observation':sorted(passing),
    'scoped_reader_cases':22,'separate_authentication_boundary_diagnostic':1,
    'v2_role_fixture_assertions':len(old_asserts),'v3_role_fixture_assertions':len(new_asserts),
    'all_v2_role_assertions_retained':True,'other_own_functions_ast_identical':True,
    'note':'20 cases passed in v2; only the two role-fixture cases were replayed in v3, with one new diagnostic. No single23-case green run is claimed.'})
dump(OUT/'resource-closure.json',leases)
review='''Revisión independiente R25: PASS_BOUNDED_READER_SCOPED

Fuente revisada: bd0501cdfbad1e48d483718b66e31bb65559f05e, candidata backend32. Sus29 archivos de fuente fueron autenticados contra los SHA GitLF del freeze del autor. No se cambió ningún archivo de producto ni aserción del autor. Esta revisión no atribuye el resultado a una composición posterior con UI, CI, SEC15 u otros fixes.

El lector obtiene la identidad desde el principal autenticado y vuelve a comprobar bajo locks las cuentas, el gimnasio, el vínculo/cliente, el último consentimiento exacto y la suscripción vigente con el derecho canónico. El cambio temporal del tenant ocurre después de esos locks, en el mismo Connection y dentro de un SAVEPOINT. No se usa un GUC como firma; el rol de aplicación ya podía configurar los GUC existentes. No apareció una función SQL que exponga el diario, SECURITY DEFINER, nuevo bypass ni ampliación de las políticas RLS del diario. La confianza en el código que puede ejecutar SQL arbitrario permanece como límite previo; no se presenta como una nueva defensa contra SQL arbitrario.

La proyección selecciona medidas declaradas y devuelve del diario sólo local_date/registered/completed/valid. El contenido JSON permanece en SQL, con materialización y cota de bytes antes del parseo. Los contadores describen snapshots completados entre los registrados: no ingestion, adherencia ni resultado clínico. La fecha, categorías, vínculo y consentimiento observados se validan en cada consulta; un cursor no concede autoridad.

Se reprodujeron16 casos PostgreSQL/HTTP del autor y se ejecutaron6 canarios propios sobre migración real32, rol restringido y pool1. En v2 pasaron20/22: los cuatro canarios propios de restauración pasaron, incluyendo error al restaurar tenant y fallo de ROLLBACK TO que obliga a invalidar el Connection antes de reutilizar el pool. Ambos errores dan503 opaco sin resultado parcial; el siguiente préstamo y /auth/me de otra cuenta fueron válidos con contexto limpio. Los locks de Usuario, Subscription y vínculo bloquearon SELECT FOR UPDATE NOWAIT con55P03 durante una lectura autorizada.

Las dos rojas finales de v2 fueron un error de fixture propio: se esperaba403 tras crear un gym/VIEWER no canónico, pero la identidad se rechazó antes con401. V3 conserva esa observación mediante un assert401 adicional, cambia después el tipo de ese VIEWER a un espacio personal canónico y mantiene intacto el assert403 original. Se repitieron sólo esos dos casos, ambos verdes. Las demás funciones propias conservan AST idéntico y todas las aserciones originales de la función de roles siguen presentes. No se relajó ningún assert del autor ni se cambió producto para obtener el resultado.

Los cinco UUID PostgreSQL del peer tienen lease inicial abierto con xb antes de CREATE, identidad OID/owner y nacimiento de proceso, actualizaciones CAS del recibo y cierre con cero sesiones, DROP normal y ausencia desde una conexión de control fresca. No se terminaron sesiones ni se modificaron HBA, roles globales o bases ajenas. En v2 y v3 permanecieron iguales10189/10190 archivos observados respectivamente,89 metadatos de distribución y SHA de Python, postgres.exe y perfil privado. pipcheck devolvió0 antes/después de ambas fases; estos metadatos no son un hash de cada byte instalado.

La primera preparación v1 falló antes de conectar a PostgreSQL: la firma ctypes de GetProcessTimes no estaba declarada para HANDLE de64 bits. Se conservan sus22 errores y sus bytes originales; se corrigió sólo el helper propio. No hubo UUID ni SQL PostgreSQL en esa fase. El conftest ordinario puede preparar su SQLite local, por lo que no se afirma ausencia de todo SQL. Los RAW JUnit/stdout/stderr quedan privados; v2 contiene representaciones diagnósticas de bearer truncadas y no se publica. Los archivos públicos sólo proyectan IDs, outcomes, hashes y recibos no secretos.

Límite de autenticación confirmado, separado de la aceptación del lector: una cuenta usuario/VIEWER nacida mediante invitación real de equipo protegida por MFA, aceptación pública y login por contraseña pudo otorgar y consultar un consentimiento completion-only hacia otro gimnasio activo. Desactivar sólo su parent mediante SQL administrativo dejó la cuenta activa, pero las rutas propias de metadata/retiro devolvieron401 por auth global; la lectura profesional devolvió404. No se creó withdraw. Reactivar el parent permitió de nuevo la proyección del grant anterior, conforme al contrato que no interpreta OFF→ON como retirada. No se afirma un endpoint público que desactive ese parent ni una vulnerabilidad de acceso. El requisito global de retiro propio cuando el login general deja de ser válido sigue abierto en R25/R31; el helper retirement_actor no constituye una entrada de autenticación independiente.

Aceptación limitada a los22 controles de lector/scope ejecutados (20 en v2 y dos replays v3). El diagnóstico adicional no cierra retiro universal, exportación/headers, restore independiente, UI, CI32, suite amplia, proveedores, operación ni revisión clínica. El coordinador informó dos canarios QA pendientes sobre Referrer-Policy de errores de exportación; su fix no está incluido ni aceptado por este peer.
'''
(OUT/'review.md').write_bytes(review.encode('utf8'))
design='''Diseño exploratorio: retiro propio cuando auth general no está disponible

No contiene implementación, nuevas rutas, DDL, credenciales o proveedor. No autoriza relajar verificar_token, MFA de login, pertenencia profesional ni RLS del diario.

Propuesta mínima: dos operaciones de propósito exclusivo, consulta de metadatos propios y retiro de un consentimiento exacto. Cada llamada demuestra otra vez titularidad mediante la primaria admitida para esa cuenta y, si existe un factor activo, TOTP/recovery existente. No se emiten access/refresh, sesión general ni grants portables. Repetir la prueba por operación permite explorar el mecanismo sin añadir otro tipo de token o revisar el CHECK de MfaAuthorization en una nueva DDL. Un TOTP usado para consultar no puede reutilizarse para retirar: haría falta otro código vigente o recovery no usado, explicado claramente en UI.

El sujeto se deriva exclusivamente de la primaria verificada y se vuelve a cargar bajo lock de Usuario. Se exige activo, no borrado, invitation_token IS NULL y SV entero0..MAX inclusivo; el cambio propuesto consiste sólo en no exigir un parent profesional disponible para ese propósito. Un bearer general inválido no sería prueba suficiente. No hay selección de sujeto por body, email sin prueba, gym/client/storage ID ni GUC aportado por el navegador. bind_mfa_actor se instalaría sólo después de demostrar esa identidad; el GUC seguiría siendo contexto interno, nunca firma.

La consulta mostraría únicamente los propios eventos actuales necesarios para elegir el recurso: sin perfil, valor de salud, contactos, cartera, lookup de fuentes o capacidad de conceder permiso. El retiro usaría ProgressConsent.user_id propio, ID/versión CAS del último grant y copia exacta de su tuple de alcance; sólo append withdraw. No permitiría crear perfiles/medidas/grants, cambiar factores, recuperar códigos ni alterar SV. TOTP/recovery consumido, auditoría mínima y evento withdraw pertenecerían a la misma transacción confirmada. Un conflicto o rollback no dejaría retirada parcial; un commit incierto produciría503 sin replay automático y exigiría consulta explícita con otra prueba válida.

Amenazas y comprobaciones necesarias antes de implementar: enumeración de cuentas y diferencias de tiempo (fallo primario genérico/dummy hash); fuerza bruta distribuida (admisión por actor+propósito/IP y presupuesto durable, Redis de producción fail-closed); mezcla de cuenta/contexto/recurso y replay (cada llamada demuestra su sujeto y exacto recurso, factor one-use, ningún secreto en Storage/URL/log); cambio de password/SV/generación entre prueba y ejecución (revalidación/locks en la transacción); carreras de reemplazo/retiro (CAS y lock del propio actor); parent/OWNER ambiguo y fuente ocultada (sólo own metadata); sesiones/pool/GUC residuales (mismos checks y canarios de restauración que el lector); volumen de historial y denegación de servicio (consulta paginada, body/tiempo acotados, sin cargado completo).

La primaria Google exige verificar antes su contrato vigente de issuer/audience/expiry/subject o vinculación de cuenta y autenticación reciente; no se sustituye por email o token no verificado. No se mantendrían locks mientras se llama al proveedor. Las cuentas sin password, un proveedor no disponible o la pérdida de todos los factores requieren diseño y pruebas explícitos; no se inventa un fallback débil ni se afirma que ese procedimiento operativo exista. La custodia/rotación de claves y recuperación legítima siguen pendientes donde corresponda.

Antes de aceptar el mecanismo: ejecutar ambas fábricas donde proceda, PostgreSQL con rol restringido/pool1, cierres de parent/source/link, todas las variantes de primaria/factor soportadas, replay/concurrencia y commit incierto; demostrar que nunca devuelve token de login ni habilita perfil/grant/cartera. Se revisará de nuevo el contrato purpose-limited, sin incorporar automáticamente esta propuesta a32.
'''
(OUT/'retirement-design.md').write_bytes(design.encode('utf8'))

scanner=ast.parse((TMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(n for n in scanner.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<maintained-public-scanner>','exec'))
phase_receipts=[]
verdicts=['REJECTED_OWN_PREPARATION','PARTIAL_TWO_OWN_FIXTURE_ERRORS','PASS_TARGETED_REPLAY_AND_AUTH_BOUNDARY_DIAGNOSTIC']
for p,s,verdict in zip(phases,summaries,verdicts):
    assert (p/'.gitattributes').read_bytes()==b'* -text\n'
    assert not (p/'manifest.json').exists() and not (p/'source.json').exists()
    dump(p/'source.json',{'source_head':HEAD,'verdict':verdict,'summary_sha256':sha((p/'summary.json').read_bytes()),
        'note':'The ownership-harness summary means no author assertions/product changes. V3 adds an own401 assert and corrects only the typed role fixture, as the final review explains.'})
    for file in p.rglob('*'):
        if file.is_file():scan(file.read_bytes(),p.name+'/'+file.relative_to(p).as_posix())
    manifest={f.relative_to(p).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())}
        for f in sorted(p.rglob('*')) if f.is_file() and f.name not in {'.gitattributes','manifest.json'}}
    dump(p/'manifest.json',manifest)
    phase_receipts.append({'prefix':p.name,'verdict':verdict,'manifest_sha256':sha((p/'manifest.json').read_bytes()),
        'source_sha256':sha((p/'source.json').read_bytes())})
source={'source_head':HEAD,'verdict':'PASS_BOUNDED_READER_SCOPED','author_cases_replayed':16,'own_reader_cases':6,
    'separate_auth_boundary_diagnostic':1,'single23_case_green_run_claimed':False,'own_postgres_uuids_closed':5,
    'phases':phase_receipts,'retirement_without_general_login':'Open R25/R31; design only, no product change',
    'scope':'Source-reader/authority/context controls only. No full R25/R31, export privacy headers, UI, CI, restore, provider, production or clinical acceptance.'}
dump(OUT/'source.json',source)
for p in OUT.rglob('*'):
    if p.is_file():scan(p.read_bytes(),p.relative_to(OUT).as_posix())
dump(OUT/'manifest.json',{p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in {'.gitattributes','manifest.json'}})
files=[p.relative_to(ROOT).as_posix() for parent in [*phases,OUT] for p in sorted(parent.rglob('*')) if p.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*files],cwd=ROOT,check=True,capture_output=True)
for name in files:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
subprocess.run(['git','commit','-m','Record scoped independent progress reader review and retirement boundary design'],cwd=ROOT,check=True,capture_output=True)
print(json.dumps({'commit':git('rev-parse','HEAD').decode().strip(),'files':len(files),
    'source_sha256':sha((OUT/'source.json').read_bytes()),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),
    'phase_receipts':phase_receipts}))
