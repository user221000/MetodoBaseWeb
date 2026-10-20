from pathlib import Path,PurePosixPath
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-followup34-peer-private-20261019'
PREFIX='docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019';O=R/PREFIX
BASE='80b9a44adf4daae160673b4d86a58cb06f809071';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
save=lambda n,x:(O/n).write_bytes((json.dumps(x,indent=2)+'\n').encode());load=lambda n:json.loads((O/n).read_bytes())
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
assert load('author-sqlite-summary.json')['outcomes']=={'passed':75,'failure':0,'error':0,'skipped':0}
assert load('sql-errors-summary.json')['outcomes']=={'passed':8,'failure':4,'error':0,'skipped':0}
assert load('author-sqlite-before.json')==load('author-sqlite-after.json')
assert load('sql-errors-before.json')==load('sql-errors-after.json')
final=load('sql-errors-after.json')
for name,digest in final['source'].items():assert sha((R/name).read_bytes())==digest
packages={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()}
assert packages==final['packages'] and len(packages)==92
assert sha(Path(sys.executable).read_bytes())==final['python'] and sha(Path(sys._base_executable).read_bytes())==final['base_python']
canary=R/'tests/test_security_followup34_sql_errors_peer.py';assert sha(canary.read_bytes())=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert pip.returncode==0
(O/'pip-after.RAW.log').write_bytes(pip.stdout+pip.stderr)
observations=O/'sql-error-observations';observations.mkdir()
for path in sorted((P/'SQL-error-receipts').glob('*.json')):
    value=json.loads(path.read_bytes());assert value['no_partial_event_or_projection'] and value['opaque_private_error'] and value['no_false_ACK']
    (observations/path.name).write_bytes(path.read_bytes())
assert len(list(observations.glob('*.json')))==10
for folder in ['drivers','canaries','preimage','prepared']:(O/folder).mkdir()
for stem in ['run-sqlite','run-own-errors','static','seal-red']:
    path=T/('metodobase-sec-followup34-peer-'+stem+'-20261019.py');(O/'drivers'/(stem+'.py')).write_bytes(path.read_bytes())
(O/'drivers/final-acl.ps1').write_bytes((T/'metodobase-sec-followup34-peer-final-acl-20261019.ps1').read_bytes())
(O/'canaries/test_security_followup34_sql_errors_peer.py').write_bytes(canary.read_bytes())
(O/'preimage/followup_tasks.py').write_bytes((R/'web/services/followup_tasks.py').read_bytes())
prepared=T/'metodobase-sec-followup34-peer-postgres-prepared-20261019.py'
(O/'prepared/test_security_followup34_postgres_peer.prepared.py').write_bytes(prepared.read_bytes())
acl=json.loads((P/'acl-final.private.json').read_bytes());assert acl['protected'] and acl['parent_SDDL_unchanged']
save('private-ACL.STRUCTURAL.json',{**acl,'initial_SDDL_SHA256':sha((P/'acl-initial.private.txt').read_bytes())})
attributes=[]
for path in sorted(P.rglob('*')):
    if path.is_file():
        assert not path.is_symlink();h=hashlib.sha256()
        with path.open('rb')as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        st=path.stat();attributes.append({'private_relative_path':path.relative_to(P).as_posix(),'bytes':st.st_size,'SHA256':h.hexdigest(),
            'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'windows_file_attributes':getattr(st,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Original SQLite stdout/stderr/XML including4RED, synthetic fixtures, structural SQL observations, ACL and prior own-source preservation receipt. No historical RAW reconstructed; payloads stay private.','files':attributes})
review='''QA-18 RED independiente sobre Backend34 `80b9a44adf4daae160673b4d86a58cb06f809071`. No se acepta globalmente Backend34 ni PostgreSQL34. La fuente de producto y los 12 canarios quedan congelados antes de cualquier corrección o importación SSR.

Se reproducen cuatro fallos de clasificación HTTP: ambos factories devuelven 409 `followup_busy` ante un IntegrityError desconocido durante flush y ante SQLITE_ERROR=1 real causado por una tabla inexistente cuyo nombre constante contiene blocked. El contrato exige 503 `followup_unconfirmed`. El primero nace del fallback de mutate para cualquier IntegrityError no reconocido; el segundo del substring locked en classify_error para cualquier DBAPIError. Son fallos de clasificación/disponibilidad bajo inyección controlada; no se atribuyen bypass de autorización, explotación remota ni fuga de datos.

Los mismos 12 canarios dan 8 PASS y 4 RED, cero errores/skips. Se conservan controles positivos: la misma tabla faltante con otro nombre produce503; rollback incierto produce503; un bloqueo SQLite real produce409. Se verifican autenticación y MFA reales, opacidad y cabeceras privadas, ausencia de ACK y de Task/Event parciales y una sola operación tras una nueva petición explícita posterior al fallo. No se sustituyen identidad ni permisos. SHA de la canaria original: `c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce`.

El replay propio del conjunto del autor da 75 SQLite PASS, cero errores/skips; cinco variantes PostgreSQL no se seleccionan. Fuentes, wire,92 distribuciones con sus METADATA y ambos ejecutables Python permanecen iguales antes/después; pip check termina0. No se lee el perfil PG ni se abren SQL/servicios PostgreSQL. El wire técnico conserva SHA `33bfe88f33705cb33b70c2ef2b57951e9ee59cb7176466143e93d3822fd83f91`.

La revisión estática verifica byte a byte los26 targets22–33 respecto a COMMON33, la ausencia del target PostgreSQL34 y la inversa completa LF/AST del restore34: se preservan las67 aserciones originales33 con cuatro bloques de extensión explícitos. Eso no es una ejecución de restore34. Los siete B608 reportados corresponden a DDL de triggers invoker/RLS con tablas, operadores y SNAPSHOT literales; no hay entrada HTTP en esos fragmentos y no se añaden suppressions. Los conteos PG28FORCE/29funciones/15triggers son previstos y permanecen sin verificar en runtime.

Quedan dos hipótesis estáticas para PG: el hint de Task en mutate se obtiene antes de authority sin predicado por assignee y puede incorporar un responsable ajeno al conjunto de locks de un Nutri no asignado; el FOR SHARE del Cliente no usa NOWAIT en servicio ni trigger. Se entregan canarios preparados propios, no ejecutados, para un futuro handoff exclusivo después del autor34 y su target PG congelado. No se atribuyen los22 PG preparados del autor como peer. El PG55483 sigue reservado a QA.

La revisión del nuevo matcher SSR de cliente queda separada y todavía no se importa en este sello. Los estados de fuente y sus errores originales se conservan. RAW/XML y atributos permanecen bajo ACL privado; los fixtures pytest distinguen OWNER RIGHTS/SYSTEM/Administrators de los captures originales current-user/SYSTEM. Se publica sólo metadato estructural y código de prueba. Sin Chrome, VM, Redis, proveedor vivo ni dependencias nuevas. Esta rama reutiliza la WT anterior; el commit b792 y sus cinco fuentes previas se preservan por referencia Git y copia privada byteidéntica.
'''
(O/'review.md').write_bytes(review.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan')
digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath)
exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('source.json',{'reviewed_commit':BASE,'criterion':'QA-18','verdict':'RED4: unknown SQL failures incorrectly return409; expected503',
    'author_SQLite_replayed':75,'author_SQLite_PASS':75,'own_SQL_error_cases':12,'own_PASS':8,'own_RED':4,'errors':0,'skips':0,
    'original_canary_SHA256':sha(canary.read_bytes()),'product_changes':False,'PG_executed':False,'PG_profile_read':False,
    'PG_target34_present':False,'global_Backend34_acceptance':False,'source_92_metadata_bothPython_quiet':True,'pip_before_after_exit':0,
    'scanner119_AST_digest':digest})
save('public-safety-scan.json',{'scanner119_AST_digest':digest,'scanner119_unchanged':True,'additional_JWT_guard':True,'all_public_files_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for path in O.rglob('*'):
    if path.is_file():
        raw=path.read_bytes();ns['scan'](raw,path.relative_to(O).as_posix())
        assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',raw),path.name
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),
    'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'verdict':'QA-18 RED frozen','scanner119_JWT':'PASS'}))
