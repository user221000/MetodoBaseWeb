from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
ROOT=Path(r'F:/mb-security-retirement-cleanup-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-retirement-owned-cleanup-independent-20261019'
OLD=Path(r'F:/mb-security-retirement-peer-20261019/docs/implementation/20261018-evolution/evidence/security-progress-retirement-independent-20261019')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-retirement-cleanup-peer-private-20261019')
HEAD='2273616eb218adfdd30680e111da50a4599a8c53'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
def dump(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert not (OUT/'manifest.json').exists()
phases={name:json.loads((OUT/name/'summary.json').read_bytes()) for name in ['sqlite-delta','postgres-delta']}
assert phases['sqlite-delta']['outcomes']=={'passed':79,'failure':0,'error':0,'skipped':0}
assert phases['postgres-delta']['outcomes']=={'passed':30,'failure':0,'error':0,'skipped':0}
comparisons={}
for current,previous,original_count in [('sqlite-delta','sqlite-freeze',75),('postgres-delta','postgres-freeze',26)]:
    summary=phases[current];assert summary['sources_packages_python_exact'] and summary['packages']==89
    assert summary['pip_before']==summary['pip_after']==summary['exit']==0
    assert json.loads((OUT/current/'before.json').read_bytes())==json.loads((OUT/current/'after.json').read_bytes())
    before={c['case']:c['outcome'] for c in json.loads((OLD/previous/'cases.STRUCTURAL.json').read_bytes())}
    after={c['case']:c['outcome'] for c in json.loads((OUT/current/'cases.STRUCTURAL.json').read_bytes())}
    assert len(before)==original_count and set(before)<=set(after)
    assert all(after[name]=='passed' for name in before)
    extra=set(after)-set(before);assert len(extra)==4 and all('invalidation_failure_restores_scope' in name for name in extra)
    comparisons[current]={'original_case_ids_exact':original_count,'original_reds_now_green':[name for name,outcome in before.items() if outcome=='failure'],'additional_criteria':4,'all_original_assertions_unchanged':True,'maintained_duplicate_not_collected':not any('test_progress_retirement_cleanup' in name for name in after)}
    assert comparisons[current]['maintained_duplicate_not_collected']
    observations=json.loads((OUT/current/'invalidation-observations.json').read_bytes());assert len(observations)==4
    for item in observations.values():
        assert item['response']==503 and item['context_restored'] and item['only_new_owned_session_invalidated'] and not item['engine_dispose_called']
        assert item['checkedout_observed_before_harness_cleanup']==(1 if item['invalidation_error_stage']=='before_real_release' else 0)
dump('same-canary-comparison.json',comparisons)
leases={p.name:json.loads(p.read_bytes()) for p in sorted((PRIVATE/'leases').glob('*.json'))};assert len(leases)==3
for state in leases.values():
    assert state['state']=='closed_absent' and state['sessions_before_drop']==0
    assert state['initial_creation']=='exclusive_xb_before_CREATE' and state['absence_verified']=='fresh_control_connection'
    assert state['launcher_birth_filetime']==state['launcher_birth_after_CREATE']
dump('resource-closure.json',leases)
command="$reviewAcl = Get-Acl -LiteralPath '"+str(PRIVATE)+"'; [pscustomobject]@{sddl=$reviewAcl.Sddl; protected=$reviewAcl.AreAccessRulesProtected; rules=$reviewAcl.Access.Count} | ConvertTo-Json -Compress"
acl=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',command]))
initial=(PRIVATE/'acl.private.raw.txt').read_text(encoding='utf-8-sig').strip()
assert acl['sddl']==initial and acl['protected'] is True and acl['rules']==2
dump('raw-acl.json',{'initial_setup_before_testing':'protected current user and SYSTEM only, two explicit rules','final_matches_initial_sddl':True,'protected':True,'explicit_rules':2,'sddl_sha256':sha(initial.encode()),'scope':'Initial setup and final recheck, not continuous ACL monitoring.'})
rawattrs={}
for path in sorted(PRIVATE.rglob('*')):
    if path.is_file():
        stat=path.stat();rawattrs[path.relative_to(PRIVATE).as_posix()]={'bytes':stat.st_size,'sha256':sha(path.read_bytes()),'mtime_ns':stat.st_mtime_ns,'creation_ns':getattr(stat,'st_birthtime_ns',stat.st_ctime_ns),'windows_file_attributes':getattr(stat,'st_file_attributes',None)}
dump('private-raw-attributes.json',rawattrs)
assert sha((OUT/'independent-faults.py').read_bytes())=='1002b027643932e0579eb5cf46b264ec46f129aea9f0f4346be0b579f7bd757a'
assert (OUT/'independent-faults.py').read_bytes()==(ROOT/'tests/test_progress_retirement_cleanup.py').read_bytes()==(ROOT/'tests/test_security_retirement_peer.py').read_bytes()
for public,live in [('independent-lineage.py','test_security_retirement_lineage.py'),('independent-postgres.py','integration_security_retirement_peer.py'),('independent-owned.py','security_retirement_owned.py'),('test_security_retirement_invalidation.py','test_security_retirement_invalidation.py'),('integration_security_retirement_invalidation.py','integration_security_retirement_invalidation.py')]:
    assert (OUT/public).read_bytes()==(ROOT/'tests'/live).read_bytes();ast.parse((OUT/public).read_bytes())
(OUT/'prepare-driver.py').write_bytes(Path(__file__).with_name('metodobase-sec-retirement-cleanup-peer-prepare-20261019.py').read_bytes())
(OUT/'seal-driver.py').write_bytes(Path(__file__).read_bytes())
import inspect,textwrap,sqlalchemy,psycopg2._psycopg,_sqlite3
from sqlalchemy.orm import Session
dump('driver-final-only.json',{'scope':'Final byte hashes only; version metadata occurs in each before/after photo, not a binary temporal-integrity claim.','SQLAlchemy':{'version':sqlalchemy.__version__,'module_sha256':sha(Path(sqlalchemy.__file__).read_bytes()),'session_implementation_sha256':sha(Path(inspect.getfile(Session)).read_bytes()),'invalidate_implementation_ast_sha256':sha(ast.dump(ast.parse(textwrap.dedent(inspect.getsource(Session.invalidate)))).encode())},'psycopg2_extension_sha256':sha(Path(psycopg2._psycopg.__file__).read_bytes()),'sqlite3_extension_sha256':sha(Path(_sqlite3.__file__).read_bytes())})
source={'source_head':HEAD,'parent':'219f89a5ee0196061fea5b67e36ae07daf7f4316','finding':'SEC18 resource robustness, no authorization/data/exploit classification',
    'verdict':'PASS_FOCAL_SEC18_OWNED_INVALIDATION','phases':phases,'same_original_sqlite_cases':75,'same_original_pg_cases':26,'additional_invalidation_failure_cases_per_dialect':4,
    'original_fault_canary_RAW_sha256':'1002b027643932e0579eb5cf46b264ec46f129aea9f0f4346be0b579f7bd757a',
    'previous_evidence_commit':'6147f9300989f4115cf8d270025a3805926d32b1','previous_manifest_sha256':'fe37709f7e1a81aff1d89e84505050fcd9b023401a0d86e17d6fc14c7d0d8b7a',
    'owned_pg_databases_closed':3,'no_product_or_original_test_edits':True,
    'confirmed_limit':'If Session.invalidate itself fails before release under the compound injected model, one checkout remains until the harness cleans its own Session. The API is opaque503 and ContextVar restored; no zero-checkout guarantee is claimed for that extra failure.',
    'scope':'Only the cleanup delta and unchanged limited-retirement controls; actual SQLite32 and restricted own PostgreSQL32 pool1. No general R25/R31 acceptance, deployed exploit, real driver-failure claim, browser/UI acceptance, Google33, new DDL or provider live.'}
dump('source.json',source)
review='''Revisión independiente focal SEC18 — PASS_FOCAL_SEC18_OWNED_INVALIDATION

Fuente2273616eb218adfdd30680e111da50a4599a8c53, padre219f89a5ee0196061fea5b67e36ae07daf7f4316. Se autentican source7df1d371ee033eb988d8a8e35cd9ef7204e20438995a55952a841c21ac3e3f62, manifest44df142f8dd1524aeb4d4b4db96841d2242737526684c732e960a3feeebabb37 y sus diez archivos listados, y la inversa completa de la ruta al padre. Checkout core.autocrlf=false: producto y test mantenido coinciden con Git LF. Los dos pip RAW CRLF del autor permanecen exactos; se conserva su recibo de errata de preparación sin normalizar esos bytes. No se modificó producto ni fuente/assert/nombre de canarios anteriores.

El delta conserva SessionLocal nueva dentro del contexto vacío y limita el respaldo a db.invalidate() de esa Session cuando db.close() falla. No dispone el engine/pool global ni retaguea una Session existente. Si invalidate lanza, registra sólo la clase, conserva el fallo de cierre y la respuesta503 opaca. El finally exterior restaura ContextVar incluso ante errores de creación, operación y limpieza. El DTO primitivo no adquiere otra conexión después del commit. Esta revisión trata robustez de recursos bajo inyección de fallos, no autorización, datos o explotación remota.

Se reprodujeron los mismos75 casos SQLite y26 PostgreSQL del peer anterior: todos pasan, conservando exactamente IDs de casos y fuente RAW del canario1002b027643932e0579eb5cf46b264ec46f129aea9f0f4346be0b579f7bd757a. El módulo mantenido idéntico no se selecciona dos veces. Los dos rojos originales por dialecto —commit de operación, rollback y close fallando antes de super, con Session retenida para impedir que GC esconda el checkout— pasan ahora el assert original pool.checkedout()==0. Continúan503 opaco, ContextVar restaurado y ninguna publicación de parámetros. Los controles de close que falla tras commit confirmado y ACK de admisión perdido también siguen verdes. El linaje real de invitación → aceptación → login → grant previo permite metadata/withdraw200 con parent OFF mientras auth general sigue401.

Se añadieron cuatro casos por dialecto para invalidate que también lanza, antes o después de liberar de verdad, en ambas fábricas. Totales de ejecución:79 SQLite PASS y30 PostgreSQL PASS, cero fallos/errores/skips. Cada nuevo caso comprueba una única llamada sobre la misma Session recién creada, cero engine.dispose, error503, ContextVar restaurado y logs sin payload de excepción. Si primero se ejecuta Session.invalidate real y después se lanza, el checkout observado es0. Si invalidate lanza antes de liberar, el checkout observado es1: se conserva como limitación explícita, no se simula que el recurso quedó libre. Tras esa observación, sólo el harness limpia la Session propia retenida mediante rollback/close reales y confirma pool0. No hay garantía de liberar una conexión cuando todas las primitivas de limpieza inyectadas permanecen indisponibles; no se transforma ese modelo extra en un resultado verde de liberación que no ocurrió.

PostgreSQL mantiene pool1, rol app con cuatro flags peligrosos false y no propietario, migración32 real y FORCE RLS según fixture. Los controles originales preservan Session A/GUC con mismo pool ocupado o un pool restringido separado mientras B aporta primaria fresca; el nuevo fallback no altera esos resultados. Las tres UUID propias tienen lease inicial exclusivo open('xb') antes de CREATE, OID/owner/nacimiento registrados,0 sesiones antes de DROP ordinario y ausencia verificada por conexión nueva. No hay FORCE, kills, cambios de roles/HBA o DB ajenas. Modelar un Session.commit/rollback/close/invalidate que lanza no afirma que psycopg2 o SQLite reales hayan sufrido esos fallos.

Fotos Python bajo web/api/core/config/tests,89 distribuciones por nombre/versión, SHA de intérprete/base y pipcheck0 permanecen exactos en cada fase; se publican conteos reales en summary y no se afirma hash de cada byte instalado ni todos los assets del repositorio. RAW/JUnit/SQLite/leases permanecen en DACL protegido de usuario actual y SYSTEM, con configuración inicial y comprobación final iguales; se conservan atributos y huellas originales. El scanner público mantenido119 pasa. No se ejecutó navegador, VM, proveedor live, instalación, Google33 ni una nueva DDL. La aceptación es sólo del delta SEC18 y controles ejecutados, no cierre global de R25/R31 ni aceptación de la página/UI.
'''
(OUT/'review.md').write_bytes(review.encode())
scanner=ast.parse(Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(n for n in scanner.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<maintained119>','exec'))
for path in OUT.rglob('*'):
    if path.is_file():scan(path.read_bytes(),path.relative_to(OUT).as_posix())
dump('scanner.json',{'maintained_scanner':'checkpoint119','function_ast_sha256':sha(ast.dump(fn).encode()),'public_files_scanned':sum(p.is_file() for p in OUT.rglob('*')),'result':'pass','private_originals_not_published':True})
dump('manifest.json',{p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
files=[p.relative_to(ROOT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*files],cwd=ROOT,check=True,capture_output=True)
for name in files:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
subprocess.run(['git','commit','-m','Record independent SEC18 owned-session invalidation replay'],cwd=ROOT,check=True,capture_output=True)
print(json.dumps({'commit':git('rev-parse','HEAD').decode().strip(),'files':len(files),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'source_sha256':sha((OUT/'source.json').read_bytes()),'verdict':source['verdict']}))
