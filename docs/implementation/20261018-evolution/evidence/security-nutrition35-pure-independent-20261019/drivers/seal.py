from pathlib import Path,PurePosixPath
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-nutrition35-pure-peer-private-20261019';PREFIX='docs/implementation/20261018-evolution/evidence/security-nutrition35-pure-independent-20261019';O=R/PREFIX
BASE='d5ef9602687730037b3e448506e14d14a3df5323';own='tests/test_security_nutrition35_boundary_peer.py';sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());load=lambda n:json.loads((O/n).read_bytes());git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
a=load('summary.json');b=load('adapter-after-summary.json');assert a['author_cases']==79 and a['own_cases']==24 and a['outcomes']=={'passed':102,'failure':1,'error':0,'skipped':0};assert b['outcomes']=={'passed':24,'failure':0,'error':0,'skipped':0}
cases=load('cases.STRUCTURAL.json');assert all(c['outcome']=='passed'for c in cases if 'test_security_nutrition35_boundary_peer'not in c['case'])
assert load('before.json')==load('after.json') and load('adapter-after-before.json')==load('adapter-after-after.json')
final=load('adapter-after-after.json')
for n,d in final['source'].items():assert sha((R/n).read_bytes())==d
packages={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()};assert packages==final['packages'] and len(packages)==92
assert sha(Path(sys.executable).read_bytes())==final['python'] and sha(Path(sys._base_executable).read_bytes())==final['base_python']
initial=(P/'initial-own-canary.RAW.py').read_bytes();fixed=(R/own).read_bytes();assert [ast.dump(n)for n in ast.walk(ast.parse(initial))if isinstance(n,ast.Assert)]==[ast.dump(n)for n in ast.walk(ast.parse(fixed))if isinstance(n,ast.Assert)]
rows=[]
for n in ['core/nutrition_restrictions.py','core/modelos.py','core/generador_planes.py','core/generador_opciones.py','core/food_catalog.py','tests/test_nutrition35_restrictions.py','tests/test_nutrition35_generation_boundary.py','tests/test_nutrition_safety.py','docs/implementation/20261018-evolution/RESTRICCIONES_NUTRICIONALES35_PROPUESTA.md']:
 raw=(R/n).read_bytes();blob=git('show',BASE+':'+n);lf=raw.replace(b'\r\n',b'\n');assert lf==blob
 row={'path':n,'Git_blob_SHA256':sha(blob),'observed_checkout_RAW_SHA256':sha(raw),'RAW_bytes':len(raw),'CRLF_count':raw.count(b'\r\n'),'LF_normalization_equals_Git_blob':True,'RAW_reconstructed':False}
 if n.endswith('.py'):assert ast.dump(ast.parse(raw))==ast.dump(ast.parse(blob));row['AST_exact']=True
 rows.append(row)
save('source-bindings.STRUCTURAL.json',rows)
subprocess.run([sys.executable,'-m','ruff','check',own,'--output-format','json'],cwd=R,stdout=(P/'ruff.stdout.RAW.json').open('wb'),stderr=(P/'ruff.stderr.RAW.log').open('wb'),check=True)
save('ruff.STRUCTURAL.json',{'own_test_diagnostics':len(json.loads((P/'ruff.stdout.RAW.json').read_bytes())),'exit':0,'product_Ruff_not_repeated':True})
(O/'drivers').mkdir(exist_ok=True);(O/'canaries').mkdir(exist_ok=True)
for src,dst in [('metodobase-sec-nutrition35-pure-peer-run-20261019.py','initial-replay.py'),('metodobase-sec-nutrition35-pure-peer-adapter-after-20261019.py','adapter-corrected-replay.py'),('metodobase-sec-nutrition35-pure-peer-final-acl-20261019.ps1','final-acl.ps1'),('metodobase-sec-nutrition35-pure-peer-seal-20261019.py','seal.py')]:
 (O/'drivers'/dst).write_bytes((T/src).read_bytes())
(O/'canaries/initial-own-adapter.py').write_bytes(initial)
acl=json.loads((P/'acl-final.private.json').read_bytes());assert acl['protected'] and acl['parent_SDDL_unchanged'];save('private-ACL.STRUCTURAL.json',{**acl,'initial_SDDL_SHA256':sha((P/'acl-initial.private.txt').read_bytes()),'execution':'Same inspected checks executed inline, no execution-policy change.'})
attrs=[]
for p in sorted(P.rglob('*')):
 if p.is_file():
  assert not p.is_symlink();st=p.stat();attrs.append({'private_relative_path':p.relative_to(P).as_posix(),'bytes':st.st_size,'SHA256':sha(p.read_bytes()),'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'windows_file_attributes':getattr(st,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Both original execution stdout/stderr/XML including initial adapter failure, original canary preimage, synthetic fixtures, Ruff and ACL. RAW original bytes retained, not reconstructed.','files':attrs})
save('repr-scope.STRUCTURAL.json',{'new_declaration_hidden_from_ClienteEvaluacion_repr':True,'preexisting_client_measurements_still_in_custom_repr':True,'AllergyDeclaration_and_NutritionRestrictions_still_have_default_fact_repr':True,'new_domain_repr_logging_callsite_identified':False,'global_health_log_privacy_asserted':False,'scope':'Only new declaration absence from outer client repr and generic domain errors is accepted; inner domain objects must not be logged. No observed external disclosure.'})
review='''Revisión independiente focal de R33 puro/constructor sobre d5ef9602687730037b3e448506e14d14a3df5323. Se acepta el contrato técnico ejecutado en este precursor. No se acepta integración35, API/UI/BDD/worker, desktop, publicación concurrente ni validación clínica o normativa humana.

Las declaraciones exigen objetos cerrados versión1, tipos exactos y estados conocidos. not_reported permanece desconocido y se distingue de none_reported por contenido y digest; ninguno acredita ausencia clínica de alergias. Una alergia reported, incluso other_reported sin alimento, o una solicitud de revisión booleana verdadera impide automatización. No existe campo de aprobación profesional que levante el guard. Se conservan errores genéricos sin repetir hechos declarados.

Ambos constructores invocan el guard antes de seeds, ajustes y lectura de plan anterior. Un catálogo suministrado más estricto no autoriza una alergia ni restaura exclusiones del perfil. La combinación no altera catálogo ni datos fuente compartidos. La validación final rechaza alimento excluido inyectado tras selección en ambos constructores, incluyendo un validador nutricional separado que artificialmente admite la corrupción. Esa prueba evalúa el límite de exclusiones, no la calidad clínica del generador.

require_current rechaza cambio de hechos sin adoptar el nuevo perfil; incluso un snapshot reported idéntico continúa bloqueando publicación automatizada. El adaptador persistente deberá aplicar autorización y bloqueo antes de publicar y compensar cuotas: siguen sin probar en este precursor. El documento de propuesta declara esas tareas pendientes y no presenta aprobación clínica disponible.

Se ejecutan79 casos originales:21 frontera/44 restricciones/14 safety, todos PASS. Los24 casos propios inicialmente dan23PASS/1FAIL por un adapter incorrecto: una función staticmethod se envolvió como método ligado, causando TypeError antes de la aserción final. Se conserva la fuente inicial y todo stdout/stderr/XML. Se corrigen sólo recepción/reenvío y registro staticmethod del adapter; inversa byteexacta y todas las aserciones ASTexactas. Los mismos24 pasan después. No se cuentan ejecuciones repetidas como casos nuevos ni se atribuye ese fallo al productor.

No se editó producto ni tests del autor. Fuentes,92 distribuciones con METADATA y ambos ejecutables Python permanecen iguales antes/después en cada fase; pip check0. El checkout observado contiene CRLF en algunos paths donde Git conservaLF; se publican ambos hashes, inversa LF y ASTexacta. No se reconstruye RAW histórico ni se normaliza retroactivamente la fuente ejecutada. El test propio termina Ruff0.

Límite de privacidad de repr: el nuevo campo no aparece en ClienteEvaluacion ni en errores genéricos. Su repr personalizado conserva mediciones anteriores y los dataclasses AllergyDeclaration/NutritionRestrictions conservan repr automático con hechos. No se identificó un callsite productor que registre esos nuevos objetos y no se demostró fuga; este sello no afirma ausencia global de salud en repr/logs. No deben registrarse los objetos ni el digest sensible. La integración futura debe mantener esa frontera.

RAW/XML y el fallo inicial permanecen privados bajo ACL current-user/SYSTEM; la comprobación distingue fixtures sintéticos pytest con OWNER RIGHTS/Administrators. El contenido público es estructural/código y pasa scanner119 sin cambios y guardJWT. No se lee perfil PG ni se ejecuta SQL externo; no VM, Chrome, Redis, proveedor vivo ni dependencias nuevas. Reutilización de WT conserva refs4187/e318/b792 y la canaria previa c3a4 byteexacta.
'''
(O/'review.md').write_bytes(review.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f';ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('source.json',{'reviewed_commit':BASE,'role':'independent technical pure/constructor peer','verdict':'ACCEPT focal executed pure/constructor contract with repr observation and integration limits','author_cases_PASS':79,'own_unique_cases_PASS_after_harness_correction':24,'initial_own_PASS_harness_FAIL':[23,1],'product_defects_confirmed':0,'original_author_tests_unchanged':True,'product_changes':False,'own_canary_SHA256':sha(fixed),'initial_canary_SHA256':sha(initial),'source_92_metadata_bothPython_quiet_each_phase':True,'pip_exit_before_after':0,'PG_profile_read_or_SQL':False,'global_R33_acceptance':False,'clinical_or_human_regulatory_approval':False,'scanner119_AST_digest':digest})
save('public-safety-scan.json',{'scanner119_AST_digest':digest,'scanner119_unchanged':True,'additional_JWT_guard':True,'all_public_files_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in O.rglob('*'):
 if p.is_file():
  raw=p.read_bytes();ns['scan'](raw,p.relative_to(O).as_posix());assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',raw),p.name
ns['scan'](fixed,own)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'own_canary_SHA256':sha(fixed),'verdict':'focal accepted, not globalR33 or clinical'}))
