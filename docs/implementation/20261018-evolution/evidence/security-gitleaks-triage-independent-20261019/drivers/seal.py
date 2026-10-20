"""Seal public structural evidence only; private captures stay private."""
from pathlib import Path,PurePosixPath
from collections import Counter
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp');PRIVATE=TEMP/'metodobase-sec-gitleaks-peer-private-20261019'
ROOT=Path(r'F:/mb-security-gitleaks-triage-peer-20261019')
PREFIX='docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019';OUT=ROOT/PREFIX
BASE='de216543a2eec05584168cdb888f627901b0e0b1'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
def save(name,obj):(OUT/name).write_bytes((json.dumps(obj,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('diff','--name-only')
assert json.loads((OUT/'final-disposition-summary.json').read_bytes())['total_verified_false_positive_locations']==31564
drivers=['review','columns','adjudicate','disposition','late-hashes','literal-proof','public-key','producer-proof','finalize-ledger','tests','tests-final','tests-prepare-final','seal']
directory=OUT/'drivers';directory.mkdir(exist_ok=True)
for stem in drivers:
    source=TEMP/('metodobase-sec-gitleaks-peer-'+stem+'-20261019.py');assert source.is_file()
    (directory/(stem+'.py')).write_bytes(source.read_bytes())
(directory/'verify-acl.ps1').write_bytes((TEMP/'metodobase-sec-gitleaks-peer-verify-acl-20261019.ps1').read_bytes())
(directory/'independent-checksum-verifier.py').write_bytes((ROOT/'tests/security_gitleaks_review.py').read_bytes())
(directory/'independent-adversarial-tests.py').write_bytes((ROOT/'tests/test_security_gitleaks_peer.py').read_bytes())
acl=json.loads((PRIVATE/'acl-final.private.json').read_bytes());acl_public={k:v for k,v in acl.items() if k!='sddl'}
acl_public['final_private_sddl_sha256']=sha(acl['sddl'].encode());acl_public['initial_private_sddl_capture_sha256']=sha((PRIVATE/'acl.private.raw.txt').read_bytes())
save('privacy-ACL.STRUCTURAL.json',acl_public)
raw=[]
for path in sorted(PRIVATE.rglob('*')):
    if not path.is_file():continue
    assert not path.is_symlink();s=path.stat();h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    raw.append({'relative_private_path':path.relative_to(PRIVATE).as_posix(),'bytes':s.st_size,'sha256':h.hexdigest(),'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'windows_file_attributes':getattr(s,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Hashes and filesystem attributes only. Private payloads, historical Git blob payloads, Match and Secret values are not published. Pytest synthetic fixtures retain Windows owner-rights/SYSTEM/Administrators ACL; actual captures inherit the private current-user/SYSTEM ACL.','files':raw})
final_photo=json.loads((OUT/'tests-final/tests-after.json').read_bytes())
photo={'sources':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for stem in ['web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
assert json.loads(json.dumps(photo))==final_photo and len(photo['packages'])==89
save('final-python-packages-source.json',photo)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert pip.returncode==0
(OUT/'pip-final.raw.log').write_bytes(pip.stdout+pip.stderr)
save('own-preparation-errata.json',{'initial_review_resource_stop':'Own first driver retained whole scanned tree bytes; stopped only the identified owned process and retried bounded caching. Genuine completed initial source photo retained; no historical payload was written.','initial_retry':'Retry encountered already-written metadata; original private traceback retained, then initial outputs moved without byte changes to attempt-initial.','first_test_run':{'passed':62,'errors':20,'failures':0,'cause':'Own fixture assumed current-checksum phase contained a UTF16 example. Replaced only own fixture with explicitly DERIVED synthetic UTF16 boundary plus separate real UTF8 positive. Original maintained assertions unchanged. Original setup RAW/XML retained; old own test source preimage was not copied, only its contemporaneous hash remains.'},'final_test_run':{'passed':83,'errors':0,'failures':0},'physical_reader':'Preliminary adjudication used universal newline reading for one console line; final proof reads original bytes split on LF retaining CR. Final ledger independently recomputes exact physical-line hashes; older 31282 receipts explicitly removed trailing CR.','quiet_check_first_attempt':'Exact full file-set assertion exposed four previously absent tracked paths now present; final check preserves added paths outside fixed report, separately verifies all original10378 hashes unchanged.','ACL_check':'Initial strict recursive check rejected the pytest Windows OWNER RIGHTS/SYSTEM/Administrators fixture DACL. Final check distinguishes synthetic fixture subtrees from actual private RAW captures and changes no ACL. PowerShell execution policy was bypassed for the verification process only, with no machine/user policy changes.'})
registry=json.loads((OUT/'finite-reviewed-location-ledger.json').read_bytes())
identity=lambda r:(r['file'],r['file_sha256'],r['start_line'],r['end_line'],r['rule_id'],r['physical_line_sha256'])
counts=Counter(identity(r) for r in registry['locations'])
save('ledger-structural-summary.json',{'occurrences':len(registry['locations']),'unique_location_rule_file_line_pins':len(counts),'duplicate_occurrences':sum(n-1 for n in counts.values()),'all_start_equals_end':all(r['start_line']==r['end_line'] for r in registry['locations']),'only_reported_RAW_file_hash_variants':True,'exact_decoded_physical_CR_preserved':True,'global_R05_acceptance':False})
zip_path=OUT/'finite-reviewed-location-ledger.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    entry=zipfile.ZipInfo('finite-reviewed-location-ledger.json',date_time=(2026,10,19,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
    archive.writestr(entry,(OUT/'finite-reviewed-location-ledger.json').read_bytes())
save('ledger-artifact.json',{'json_sha256':sha((OUT/'finite-reviewed-location-ledger.json').read_bytes()),'zip_sha256':sha(zip_path.read_bytes()),'zip_single_member':'finite-reviewed-location-ledger.json','member_bytes':(OUT/'finite-reviewed-location-ledger.json').stat().st_size,'zip_bytes':zip_path.stat().st_size,'meaning':'Review ledger only; no implementation of scanner classification in this peer.'})
review='''Revisión independiente R05: informe fijo de gitleaks

Aceptación focal: las 31.564 ocurrencias restantes del informe SHA256 `0e5d0cfc77c1626912beca8c9b39e91fe56464e9e9cc71502947e44288b09352` se clasificaron por ubicación y prueba. No constituye aceptación global R05, modificación del scanner, implementación de registro ni ampliación de allowlist. Las dos clasificaciones previas de fragmentos se mantienen separadas.

La fuente de referencia es `de216543a2eec05584168cdb888f627901b0e0b1`. Se comprobó independientemente la partición 5.669 + 15.045 + 1.835 + 8.733 = 31.282: archivo congelado actual, pertenencia OID/ruta a commits fijados, bytes de blobs Git y miembros concretos de artefactos retenidos. Los 23.546 checksums derivados LF→CRLF se identifican como DERIVED; no son ejecución RAW reconstruida. Sólo se leyeron en memoria los 92 blobs históricos necesarios, sin publicarlos.

Las 282 ubicaciones adicionales incluyen 204 checksums ya contrastados, 32 de archivo público exacto, 15 identificadores Git públicos, ocho huellas OpenPGP, dos checksums de zona horaria Apia retenida, dos localizadores sintéticos de objeto SQLite temporal, un nombre de captura local, un identificador público X.509 de consola y un checksum de fuente Git observado con referencias posteriores. Las otras 16 son metadatos SHA256 de un productor puro verificado, con recibos fijados y sin passthrough de configuración. Faltan las preimágenes WIP de tres archivos: auth.py y dos tests MFA31. Esta prueba clasifica esos valores finitos como checksums; no recomputa sus preimágenes, reproduce ejecuciones históricas ni cierra su trazabilidad QA. Véase `original-source-unavailable.STRUCTURAL.json`.

La huella OpenPGP se calculó de los paquetes públicos retenidos y del enlace del responsable 3.12/3.13 publicado por [Python](https://www.python.org/downloads/metadata/pgp/), que lleva a su [clave pública](https://github.com/Yhg1s.gpg). Esto acredita identidad de clave pública; no añade una validación de firma. Para la línea X.509 se verificaron el texto físico fijado y la semántica del [cargador Linux 6.1](https://github.com/torvalds/linux/blob/v6.1/crypto/asymmetric_keys/x509_loader.c) y de la [descripción del certificado](https://github.com/torvalds/linux/blob/v6.1/crypto/asymmetric_keys/x509_public_key.c): imprime identificador/serial público. No se arrancó VM ni se validó criptográficamente ese certificado.

El replay focal usa gitleaks 8.30.1 fijado, configuración idéntica, `--redact=100` y snapshot privado de los archivos con las 282 ubicaciones. Conservó salida 1 y 993 hallazgos totales en esa selección; las 282 ocurrencias fijadas se reprodujeron exactamente. No es un escaneo del árbol completo. La corrección del conteo de entradas/directorios está en `focal-scope-correction.json`.

Pruebas finales: 83 PASS. Incluyen rechazo de falsificaciones de ruta, línea, hash, metadata, encoding, payload, OID/pertenencia y fragmentos, junto con los controles mantenidos de seguridad del scanner y sus dos pins de fragmentos. La primera ejecución se conserva: 62 PASS y 20 errores de preparación propios, corregidos sólo en el fixture independiente. Fuente Python, 89 paquetes y ejecutables quedaron iguales antes/después; pip check devuelve 0. No se instalaron dependencias ni se alteró código de producto o pruebas mantenidas.

Los 10.378 archivos originalmente escaneados conservan sus hashes iniciales. Cuatro rutas antes ausentes ahora existen y quedan fuera de este informe; se enumeran en `source-set-delta.json`. No se afirma quietud del conjunto completo de archivos ni aceptación de esos agregados. Las fotos iniciales completas y los intentos propios se conservan con su alcance explícito.

`finite-reviewed-location-ledger.json` y su ZIP idéntico contienen sólo las ubicaciones revisadas: archivo canónico, SHA RAW, línea inicial=final, regla, SHA de línea física exacta y tipo de prueba. Los hashes físicos se recomputaron reteniendo CR y excluyendo sólo LF; el mapa de encoding registra la transformación explícita del informe. Los recibos antiguos de 31.282 checksums quitaban CR en su campo de línea, por lo que ese campo no debe sustituir el nuevo. No se aprueban variantes alternativas LF/CRLF/BOM implícitas. Un registro futuro debe verificar estrictamente entrada, configuración/binario y todos estos pins, rechazar cambios y preservar la salida RAW original.

RAW, errores y XML se retienen en almacenamiento privado; el manifiesto público sólo contiene hashes/atributos y proyecciones estructurales. El ACL de capturas privadas permite usuario actual/SYSTEM. Los subárboles sintéticos de pytest tienen el ACL Windows OWNER RIGHTS/SYSTEM/Administrators y se declaran por separado. No se publican Match/Secret, credenciales ni payloads históricos de Git. No se usó PostgreSQL, Chrome, VM ni servicios de producto externos.
'''
(OUT/'review.md').write_bytes(review.encode())
scanner_source=TEMP/'metodobase-checkpoint119-prepare.py';tree=ast.parse(scanner_source.read_bytes());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
ns=dict(ast=ast,hashlib=hashlib,io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath)
exec(compile(ast.Module(body=[node],type_ignores=[]),str(scanner_source),'exec'),ns)
scan=ns['scan'];scan_hash=sha(ast.dump(node).encode());assert scan_hash=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
for path in OUT.rglob('*'):
    if path.is_file():scan(path.read_bytes(),path.relative_to(OUT).as_posix())
save('source.json',{'reviewed_source_commit':BASE,'worktree':str(ROOT),'input_source_worktree':r'F:/mb-progress-retirement-ui-20261019','product_changes':False,'scanner_changes':False,'packages':89,'python_packages_sources_quiet':True,'pip_exit':0,'scanner119_function_AST_sha256':scan_hash,'fixed_report_sha256':registry['input_report_sha256'],'finite_ledger_sha256':sha((OUT/'finite-reviewed-location-ledger.json').read_bytes()),'finite_ledger_zip_sha256':sha(zip_path.read_bytes()),'proofs_scope':'Focal fixed-report false-positive review; not global R05 acceptance.'})
save('public-safety-scan.json',{'scanner':'unchanged checkpoint119 function','function_ast_sha256':scan_hash,'all_public_files_pass':True,'archives_recursively_checked':True,'no_general_allowlist':True})
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}
save('manifest.json',manifest)
for path in OUT.rglob('*'):
    if path.is_file():scan(path.read_bytes(),path.relative_to(OUT).as_posix())
print(json.dumps({'proof_files':len(manifest)+1,'source_sha256':sha((OUT/'source.json').read_bytes()),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'ledger':json.loads((OUT/'ledger-artifact.json').read_bytes()),'ledger_locations':len(registry['locations']),'scanner119':'PASS'}))
