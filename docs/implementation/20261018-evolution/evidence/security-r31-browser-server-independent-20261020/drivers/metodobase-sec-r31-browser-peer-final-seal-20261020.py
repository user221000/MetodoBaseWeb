from pathlib import Path, PurePosixPath
import ast, hashlib, importlib.metadata, io, json, re, subprocess, sys, tarfile, zipfile

R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r31-browser-peer-private-20261020'
BASE='8a427c310ec9b5ff37983ac9bdff354343be1708';PRODUCT='18083901812b23e5862678da30f8845f9733c0be';RED='984c9433d157886ee824458281e0878c359898e9'
O=R/'docs/implementation/20261018-evolution/evidence/security-r31-browser-server-independent-20261020'
sha=lambda b:hashlib.sha256(b).hexdigest();git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
phases=['initial-frozen50-and-admission','independent-transport-initial','independent-finite-boundaries-before','frozen-fix-complete-focused']
expected=[(52,51,1),(24,24,0),(18,12,6),(106,106,0)]
for phase,(total,passed,failed) in zip(phases,expected):
 d=P/phase;s=json.loads((d/'summary.json').read_bytes());assert s['cases']==total and s['outcomes']=={'passed':passed,'failure':failed,'error':0,'skipped':0};assert (d/'before.json').read_bytes()==(d/'after.json').read_bytes()
final=json.loads((P/phases[-1]/'after.json').read_bytes())
for n,digest in final['source'].items():assert sha((R/n).read_bytes())==digest,n
pkgs={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()};assert pkgs==final['packages'] and len(pkgs)==92
assert sha(Path(sys.executable).read_bytes())==final['python'] and sha(Path(sys._base_executable).read_bytes())==final['base_python']
own=['tests/test_security_r31_browser_admission_peer.py','tests/test_security_r31_browser_transport_peer.py','tests/test_security_r31_browser_boundaries_peer.py']
assert sha((R/own[0]).read_bytes())=='689a09fd65afe8746ca37e3c3c307eed34ae4f39b18a66021d3168807a3ac0b0'
assert (R/own[0]).read_bytes()==git('show',RED+':'+own[0])
assert sha((R/own[2]).read_bytes())==json.loads((P/phases[2]/'after.json').read_bytes())['source'][own[2]]
original=(P/phases[1]/'test_security_r31_browser_transport_peer.executed.RAW.py').read_bytes();current=(R/own[1]).read_bytes()
old=b'    with caplog.at_level(logging.ERROR, logger="web.browser_session"):\n        with monkeypatch.context() as patch:\n            patch.setattr(auth, "rotar_refresh_token", lost_ack)\n            result = fixtures.post(browser, "/api/auth/refresh")\n'
new=b'    with caplog.at_level(logging.ERROR, logger="web.browser_session"), monkeypatch.context() as patch:\n        patch.setattr(auth, "rotar_refresh_token", lost_ack)\n        result = fixtures.post(browser, "/api/auth/refresh")\n'
assert current.count(new)==1 and current.replace(new,old)==original
assert [ast.dump(n)for n in ast.walk(ast.parse(original))if isinstance(n,ast.Assert)]==[ast.dump(n)for n in ast.walk(ast.parse(current))if isinstance(n,ast.Assert)]
acl=json.loads((P/'ACL-final.private.json').read_bytes());assert acl['parent_DACL_protected'] and acl['initial_parent_SDDL_unchanged'] and acl['unexpected_allow_or_deny_rules']==0
O.mkdir(exist_ok=False);(O/'.gitattributes').write_bytes(b'* -text\n');save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
for phase in phases:
 d=P/phase;out=O/phase;out.mkdir()
 for n in ['before.json','after.json','summary.json','cases.STRUCTURAL.json','argv.json','pip-before.RAW.log','pip-after.RAW.log']:(out/n).write_bytes((d/n).read_bytes())
(O/'transport-first-executed.RAW.py').write_bytes(original)
save('style-inverse.json',{'initial_Ruff_SIM117':1,'exact_inverse':'One nested pair of context managers combined into one with statement, with same order/extent; no assertion or behavior change.','executed_original_SHA256':sha(original),'current_SHA256':sha(current),'complete_text_inverse_exact':True,'all_assertion_ASTs_exact':True,'corrected_fault_test_replayed_before_fix':2,'complete_current_module_replayed_after_fix':24})
paths=['web/browser_session.py','web/routes/auth.py','web/routes/mfa.py','web/routes/google_link.py','web/routes/team.py','web/middleware/security_headers.py','docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_WIRE.json','web/middleware/tenant.py','tests/test_browser_session31_transport.py','tests/test_browser31_google_compat.py','tests/test_browser31_pre_auth_boundary.py']
bindings=[]
for n in paths:
 raw=(R/n).read_bytes();blob=git('show',BASE+':'+n);assert raw.replace(b'\r\n',b'\n')==blob
 if n.endswith('.py'):assert ast.dump(ast.parse(raw))==ast.dump(ast.parse(blob))
 bindings.append({'path':n,'RAW_SHA256':sha(raw),'GitLF_SHA256':sha(blob),'RAW_equals_Git':raw==blob,'LF_inverse_exact':True,'CRLF_count':raw.count(b'\r\n'),'RAW_reconstructed':False})
assert [n for n in git('diff','--name-only',PRODUCT,BASE,'--','web','api','src','core','config').decode().splitlines()]==['web/middleware/tenant.py']
for n in paths[:7]:assert git('show',PRODUCT+':'+n)==git('show',BASE+':'+n)
before_ast=ast.parse(git('show',PRODUCT+':web/middleware/tenant.py'));after_ast=ast.parse(git('show',BASE+':web/middleware/tenant.py'))
for name in ['__init__','_extract_tenant','get_current_tenant']:
 a=next(n for n in ast.walk(before_ast)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name==name);b=next(n for n in ast.walk(after_ast)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name==name);assert ast.dump(a)==ast.dump(b)
save('source-bindings.json',bindings)
quality=subprocess.run([sys.executable,'-m','ruff','check',*own,'--output-format','json'],cwd=R,capture_output=True);(P/'ruff-final.stdout.RAW.json').write_bytes(quality.stdout);(P/'ruff-final.stderr.RAW.log').write_bytes(quality.stderr);assert quality.returncode==0
save('quality.json',{'final_own_Ruff_exit':0,'final_own_diagnostics':len(json.loads(quality.stdout)),'new_suppressions':False,'product_edited_by_peer':False,'original689a_and_boundary_assertions_unchanged':True})
save('private-ACL.json',{k:v for k,v in acl.items()if k!='parent_SDDL'}|{'parent_SDDL_SHA256':sha(acl['parent_SDDL'].encode()),'initial_snapshot_SHA256':sha((P/'initial-SDDL.private.txt').read_bytes()),'all_test_isolation_under_private_parent':True})
attrs=[]
for p in sorted(P.rglob('*')):
 if p.is_file():
  assert not p.is_symlink();s=p.stat();attrs.append({'private_relative_path':p.relative_to(P).as_posix(),'bytes':s.st_size,'SHA256':sha(p.read_bytes()),'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'windows_attributes':getattr(s,'st_file_attributes',None)})
save('private-original-bindings.json',attrs)
(O/'drivers').mkdir()
for n in ['metodobase-sec-r31-browser-peer-run-20261020.py','metodobase-sec-r31-browser-transport-run-20261020.py','metodobase-sec-r31-browser-fix-replay-run-20261020.py','metodobase-sec-r31-browser-peer-final-acl-20261020.ps1','metodobase-sec-r31-browser-peer-final-seal-20261020.py']:(O/'drivers'/n).write_bytes((T/n).read_bytes())
review='''Independent focused R31 server review on ROOT product180839, author testsb297 and SEC24 fix8a427. The initial52-case run preserves50 frozen author PASS, the independent SaaS ordering PASS and original API ordering RED. The original canary689a delegates genuine persisted bearer verification, with no identity override. Before that failed assertion,403/private headers/unchanged cookie/valid old proof are observed. Its later SQL-zero assertion is not reached on the failing API case; no numerical SQL count is claimed there. This is strict admission-order failure, not authentication bypass, proof consumption or external disclosure.

ROOT owns the correction: only TenantMiddleware admission and imports change from the seven-path R31 product. With the browser header present and a finite cookie-capable path or its one-slash alias, admit runs before optional tenant extraction. Its rejection is returned with opaque existing code/detail and private headers. Configuration failure, Origin/header/content-type/method/query failures cannot authenticate or mutate refresh proof first. No-header and adjacent paths keep normal extraction; valid requests still follow the existing tenant/RBAC path. The __init__, extractor and context accessor ASTs are exact; existing ContextVar finally is unchanged. No broad public-prefix exclusion or authorization relaxation is added.

Independent additional24 cases pass before the fix. They verify cookie accountA remains distinct from genuine bearerB, refresh and logout affect onlyA, duplicate Cookie header lines cannot select a proof, HTTP-dev cookie cannot refresh HTTPS, cookie alone cannot read actual client resources or replace the legacy JSON refresh body, and malformed closed bodies cannot consume the valid proof or reflect private marker input. Explicit legacy migration replay invokes the existing reuse defense for its owner without revokingB. Lost ACK is injected AFTER actual durable rotation: exactly one call, old proof revoked, fresh proof exists only in RAM and is not returned/adopted,503 without tokens or confirmation, expired client cookie and class-only log with no exception value/traceback. This exercises truthful uncertainty, not rollback or prevention of a completed rotation. Actual nonproduction HTTP loopback emits the separate HttpOnly/Strict/Path cookie without Secure or Domain; synthetic HTTPS emits the secure Host cookie in original author cases.

Six of16 finite-boundary cases are RED before8a427, with10 controls PASS; the separate2 corrected-style ACK cases PASS. The same unmodified16 pass afterward. They cover slash, duplicate/empty browser header, content type and query, plus legacy/no-header, adjacent path and double-slash redirect controls; the latter preserve genuine API verifier execution and exact redirect framing. Final focused106/106PASS,0failure/error/skip:50 original author criteria,14 author pre-tenant cases,2 immutable689a cases,24 own transport cases and16 own boundaries. There are42 unique independent cases, not a sum of repeated executions. Author Google cases use signed RSA/JWKS verification with provider transport mocked only; no Google network occurs. Real HTTP account/password/MFA authentication is inherited from frozen migrated SQLite35 fixtures. The14 author pre-tenant cases additionally observe SQL0 and verifier0 for rejected variants, in both factories. No PG/RLS/runtime-pool proof is claimed.

Static review confirms opt-in only; access remains bearer authority and legacy JSON is unchanged without the header. Fixed canonical BASE_URL origin is independent of caller Host/forwarding; HTTP is restricted to nonproduction loopback. Browser refresh/migrate/logout use bounded closed JSON and exact current cookie name, with duplicate ambiguity rejected. Server pair adaptation validates the real signed refresh expiry and bounds cookie lifetime to the minted proof. MFA202 emits challenge without pair and expires the old cookie; successful MFA/Google credential-change ACKs retain body schema. Admission runs before route dependencies and, after8a427, before the optional middleware verifier. Cookie does not replace factor, current role/SV/parent or general resource authorization. No new DDL or provider/credential contract is introduced by this transport review.

The only own style correction combines two nested context managers in their original order/extent. Original executed bytes are retained, exact inverse is checked and every assertion AST is identical. Both affected cases replay PASS before8a427, and the entire current module passes after it. Original689a and16 boundary tests are byte exact across before/after. Own Ruff0 and no suppressions. All phase source/92-package METADATA/both Python binaries are quiet, pip check0; final hashes rechecked. RAW/GitLF differences are explicit, original stdout/stderr/XML retained privately with hashes/attributes, no RAW reconstruction. Protected DACL was set before payload and remains identical; only synthetic pytest/cache entries permit their existing OWNER_RIGHTS/Administrators fixture rules. Publication uses unchanged scanner119 plus JWT guard, not a fresh full gitleaks scan.

Acceptance is focal SEC24 and the executed R31 server transport boundaries only. It does not certify frontend RAM/Storage removal, native browser cookie/SameSite enforcement, intertab coordination, all invite-accept/MFA combinations, production Redis, PG/RLS/locking, global R31, clinical or legal compliance. No private SQL profile/PG lease, Chrome/browser, VM, Redis/service start, Desktop, live provider/email, new dependencies or product edit by this peer. ROOT owns product correction; frontend remains separate. Prior a21e/dae93/bb refs and cf32/c3a4 originals remain preserved.
'''
(O/'review.md').write_bytes(review.encode())
save('source.json',{'reviewed_product':PRODUCT,'reviewed_author_tests':'b297df83e855197fd20e6c5b650136d5b19f3f6c','reviewed_SEC24_fix':BASE,'original_RED_seal':RED,'verdict':'ACCEPT focal SEC24 fix and executed R31 server transport; no global R31 acceptance','role':'independent peer; ROOT author of product/fix','final_cases':106,'author_original_cases':50,'author_admission_cases':14,'unique_independent_cases':42,'final_failure_error_skip':0,'before_additional24_PASS':24,'before_boundaries16_PASS':10,'before_boundaries16_RED':6,'source_packages92_bothPython_quiet':True,'pip_check_before_after_exit':0,'PG_SQL_profile_or_lease':False,'global_R31_acceptance':False,'native_browser_or_Storage_claim':False,'own_test_SHA256':{n:sha((R/n).read_bytes())for n in own}})
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f';ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('public-safety-scan.json',{'scanner119_AST_SHA256':digest,'unchanged':True,'JWT_guard':True,'files_pass':True,'fresh_full_gitleaks_scan':False})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in list(O.rglob('*'))+[R/n for n in own]:
 if p.is_file():
  b=p.read_bytes();ns['scan'](b,p.name);assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',b)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'verdict':'ACCEPT focal SEC24/R31 server controls'}))
