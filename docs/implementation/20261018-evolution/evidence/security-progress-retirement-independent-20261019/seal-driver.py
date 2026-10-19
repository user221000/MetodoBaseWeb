from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(r'F:/mb-security-retirement-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-progress-retirement-independent-20261019'
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-retirement-peer-private-20261019')
HEAD='fcfb55e5849e0e20b568be8729dcc1b8c6b1762e'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
def dump(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert not (OUT/'manifest.json').exists()
phases={name:json.loads((OUT/name/'summary.json').read_bytes()) for name in ['baseline-lineage','sqlite-freeze','postgres-freeze']}
assert phases['baseline-lineage']['outcomes']=={'passed':0,'failure':1,'error':0,'skipped':0}
assert phases['sqlite-freeze']['outcomes']=={'passed':73,'failure':2,'error':0,'skipped':0}
assert phases['postgres-freeze']['outcomes']=={'passed':24,'failure':2,'error':0,'skipped':0}
for name,summary in phases.items():
    assert summary['sources_packages_python_exact'] and summary['packages']==89
    assert summary['pip_before']==summary['pip_after']==0
    assert json.loads((OUT/name/'before.json').read_bytes())==json.loads((OUT/name/'after.json').read_bytes())
for phase in ['sqlite-freeze','postgres-freeze']:
    cases=ET.parse(PRIVATE/phase/'results.xml').findall('.//testcase')
    failed=[c for c in cases if c.find('failure') is not None]
    assert len(failed)==2
    assert all(c.get('name').startswith('test_unavailable_commit_rollback_and_precleanup_close_invalidates_owned_session') for c in failed)
    assert all('assert 1 == 0' in c.find('failure').get('message','') for c in failed)
import sqlalchemy,psycopg2._psycopg,_sqlite3
dump('driver-final-only.json',{'scope':'After tests only; version metadata is included in each before/after photo. No temporal binary-byte integrity claim.',
    'SQLAlchemy':{'version':sqlalchemy.__version__,'module_sha256':sha(Path(sqlalchemy.__file__).read_bytes())},
    'psycopg2_extension_sha256':sha(Path(psycopg2._psycopg.__file__).read_bytes()),
    'sqlite3_extension_sha256':sha(Path(_sqlite3.__file__).read_bytes())})
baseline=json.loads((OUT/'baseline-lineage/lineage.json').read_bytes());current=json.loads((OUT/'sqlite-freeze/lineage.json').read_bytes())
assert (baseline['metadata_http'],baseline['withdraw_http'])==(404,404)
assert (current['metadata_http'],current['withdraw_http'])==(200,200)
assert baseline['general_login_after_parent_off']==current['general_login_after_parent_off']==401
leases={p.name:json.loads(p.read_bytes()) for p in sorted((PRIVATE/'leases').glob('*.json'))}
assert len(leases)==2
for state in leases.values():
    assert state['state']=='closed_absent' and state['sessions_before_drop']==0
    assert state['initial_creation']=='exclusive_xb_before_CREATE' and state['absence_verified']=='fresh_control_connection'
    assert state['launcher_birth_filetime']==state['launcher_birth_after_CREATE']
dump('resource-closure.json',leases)
command="$reviewAcl = Get-Acl -LiteralPath '"+str(PRIVATE)+"'; [pscustomobject]@{sddl=$reviewAcl.Sddl; protected=$reviewAcl.AreAccessRulesProtected; rules=$reviewAcl.Access.Count} | ConvertTo-Json -Compress"
acl=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',command]))
initial=(PRIVATE/'acl.private.raw.txt').read_text(encoding='utf-8-sig').strip()
assert acl['sddl']==initial and acl['protected'] is True and acl['rules']==2
dump('raw-acl.json',{'initial_setup_before_testing':'protected current user and SYSTEM only, two explicit rules','final_matches_initial_sddl':True,'protected':True,'explicit_rules':2,'sddl_sha256':sha(initial.encode()),'scope':'Initial setup and final recheck. No claim of per-byte installed-package integrity or continuous ACL monitoring.'})
rawattrs={}
for path in sorted(PRIVATE.rglob('*')):
    if path.is_file():
        stat=path.stat();rawattrs[path.relative_to(PRIVATE).as_posix()]={'bytes':stat.st_size,'sha256':sha(path.read_bytes()),'mtime_ns':stat.st_mtime_ns,'creation_ns':getattr(stat,'st_birthtime_ns',stat.st_ctime_ns),'windows_file_attributes':getattr(stat,'st_file_attributes',None)}
dump('private-raw-attributes.json',rawattrs)
for name in ['test_security_retirement_peer.py','test_security_retirement_lineage.py','integration_security_retirement_peer.py','security_retirement_owned.py']:ast.parse((ROOT/'tests'/name).read_bytes())
(OUT/'prepare-driver.py').write_bytes(Path(__file__).with_name('metodobase-sec-retirement-peer-prepare-20261019.py').read_bytes())
(OUT/'seal-driver.py').write_bytes(Path(__file__).read_bytes())
copies={'independent-faults.py':'test_security_retirement_peer.py','independent-lineage.py':'test_security_retirement_lineage.py','independent-postgres.py':'integration_security_retirement_peer.py','independent-owned.py':'security_retirement_owned.py'}
for public,live in copies.items():assert (OUT/public).read_bytes()==(ROOT/'tests'/live).read_bytes()
models={'fault_source_sha256':sha((ROOT/'tests/test_security_retirement_peer.py').read_bytes()),'source_immutable':True,
    'sqlalchemy':'2.1.5','psycopg2-binary':'2.9.13','first_sqlite':phases['sqlite-freeze'],'first_postgres':phases['postgres-freeze'],
    'passing_close_control':'Session.close raises before super only after successful real operation commit; connection is already returned by SQLAlchemy commit.',
    'failing_cleanup_model':'Operation Session.commit raises before super; the same retained Session.rollback raises before super; Session.close raises before super. A strong reference prevents GC masking the retained checkout.',
    'confirmed_observations':['503 opaque result; no successful response','ContextVar restored to previous unrelated actor','pool.checkedout()==1 before harness cleanup on both factories and both dialects','No explicit Session.invalidate fallback exists in frozen _execute','Harness finally calls unbound real Session.rollback/close only on its retained own Session; owned DBs then close normally'],
    'limits':'Synthetic Session-boundary fault injection, not an observed psycopg2/SQLite driver failure, remote exploit, cross-tenant data leak or general authentication bypass.',
    'recommendation':'Consider invalidating only the newly owned Session after failed cleanup, preserving opaque503 and finally restoration. Retain these exact assertions; no pool-wide dispose, ambient retagging or reuse of an uncertain factor.'}
dump('cleanup-fault-model.json',models)
source={'source_head':HEAD,'parent':'345aa7ce16f65fec9481b48cfcd63c33ff3835fc','verdict':'FUNCTIONAL_SECURITY_CONTROLS_PASS_CLEANUP_FAULT_OPEN',
    'author_sqlite_pass':68,'author_pg_pass':16,'own_sqlite':{'passed':5,'cleanup_fault_red':2},'own_pg':{'passed':8,'cleanup_fault_red':2},
    'baseline_supported_lineage':{'same_canary_source':True,'expected_contract_red':1,'metadata':404,'withdraw':404},
    'candidate_supported_lineage':{'metadata':200,'withdraw':200,'general_auth':401},
    'phases':phases,'owned_pg_databases_closed':len(leases),'no_product_or_author_test_changes':True,
    'source_photos_scope':'Every Python source beneath web/api/core/config/tests, including own harness:513 baseline and526 candidate. Distribution name/version metadata89 and interpreter/base executable hashes. No claim of hashing all installed package bytes or every repository asset.',
    'scope':'Frozen limited-retirement APIs, real factories, SQLite32 and restricted own PostgreSQL32 pool1; excludes mounted SSR/UI/browser, Google33/recovery, live providers, deployment and global R25/R31 closure.'}
dump('source.json',source)
review='''Revisión independiente del retiro propio limitado — fuente fcfb55e5849e0e20b568be8729dcc1b8c6b1762e

Los controles funcionales y de autoridad ejecutados pasan. Queda un borde reproducido de limpieza bajo fallo compuesto de Session; esta revisión no da aceptación incondicional ni cierra R25/R31 globalmente. No se cambió producto ni aserciones del autor. Se autenticaron 67 archivos listados más el manifiesto del autor, las doce fuentes Git LF congeladas y wire-v1; source/manifest y detalles constan en author-authentication.json.

El canario propio conserva el mismo RAW antes/después. Crea un VIEWER por invitación de equipo realmente protegida por MFA, aceptación pública y login de contraseña, y obtiene previamente un grant explícito por HTTP con otro gimnasio profesional. La elegibilidad comercial y Cliente son fixtures declarados; únicamente apagar el parent es estímulo SQL administrativo, sin afirmar una ruta pública de desactivación. Con parent OFF, auth general permanece401. En345aa7 las dos rutas de retiro devuelven404; en fcfb55e devuelven200, consultan el evento propio y añaden un withdraw, sin tokens generales. No se sustituye identidad ni se crea una membresía imposible mediante SQL en este canario.

Primer replay SQLite:75 casos,73 PASS y2 rojos de limpieza; los68 casos del autor pasan intactos. Los siete propios aportan un linaje soportado, dos controles de close antes de super tras commit confirmado y dos ACK perdidos de admisión —todos verdes— y dos fallos compuestos rojos. Primer replay PostgreSQL:26 casos,24 PASS y2 rojos equivalentes; los16 casos del autor pasan. Los diez propios añaden ACK de admisión, cierre, ContextVar y dos modelos de Session ambiental con pool1. No se suman repeticiones como criterios distintos.

El modelo rojo es exacto: Session.commit de la operación falla antes de super; rollback de esa misma Session falla antes de super; close falla antes de super, manteniendo una referencia fuerte para impedir que GC esconda un checkout. En ambas fábricas y dialectos se devuelve503 opaco y se restaura ContextVar, pero pool.checkedout() es1 antes de la limpieza del harness. Esto reproduce ausencia de una garantía explícita de liberación/invalidation en _execute para ese modelo. No prueba un fallo real de psycopg2/SQLite, una condición activable remotamente, fuga entre tenants o bypass de autenticación. El control separado que hace fallar close antes de super tras un commit real confirmado pasa: SQLAlchemy ya devuelve la conexión durante commit y el DTO primitivo evita otra lectura. El modelo, versiones y SHA inmutable están en cleanup-fault-model.json. Después de observar cada rojo, el harness limpia sólo su Session retenida con rollback/close reales; no se oculta el primer resultado ni se cancela ninguna sesión ajena.

PostgreSQL usa dos UUID propias con recibo inicial open('xb') antes de CREATE, OID/owner y nacimiento del launcher registrados. Migración32 real, rol app restringido con super/bypassrls/createdb/createrole false, no propietario y pool de una conexión; el fixture verifica FORCE RLS. Los16 controles heredados cubren factor real, SQL abortado, NOWAIT, cambios de SV/activo tras admisión, incertidumbre de ACK, pool agotado y bearer ajeno. Los modelos propios conservan una Session A ya conectada: con el mismo pool ocupado la operación B falla503 sin retag de A; con pool restringido independiente, B puede consultar sus propios eventos mientras A conserva sus tres GUC y Session.info. Las lecturas de pool vacío vuelven a los tres GUC vacíos y cero eventos visibles sin actor. Al cierre hay0 sesiones, DROP ordinario y ausencia por conexión nueva para ambas UUID; sin FORCE, kills, cambios de roles/HBA o DB ajenas.

El contrato restante observado sigue limitado a metadata/withdraw propios: nueva contraseña por operación y factor vigente de un solo uso cuando existe, actor recargado0..MAX, parent ignorado sólo aquí; sin emisión de acceso/refresh/challenge/grants, perfil, fuente ni permiso de grant. El budget de actor se confirma antes de la operación; CAS, primaria incorrecta, SQL abortado y ACK perdido no lo borran. El ACK perdido de admisión no consume factor. La nueva consulta usa últimos eventos propios, elimina source_profile_id y no necesita leer fuentes/links ocultos. Google permanece503 sin asociación por email ni llamada de proveedor para esta finalidad. Las cabeceras exactas API/slash/SSR reservada son privadas también en errores, mientras vecinos conservan su política; este ensayo no monta ni acepta la página SSR.

Fotos antes/después:513 fuentes Python en baseline y526 en candidato,89 distribuciones por nombre/versión, hashes de ejecutable Python/base idénticos en cada fase y pipcheck0. El alcance de foto no incluye cada byte instalado ni todos los assets del repositorio. RAW, JUnit, SQLite y recibos originales se preservan bajo DACL protegido de usuario actual y SYSTEM; se verifica configuración inicial y coincidencia final, no monitorización continua. Se publican sólo proyecciones estructurales, huellas y atributos RAW; el scanner mantenido119 revisa todos los archivos públicos. Sin PG de terceros, navegador, VM, proveedor live, nuevas dependencias ni cambios Google33.

Recomendación técnica pendiente: un respaldo de invalidate sobre la Session recién creada y exclusivamente propia podría cerrar el borde si falla la limpieza, conservando503 y restauración del contexto. Debe probarse contra los canarios originales sin bajar el assert y sin disponer globalmente el pool ni retag de una Session ambiental. No se implementa en este peer ni se etiqueta como exploit confirmado.
'''
(OUT/'review.md').write_bytes(review.encode())
scanner=ast.parse(Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(n for n in scanner.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<maintained119>','exec'))
for path in OUT.rglob('*'):
    if path.is_file():scan(path.read_bytes(),path.relative_to(OUT).as_posix())
dump('scanner.json',{'maintained_scanner':'checkpoint119','function_ast_sha256':sha(ast.dump(fn).encode()),'public_files_scanned':sum(p.is_file() for p in OUT.rglob('*')),'result':'pass','private_originals_not_published':True})
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}
dump('manifest.json',manifest)
files=[p.relative_to(ROOT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*files],cwd=ROOT,check=True,capture_output=True)
for name in files:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
subprocess.run(['git','commit','-m','Record independent limited-retirement security controls and cleanup fault'],cwd=ROOT,check=True,capture_output=True)
print(json.dumps({'commit':git('rev-parse','HEAD').decode().strip(),'files':len(files),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'source_sha256':sha((OUT/'source.json').read_bytes()),'verdict':source['verdict']}))
