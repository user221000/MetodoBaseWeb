from pathlib import Path,PurePosixPath
from collections import Counter
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
ROOT=Path(r'F:/mb-security-r05-classifier-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r05-classifier-peer-private-20261019'
PREFIX='docs/implementation/20261018-evolution/evidence/security-r05-registry-independent-20261019';O=ROOT/PREFIX
BASE='f7b12a71a89de2e35b0035ccef147a673ad50d29';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def streamsha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
summary=json.loads((O/'tests-final-summary.json').read_bytes());assert summary['passed']==summary['cases']==171 and summary['error']==summary['failure']==summary['skipped']==0
cases=json.loads((O/'tests-final.STRUCTURAL.json').read_bytes());counts=Counter(r['case'].split('::')[0] for r in cases)
save('case-groups.json',{'final_unique_cases':171,'by_module':counts,'same171_on_predecessor_are_replay_not_additional_cases':True,'old83_assertions_or_fixtures_changed':False,'new_independent_cases':39})
final=json.loads((O/'tests-final-after.json').read_bytes())
now={'commit':BASE,'sources':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for stem in ['scripts','web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes()),'data_zip':sha((ROOT/'scripts/data/reviewed_scan_locations_v1.zip').read_bytes())}
assert json.loads(json.dumps(now))==final and len(now['packages'])==89
save('final-source-packages-python.json',now)
binding=json.loads((O/'dataset-ledger-binding.json').read_bytes());source=Path(r'F:/mb-progress-retirement-ui-20261019')
for name,digest in binding['source_hashes'].items():assert streamsha(source/name)==digest
with zipfile.ZipFile(ROOT/'scripts/data/reviewed_scan_locations_v1.zip') as arc:data=json.loads(arc.read('reviewed-locations.json'))
for record in data['files']:assert streamsha(P/'baseline-snapshot'/record['path'])==record['scanner_digest']
save('final-fixture-source-quiet.json',{'frozen_UI_RAW_inputs_checked':len(binding['source_hashes']),'registry_record_snapshot_files_checked':len(data['files']),'all_RAW_and_snapshot_bytes_unchanged':True,'scope':'Only534 reviewed input files and exact config; no all-tree source assertion.'})
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert pip.returncode==0
(O/'pip-final-seal.raw.log').write_bytes(pip.stdout+pip.stderr)
acl=json.loads((P/'acl-final.private.json').read_bytes());assert acl['sddl']==(P/'acl-initial.private.txt').read_text(encoding='utf8')
save('private-ACL.STRUCTURAL.json',{**{k:v for k,v in acl.items() if k!='sddl'},'initial_and_final_parent_SDDL_exact':True,'private_parent_SDDL_sha256':sha(acl['sddl'].encode())})
attributes=[]
for path in sorted(P.rglob('*')):
    if path.is_file():
        assert not path.is_symlink();s=path.stat();attributes.append({'private_relative_path':path.relative_to(P).as_posix(),'bytes':s.st_size,'sha256':streamsha(path),'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'windows_file_attributes':getattr(s,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Private original redacted scanner reports/stdout/stderr, JUnit, sanitized reports, owned synthetic repository objects and fixtures. Payloads remain private; no historical production Git payloads copied.','files':attributes})
drivers=O/'drivers';drivers.mkdir()
for stem in ['prepare','tests','final-transition','run-final','real-probes','seal']:
    path=T/('metodobase-sec-r05-classifier-peer-'+stem+'-20261019.py');(drivers/(stem+'.py')).write_bytes(path.read_bytes())
(drivers/'verify-acl.ps1').write_bytes((T/'metodobase-sec-r05-classifier-peer-verify-acl-20261019.ps1').read_bytes())
for name in ['test_security_r05_registry_peer.py','test_security_gitleaks_peer.py','security_gitleaks_review.py']:(drivers/name).write_bytes((ROOT/'tests'/name).read_bytes())
probes=json.loads((O/'actual-gitleaks-probes.STRUCTURAL.json').read_bytes());assert len(probes)==12 and sum(r['actual_scan'] for r in probes)==10
review='''Peer independiente R05: clasificador de ubicaciones revisadas v1

Aceptación focal del producto congelado `f7b12a71a89de2e35b0035ccef147a673ad50d29`. No se encontraron defectos bloqueantes en el delta. La revisión no cierra R05 global: el escaneo actual informado por autor conserva 14.557 hallazgos bloqueantes en rutas nuevas. Este peer no los clasifica ni cambia el registro para incluirlos.

La revisión estática cubre el cargador, su integración después de los dos fragment pins mantenidos, el ZIP anclado y las pruebas de autor. El dataset SHA256 `813f66c2f414065200aff734bffe96ebce6673bd0f20b46f68821686b55c604e` contiene 534 archivos y 31.394 pins únicos. Se contrastó independientemente cada pin con el ledger SHA256 `2b42fdd68d828f9a7d0971326dcb76f650cd83028464b897e546dec2508a3233`, incluyendo SHA RAW, snapshot UTF8, línea física reteniendo CR, ruta y regla. Se reejecutó la clasificación real de los 31.394 controles válidos. Esto es un replay de ubicaciones; no es otro escaneo fresco del informe antiguo.

El cargador fija dataset, versión y configuración; rechaza esquemas, tipos, claves duplicadas y rutas inválidos; limita archivo comprimido, tamaño descomprimido, archivos, reglas y pins. Una ausencia del dataset desactiva las clasificaciones. Datos presentes corruptos o configuración alterada abortan con mensaje saneado. La clasificación exige identidad RAW y snapshot, línea inicial=final y regla exactas; no usa Match, Secret, Line ni Fingerprint como prueba. La caché es por instancia de escaneo y el control independiente comprueba que no se reutiliza entre escaneos.

171 pruebas únicas PASS sobre el commit final: 61 mantenidas del scanner y fragmentos, 22 del peer previo copiadas byteidénticas, 49 del autor y 39 nuevas independientes. Los 39 casos cubren tipos y campos adicionales, claves duplicadas en cada nivel, compresión no permitida, límites reales de 100.000/100.001 pins y 2.000/2.001 archivos, configuración/fuentes ausentes, snapshot distinto, campos no confiables y la integración de salidas con hallazgos vecinos. Los mismos 171 se ejecutaron antes sobre `17c9`; se conservan como replay y no se suman. El paso al commit final sólo eliminó un LF terminal en dos archivos: AST, runner y ZIP permanecen idénticos.

Se añadieron doce canarios independientes con el binario gitleaks 8.30.1 SHA256 `17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c`: diez escaneos reales en repositorios sintéticos privados y dos rechazos de dataset/configuración previos al escaneo. El archivo revisado exacto se clasifica. Añadir una credencial sintética, copiar a una ruta vecina, cambiar CRLF o introducir BOM UTF8/UTF16/UTF32 mantiene hallazgos bloqueantes. Una credencial en evidencia vecina también bloquea aunque las coincidencias anteriores se clasifiquen. Retirar el dataset bloquea las coincidencias. Cambiar la fuente propia después del escaneo real fuerza salida 2 aunque las coincidencias antiguas estén clasificadas. Se conserva exit RAW 1, conteos, salida efectiva y RAW redacted=100; nunca se publican los valores sintéticos ni Match/Secret.

Fuente Python, 89 distribuciones y ambos ejecutables Python permanecieron idénticos antes/después; pip check devuelve 0. Las 534 fuentes RAW revisadas, la configuración y los snapshots usados en el replay permanecieron iguales al cierre. Las tres preimágenes WIP históricas ausentes no se usan ni se reconstruyen. Sólo se copian los archivos públicos de metadatos que las mencionan, conforme al alcance del ledger.

No se modificó código de producto, pruebas mantenidas, dataset, allowlists ni fuentes del autor. El sello agrega sólo evidencia independiente. RAW/XML y sus errores/atributos se retienen bajo ACL privado; los fixtures sintéticos pytest declaran por separado el ACL Windows OWNER RIGHTS/SYSTEM/Administrators. No se usaron PostgreSQL, VM, Chrome, dependencias nuevas ni servicios de producto externos.
'''
(O/'review.md').write_bytes(review.encode())
scanner=T/'metodobase-checkpoint119-prepare.py';node=next(n for n in ast.parse(scanner.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
scan_hash=sha(ast.dump(node).encode());assert scan_hash=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[node],type_ignores=[]),'unchanged-checkpoint119','exec'),ns)
save('source.json',{'reviewed_commit':BASE,'initial_reviewed_commit':'17c9b836776d8ebe51b619ab2b552fafab51f4de','worktree':str(ROOT),'dataset_zip_sha256':now['data_zip'],'ledger_sha256':binding['ledger_sha256'],'unique_pins':31394,'product_changes':False,'global_R05_acceptance':False,'cases_unique_final':171,'independent_new_cases':39,'actual_gitleaks_scans':10,'registry_pre_scan_rejection_canaries':2,'Python_packages_sources_exact':True,'packages':89,'pip_final_exit':0,'scanner119_function_AST_sha256':scan_hash})
save('public-safety-scan.json',{'function_ast_sha256':scan_hash,'unchanged_scanner119':True,'all_public_files_pass':True,'no_general_allowlist':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='manifest.json'})
for path in O.rglob('*'):
    if path.is_file():ns['scan'](path.read_bytes(),path.relative_to(O).as_posix())
print(json.dumps({'files':sum(p.is_file() for p in O.rglob('*')),'source_sha256':sha((O/'source.json').read_bytes()),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'scanner119':'PASS','verdict':'focal_acceptance_no_global_R05'}))
