from pathlib import Path, PurePosixPath
import ast, hashlib, importlib.metadata, io, json, re, subprocess, sys, tarfile, zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-qa23-peer-private-20261020';BASE='4834c3c2fb632701275498d56196ac4209086298';AUTHOR='48ba43d8'
O=R/'docs/implementation/20261018-evolution/evidence/security-qa23-handoff-independent-20261020';O.mkdir(exist_ok=True);(O/'.gitattributes').write_bytes(b'* -text\n')
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
summary=json.loads((P/'summary.json').read_bytes());assert summary['outcomes']=={'passed':33,'failure':0,'error':0,'skipped':0}and summary['own_cases']==8
before=json.loads((P/'before.json').read_bytes());after=json.loads((P/'after.json').read_bytes());assert before==after
own='tests/test_security_qa23_handoff_peer.py';original=(P/'original-own-canary-before-import-style.RAW.py').read_bytes();current=(R/own).read_bytes();assert ast.dump(ast.parse(original))==ast.dump(ast.parse(current))
assert sha(original)==after['source'][own]
for n,d in after['source'].items():
 if n!=own:assert sha((R/n).read_bytes())==d,n
pkgs={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()};assert pkgs==after['packages']and len(pkgs)==92
assert sha(Path(sys.executable).read_bytes())==after['python']and sha(Path(sys._base_executable).read_bytes())==after['base_python']
for n in ['before.json','after.json','summary.json','cases.STRUCTURAL.json','argv.json','pip-before.RAW.log','pip-after.RAW.log','style-inverse.json']:(O/n).write_bytes((P/n).read_bytes())
(O/'original-own-canary-before-import-style.RAW.py').write_bytes(original)
rows=[]
for path in ['web/services/gym_generation_quota.py','web/routes/planes.py','api/routes/planes.py','tests/test_gym_generation_handoff.py','tests/integration_nutrition35_postgres.py']:
 blob=git('show',BASE+':'+path);auth=git('show',AUTHOR+':'+path);raw=(R/path).read_bytes();assert blob==auth and raw.replace(b'\r\n',b'\n')==blob and ast.dump(ast.parse(raw))==ast.dump(ast.parse(blob))
 rows.append({'path':path,'current_RAW_SHA256':sha(raw),'frozen_GitLF_SHA256':sha(blob),'author_commit_LF_exact':True,'RAW_equals_GitLF':raw==blob,'LF_inverse_and_AST_exact':True,'CRLF_count':raw.count(b'\r\n'),'RAW_reconstructed':False})
save('source-bindings.json',rows)
for path in ['web/routes/planes.py','api/routes/planes.py']:
 raw=(R/path).read_text();assert raw.count('request_key, stable_result=True)')==1
assert git('diff','--name-only',BASE,'--','web','api','core','src','config')==b''
quality=subprocess.run([sys.executable,'-m','ruff','check',own,'--output-format','json'],cwd=R,capture_output=True);(P/'ruff-final.stdout.RAW.json').write_bytes(quality.stdout);(P/'ruff-final.stderr.RAW.log').write_bytes(quality.stderr);assert quality.returncode==0
save('quality.json',{'initial_own_I001_import_wrap':1,'final_own_Ruff_diagnostics':len(json.loads(quality.stdout)),'final_exit':0,'whole_module_AST_exact_after_import_wrap':True,'function_or_assertion_changes':False,'new_suppressions':False,'product_changes':False})
acl=json.loads((P/'ACL-final.private.json').read_bytes());assert acl['parent_DACL_protected']and acl['initial_parent_SDDL_unchanged']and acl['unexpected_allow_or_deny_rules']==0
save('private-ACL.json',{k:v for k,v in acl.items()if k!='parent_SDDL'}|{'parent_SDDL_SHA256':sha(acl['parent_SDDL'].encode()),'initial_snapshot_SHA256':sha((P/'initial-SDDL.private.txt').read_bytes()),'test_isolation_root_under_protected_parent_before_payload':True})
save('closure-framing.json',{'initial_checker_rejected_relocated_pytest_cache':True,'exact_scope_adjusted':'Only pytest_cache metadata now receives the same OWNER_RIGHTS/Administrators fixture allowance as pytest temporary directories. Actual RAW captures and code remain current-user/SYSTEM only.','ACL_permissions_changed_to_close_check':False,'unexpected_or_broad_groups':0,'initial_checker_driver_and_unpublished_partial_seal_retained_privately':True,'initial_missing_ACL_receipt_aborted_sealer':True})
attrs=[]
for p in sorted(P.rglob('*')):
 if p.is_file():
  assert not p.is_symlink();s=p.stat();attrs.append({'private_relative_path':p.relative_to(P).as_posix(),'bytes':s.st_size,'SHA256':sha(p.read_bytes()),'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'windows_attributes':getattr(s,'st_file_attributes',None)})
save('private-original-bindings.json',attrs)
(O/'drivers').mkdir()
for src,dst in [('metodobase-sec-qa23-handoff-peer-run-20261020.py','replay.py'),('metodobase-sec-qa23-peer-final-acl-20261020.ps1','final-acl.ps1'),('metodobase-sec-qa23-handoff-peer-seal-20261020.py','seal.py')]:(O/'drivers'/dst).write_bytes((T/src).read_bytes())
review='''Independent focal technical acceptance of QA23 on frozen ROOT4834c3c. Product paths are LF/AST exact to ROOT author48ba43d8: both HTTP factories explicitly request stable_result=True; the quota service captures only scalar id/status/result_json inside the transaction and returns the immutable handoff only after db.commit returns. Flush occurs before capturing newly generated IDs. Both new and completed-replay branches retain the same commit boundary. There is no retry, alternate result adoption, new auth/billing decision, SQL RPC, migration, worker or publication change. Legacy internal callers keep the tracked ORM return contract when stable_result=False; the no-checkout claim is limited to the new HTTP stable view.

33PASS, zero failure/error/skip:4 author handoff tests,8 original selected quota cases,13 original migrated SQLite35 HTTP cases and8 independent cases. The8 own cases use a real SQLite QueuePool of1 with overflow0 for reserved/completed handoffs and expire_on_commit True/False. After closing the Session, status/id/result_json reads issue zero SQL and retain zero checkouts, and a simulated worker can obtain the one connection. The DTO is frozen and its repr omits the synthetic replay payload. Two completed-replay commit-ACK-loss cases propagate uncertainty instead of returning cached success; a later explicit request can read the same durable result with one plan/reservation. Two before-durability failures do not return the constructed snapshot; the caller explicitly rolls back and no reservation/plan remains. This proves the handoff and uncertainty boundary in SQLite; it is not PG/RLS/lock/pool-runtime acceptance.

The4 author cases additionally preserve new-reservation lost-ACK semantics, with no retry or false refund. The original8 quota cases cover per-client/day and global/day/month limits, exact replay and changed-payload conflict, idempotent release, crash after durable publication and client binding. The13 real-auth HTTP cases retain declaration/quota/worker-recheck/PDF stale-publication behavior and personal scope. Unit fixtures persist synthetic accounts and issue local test tokens; only the HTTP fixture cases are claimed as real password/MFA HTTP authentication. Clinical or regulatory approval, broad35 acceptance and the separate R31 legacy Storage task remain outside this technical review.

No product or author-test edits. The new peer test had one I001 import-wrap diagnostic; its exact executed preimage is retained and the formatted final file has an identical whole-module AST, with no function/assertion changes. Ruff0, no new suppression. Recorded source/package92 METADATA and both Python binaries remain quiet before/after the33-case phase; final package/binary hashes are rechecked and pip check0. GitLF and observed CRLF hashes are explicit and AST exact, with no reconstructed execution RAW. Original stdout/stderr/XML remain private with hashes and attributes. The parent DACL is protected and identical to the snapshot taken before payload; all isolation/SQLite data is under that parent. Publication uses unchanged scanner119 plus JWT guard, not a fresh full gitleaks scan. No PG SQL or private profile, lease, browser/Chrome, VM, Redis, Desktop, live provider/email or dependency install. ROOT owns PG; no ROOT result is counted as this peer's execution. Prior API35/SEC21/22 and34 branches and cf32/c3a4 originals remain preserved.
'''
(O/'review.md').write_bytes(review.encode())
save('source.json',{'reviewed_commit':BASE,'author_product_commit':git('rev-parse',AUTHOR).decode().strip(),'verdict':'ACCEPT focal QA23 stable HTTP handoff, SQLite and static scope only','role':'independent peer of ROOT QA23; no product edits','cases':33,'author_handoff_cases':4,'original_quota_cases':8,'original_HTTP35_cases':13,'own_cases':8,'failures_errors_skips':0,'own_executed_SHA256':sha(original),'own_final_SHA256':sha(current),'whole_AST_exact_import_wrap_only':True,'packages':92,'pip_before_after_exit':0,'source_packages_bothPython_quiet':True,'PG_SQL_private_profile_or_lease':False,'global35_acceptance':False,'R31_Storage_acceptance':False})
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f';ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('public-safety-scan.json',{'scanner119_AST_SHA256':digest,'unchanged':True,'JWT_guard':True,'files_pass':True,'fresh_full_gitleaks_scan':False});save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in list(O.rglob('*'))+[R/own]:
 if p.is_file():
  b=p.read_bytes();ns['scan'](b,p.name);assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',b)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'verdict':'ACCEPT focal QA23 only'}))
