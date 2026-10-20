from pathlib import Path, PurePosixPath
import ast, hashlib, importlib.metadata, io, json, re, shutil, subprocess, sys, tarfile, zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-nutrition35-api-peer-private-20261019'
O=R/'docs/implementation/20261018-evolution/evidence/security-nutrition35-api-privacy-author-20261020'
BASE='f7c11d103c0a10c9896a1193106e7b889369e91c';FINAL='d47447b5469c05203794cdb14fb8efdd865e6976';CDF='cdf103a28fe33e32cfeaac825d338d1901a5295e'
sha=lambda b:hashlib.sha256(b).hexdigest();git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
assert git('rev-parse','HEAD').decode().strip()==FINAL and not git('status','--porcelain','--untracked-files=no')
O.mkdir(exist_ok=True);assert not (O/'manifest.json').exists()or(O/'source.json').exists();(O/'.gitattributes').write_bytes(b'* -text\n');save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
phases={
 'closed-write-before':{'passed':3,'failure':2,'error':0,'skipped':0},
 'closed-write-after':{'passed':5,'failure':6,'error':0,'skipped':0},
 'closed-write-after-router':{'passed':11,'failure':0,'error':0,'skipped':0},
 'sec22-after':{'passed':28,'failure':0,'error':0,'skipped':0},
 'sec22-logs-and-export':{'passed':10,'failure':0,'error':0,'skipped':0},
 'sec22-final-logging':{'passed':2,'failure':2,'error':0,'skipped':0},
 'sec22-final-no-exception-info':{'passed':4,'failure':0,'error':0,'skipped':0},
}
summaries={}
for phase,expected in phases.items():
 D=P/phase;summary=json.loads((D/'summary.json').read_bytes());assert summary['outcomes']==expected;assert (D/'before.json').read_bytes()==(D/'after.json').read_bytes();summaries[phase]=summary
 for n in ['before.json','after.json','pip-before.RAW.log','pip-after.RAW.log','cases.STRUCTURAL.json','summary.json','argv.json']:(O/(phase+'-'+n)).write_bytes((D/n).read_bytes())
save('phases-summary.json',summaries)
final=json.loads((P/'sec22-final-no-exception-info/after.json').read_bytes())
for n,d in final['source'].items():assert sha((R/n).read_bytes())==d,n
pkgs={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()};assert pkgs==final['packages'] and len(pkgs)==92
assert sha(Path(sys.executable).read_bytes())==final['python'] and sha(Path(sys._base_executable).read_bytes())==final['base_python'] and sha(Path(shutil.which('node')).read_bytes())==final['node']
for n in ['before.json','after.json','results.STRUCTURAL.json','summary.json']:(O/('node-'+n)).write_bytes((P/'node-current'/n).read_bytes())
node=json.loads((P/'node-current/summary.json').read_bytes());assert node['cases']==node['passed']==66 and node['own_cases']==7
assert (P/'node-current/before.json').read_bytes()==(P/'node-current/after.json').read_bytes()
expected_tests={'tests/test_security_nutrition35_error_privacy_peer.py':'21b224280ef10843f4076d6107649f11318e1428259441f26a72941216a2b2ca','tests/test_nutrition35_write_error_boundary.py':'92fe9d9d00d6fb5ef8206ee061f22151d00e0aa6bd3d9650ae61963ba3953644','tests/test_nutrition35_private_error_boundary.py':'928bb7ec44b153b02aecd45ff2755ded76a38a4b5d870f49ab469d6b6cab0c9f','tests/e2e/security_nutrition35_peer.cjs':'6ec7466085efdab8bcd3ead24da9a5c44ca8f8678be870331bc6129c27221d88'}
for n,d in expected_tests.items():assert sha((R/n).read_bytes())==d
changed=git('diff','--name-only',BASE,FINAL,'--','web','api','core','src','config').decode().splitlines();assert changed==['web/middleware/security_headers.py','web/nutrition_http.py','web/nutrition_paths.py']
bindings=[]
for path in changed+list(expected_tests)+['tests/test_security_nutrition35_http_peer.py']:
 raw=(R/path).read_bytes();blob=git('show',FINAL+':'+path);assert raw.replace(b'\r\n',b'\n')==blob
 if path.endswith('.py'):assert ast.dump(ast.parse(raw))==ast.dump(ast.parse(blob))
 bindings.append({'path':path,'RAW_SHA256':sha(raw),'Git_blob_SHA256':sha(blob),'RAW_equals_Git_blob':raw==blob,'LF_inverse_equals_Git_blob':True,'AST_exact_if_Python':True,'CRLF_count':raw.count(b'\r\n'),'RAW_reconstructed':False})
 if raw!=blob:(O/'executed-nutrition-http.RAW.py').write_bytes(raw)
save('final-executed-source-bindings.json',bindings)
current=(R/'web/nutrition_http.py').read_bytes().replace(b'\r\n',b'\n');base=git('show',CDF+':web/nutrition_http.py')
generic=b'''            except Exception as error:
                # SQL/renderer exception text can contain declared facts.
                # Explicitly omit exception values and tracebacks from the log.
                logger.exception("Nutrition request failed class=%s", type(error).__name__, exc_info=None)
                body = {"detail": "Error interno del servidor"}
                request_id = getattr(request.state, "request_id", None)
                if request_id:
                    body["request_id"] = request_id
                return JSONResponse(body, status_code=500, headers=HEADERS)
'''
assert current.count(generic)==1
inverse=current.replace(b'import logging\n\n',b'',1).replace(b'from fastapi.exception_handlers import request_validation_exception_handler\n',b'',1).replace(b'logger = logging.getLogger(__name__)\n',b'',1).replace(b'                response = await request_validation_exception_handler(request, error)\n',b'                raise\n',1).replace(generic,b'',1)
assert inverse==base
headers=(R/'web/middleware/security_headers.py').read_bytes();headers_inverse=headers.replace(b'from web.nutrition_paths import is_nutrition_private\n',b'',1).replace(b'        nutrition_api = is_nutrition_private(request.url.path)\n',b'',1).replace(b'                    and not nutrition_api\n',b'',1).replace(b'                or nutrition_api\n',b'',1).replace(b'or followup_api or nutrition_api or export_api',b'or followup_api or export_api',1)
assert headers_inverse==git('show',CDF+':web/middleware/security_headers.py')
save('full-source-inverses.json',{'nutrition_http_SEC22_inverse_to_CDF_GitLF_byte_exact':True,'nutrition_http_inverse_SHA256':sha(inverse),'executed_nutrition_http_RAW_preimage_retained':True,'executed_RAW_never_normalized_retroactively':True,'security_headers_inverse_to_CDF_GitLF_byte_exact':True,'security_headers_inverse_SHA256':sha(headers_inverse),'new_matcher_deleted_for_inverse':True,'other_product_paths_unchanged_from_frozen35':True,'product_paths_changed':changed,'DTO_auth_permissions_quota_worker_DDL_UI_R31_changed':False,'no_assertion_or_original_canary_changes':True})
lineages={}
for name in ['55a3f4f9','816805915ccebf4208bd8eeaeaf1d397ad967c19','dfab','e0ca16da']:
 oid=git('rev-parse',name).decode().strip();subprocess.run(['git','merge-base','--is-ancestor',oid,BASE],cwd=R,check=True);lineages[name]={'commit':oid,'ancestor_of_frozen35':True}
ui=[]
for n in git('diff-tree','--no-commit-id','--name-only','-r','816805915ccebf4208bd8eeaeaf1d397ad967c19','--','web').decode().splitlines():
 blob=git('show','816805915ccebf4208bd8eeaeaf1d397ad967c19:'+n);raw=(R/n).read_bytes();assert raw.replace(b'\r\n',b'\n')==blob
 ui.append({'path':n,'observed_RAW_SHA256':sha(raw),'UI816_GitLF_SHA256':sha(blob),'LF_inverse_equal_UI816':True,'RAW_reconstructed':False})
save('frozen35-lineage-and-UI.json',{'frozen35':BASE,'lineage':lineages,'UI_paths':ui,'own_source_published_after_execution_LF_inverse_matches_Git_and_Python_AST_exact':True,'nutrition_http_executed_RAW_preserved_separately':True,'PG_checks_or_ROOT_proofs_attributed_to_this_review':False})
quality=[]
for i,path in enumerate(['web/nutrition_http.py','web/nutrition_paths.py','web/middleware/security_headers.py','tests/test_nutrition35_private_error_boundary.py']):
 r=subprocess.run([sys.executable,'-m','ruff','check','--stdin-filename',path,'--output-format','json','-'],cwd=R,input=(R/path).read_bytes(),capture_output=True);(P/'quality'/f'{i}-final.stdout.RAW.json').write_bytes(r.stdout);(P/'quality'/f'{i}-final.stderr.RAW.log').write_bytes(r.stderr)
 codes=[d['code']for d in json.loads(r.stdout)];assert codes==(['I001','F541','BLE001']if path.endswith('security_headers.py')else[]);quality.append({'path':path,'diagnostic_codes':codes,'exit':r.returncode,'baseline_unchanged':path.endswith('security_headers.py')})
save('quality.json',{'final':quality,'no_new_suppression':True,'initial_logger_error_catcher_BLE001_preserved_privately':True,'logger_exception_uses_explicit_exc_info_None_and_caplog_proves_no_traceback_or_values':True,'original_RED_test_style_not_rewritten':True})
acl=json.loads((P/'ACL-final.private.json').read_bytes());assert acl['parent_DACL_protected']and acl['unexpected_allow_or_deny_rules']==0
save('private-ACL.json',{k:v for k,v in acl.items()if k!='parent_SDDL'}|{'parent_SDDL_SHA256':sha(acl['parent_SDDL'].encode()),'execution':'Exact inspected .ps1 executed via scriptblock, no execution-policy change. Initial ACL set by tool before payload; no initial SDDL snapshot retained.'})
attrs=[]
for p in sorted(P.rglob('*')):
 if p.is_file():
  assert not p.is_symlink();st=p.stat();attrs.append({'relative_private_path':p.relative_to(P).as_posix(),'bytes':st.st_size,'SHA256':sha(p.read_bytes()),'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'windows_file_attributes':getattr(st,'st_file_attributes',None)})
save('private-retention-bindings.json',{'files':attrs,'scope':'Actual retained captures and synthetic SQLite/pytest data under this protected parent only. No claim about unrelated global Temp/isolation directories.','RAW_XML_original_bytes_retained':True,'PowerShell_initial_node_capture_stream_bytes_claimed_RAW':False})
save('attempts-and-limits.json',{'SEC21_first_prefixed_only_author_patch':'6FAIL/5PASS retained; router closure template is unprefixed in the current FastAPI. Finite declared+mounted route templates fix the same assertions.','SEC22_first_logger_error':'Functional28+10PASS; one new BLE001 quality diagnostic, retained, no noqa.','SEC22_logger_exc_info_False':'2PASS+2FAIL strict LogRecord.exc_info is None assertions. No traceback/values were emitted, but exact criterion failed. Changed only product to explicit None, same4PASS.','viewer':'Initial own HTTP12:9PASS,2realSEC22RED,1fixture-contract expectation failure. Exact inverse adapts only API OWNER403 versus SaaS viewer200; original retained.','initial_diagnostic_create_app':'One inline inspection without migrated fixture aborted missing application table; tool output only, no original RAW capture retained; not a product defect.','driver_revisions':'Initial RED driver and affected-maintained driver retained exactly in prior RED prefixes. Current actual driver retained here. Earlier closed-write driver revisions were not separately retained before editing; exact argv, test/source snapshots and capture bytes survive. No reconstructed driver is labelled execution RAW.','initial_Node_stdout':'First7case run captured by PowerShell redirection in files named RAW; encoding can be PowerShell-specific. Do not treat these as byte-exact process stdout. All66 cases subsequently captured with subprocess bytes and quiet photographs.','no_PG':'No PG SQL, private SQL profile, lease creation or return in this task. ROOT retained the PG55483 lease throughout.','excluded':'Pure domain fad3 already reviewed; no broad repeat. R31 legacy Storage remains known and outside this review. No native Chrome, VM, Redis, Desktop, live provider, external email or dependency installation.','publication_scanner':'Unchanged scanner119 and additional JWT guard only; no fresh full gitleaks scan/globalR05PASS.'})
limits=json.loads((O/'attempts-and-limits.json').read_bytes());limits['initial_sealer_RAW_equality']='First unpublished seal rejected RAW==Git on nutrition_http.py:66CRLF observed versus GitLF. Unpublished partial proof and actual failing driver retained privately. Final RAW preimage is preserved separately; LF inverse and AST are exact, and no execution RAW was normalized or reconstructed.';save('attempts-and-limits.json',limits)
(O/'drivers').mkdir(exist_ok=True)
for source,dest in [('metodobase-sec-nutrition35-api-peer-run-20261019.py','current-replay.py'),('metodobase-sec-nutrition35-node-peer-run-20261019.py','node-replay.py'),('metodobase-sec-nutrition35-api-final-acl-20261019.ps1','final-acl.ps1'),('metodobase-sec-nutrition35-api-peer-red-seal-20261019.py','seal-SEC21-RED.py'),('metodobase-sec-nutrition35-header-red-seal-20261019.py','seal-SEC22-RED.py'),('metodobase-sec-nutrition35-api-peer-seal-20261019.py','seal.py')]:
 (O/'drivers'/dest).write_bytes((T/source).read_bytes())
review='''Technical API/UI35 review begins on frozen ROOT f7c11d (55a backend, QA20 dfab, QA22 e0ca, UI816 lineage verified). Independent review found SEC21 and SEC22. Authorization then explicitly made this reviewer the author of the narrow corrections. This seal is author validation for those corrections; ROOT independent peer remains required. It is not global35 acceptance or clinical/legal certification.

SEC21: original immutable21b224 canary gives4RED+2controlsPASS across both real-auth HTTP factories when rejected list envelopes reflect submitted declaration values. RED f7adf67f preserves the initial source and original captures. CDF fixes only NutritionRoute through a finite method/template set for profile writes, regardless of JSON shape; it does not accept invalid envelopes or change DTOs. Both declared and mounted templates are explicit because current FastAPI router closures preserve unprefixed templates. The initial prefix-only patch remains a failed author attempt. The same6 plus5 boundary controls pass11/11: nested arrays, scalar/null/type/extra-field and truncated JSON errors are bounded; read query validation detail and neighbors keep their contract.

SEC22: original unexpected profile-read injection gives2RED solely for absent private headers on opaque500; no marker reflection or third-party disclosure was observed. RED fe020d6b retains those exact functions and the single viewer-read framing correction with a full inverse. The generic boundary now returns500 with no-store/no-referrer and existing request correlation, logs only the exception class with explicit exc_info=None, and never emits an ACK, ordinary conflict or error string. Standard read validation keeps its detail and receives private headers. A finite matcher covers client list/detail and the three personal/gym profile/generation APIs plus one slash alias, including405/404 for unsupported or intentionally unmounted personal APIs. No extra segments, nearby prefixes, SSR, static paths, new CSP policy, auth grants or API surface are added. Exact positive and negative HTTP controls pass. The final4 replay passes both original500 cases and strict logging checks; previous False-versus-None LogRecord failures remain preserved and no assertion was changed.

Independent controls establish real Viewer mutation denial, current SV revocation, parent-OFF denial, rejection of body authority fields, and no generation side effects. A real PDF pending publication is followed by a controlled deactivation between publication steps; ready association/plan creation is rejected and the pending object remains unreadable, with reservation compensation. This is controlled SQLite scheduling, not a claim of observed PG lock concurrency. Existing maintained HTTP, corrupt-read and SSR/JS bridge cases pass34/34 before the SEC22 patch; selected original QA foreign/anonymous/portfolio and personal-export cases pass3/3 after it. Export includes the exact own declaration and excludes professional portfolios. No assertions or original tests from ROOT/FE/QA are modified. Actual source and retained cases define the epoch; repeated executions are not unique extra cases.

UI source9paths remains LF-equivalent to UI816. New declaration rendering uses textContent/created DOM, fixed Jinja keys, detached state and explicit confirmation; no new declaration Storage/log sink was identified. Actual Api.nutrition+controller run through59 maintained and7 independent Node controls, all66PASS. Own controls cover persistent-subject change before render, wrong client binding, account replacement during JSON parsing, refresh-pair replacement, single-dispatch401/503 handling without refresh/readback/response-text rendering, and UTF8 byte caps before dispatch. Transports and minimal DOM are synthetic RAM seams: this is not browser/layout/Chrome, real HTTP transport or live-provider acceptance. R31 legacy credential Storage is a known separate task and is neither closed nor attributed to this35 patch.

Final product d47447b has three product paths and one new maintained test, atop SEC21 CDF and immutable proof commits. Full GitLF byte inverses recover the CDF NutritionRoute and security middleware. Executed NutritionRoute retains66CRLF and its own RAW hash/preimage; its LF inverse and Python AST match Git exactly. No execution RAW is normalized retroactively. Original21b224 remains byte exact and SEC22 functions remain AST exact. Before/after snapshots are quiet for92 package METADATA, both Python binaries, Node and the recorded source scope in every phase; pip check0. New route/matcher/test Ruff0. Security middleware keeps its exact baseline I001/F541/BLE001 codes; no new suppression or assertion relaxation. Logs/RAW/XML stay private under the protected parent, with structural attributes and hashes. Initial SDDL and some earlier driver revision preimages were not separately retained; their precise limitations are recorded rather than reconstructed as RAW. Unchanged scanner119 plus JWT guard protect publication, not a full secret-scan certification.

No PG SQL/private SQL profile, lease operation, Chrome/VM/Redis/Desktop work, external email/provider call or dependency install occurs here. ROOT owns PG throughout and separately investigates QA23 connection handoff. All PG/RLS/pool concurrency and ROOT subsequent integration results remain outside this seal. The branch preserves bb9046 and both prior cf32/c3a4 originals; no changes are made to ROOT, MAIN or the R31/R27 working trees.
'''
(O/'review.md').write_bytes(review.encode())
save('source.json',{'frozen35':BASE,'SEC21_RED':'f7adf67faabd13113961c7f219d507061018e69c','SEC21_fix':CDF,'SEC22_RED':'fe020d6b3928a8e0d0e0b40cbd2b987a7b5dc26d','SEC22_fix':FINAL,'role':'Independent finder of SEC21/22, then explicitly authorized focal author; independent review of unchanged ROOT/FE35 controls only','final_author_validation':'PASS focal executed cases; ROOT independent peer pending','own_unique_HTTP_or_matcher_cases':30,'own_unique_Node_cases':7,'maintained_HTTP_UI_cases_replayed_before_SEC22':34,'QA_foreign_export_cases_replayed_after_SEC22':3,'maintained_Node_cases':59,'global35_or_clinical_legal_acceptance':False,'PG_SQL_or_private_profile':False,'R31_Storage_closed':False,'source_packages92_bothPython_Node_quiet_each_phase':True,'pip_exit_before_after':0,'RAW_driver_limitations_recorded':True,'product_paths':changed})
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('public-safety-scan.json',{'scanner119_AST_SHA256':digest,'unchanged':True,'additional_JWT_guard':True,'all_public_files_pass':True,'fresh_full_gitleaks_scan':False})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in O.rglob('*'):
 if p.is_file():
  raw=p.read_bytes();ns['scan'](raw,p.name);assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',raw),p.name
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'final_product':FINAL,'verdict':'Author focal validation only; ROOT peer pending'}))
