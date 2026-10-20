"""Seal owned UI34 sources and honest phase-specific proofs without live services."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

ROOT=Path('F:/mb-followup-actions-ui-20261019')
TEMP=Path('C:/Users/Consu/AppData/Local/Temp')
BASE='36c1a1de32dea878442eb0f158d4fca30fb37659'
PREFIX='docs/implementation/20261018-evolution/evidence/followup-ui34-author-20261020'
OUT=ROOT/PREFIX
DOC=ROOT/'docs/implementation/20261018-evolution/SEGUIMIENTO_UI34_IMPLEMENTACION.md'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT)
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf8')
def archive(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,blob in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,blob)
    return stream.getvalue()

assert git('rev-parse','HEAD').decode().strip()==BASE
assert not OUT.exists() and not DOC.exists()
tracked=set(git('diff','--name-only',BASE).decode().splitlines())
untracked=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
names=sorted(tracked|untracked)
assert len(names)==18,(len(names),names)
assert all(name.startswith(('web/','tests/')) for name in names)
sources={name:(ROOT/name).read_bytes() for name in names}
latest=json.loads((TEMP/'metodobase-followup-ui34-runtime-final-v4-20261020/after.json').read_text())
assert all(latest['source'][name]==sha(blob) for name,blob in sources.items())
node4=json.loads((TEMP/'metodobase-followup-ui34-runtime-final-v4-20261020/node-results.json').read_text())
assert [(x['report']['passed'],x['report']['total'],x['exit']) for x in node4]==[(14,14,0),(42,42,0),(10,10,0),(6,6,0)]
receipt4=json.loads((TEMP/'metodobase-followup-ui34-runtime-final-v4-20261020/receipt.json').read_text())
assert receipt4['quiet'] and receipt4['pytest_exit']==0 and receipt4['pip_before']==receipt4['pip_after']==0

# The existing API, Google, MFA and legacy session authority are exactly intact
# after removing the one additive purpose-closed block and one return member.
api=sources['web/static/js/api.js'].decode('utf8')
start=api.index('  // Wire34: purpose-closed, exact-access operations.')
end=api.index('  const billing = {',start)
inverse=api[:start]+api[end:]
inverse=inverse.replace('mfa, googleLink, followup, clearTokens','mfa, googleLink, clearTokens')
old=git('show',BASE+':web/static/js/api.js')
assert inverse.encode()==old
assert not any(word in api[start:end] for word in ('localStorage','sessionStorage','_doRefresh','_handleRefresh'))

backend=json.loads((ROOT/'docs/implementation/20261018-evolution/evidence/backend-followup34-author-20261019/candidate-source.json').read_text())
backend_comparison={}
for name in backend['paths']:
    if name=='web/followup_paths.py':continue
    raw=(ROOT/name).read_bytes();blob=git('show','80b9a44adf4daae160673b4d86a58cb06f809071:'+name)
    assert raw.replace(b'\r\n',b'\n')==blob
    backend_comparison[name]={'git_sha256':sha(blob),'working_raw_sha256':sha(raw),'git_raw_equal':raw==blob,'lf_normalization_equal':True}
assert sha(sources['web/followup_paths.py'])=='2db2e41a41ff89b596be4dc8ed7301bd97366133c8608cf7fded8894a0071d39'
assert sha(sources['tests/test_followup34_client_ssr_privacy.py'])=='2cf14eeeb9e113b92ac269059db7c8683fef1a7478c9579f14aeb773216824c0'

proofs={}
phases=['metodobase-followup-ui34-runtime-v1-20261019','metodobase-followup-ui34-runtime-final-v2-20261020','metodobase-followup-ui34-runtime-final-v3-20261020','metodobase-followup-ui34-runtime-final-v4-20261020','metodobase-followup-ui34-redirect-probe-20261020','metodobase-followup-ui34-final-alias-20261020']
for directory in phases:
    parent=TEMP/directory
    assert parent.is_dir()
    for path in parent.iterdir():
        if path.is_file() and path.suffix in {'.json','.xml','.stdout','.stderr','.py','.cjs','.js'}:
            proofs['phases/'+directory+'/'+path.name]=path.read_bytes()
    log=TEMP/(directory+'.stdout')
    if log.is_file():proofs['phases/'+directory+'/process.stdout.raw']=log.read_bytes()
standalone=['metodobase-followup-ui34-before-api-20261019.json','metodobase-followup-ui34-after-api-v1-20261019.json','metodobase-followup-ui34-after-api-v2-20261019.json','metodobase-followup-ui34-state-v1-20261019.json','metodobase-followup-ui34-state-v2-before-guard-20261020.json','metodobase-followup-ui34-state-v2-after-guard-20261020.json','metodobase-followup-ui34-state-v3-20261020.json','metodobase-followup-ui34-dom-v1-20261020.json','metodobase-followup-ui34-state-v2-before-guard-source-20261020.js','metodobase-followup-ui34-state-v2-before-guard-test-20261020.cjs','metodobase-followup-ui34-matcher-composition-20261020.json']
for name in standalone:proofs['intermediate/'+name]=(TEMP/name).read_bytes()
drivers=['metodobase-followup-ui34-run-v1-20261019.py','metodobase-followup-ui34-run-final-v2-20261020.py','metodobase-followup-ui34-run-final-v3-20261020.py','metodobase-followup-ui34-run-final-v4-20261020.py','metodobase-followup-ui34-probe-redirect-20261020.py','metodobase-followup-ui34-compose-matcher-20261020.py','metodobase-followup-ui34-compose-final-alias-20261020.py','metodobase-followup-ui34-refine-fixtures-20261020.py']
for name in drivers:proofs['drivers/'+name]=(TEMP/name).read_bytes()

prior_nodes=json.loads((TEMP/'metodobase-followup-ui34-runtime-final-v2-20261020/node-results.json').read_text())
prior_commands=[entry for entry in prior_nodes if Path(entry['file']).stem not in {'followup_tasks_api','followup_tasks_state','followup_tasks_dom','dashboard_followup34'}]
prior_regressions=[]
helper_loads=[]
for entry in prior_commands:
    assert entry['exit']==0
    report=entry['report']
    if report.get('unparsed'):
        assert entry['file']=='tests/e2e/mfa31_login.cjs'
        assert not (TEMP/'metodobase-followup-ui34-runtime-final-v2-20261020/mfa31_login.stdout').read_bytes()
        helper_loads.append({'file':entry['file'],'exit':0,'cases':0,'scope':'Module exported helpers only; no login, HTTP or browser scenario executed'})
        continue
    if 'report' in report:
        rows=report['report'];assert isinstance(rows,list) and all(v['passed'] is True for v in rows)
        report={**report,'passed':len(rows),'total':len(rows)}
    assert report['passed']==report['total']
    prior_regressions.append({**entry,'normalized_count_only':{'passed':report['passed'],'total':report['total']}})
assert len(prior_regressions)==17 and len(helper_loads)==1
regression_cases=sum(x['normalized_count_only']['total'] for x in prior_regressions)
assert regression_cases==245
proofs['drivers/seal-count-preflight-v1.py']=(TEMP/'metodobase-followup-ui34-seal-count-preflight-v1-20261020.py').read_bytes()
proofs['intermediate/seal-count-preflight-erratum.json']=encoded({'error':'First sealing preflight assumed every report had top-level passed/total; KeyError before writing public prefix or changing source.','resolution':'Parse the retained race-review report array and distinguish mfa31_login module load (zero cases). Preserve original RAW node-results and stdout.','effective_prior_regression_suites':17,'effective_prior_regression_cases':245,'helper_module_loads':helper_loads,'product_change':False,'tests_reexecuted':False})
metadata={'base_head':BASE,'main_parent':'e0da4c551f67ad3bff286041e77ab8b7c9be81f2','backend_author':'80b9a44adf4daae160673b4d86a58cb06f809071','root_private_alias_producer':'2f74c634028e2fa487e71423737194c4d8868167','wire34_sha256':'33bfe88f33705cb33b70c2ef2b57951e9ee59cb7176466143e93d3822fd83f91','scope':'UI sources plus root-approved exact private SSR matcher/test; author VM/DOM/SSR/SQLite HTTP DTO compatibility only','sources':{name:{'bytes':len(blob),'raw_sha256':sha(blob),'normalized_lf_sha256':sha(blob.replace(b'\r\n',b'\n'))} for name,blob in sources.items()},'source_count':len(sources),'products':sum(name.startswith('web/') for name in sources),'tests':sum(name.startswith('tests/') for name in sources)}
classification={'current_own_cases':{'api_vm':14,'controller_vm':42,'mounted_minimal_dom':10,'dashboard_vm':6,'pytest_ssr_privacy_and_real_sqlite_http_dto_bridge':15},'current_source_quiet':receipt4,'prior_regression_suites':len(prior_regressions),'prior_regression_cases':regression_cases,'helper_module_loads':helper_loads,'prior_regressions_source_preserved_except_new_UI_controller_and_view_not_used_by_them':True,'baseline_missing_namespace':{'absence_canary':1,'dependent_cases_blocked_by_absent_namespace':12,'all_reported_red':13,'execution_source_photograph':'No full before/after photo was captured for the initial absence run; original API is retained immutable Git base36c. No stronger RAW provenance claim.'},'state_guard_causality':{'before_total':39,'before_passed':37,'same_test_after_passed':39,'prechange_source_and_test':'RAW files captured after the RED execution and before applying the guard; not an atomic before/during source photo'},'mounted_alias_transition':{'v2_pytest_passed':11,'v2_pytest_failed':2,'cause':'Historical unmounted matcher test expected404 for //; mounted Starlette canonicalized307. Root extended only SSR private alias and preserved every privacy assertion. A local strict-referrer adaptation was never executed or accepted.','diagnostic_probe_cases':3,'diagnostic_is_acceptance':False,'current_private_alias_status':307,'current_location':'http://testserver/clientes/legacy42/seguimiento','current_referrer':'no-referrer'},'limitations':['No Chrome, visual widths, native dialog behavior or axe result claimed. CSS provides responsive rules but those need independent browser acceptance at320/390/768/1440.','No PostgreSQL migration/concurrency/restore, desktop install, live provider, production performance or deployment acceptance.','The shared92-package environment stayed readonly and unchanged; no pip install or new dependencies.','No server task is automatically created/completed/retried/read back after a write. Explicit GETs provide scope and fresh preparation.','Global legacy browser token storage is unchanged, proved by exact API inverse. This module stores only closed handles in RAM; it does not close the global R31 session-storage requirement.','Scanner119 validates public payload structure; it is not a global gitleaks run or R05 acceptance.']}
preservation={'api_additive_full_inverse_equal_git_base':True,'api_original_sha256':sha(old),'api_inverse_sha256':sha(inverse.encode()),'backend_paths_preserved_except_root_private_matcher':backend_comparison,'root_private_matcher_exact':True,'root_private_test_exact':True,'old_test_files_modified':[]}

files={'source.json':encoded(metadata),'source.raw.zip':archive(sources),'proofs.raw.zip':archive(proofs),'classification.json':encoded(classification),'preservation.json':encoded(preservation),'seal-driver.py':Path(__file__).read_bytes(),'.gitattributes':b'* -text\n'}
scanner_source=(TEMP/'metodobase-checkpoint119-prepare.py').read_bytes()
tree=ast.parse(scanner_source.decode('utf8'));function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
scanner_ast=ast.Module(body=[function],type_ignores=[])
scope={'re':re,'zipfile':zipfile,'io':io,'tarfile':tarfile,'PurePosixPath':PurePosixPath}
exec(compile(scanner_ast,'retained-scanner119','exec'),scope)
files['scanner119-function.py']=(ast.get_source_segment(scanner_source.decode('utf8'),function)+'\n').encode()
for name,blob in files.items():scope['scan'](blob,name)
files['scan-public.json']=encoded({'scanner':'Exact retained scanner119 function expanded archives','source_file_sha256':sha(scanner_source),'function_sha256':sha(files['scanner119-function.py']),'public_files_checked':len(files),'accepted':True,'global_gitleaks_or_R05_acceptance':False})

OUT.mkdir(parents=True)
(OUT/'.gitattributes').write_bytes(files.pop('.gitattributes'))
for name,blob in files.items():(OUT/name).write_bytes(blob)
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(OUT.iterdir()) if p.is_file()}
(OUT/'manifest.json').write_bytes(encoded({'files':manifest,'self_excluded':True,'scope':'Exact closed proof bytes'}))
DOC.write_text('''# UI34: tareas de seguimiento\n\nLa página `/seguimiento` y la ficha `/clientes/{id}/seguimiento` permiten consultar tareas autorizadas, preparar una creación por causa vigente, editar paso y responsable, registrar una revisión completada o cancelar con motivo cerrado. Cada escritura exige confirmación; cargar, filtrar, abrir una ficha o consultar cifras sólo hace lecturas. El dashboard conserva sus hechos y muestra tareas abiertas por causa con próximo paso y responsable.\n\nEl servidor fija el alcance. OWNER/ADMIN gestiona su gimnasio; Nutri recibe sólo sus asignaciones y puede completar las tareas permitidas. La página tiene shell propio y no carga estadísticas globales ni el sidebar heredado. Los nombres de responsables no elegibles permanecen nulos; no se buscan contactos. Las fechas de membresía no prueban deuda y una revisión completada es una declaración del actor, sin contacto, entrega, cobro, renovación ni efecto clínico inferido.\n\n`Api.followup` fija rutas, cuerpos, versiones y cursores. Las operaciones tienen UUID idempotente y cuerpo capturado en un handle opaco en RAM, vinculado al acceso exacto. El transporte no rota credenciales, reintenta ni consulta el resultado después de escribir. El ACK debe corresponder a la clave de operación, recurso, cliente, causa, versión, paso, responsable y tiempo esperados. Un replay confirma una operación histórica y obliga a consultar expresamente el estado actual. Una respuesta incierta bloquea otra preparación hasta una lectura primaria explícita; consultar métricas o responsables no desbloquea un DTO viejo.\n\nLa historia pagina por versión ascendente. Las cifras separan estado actual de eventos del periodo y muestran fuente, cobertura de clientes activos y zona America/Mexico_City. No se convierten errores en ceros. Los formularios usan diálogo nativo, labels, regiones status/alert, confirmación, Escape y retorno lógico de foco; el adaptador sólo utiliza textContent para datos. Se limpian datos visibles y ocultos por cambio de sesión, Storage, pagehide y retorno de bfcache.\n\nValidación de autor: 72 casos VM/DOM propios y 15 casos SSR/privacidad/compatibilidad entre DTO HTTP SQLite reales y parsers JavaScript. Ambas factories pasan, incluidos alias //307 con Location exacta y headers privados. La fase final mantuvo 1076 fuentes, 92 paquetes y Python/Node quietos, con pip check con salida 0 antes y después. Las 17 suites previas de regresión auth/MFA/Google/dashboard (245 casos) están conservadas con su fuente y ejecución propias. Otro comando sólo cargó un helper y no ejecutó casos de login; no se suman ejecuciones superpuestas.\n\nLa evidencia conserva el namespace ausente inicial, los dos canarios de bloqueo que fallaron durante WIP y la transición de framing del alias SSR. No afirma revisión independiente ni aceptación Chrome, layout en 320/390/768/1440, axe, PostgreSQL, instalación desktop, proveedor real, rendimiento o despliegue. El almacenamiento global heredado de tokens sigue abierto para R31: el bloque nuevo no lo altera, como acredita la inversa exacta de api.js.\n\nFuente y fases: [source.json](evidence/followup-ui34-author-20261020/source.json), [clasificación y límites](evidence/followup-ui34-author-20261020/classification.json), [preservación](evidence/followup-ui34-author-20261020/preservation.json), [manifiesto](evidence/followup-ui34-author-20261020/manifest.json). Contrato: [wire34 v1](SEGUIMIENTO_TAREAS_WIRE34.json).\n''',encoding='utf8',newline='')
scope['scan'](DOC.read_bytes(),DOC.name)
result={'source_paths':len(sources),'source_sha256':sha((OUT/'source.json').read_bytes()),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'prior_regression_suites':len(prior_regressions),'prior_regression_cases':regression_cases,'proof_zip_members':len(proofs),'scope':'Author UI34 sealed; independent browser/PG still pending'}
(TEMP/'metodobase-followup-ui34-seal-result-20261020.json').write_bytes(encoded(result))
print(json.dumps(result))
