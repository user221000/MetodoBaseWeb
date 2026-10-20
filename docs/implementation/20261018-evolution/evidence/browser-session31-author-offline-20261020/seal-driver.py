"""Seal the owned offline R31 phase without claiming native/global acceptance."""
from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,os,re,subprocess,tarfile,zipfile
ROOT=Path('F:/mb-followup-actions-ui-20261019');TEMP=Path(os.environ['TEMP']);BASE='f7c11d103c0a10c9896a1193106e7b889369e91c';SNAPSHOT='bee520a8a0c9654239dd04fa54696bd098c51faf'
PREFIX='docs/implementation/20261018-evolution/evidence/browser-session31-author-offline-20261020';OUT=ROOT/PREFIX;DOC=ROOT/'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_IMPLEMENTACION.md'
git=lambda *args:subprocess.check_output(['git','-c','core.autocrlf=false','--no-replace-objects',*args],cwd=ROOT)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda value:(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf8')
assert git('rev-parse','HEAD').decode().strip()==SNAPSHOT and not OUT.exists() and not DOC.exists()
def archive(entries):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for name,raw in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    return output.getvalue()
final=TEMP/'metodobase-r31-browser-offline-final-gate-20261020';receipt=json.loads((final/'receipt.json').read_text());before=json.loads((final/'before.json').read_text());after=json.loads((final/'after.json').read_text());assert before==after
assert receipt['quiet']and receipt['node_exit']==receipt['pytest_exit']==receipt['ruff_exit']==receipt['pip_before']==receipt['pip_after']==0
assert receipt['node_commands']==51 and receipt['node_passed']==receipt['node_total']==925 and receipt['map_obligations']==865
names=sorted(set(git('diff','--name-only',BASE).decode().splitlines())|set(git('ls-files','--others','--exclude-standard').decode().splitlines()))
assert all(name.startswith(('web/static/','web/templates/','tests/','docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_'))for name in names)
sources={name:(ROOT/name).read_bytes()for name in names}
assert all(name not in after['source']or sha(raw)==after['source'][name]for name,raw in sources.items())
assert sha(sources['docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_WIRE.json'])=='60ef5966a8d2349ff77a0590a46017676bf9a44bab1942b5d85b6aae468d8d08'
snapshot_doc=json.loads((ROOT/'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_SNAPSHOT.json').read_text())
products=[name for name in names if name.startswith('web/')]
assert all(sha(sources[name])==snapshot_doc['sources'][name]for name in products)
mapping=json.loads((ROOT/'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_CI_MAP.json').read_text())
old_names=set(value['path']for value in mapping['historical_sources'].values())
old_names.update('tests/e2e/'+command['key'][7:]+'.cjs'for command in mapping['current_commands']if command['key'].startswith('compat.'))
old_names.update(['tests/e2e/personal_export_context.cjs','tests/e2e/personal_export_controls.cjs','tests/e2e/member_link_export.cjs','tests/e2e/progress_export.cjs'])
preserved={}
for name in sorted(old_names):
    raw=(ROOT/name).read_bytes();assert raw==git('show',BASE+':'+name),name;preserved[name]=sha(raw)
proofs={}
for path in sorted(TEMP.glob('metodobase-r31-browser-*')):
    if path.is_file():proofs['author-phases/'+path.name]=path.read_bytes()
    elif path.is_dir():
        for child in sorted(path.rglob('*')):
            if child.is_file()and not any(part in {'cache','__pycache__','.pytest_cache'}for part in child.relative_to(path).parts):
                assert not child.is_symlink();proofs['author-phases/'+path.name+'/'+child.relative_to(path).as_posix()]=child.read_bytes()
proofs['git/full-R31-before-seal.diff.raw']=git('diff',BASE,'--',*names)
proofs['git/status-before-seal.raw']=git('status','--porcelain=v1')
proofs['retained/legacy-tests-preserved.json']=encoded(preserved)
classification={
 'accepted_owned_offline':receipt,
 'counts':{'executed_current_node_commands':51,'current_node_case_executions':925,'distinct_current_nodeids':len({row['nodeid']for command in mapping['current_commands']for row in command['expected_cases']}),'unique_case_labels':len({row['name']for command in mapping['current_commands']for row in command['expected_cases']}),'ROOT_export_executions':108,'ROOT_export_unique_labels':49,'mapped_obligations':865,'actual_inert_SSR_pytest_cases':56},
 'historical_results_not_current_acceptance':[
  {'phase':'initial-before.stdout','classification':'Stopped on unhandled legacy auth Promise; not a valid complete baseline count.'},
  {'phase':'baselines','classification':'Isolated capability-absence canary RED, dependent wire cases BLOCKED; same DOM synthetic-residue canary RED then PASS. No fabricated pre-implementation browser acceptance.'},
  {'phase':'runtime-web-v1','classification':'28/35 current-candidate commands exit0,7 RED +2 explicitly historical Storage diagnostics; original outputs retained. Controller/business assertions were preserved in companions; missing argv and eighth-dataset DOM are framing, not product acceptance.'},
  {'phase':'core and focused RED phases','classification':'Retain own-primary/discardMfa, refresh-fence/inside-Lock uncertainty, native Storage error normalization and intent capture before await causal RED/preimages/PASS.'},
  {'phase':'native-storage-error/logged-lock-error','classification':'Actual native DOMException fixture versus renamed Error is explicitly retained. The focused40/42→42/42 correction keeps session_storage_error instead of misclassifying a normalized Storage SecurityError as a native Lock denial.'},
  {'phase':'logout-framing','classification':'Parent decision: invalidated tabB must not revoke newer account. Late SetCookie→logout test uses current tabA; separate B no-I/O counterexample retained.'},
  {'phase':'recovery3/6','classification':'Shared VM lacked standard queueMicrotask; fixture-only change, assertions unchanged. Original recovery source remains0/2RED under corrected fixture; current6/6PASS.'},
  {'phase':'MFA companion RED','classification':'Cancel waits observed request dispatch; absent lazy module removes shared fixture document only in that scenario. Business assertions remain.'},
  {'phase':'transport-regressions-v3','classification':'56/57 then57/57: expiry clear and newly introduced listener Storage fault are2 distinct invalidations. Exact count2, blocked continuation/no redirect/RAM-empty checks unchanged; no product mutation.'},
  {'phase':'mapped-offline-v1','classification':'47 Node launches failed before execution because Windows backslashes were consumed in NODE_OPTIONS.0 cases executed, not817 assertion failures. POSIX path framing fixed; mapped-offline-v2 actual47/817PASS, final51/925PASS.'},
 ],
 'limits':['No actual browser cookie backend HTTP was executed by this author; parent backend and independent QA proof is separate.','No Chromium/native focus/layout/axe/screenshots, PostgreSQL, live provider, deployment, performance or global CI acceptance.','Historical JWT-Storage suites remain byte-exact; their prior criteria are explicitly superseded/mapped, never retroactively marked PASS.','The deterministic WebLock/cookie/Storage doubles test source behavior, not universal browser/unload compatibility. Web Locks absent/denied fails closed.','An invalidated tab does not adopt or revoke a newly selected account. Epoch is not edit CAS and does not protect against another authorized editor with a distinct intent.','Native browser CI fixtures still require migration and leased independent execution; direct and transitive paths will be handled as a subsequent source-frozen phase.','Desktop is outside the user-authorized current scope.','Scanner119 scans this payload/archive structure; it does not claim global Gitleaks/R05 acceptance.']}
metadata={'base':BASE,'product_snapshot':SNAPSHOT,'products':products,'tests':[name for name in names if name.startswith('tests/')],'sources':{name:sha(raw)for name,raw in sources.items()},'wire_sha256':after['documents']['SESION_NAVEGADOR_R31_WIRE.json'],'CI_map_sha256':after['documents']['SESION_NAVEGADOR_R31_CI_MAP.json'],'scope':'Owned R31 frontend offline author freeze. Product stays exactly at early review snapshot; source additions afterwards are tests/maps/ROOT export wrappers. No backend/native/global acceptance.'}
preservation={'legacy_tests_raw_equal_f7':preserved,'product_raw_equal_review_snapshot':{name:sha(sources[name])for name in products},'legacy_frontend_preimages':'author-phases/metodobase-r31-browser-inventory-20261020/frontend-preimages.raw.zip','preserved_ui35':'816805915ccebf4208bd8eeaeaf1d397ad967c19','ROOT_export_import':mapping['ROOT_export_import'],'source_package_binary_quiet':receipt['quiet']}
files={'source.json':encoded(metadata),'source.raw.zip':archive(sources),'proofs.raw.zip':archive(proofs),'classification.json':encoded(classification),'preservation.json':encoded(preservation),'seal-driver.py':Path(__file__).read_bytes(),'.gitattributes':b'* -text\n'}
scanner_source=(TEMP/'metodobase-checkpoint119-prepare.py').read_bytes();tree=ast.parse(scanner_source.decode());function=next(node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name=='scan');scope={'re':re,'io':io,'zipfile':zipfile,'tarfile':tarfile,'PurePosixPath':PurePosixPath};exec(compile(ast.Module(body=[function],type_ignores=[]),'retained-scanner119','exec'),scope);files['scanner119-function.py']=(ast.get_source_segment(scanner_source.decode(),function)+'\n').encode()
for name,raw in files.items():scope['scan'](raw,name)
files['scan-public.json']=encoded({'accepted':True,'scanner':'Exact retained scanner119 function; nested archives expanded','source_sha256':sha(scanner_source),'function_sha256':sha(files['scanner119-function.py']),'global_gitleaks_or_R05_acceptance':False,'files_checked_before_receipt':len(files)})
OUT.mkdir(parents=True)
for name,raw in files.items():(OUT/name).write_bytes(raw)
manifest={name:{'bytes':len(raw),'sha256':sha(raw)}for name,raw in files.items()};(OUT/'manifest.json').write_bytes(encoded({'files':manifest,'self_excluded':True,'scope':'Exact closed offline author evidence bytes'}))
DOC.write_text('''# Sesión web del navegador R31 — fase offline del autor

El cliente conserva el access sólo en RAM y renueva mediante la cookie HttpOnly del servidor. Bootstrap, migración única, autenticación y cierre esperan el mismo Web Lock hasta consumir JSON. El epoch sin secretos invalida RAM y DOM de otras pestañas, que requieren abrir de nuevo la cuenta para adoptar otra identidad. No se añaden refresh/replay/readback a namespaces privados.

La fuente de producto coincide byte a byte con `bee520a8a0c9654239dd04fa54696bd098c51faf`. Esta fase añade la composición versionable de pruebas y el mapa por comando/caso. No modifica backend ni desktop.

Validación del autor: **51 comandos / 925 ejecuciones Node PASS**, **865 obligaciones del mapa verificadas**, **56 SSR PASS** en ambas factories. Los 45 JS parsean; Ruff y pip check dan0. 1127 fuentes,92 distribuciones y binarios permanecen idénticos durante el gate. Los4 comandos export de ROOT suman108 ejecuciones y49 nombres distintos; no representan108 criterios independientes.

El [mapa CI](SESION_NAVEGADOR_R31_CI_MAP.json) conserva los comandos, NodeIDs y motivos de cada cambio normativo. `python tests/e2e/run_browser31_ci.py --output <directorio-nuevo>` ejecuta los criterios offline actuales, verifica los nombres/cantidades/hashes y guarda diagnósticos RAW privados. ROOT mantiene la edición de `.github`. Los archivos históricos conservan sus bytes; no se les atribuye PASS bajo el transporte nuevo.

Contrato: [wire R31](SESION_NAVEGADOR_R31_WIRE.json). Evidencia: [fuente](evidence/browser-session31-author-offline-20261020/source.json), [clasificación](evidence/browser-session31-author-offline-20261020/classification.json), [preservación](evidence/browser-session31-author-offline-20261020/preservation.json), [manifiesto](evidence/browser-session31-author-offline-20261020/manifest.json).

Esta evidencia usa VM/DOM mínimo, dobles de cookie/Storage/Web Locks y SSR inerte real. Backend HTTP, Chrome, foco/layout/axe, PG y QA independiente requieren pruebas separadas. La migración de los arneses nativos directos y transitivos de CI sigue pendiente como fase distinta; no se declara CI global verde ni compatibilidad universal de unload.
''',encoding='utf8')
scope['scan'](DOC.read_bytes(),DOC.name);scope['scan']((OUT/'manifest.json').read_bytes(),'manifest.json')
result={'source_paths':len(sources),'product_paths':len(products),'proof_members':len(proofs),'source_sha256':sha((OUT/'source.json').read_bytes()),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'CI_map_sha256':metadata['CI_map_sha256'],'counts':classification['counts'],'scope':metadata['scope']};(TEMP/'metodobase-r31-browser-offline-seal-receipt-20261020.json').write_bytes(encoded(result));print(json.dumps(result))
