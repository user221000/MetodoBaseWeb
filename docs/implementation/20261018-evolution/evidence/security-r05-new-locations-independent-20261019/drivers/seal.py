from pathlib import Path,PurePosixPath
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
R=Path(r'F:/mb-security-r05-classifier-peer-20261019');A=Path(r'F:/mb-r05-review-classifier-20261019')
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r05-new-peer-private-20261019'
PREFIX='docs/implementation/20261018-evolution/evidence/security-r05-new-locations-independent-20261019';O=R/PREFIX
BASE='a704f0706827d9e02392902737ed96ef4ce8d764';CANDIDATE='8012dc7d5098ac9064cd87078bcec3ba88d86415'
sha=lambda b:hashlib.sha256(b).hexdigest();load=lambda n:json.loads((O/n).read_bytes())
save=lambda n,x:(O/n).write_bytes((json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==BASE
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=A).decode().strip()==CANDIDATE
summary=load('tests-summary.json');assert summary['cases']==113 and summary['exit']==0
assert summary['outcomes']=={'passed':113,'failure':0,'error':0,'skipped':0}
assert load('tests-before.json')==load('tests-after.json')
before=load('before.json');after=load('after-semantic.json');assert before==after
for name,digest in before['sources'].items():assert sha((R/name).read_bytes())==digest
assert sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions())==before['packages']
assert sha(Path(sys.executable).read_bytes())==before['python'] and sha(Path(sys._base_executable).read_bytes())==before['base_python']
assert len(before['packages'])==89 and before['installed_v1']=='813f66c2f414065200aff734bffe96ebce6673bd0f20b46f68821686b55c604e'
C=A/'docs/implementation/20261018-evolution/evidence/root-r05-new-locations-candidate-20261019'
for name,digest in before['candidate_files'].items():assert sha((C/name).read_bytes())==digest
binding=load('countercanary-input-binding.json')
for name,meta in binding['files'].items():
    assert sha((A/name).read_bytes())==meta['RAW_SHA256']
    assert sha((Path(binding['snapshot'])/name).read_bytes())==meta['scanner_SHA256']
assert sha((R/'.gitleaks.toml').read_bytes())==binding['configuration_digest']
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert pip.returncode==0
(O/'pip-after.RAW.log').write_bytes(pip.stdout+pip.stderr)

ledger=(O/'independent-ledger.json').read_bytes();assert len(json.loads(ledger))==14557
info=zipfile.ZipInfo('independent-ledger.json',(2026,10,19,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
with zipfile.ZipFile(O/'independent-ledger.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:archive.writestr(info,ledger)
with zipfile.ZipFile(O/'independent-ledger.zip') as archive:assert archive.read('independent-ledger.json')==ledger
save('ledger-binding.json',{'member':'independent-ledger.json','uncompressed_bytes':len(ledger),'member_SHA256':sha(ledger),
    'ZIP_SHA256':sha((O/'independent-ledger.zip').read_bytes()),'occurrences':14557,'unique_pins':14516,
    'exact_original_JSON_bytes_retained_in_ZIP':True,'plain_JSON_replaced_only_after_member_equality_check':True})
(O/'independent-ledger.json').unlink()
acl=json.loads((P/'acl-final.private.json').read_bytes());assert acl['protected'] and acl['parent_SDDL_unchanged']
save('private-ACL.STRUCTURAL.json',{**acl,'initial_SDDL_SHA256':sha((P/'acl-initial.private.txt').read_bytes())})
retained=[]
for path in sorted(P.rglob('*')):
    if path.is_file():
        assert not path.is_symlink();h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        stat=path.stat();retained.append({'private_relative_path':path.relative_to(P).as_posix(),'bytes':stat.st_size,
            'SHA256':h.hexdigest(),'mtime_ns':stat.st_mtime_ns,'ctime_ns':stat.st_ctime_ns,'windows_file_attributes':getattr(stat,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Original v2/v3 and pytest stdout/stderr/XML, downloaded public header, private UTF8 scanner snapshot, attempt1 source and tool-result receipt, ACL. Snapshot recoding is explicit, not execution RAW. Attempt1 tool text is not reconstructed process RAW.','files':retained})
drivers=O/'drivers';drivers.mkdir()
for stem in ['review','review-v2','review-v3','review-final-executed','test-run','seal']:
    path=T/('metodobase-sec-r05-new-peer-'+stem+'-20261019.py');(drivers/(stem+'.py')).write_bytes(path.read_bytes())
(drivers/'final-acl.ps1').write_bytes((T/'metodobase-sec-r05-new-peer-final-acl-20261019.ps1').read_bytes())
canaries=O/'canaries';canaries.mkdir()
test=T/'metodobase-sec-r05-new-peer-canaries-20261019.py'
(canaries/'test_r05_new_locations_peer.py').write_bytes(test.read_bytes())
save('replay-contract.json',{'reviewed_candidate':CANDIDATE,'installed_v1_peer_base':BASE,
    'semantic_driver':'drivers/review-v3.py','executed_full_source':'drivers/review-final-executed.py',
    'original_attempts':'drivers/review.py and review-v2.py; recorded failures retained privately, with exact inverse for final framing changes.',
    'semantic_replay':'Use a fresh private/evidence coordinate adapter; requires the sealed candidate ZIPs, exact155 input files, reachable433 Git objects/paths, retained public witnesses and the original digest producer source. No historical driver import/execution.',
    'countercanaries':'drivers/test-run.py and canaries/test_r05_new_locations_peer.py use only a private snapshot plus isolated in-memory candidate constants of the unchanged v1 parser. No installed registry replacement.',
    'ledger':'independent-ledger.zip contains original UTF8 JSON byte-identical to recomputed ledger. Verify ledger-binding.json and extract to a private destination if needed.',
    'private_configuration_preimages_reconstructed':False,'new_gitleaks_scans':0})
review='''Aceptación finita independiente del candidato R05 `8012dc7d5098ac9064cd87078bcec3ba88d86415`. Se aceptan como falsos positivos exclusivamente las 14.557 ocurrencias del informe fijado `f273556e…`, equivalentes a 14.516 pins únicos en 155 archivos. No se instala el candidato, no se modifica el registro v1, no se ejecuta un nuevo gitleaks y no se acepta R05 global. El árbol actual33 y sus fuentes posteriores requieren un escaneo completo propio.

Se recomputan desde los archivos exactos el SHA RAW, el frame UTF8 que recibe el scanner y cada línea física reteniendo CR, junto con ruta y regla. Se contrasta por multiconjunto cada ocurrencia con el informe y cada pin con el ZIP candidato anclado `74561c02…`. Las 8.746 filas originales sin digest físico se verifican desde el archivo exacto; los JSON de origen no se alteran. Match, Secret y Line no son autoridad; el fingerprint sólo identifica una ocurrencia para comprobar cobertura.

| Fase | Ocurrencias verificadas |
| --- | ---: |
| Preimagen pública actual | 5.234 |
| Blob histórico de producto | 3.918 |
| Artefacto público/miembro ZIP | 1.546 |
| Blob histórico de evidencia | 3.282 |
| Inventario de objetos Git | 499 |
| Material público de firma/header | 15 |
| Mapas runtime íntegros | 48 |
| Últimas ubicaciones | 15 |

Se verifican 156 preimágenes públicas actuales y 465 blobs necesarios mediante SHA1 del encabezado Git+bytes y SHA256. Son los objetos utilizados por los testigos; no se atribuye la búsqueda de 954 objetos del autor como ejecución propia. Se comprueban paths/OIDs contra metadatos de 433 commits actualmente alcanzables; los 499 inventarios además concuerdan con 56 árboles concretos. Los miembros de ZIP se leen sin extracción y con límites, identidad de archivo público/Git y SHA del miembro. Un miembro relocalizado sólo prueba una preimagen pública del checksum; no prueba identidad de la antigua ruta ni ejecución histórica. Los tres mapas se analizan como datos y se comprueban sus 1.009 pares completos. Las variantes LF→CRLF se etiquetan como derivaciones, sin atribuirles RAW de ejecución.

Las cinco huellas GPG coinciden con el paquete público retenido y el proof independiente d536; no se realiza importación de clave ni otra verificación de firma. Se confirma la referencia primaria de [Python para las claves de publicación](https://www.python.org/downloads/metadata/pgp/). Los diez checksums del header coinciden con una descarga propia de 3.050 bytes del [tag oficial CPython v3.12.13](https://raw.githubusercontent.com/python/cpython/v3.12.13/Include/internal/pycore_token.h), SHA256 `91c75ef718b8e8be2383fdcea502c1e63ebfa6d681afd45672e379ea7e5d3668`. Esto prueba una preimagen pública, sin reatestar el contenedor antiguo.

Las últimas 15 ocurrencias se prueban por separado: cuatro checksums de blobs VM retenidos que realmente contienen BOM UTF16, un checksum de clave pública, una cabecera AST con dos checksums literales de recibos públicos y nueve digests de configuración. Para estos nueve se fija el productor completo, su AST puro y su identidad en tres recibos; se compila sólo la función contra dependencias sintéticas y se comprueba la copia idéntica de los siete digests en ready/log/closure. Las preimágenes privadas originales no se reconstruyen ni se revelan. Los valores opcionales iguales se admiten: SHA256 no exige unicidad entre configuraciones. Quitar o alterar el productor o sus recibos impide aprobar la procedencia offline. El clasificador runtime de un pin ya revisado no exige recuperar otra vez el productor; ambos controles se declaran por separado.

113 controles propios PASS, sin errores ni skips: un replay real del parser/clasificador v1 cubre los 14.516 pins usando sólo constantes aisladas en memoria sobre el candidato privado; 105 controles negativos aplican siete cambios a cada una de las 15 ocurrencias finales (byte vecino, identidad RAW, ruta vecina, regla, rango multilínea, CR y línea alterada incluso con scanner digest forjado); siete controles cubren productor/recibos y digests opcionales iguales. Ninguno cambia el registro instalado ni los asserts anteriores. Los intentos de recomputación no se suman como casos nuevos.

Se preservan dos errores del harness. Primero, dos IDs del inventario histórico de 427 ya no estaban en refs actuales; se restringe la prueba a los 433 actualmente alcanzables y se verifica toda la cobertura sin esos dos. El primer fallo sólo dispone de recibo textual de tool y fuente exacta; no se reconstruye stdout/stderr RAW. Después, literal_eval de la tupla completa encontró una llamada Path; se corrige el lector para evaluar sólo sus dos campos literales, sin ejecutar esa llamada ni el driver histórico. El v2 conserva stdout/stderr RAW originales. La inversa de los cambios de framing es exacta y las aserciones semánticas negativas se mantienen.

Fuentes seleccionadas, archivos candidatos, 155 entradas RAW/scanner, snapshot privado, 89 distribuciones y ambos ejecutables Python quedan quietos; pip check inicial/final termina 0. El ZIP v1 conserva su SHA `813f66c2…`. Las limitaciones de los 16 checksums/3 preimágenes WIP ausentes del peer anterior quedan inmutables. El sello sólo agrega pruebas, metadatos y drivers propios; no toca producto, allowlists, registro, autores ni historia. RAW/XML y atributos permanecen privados bajo ACL comprobado. Scanner119 intacto y guard JWT revisan los artefactos publicados, incluido el ledger comprimido byteidéntico. No se usan SQL, Chrome, VM ni dependencias nuevas.
'''
(O/'review.md').write_bytes(review.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
scanner_digest=sha(ast.dump(scanner).encode());assert scanner_digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath)
exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('source.json',{'candidate_commit':CANDIDATE,'peer_base':BASE,'candidate_source_SHA256':before['candidate_files']['source.json'],
    'candidate_manifest_SHA256':before['candidate_files']['manifest.json'],'candidate_data_digest':binding['candidate_digest'],
    'verdict':'finite candidate locations accepted; no registry installation or global R05 acceptance',
    'occurrences':14557,'unique_pins':14516,'files':155,'all_semantic_evidence_verified':True,'tests_passed':113,
    'runtime_replayed_pins':14516,'negative_final_location_cases':105,'offline_provenance_cases':7,
    'private_configuration_preimages_reconstructed':False,'installed_v1_unchanged':True,'new_gitleaks_scans':0,
    'sources_89_bothPython_snapshot_quiet':True,'pip_before_after_exit':0,'scanner119_AST_digest':scanner_digest})
save('public-safety-scan.json',{'scanner119_AST_digest':scanner_digest,'unchanged_scanner119':True,
    'additional_JWT_guard_recursive':True,'all_public_files_and_compressed_ledger_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='manifest.json'})
def safety(raw,name):
    ns['scan'](raw,name)
    assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',raw),name
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for i in z.infolist():
                if not i.is_dir():safety(z.read(i),name+'/'+i.filename)
for path in O.rglob('*'):
    if path.is_file():safety(path.read_bytes(),path.relative_to(O).as_posix())
print(json.dumps({'files':sum(p.is_file() for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),
    'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'ledger_member_SHA256':sha(ledger),
    'verdict':'finite locations accepted, no installation/global R05 acceptance','public_safety':'PASS'}))
