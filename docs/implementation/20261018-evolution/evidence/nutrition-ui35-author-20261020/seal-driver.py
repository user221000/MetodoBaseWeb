"""Seal owned web nutrition35 sources and phase-specific proofs without live services."""
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
BASE='bb5999589246ada1d917194a9d93bf7b5b9ac8af'
BACKEND='55a3f4f9b1c1d03937bae78a5cee4f1d1b6379af'
UI34='1ebfb98f205d6be25a088b9fd70c2fa2633d87ba'
PREFIX='docs/implementation/20261018-evolution/evidence/nutrition-ui35-author-20261020'
OUT=ROOT/PREFIX
DOC=ROOT/'docs/implementation/20261018-evolution/NUTRICION_UI35_IMPLEMENTACION.md'
sha=lambda blob:hashlib.sha256(blob).hexdigest()
git=lambda *args:subprocess.check_output(['git','-c','core.autocrlf=false','--no-replace-objects',*args],cwd=ROOT)
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf8')
def archive(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,blob in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,blob)
    return stream.getvalue()
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not OUT.exists() and not DOC.exists()
names=sorted(set(git('diff','--name-only',BASE).decode().splitlines())|set(git('ls-files','--others','--exclude-standard').decode().splitlines()))
assert len(names)==15,(len(names),names)
assert all(name.startswith(('web/static/','web/templates/','tests/')) for name in names)
sources={name:(ROOT/name).read_bytes() for name in names}
final1=TEMP/'metodobase-nutrition-ui35-runtime-final-v1-20261020'
final2=TEMP/'metodobase-nutrition-ui35-runtime-final-v2-20261020'
latest=json.loads((final2/'after.json').read_text())
assert all(latest['source'][name]==sha(blob) for name,blob in sources.items())
receipt1=json.loads((final1/'receipt.json').read_text());receipt2=json.loads((final2/'receipt.json').read_text())
assert receipt1['quiet'] and receipt1['pytest_exit']==1 and receipt1['ruff_exit']==0
assert receipt2['quiet'] and receipt2['pytest_exit']==0 and receipt2['ruff_exit']==0
assert receipt1['pip_before']==receipt1['pip_after']==receipt2['pip_before']==receipt2['pip_after']==0
framing=json.loads((final2/'framing.json').read_text())
assert framing['exact_three_changes_verified'] and not framing['product_change']
assert framing['changed_paths']==['tests/test_nutrition35_ui.py']

# Invert the additive nutrition API extension, retaining every previous byte.
api=sources['web/static/js/api.js'].decode('utf8')
start=api.index('  // Nutrition35 is additive and purpose-closed.')
end=api.index('  const billing = {',start)
inverse=(api[:start]+api[end:]).replace('googleLink, followup, nutrition, clearTokens','googleLink, followup, clearTokens')
old=git('show',BASE+':web/static/js/api.js')
assert inverse.encode()==old
assert not any(word in api[start:end] for word in ('localStorage','sessionStorage','_doRefresh','_handleRefresh'))
backend_paths=git('diff','--name-only',BACKEND+'^',BACKEND).decode().splitlines()
backend={}
for name in backend_paths:
    raw=(ROOT/name).read_bytes();blob=git('show',BACKEND+':'+name)
    assert raw.replace(b'\r\n',b'\n')==blob,name
    backend[name]={'git_sha256':sha(blob),'working_raw_sha256':sha(raw),'git_raw_equal':raw==blob,'lf_normalization_equal':True}
wire=ROOT/'docs/implementation/20261018-evolution/NUTRICION35_WIRE.json'
assert sha(wire.read_bytes())=='dd39f10cad4f9fac10b4d078236ee7bb9758fc9059bb9bee8083703f09394471'
old34=json.loads((ROOT/'docs/implementation/20261018-evolution/evidence/followup-ui34-author-20261020/source.json').read_text())
preserved34={}
for name in old34['sources']:
    if name in sources:preserved34[name]={'deliberate_additive_UI35_extension':True};continue
    raw=(ROOT/name).read_bytes();blob=git('show',UI34+':'+name)
    assert raw==blob,name
    preserved34[name]={'git_raw_equal':True,'sha256':sha(raw)}

node_entries=json.loads((final1/'node-results.json').read_text())
assert len(node_entries)==27 and all(entry['exit']==0 for entry in node_entries)
node_counts=[]
for entry in node_entries:
    report=entry['report']
    if 'report' in report:
        assert all(row['passed'] is True for row in report['report'])
        passed=total=len(report['report'])
    else:passed,total=report['passed'],report['total']
    assert passed==total
    node_counts.append({'file':entry['file'],'passed':passed,'total':total,'exit':0})
own_names={'nutrition35_api','nutrition35_state','nutrition35_dom','nutrition35_personal_generation'}
own=[entry for entry in node_counts if Path(entry['file']).stem in own_names]
prior=[entry for entry in node_counts if Path(entry['file']).stem not in own_names]
assert [entry['total'] for entry in own]==[12,31,10,6]
assert len(prior)==23

proofs={}
dirs=['metodobase-nutrition-ui35-before-api-quiet-20261020','metodobase-nutrition-ui35-composition-20261020','metodobase-nutrition-ui35-partial-empty-repro-20261020','metodobase-nutrition-ui35-personal-template-20261020','metodobase-nutrition-ui35-runtime-final-v1-20261020','metodobase-nutrition-ui35-runtime-final-v2-20261020','metodobase-nutrition-ui35-state-fixture-20261020','metodobase-nutrition-ui35-wizard-controls-20261020']
for directory in dirs:
    parent=TEMP/directory;assert parent.is_dir()
    for path in sorted(parent.rglob('*')):
        if not path.is_file() or {'cache','__pycache__'}&set(path.relative_to(parent).parts):continue
        assert path.suffix in {'.json','.xml','.stdout','.stderr','.py','.cjs','.js','.html','.raw'},path
        proofs['phases/'+directory+'/'+path.relative_to(parent).as_posix()]=path.read_bytes()
for path in sorted(TEMP.glob('metodobase-nutrition-ui35-*')):
    if path.is_file() and path!=Path(__file__):
        assert path.suffix in {'.py','.json','.cjs','.stdout'},path
        proofs['drivers-and-intermediate/'+path.name]=path.read_bytes()
for name in git('diff','--name-only',BASE).decode().splitlines():proofs['base-preimages/'+name]=git('show',BASE+':'+name)
api_repro=json.loads((TEMP/'metodobase-nutrition-ui35-partial-empty-repro-20261020/api-app.json').read_text())
saas_repro=json.loads((TEMP/'metodobase-nutrition-ui35-partial-empty-repro-20261020/web-main_web.json').read_text())
assert api_repro['status']==400 and api_repro['attribute_observation']['attribute_name']=='lower' and api_repro['attribute_observation']['receiver_type']=='NoneType'
assert saas_repro['status']==200
metadata={'base_head':BASE,'composition_parents':[UI34,BACKEND],'wire35_sha256':sha(wire.read_bytes()),'scope':'Owned web35 UI only; backend35 frozen source preserved; desktop explicitly excluded by user','sources':{name:{'bytes':len(blob),'raw_sha256':sha(blob),'normalized_lf_sha256':sha(blob.replace(b'\r\n',b'\n'))} for name,blob in sources.items()},'source_count':len(sources),'products':sum(name.startswith('web/') for name in sources),'tests':sum(name.startswith('tests/') for name in sources)}
classification={
 'own_current':{'api_vm':12,'controller_vm':31,'mounted_minimal_dom':10,'personal_generation_vm':6,'total_own_vm_dom':59,'ssr_actual_sqlite_http_dto_bridge':13},
 'execution_phases':{'final_v1':receipt1,'final_v2':receipt2,'node_suite_commands':27,'node_count_rows':node_counts,'overlapping_cases_not_summed':True,'closed_node_sources_preserved_in_final_v2':True},
 'prior_regressions':{'suite_commands':len(prior),'cases':sum(row['total'] for row in prior),'all_exit_zero':True,'own_35_cases_excluded':True},
 'red_history':{
  'namespace_absent':{'total':12,'passed':0,'absence_canary':1,'dependent_blocked':11,'initial_report_and_repeated_quiet_phase_retained':True},
  'state_v1':{'total':31,'passed':27,'failed':4,'two_fixture_dispatch_semantics':2,'one_fixture_request_start_barrier':1,'one_product_unknown_create_guard':1},
  'state_after_fixture_before_guard':{'total':31,'passed':30,'failed':1},
  'state_guard_fix':{'total':31,'passed':31,'same_business_assertions':True},
  'personal_generation_harness_v1':{'total':6,'passed':0,'failed':6,'cause':'Synthetic window separate from VM global; fixture looked at wrong export object. Fixed only sandbox.Nutrition35 to sandbox.window.Nutrition35; product and assertions unchanged.'},
  'wizard_driver_preflight':{'expected':3,'actual':2,'mutation_before_failure':False,'cause':'Only two exact legacy false-reset loops; corrected preflight count retained separately.'},
  'final_v1_pytest':{'total':13,'passed':6,'failed':7,'five_wrong_literal_in_new_assertion':5,'one_empty_synthetic_anthro_prestate':1,'one_personal_incomplete_anthro_precondition':1,'exact_framing_proof':framing},
  'independent_partial_empty':{'status':'Still RED on frozen backend55a; ROOT registered QA20 and owns separate correction. Not silently repaired or accepted here.','api_app_failed':1,'web_main_web_passed':1,'route':api_repro['route'],'public_error':api_repro['public_error'],'missing_attribute':'NoneType.lower','auth':'Real registration/login/existing MFA; no auth override','instrumentation':'Attribute name, receiver class and stack location only; reraises original. No str(exc) or auth/health value log.'}
 },
 'limitations':['No Chrome, native dialog/focus, visual widths320/390/768/1440 or axe result claimed; minimal DOM and SSR syntax do not establish those.','No PostgreSQL35 migration/concurrency, independent security, actual professional validation, live provider, performance or deployment acceptance. Desktop is explicitly outside current user scope.','HTTP compatibility uses real authenticated isolated SQLite HTTP DTOs piped into the maintained JS controller; it is not live JS network/browser acceptance.','A declared lack of allergies is a personal declaration, not clinical approval or a cross-contact assurance. Reported allergies/review request block automated generation at every tier.','No edit CAS is offered by this DTO. A session fence prevents own stale-session use; it does not prevent another authorized editor changing the declaration.','Global legacy token storage remains unchanged; exact api.js inverse proves extension scope, not global R31 closure.','Scanner119 validates these public payloads and nested archive structure; it is not global gitleaks or R05 acceptance.']
}
preservation={'api_additive_full_inverse_equal_git_base':True,'api_original_sha256':sha(old),'api_inverse_sha256':sha(inverse.encode()),'api_nutrition_no_storage_or_refresh_hooks':True,'backend35_paths_exact_after_lf_normalization':backend,'ui34_paths':preserved34,'old_tests_modified':[],'shared_environment_readonly':True,'desktop_files_modified':False}
files={'source.json':encoded(metadata),'source.raw.zip':archive(sources),'proofs.raw.zip':archive(proofs),'classification.json':encoded(classification),'preservation.json':encoded(preservation),'seal-driver.py':Path(__file__).read_bytes(),'.gitattributes':b'* -text\n'}
scanner_source=(TEMP/'metodobase-checkpoint119-prepare.py').read_bytes()
tree=ast.parse(scanner_source.decode('utf8'));function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
scope={'re':re,'zipfile':zipfile,'io':io,'tarfile':tarfile,'PurePosixPath':PurePosixPath}
exec(compile(ast.Module(body=[function],type_ignores=[]),'retained-scanner119','exec'),scope)
files['scanner119-function.py']=(ast.get_source_segment(scanner_source.decode('utf8'),function)+'\n').encode()
for name,blob in files.items():scope['scan'](blob,name)
files['scan-public.json']=encoded({'scanner':'Exact retained scanner119 function expanded archives','source_file_sha256':sha(scanner_source),'function_sha256':sha(files['scanner119-function.py']),'public_files_checked':len(files),'accepted':True,'global_gitleaks_or_R05_acceptance':False})
OUT.mkdir(parents=True)
(OUT/'.gitattributes').write_bytes(files.pop('.gitattributes'))
for name,blob in files.items():(OUT/name).write_bytes(blob)
manifest={path.relative_to(OUT).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(OUT.iterdir()) if path.is_file()}
(OUT/'manifest.json').write_bytes(encoded({'files':manifest,'self_excluded':True,'scope':'Exact closed proof bytes'}))
DOC.write_text('''# UI35: declaraciones nutricionales web

Las fichas de clientes, el alta desde generación y el perfil personal permiten consultar y editar explícitamente la declaración versionada. Se distingue entre falta de declaración, declaración personal de no tener alergias y alergias reportadas; se pueden elegir IDs del catálogo, reportar otras alergias sin texto libre y solicitar revisión profesional. Las exclusiones alimentarias existentes siguen siendo un campo independiente. El formulario no aprueba clínicamente, infiere ingredientes o alérgenos, garantiza ausencia de contaminación cruzada ni envía contactos.

La comparación canónica vive en RAM. Guardar sólo peso u otro dato general omite `restricciones_nutricionales`, incluso si el llamador conserva un objeto previo. Un cambio real exige objeto completo, confirmación y guardado explícito. Las lecturas corruptas o fallidas bloquean el formulario; nunca se convierten en un valor de ausencia de alergias. Las alergias reportadas, la revisión solicitada y una declaración modificada sin guardar impiden iniciar generación automática, incluido Pro. Los errores 409/422 y la incertidumbre 503 tienen mensajes propios sin afirmar devolución o liberación de cupo.

`Api.nutrition` añade rutas cerradas sobre los handles y acceso exacto de sesión existentes. No agrega step-up ni rotación, reintento o consulta automática después de escribir. La respuesta incierta bloquea otro guardado hasta una lectura autorizada y manual; un alta sin ID confirmado no se desbloquea inventando una ficha nueva. Los cambios de sesión/recurso invalidan datos y resultados tardíos. La interfaz conserva sólo su estado en RAM y limpia sus campos al salir/cambiar sesión. El contrato no ofrece CAS de edición: esto no impide que otro editor autorizado cambie el perfil.

Validación de autor: 59 casos propios VM/DOM y 13 casos SSR/compatibilidad de DTO HTTP SQLite autenticados con el controlador JavaScript actual. Los casos de gimnasio cubren ambas factories; los personales cubren sólo SaaS. La fase JavaScript ejecutó 27 suites con salida 0, incluidas 23 regresiones anteriores. Tras corregir tres detalles de framing del nuevo test SSR/HTTP, sólo se repitieron sus 13 casos; el resto de las fuentes permaneció idéntico. Ambas fases conservaron 1097 fuentes, 92 paquetes y binarios Python/Node, con `pip check` y Ruff con salida 0.

La evidencia conserva los RED iniciales, preimágenes, el fallo real del guard de alta incierta y las correcciones de dobles de prueba. Conserva además una regresión independiente: sobre el backend congelado55a, actualizar sólo peso en un perfil antropométrico completamente vacío devuelve400 en api.app por NoneType.lower; SaaS acepta la actualización. ROOT registró QA20 y corrige ese backend por separado. Los escenarios de nutrición parten del perfil sintético completo VALID para evaluar el guard nutricional y no ocultan la regresión original.

Este sello no afirma aceptación Chrome, foco o diálogo nativo, layout320/390/768/1440, axe, PostgreSQL35, revisión independiente de seguridad, validación profesional real o despliegue. Desktop queda fuera del alcance actual por instrucción explícita del usuario. El almacén global heredado de tokens sigue sin cambios; la inversa exacta de api.js acredita el alcance de esta extensión, sin cerrar globalmente R31.

Contrato: [wire35 v1](NUTRICION35_WIRE.json). Fuente y fases: [source.json](evidence/nutrition-ui35-author-20261020/source.json), [clasificación](evidence/nutrition-ui35-author-20261020/classification.json), [preservación](evidence/nutrition-ui35-author-20261020/preservation.json), [manifiesto](evidence/nutrition-ui35-author-20261020/manifest.json).
''',encoding='utf8',newline='')
scope['scan'](DOC.read_bytes(),DOC.name)
scope['scan']((OUT/'manifest.json').read_bytes(),'manifest.json')
result={'source_paths':len(sources),'products':metadata['products'],'tests':metadata['tests'],'source_sha256':sha((OUT/'source.json').read_bytes()),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'prior_regression_suites':len(prior),'prior_regression_cases':sum(row['total'] for row in prior),'proof_zip_members':len(proofs),'scope':'Web UI35 author sealed; independent browser/PG/security pending. Desktop excluded. QA20 parent-owned.'}
(TEMP/'metodobase-nutrition-ui35-seal-result-20261020.json').write_bytes(encoded(result))
print(json.dumps(result))
