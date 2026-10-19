from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

ROOT=Path(r'F:\mb-security-google-subject-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-google-subject-association-independent-20261019'
HEAD='345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert (OUT/'.gitattributes').read_bytes()==b'* -text\n'
assert not (OUT/'manifest.json').exists() and not (OUT/'source.json').exists()
summary=json.loads((OUT/'summary.json').read_bytes())
assert summary['outcomes']=={'passed':4,'failure':4,'error':0,'skipped':0} and summary['exit']==1
assert summary['sources_packages_python_acl_exact'] and summary['pip_before']==summary['pip_after']==0
assert json.loads((OUT/'before.json').read_bytes())==json.loads((OUT/'after.json').read_bytes())
observed=json.loads((OUT/'observations.json').read_bytes())
assert len(observed)==8
for name,item in observed.items():
    if name.startswith('unbound-login'):
        assert len(item['outcomes'])==2 and item['persisted_password_unchanged']
        assert all(x=={'google_http':200,'issued_general_tokens':True,'resolved_existing_password_account':True} for x in item['outcomes'])
        assert len(item['provider_calls'])==2
    elif name.startswith('unbound-reauth'):
        assert item['google_reauth_http']==200 and item['issued_primary_reauthentication_proof']
        assert item['existing_second_factor_still_required'] is True
    else:assert item['google_http']==401 and item['issued_general_tokens'] is False
    for call in item['provider_calls']:
        assert call['fixed_https_tokeninfo'] and call['sub_nonempty'] and call['issuer_google'] and call['future_exp']
        assert call['hd_absent'] and call['email_verified_true']

(OUT/'seal-driver.py').write_bytes(Path(__file__).read_bytes())
provider_ast=ast.parse((ROOT/'web/services/google_identity.py').read_bytes())
primary=next(n for n in provider_ast.body if isinstance(n,ast.ClassDef) and n.name=='VerifiedGooglePrimary')
primary_fields=[n.target.id for n in primary.body if isinstance(n,ast.AnnAssign)]
assert primary_fields==['email','authenticated_at']
routes_ast=ast.parse((ROOT/'web/routes/auth.py').read_bytes())
login=next(n for n in routes_ast.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='google_login')
service_ast=ast.parse((ROOT/'web/services/mfa_service.py').read_bytes())
reauth=next(n for n in service_ast.body if isinstance(n,ast.FunctionDef) and n.name=='reauthenticate')
models_ast=ast.parse((ROOT/'web/database/models.py').read_bytes())
payments=next(n for n in models_ast.body if isinstance(n,ast.ClassDef) and n.name=='ProviderSubjectAssociation')
payment_strings=[n.value for n in ast.walk(payments) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
assert "provider IN ('stripe','mercadopago')" in payment_strings
assert "resource_type IN ('customer','subscription','payment','preference')" in payment_strings
static={'source_head':HEAD,'VerifiedGooglePrimary_fields':primary_fields,
    'google_login_function_ast_sha256':sha(ast.dump(login).encode()),
    'reauthenticate_function_ast_sha256':sha(ast.dump(reauth).encode()),
    'payment_association_provider_check':"provider IN ('stripe','mercadopago')",
    'payment_association_resource_check':"resource_type IN ('customer','subscription','payment','preference')",
    'reviewed_paths':['web/services/google_identity.py','web/routes/auth.py','web/services/mfa_service.py',
        'web/database/models.py','web/sync_user.py'],
    'observations':['Login selects persisted Usuario by normalized provider email, not Google subject.',
        'Google primary reauthentication compares provider email and fresh auth_time, without a persisted Google subject binding.',
        'The sync bridge is a no-op; payment subject mappings are a separate constrained domain and are not a hidden Google identity binding.']}
(OUT/'static-boundary.json').write_bytes((json.dumps(static,indent=2)+'\n').encode())
review='''Revisión independiente: CONFIRMED_ASSOCIATION_CONTRACT_GAP_SCOPED — SEC17 propuesto

Fuente345aa7ce16f65fec9481b48cfcd63c33ff3835fc. La revisión confirma una decisión local de asociación por email, no un bypass de validación criptográfica de Google. Se autenticaron las cuatro entradas y el hash del manifiesto del análisis root47f479889f5ff5693894909767df971f930116c897e1a1342c4f39ebc6c5d330, y sus cuatro fuentes contra GitLF. No se cambió producto, auth, DTO, DDL ni criterio anterior.

Google recomienda asociar el sub estable con la cuenta local. Para correos externos sin hd, email_verified puede reflejar una verificación histórica y Google recomienda otra prueba de propiedad; también describe vincular una cuenta existente tras demostrar acceso a ella. [Contrato oficial de Google, consultado para esta revisión](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

Se ejecutaron dos fábricas reales sobre SQLite propia migrada32, con registro/login por contraseña reales. El único doble del proveedor es httpx.MockTransport bajo un AsyncClient real; no se reemplazó verified_google_info, verified_google_reauthentication, identidad, auth dependency ni verificador de tokens locales. La entrega offline y configuración de base son las del fixture ya declarado. El doble exige GET al HTTPS fijo tokeninfo y presenta un resultado modelado coherente en aud, issuer Google, exp futuro, sub no vacío y email_verified=true para correo sintético externo sin hd. El credential de entrada es sintético: no es un ID token firmado ni fue aceptado por Google real.

Primer resultado preservado: ocho casos, cuatro canarios rojos y cuatro controles verdes, cero errores/skips. En cada fábrica /auth/google emitió200 con access/refresh ante dos sub modelados distintos que presentaban el mismo email de una cuenta local creada con contraseña. /auth/me de esos tokens resolvió esa misma cuenta. La petición Google no presentó password, segundo factor ni Authorization. El hash de password persistido no cambió; la observación es emisión de autoridad a esa cuenta sin vinculación de sujeto, no sustitución de su contraseña.

Otros dos canarios completaron por HTTP configuración MFA, password login y recuperación de un solo uso, y observaron200 con prueba de reautenticación primaria al presentar un Google subject no vinculado con el mismo email y auth_time reciente. La regeneración de recovery sin segundo factor permaneció422. Esto confirma la asociación incompleta de primaria, sin demostrar bypass del segundo factor. Los cuatro controles de aud incorrecto o respuesta tokeninfo400 devolvieron401 sin sesión local.

Interpretación y alcance: si Google entrega legítimamente un resultado con email externo cuya propiedad cambió, confiar sólo en ese email puede asociar otra identidad Google con una cuenta password preexistente. Es una inferencia del contrato oficial junto con la decisión local reproducida, no un caso de Google live ni una cuenta real comprometida. El test no demuestra que Google acepte firmas falsas, issuer inválido o tokens vencidos; esos casos imposibles no se usaron como prueba. La sucesión de dos subjects modela la independencia de sujeto y email, no afirma que Google haya emitido ambas assertions concretas.

R02 conserva un criterio sobre transformación de permisos/rol/membresía persistidos entre métodos de login. Este hallazgo distinto concierne a qué identidad externa puede seleccionar esa cuenta antes de aplicar esa transformación. Se propone SEC17 por asociación automática de un subject no vinculado con una cuenta existente. Riesgo sugeridoP1 para priorización por el coordinador, condicionado al escenario del proveedor; no se etiqueta como exploit de producción demostrado. La misma evaluación no convierte todos los usos de Google/email en una vulnerabilidad ni invalida controles MFA ya observados.

Los10342 archivos observados,89 metadatos de distribución y SHA de Python permanecieron idénticos durante la ejecución; pipcheck0 antes/después. Los metadatos no hashéan cada byte instalado. El DACL de RAW/SQLite de este ensayo permaneció protegido con dos reglas explícitas, usuario actual y SYSTEM, antes/después; sólo su huella se publica. Se conservan JUnit/stdout/stderr originales y SQLite bajo ese directorio privado. Los ocho recibos públicos omiten credential, bearer, factor, seed, códigos, email e IDs locales, y se escanean con el detector mantenido119.

No se ejecutaron Google live, PostgreSQL, Chrome, VM, carga, proveedor de correo, migración33 o fix de retiro. Esta evidencia establece un canario independiente rojo y un contrato pendiente, no aprueba el candidato para este requisito. Los cuatro canarios quedan inmutables para el replay de un futuro fix; ninguna aserción se bajó para obtener un verde.
'''
(OUT/'review.md').write_bytes(review.encode('utf8'))
design='''Propuesta futura de asociación Google — diseño, sin implementación

Separar la identidad externa de email/contacto. Una migración33 aditiva puede crear una tabla de asociaciones de autenticación con issuer Google validado/canónico, sub estable y FK al Usuario, con unicidad de issuer/sub que impida asociarlo a dos cuentas. El CHECK de ProviderSubjectAssociation pertenece a pagos Stripe/MercadoPago; no se extiende ni se reutiliza silenciosamente. Se congelarán targets y firmas nuevos sin modificar las migraciones/contratos22–32 ni inferir sub históricos.

Un login Google con asociación existente resolvería Usuario por issuer/sub y aplicaría después exactamente la identidad persistida, revocación y MFA actuales. Email cambiado no seleccionaría otra cuenta ni sobrescribiría contactos, rol, tipo, membresía, catálogo o derechos. La normalización de issuer admitiría sólo los valores Google ya verificados; audience seguiría validándose contra configuración del servidor. La existencia de una cuenta con email coincidente no autorizaría merge/login por sí sola.

Para vincular una identidad no asociada a una cuenta existente: prueba primaria independiente vigente de esa cuenta y segundo factor existente cuando esté habilitado, más Google verificado con el subject elegido. El flujo debe demostrar ambas titularidades, mostrar la acción explícita y consumir un intento de vinculación de un solo uso, ligado al Usuario, issuer/sub, intención, SV y generación MFA. No basta el email, un access obtenido por el camino actual no vinculado, un token aportado por el navegador sin verificar o una sesión genérica como sustituto de primaria fresca. Los dos lados se vuelven a validar bajo locks/CAS y restricción única; no sale sesión ni confirmación antes del ACK del commit.

El mecanismo de intento/vínculo duradero, sus permisos y targets se decidirá dentro del diseño33 y tendrá revisión independiente. No se inventa una firma en un GUC ni se amplían RLS del diario. No se mantienen locks durante llamadas Google. Un conflicto entre dos cuentas, repetición, rollback o commit incierto queda visible sin adopción parcial ni retry automático. Preservar rol/membresía es obligación adicional a probar el subject, no una alternativa.

Las cuentas Google-only legadas tienen password aleatorio desconocido y carecen de sub histórico verificado en este camino. La migración no rellena subject desde email ni marca propiedad histórica supuesta. Su vinculación requiere una prueba vigente que realmente puedan completar o un proceso de recuperación ya autorizado y revisado, manteniendo el factor existente. No se afirma que soporte manual, proveedor live o esa recuperación operacional hayan sido validados. Deben evaluarse continuidad y salida para esas cuentas antes de integrar un bloqueo; no se deja un fallback de asociación por email para evitar el problema. Onboarding nuevo con correo externo no autoritativo y operaciones de unlink/reasignación requieren contrato propio para no convertir un contacto ambiguo en prueba de recuperación.

MFA Google reauth debe conservar issuer/sub verificado y confirmar que su asociación corresponde al actor esperado, además de auth_time reciente; iat o refresh no sustituyen esa prueba. El segundo factor y los grants de acciones permanecen exactos. El retiro excepcional actual32 sigue siendo password-only/fail-closed para primaria no disponible; este diseño33 no se mezcla con él.

Validación futura mínima: conservar los ocho casos originales y su RAW; negar sesión y reauth primaria para sub no vinculado, conservar cuatro controles; probar vínculo explícito password+MFA+Google y login por sub tras cambio de email; colisión/replay/concurrencia entre usuarios; revocación y cambio SV/generación; Google-only legado sin backfill; errores de proveedor/rollback/ACK; ambas fábricas y PostgreSQL restringido/pool1; restore/upgrade/downgrade revisados y correspondencia CI33, preservando archivos/asserts históricos. Un downgrade no destruirá asociaciones sin una vía de restauración/exportación revisada.
'''
(OUT/'future-binding-contract.md').write_bytes(design.encode('utf8'))
source={'source_head':HEAD,'verdict':'CONFIRMED_ASSOCIATION_CONTRACT_GAP_SCOPED','proposed_finding_id':'SEC17',
    'first_run_cases':8,'failed_security_canaries':4,'passed_provider_rejection_controls':4,
    'factory_count':2,'canary_source_sha256':sha((ROOT/'tests/test_security_google_subject_peer.py').read_bytes()),
    'root_contract_manifest_sha256':'47f479889f5ff5693894909767df971f930116c897e1a1342c4f39ebc6c5d330',
    'no_product_changes':True,'no_live_google_or_cryptographic_bypass_claim':True,
    'future_design_only':'Separate identity binding, explicit independent primary+existing factor+verified Google subject, additive33; no subject backfill from email',
    'scope':'Modeled valid-result local association decision and HTTP canaries only. No deployed exploit, PG, browser, VM, future fix, migration33 or global auth acceptance.'}
(OUT/'source.json').write_bytes((json.dumps(source,indent=2)+'\n').encode())
scanner=ast.parse(Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(n for n in scanner.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<maintained-public-scanner>','exec'))
for p in OUT.rglob('*'):
    if p.is_file():scan(p.read_bytes(),p.relative_to(OUT).as_posix())
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in {'.gitattributes','manifest.json'}}
(OUT/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
files=[p.relative_to(ROOT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*files],cwd=ROOT,check=True,capture_output=True)
for name in files:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
subprocess.run(['git','commit','-m','Record independent Google account-association canaries and binding contract'],cwd=ROOT,check=True,capture_output=True)
print(json.dumps({'commit':git('rev-parse','HEAD').decode().strip(),'files':len(files),
    'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'source_sha256':sha((OUT/'source.json').read_bytes()),
    'canary_sha256':source['canary_source_sha256']}))
