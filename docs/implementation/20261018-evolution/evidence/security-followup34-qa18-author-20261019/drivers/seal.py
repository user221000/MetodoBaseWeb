from pathlib import Path,PurePosixPath
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-followup34-qa18-author-private-20261019';PREFIX='docs/implementation/20261018-evolution/evidence/security-followup34-qa18-author-20261019';O=R/PREFIX
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());load=lambda n:json.loads((O/n).read_bytes())
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
BASE='e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee';PRODUCT='41dc5ae6e9c02d9b846685428df1fc722aa4cca7';assert git('rev-parse','HEAD').decode().strip()==PRODUCT and git('rev-parse','HEAD^').decode().strip()==BASE
assert load('sql-errors-summary.json')['outcomes']=={'passed':12,'failure':0,'error':0,'skipped':0}
assert load('maintained-summary.json')['outcomes']=={'passed':12,'failure':0,'error':0,'skipped':0}
assert load('sql-errors-before.json')==load('sql-errors-after.json') and load('maintained-before.json')==load('maintained-after.json')
final=load('maintained-after.json')
for name,digest in final['source'].items():assert sha((R/name).read_bytes())==digest
packages={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()}
assert packages==final['packages'] and len(packages)==92
assert sha(Path(sys.executable).read_bytes())==final['python'] and sha(Path(sys._base_executable).read_bytes())==final['base_python']
canary=R/'tests/test_security_followup34_sql_errors_peer.py';assert sha(canary.read_bytes())=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'
service='web/services/followup_tasks.py';maint='tests/test_followup34_sql_error_classification.py'
pre=R/'docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019/preimage/followup_tasks.py'
assert git('show',BASE+':'+service)==pre.read_bytes()
patch=git('diff','--binary','--no-ext-diff',BASE,PRODUCT,'--',service);inverse=subprocess.run(['git','apply','--reverse','--check','-'],cwd=R,input=patch,capture_output=True);assert inverse.returncode==0
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED)as z:
 info=zipfile.ZipInfo('product-change.patch',date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,patch)
assert zipfile.ZipFile(io.BytesIO(buffer.getvalue())).read('product-change.patch')==patch
old_patch=O/'product-change.patch'
if old_patch.exists():
 assert old_patch.read_bytes()==patch;old_patch.unlink()
(O/'product-change.patch.zip').write_bytes(buffer.getvalue())
quality=load('quality-baseline-binding.json');quality['initial_quality_attempt']='Initial maintained copy exposed existing import framing F401/F811/I001; explicit import reexports then exposed PLC0414. Shared fixture-module registration resolved all test diagnostics. All attempt RAW retained; product baseline rules unchanged.';save('quality-baseline-binding.json',quality)
observations=O/'sql-error-observations';observations.mkdir(exist_ok=True)
for path in sorted((P/'SQL-error-receipts').glob('*.json')):
 value=json.loads(path.read_bytes());assert value['no_partial_event_or_projection'] and value['opaque_private_error'] and value['no_false_ACK'];(observations/path.name).write_bytes(path.read_bytes())
assert len(list(observations.glob('*.json')))==10
(O/'drivers').mkdir(exist_ok=True)
for src,dst in [('metodobase-sec-followup34-qa18-run-20261019.py','prepare-exact-replay.py'),('metodobase-sec-followup34-qa18-run-executed-20261019.py','exact-replay.py'),('metodobase-sec-followup34-qa18-final-replay-20261019.py','maintained-replay.py'),('metodobase-sec-followup34-qa18-final-acl-20261019.ps1','final-acl.ps1'),('metodobase-sec-followup34-qa18-seal-20261019.py','seal.py')]:
 (O/'drivers'/dst).write_bytes((T/src).read_bytes())
acl=json.loads((P/'acl-final.private.json').read_bytes());assert acl['protected'] and acl['parent_SDDL_unchanged'];save('private-ACL.STRUCTURAL.json',{**acl,'initial_SDDL_SHA256':sha((P/'acl-initial.private.txt').read_bytes())})
attrs=[]
for p in sorted(P.rglob('*')):
 if p.is_file():
  assert not p.is_symlink();h=hashlib.sha256()
  with p.open('rb')as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  st=p.stat();attrs.append({'private_relative_path':p.relative_to(P).as_posix(),'bytes':st.st_size,'SHA256':h.hexdigest(),'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'windows_file_attributes':getattr(st,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Original exact replay and maintained replay stdout/stderr/XML, all quality attempts, synthetic fixture files, structural observations and ACL; original RAW bytes retained privately, not reconstructed.','files':attrs})
review='''QA-18 author validation, independent ROOT/QA review pending. RED commit e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee remains immutable; this fix is a separate commit. It corrects the classification of unknown IntegrityError and arbitrary SQL error text containing locked. Unknown writes return503 followup_unconfirmed after confirmed rollback; uncertain rollback remains503. This is response classification and resource robustness under fault injection, without a demonstrated remote exploit or authorization/data disclosure.

Only web/services/followup_tasks.py changes product behavior. Known409 outcomes require driver diagnostics: PostgreSQL55P03 for lock conflict;23505 plus exact open-cause constraint;23514 plus either exact existing trigger message. SQLite BUSY/LOCKED uses native integer error codes including extended codes; known unique/trigger conflicts require the native IntegrityError, exact extended code and exact diagnostic. Unknown constraints/messages/codes do not become ordinary409. No retry, readback, authority, schema or lock-order change.

The original12-case canary SHA c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce is byte-identical: original8PASS/4RED becomes12PASS with zero errors/skips. Both HTTP factories retain real registration/login/MFA, no partial Task/Event, no false ACK, opaque private errors, uncertain rollback503, actual SQLite BUSY409 and explicit retry after fault removal. The maintained test replays those same12 cases once more, not12 new unique cases. Its original test functions and assertions are AST-exact; only shared fixture import registration and a pytest-owned structural receipt directory are added.

Each replay has its own source/distribution/Python before-after photos. All92 installed distribution versions and METADATA and both Python binaries are unchanged. No dependencies installed. Pip check before/after0. Existing nine service Ruff diagnostics remain identical by rule; maintained test Ruff0. Initial import-format findings and both refinement attempts are retained as original private RAW, with no weakened business assertion. Reverse Git patch check verifies the full product inverse against the sealed RED preimage.

No PostgreSQL profile or SQL was used. Backend34 PostgreSQL/runtime, the prepared independent PG hypotheses, global Backend34 acceptance and the separate client SSR matcher remain outside this author validation. ROOT and QA must review the product fix independently because this reviewer became its author. Original RED RAW/evidence was not overwritten. New RAW/XML and quality captures remain under current-user/SYSTEM ACL; synthetic pytest fixture subtrees explicitly account for OWNER RIGHTS/Administrators. Public artifacts contain structural metadata and code, scanned using unchanged checkpoint119 scanner plus JWT guard. No VM, Chrome, Redis or live provider.
'''
(O/'review.md').write_bytes(review.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('source.json',{'product_commit':PRODUCT,'base_RED_commit':BASE,'original_product_commit':'80b9a44adf4daae160673b4d86a58cb06f809071','criterion':'QA-18','role':'author validation, independent acceptance pending','product':{service:sha((R/service).read_bytes())},'maintained_test':{maint:sha((R/maint).read_bytes())},'original_canary_SHA256':sha(canary.read_bytes()),'unique_cases':12,'before_PASS_RED':[8,4],'after_PASS':12,'maintained_copy_same_twelve_PASS':12,'errors':0,'skips':0,'product_full_inverse_git_reverse_check':True,'source_92_metadata_bothPython_quiet_per_phase':True,'pip_before_after_exit':0,'PG_executed':False,'PG_profile_read':False,'global_Backend34_acceptance':False,'scanner119_AST_digest':digest})
save('public-safety-scan.json',{'scanner119_AST_digest':digest,'scanner119_unchanged':True,'additional_JWT_guard':True,'all_public_files_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in O.rglob('*'):
 if p.is_file():
  raw=p.read_bytes();ns['scan'](raw,p.relative_to(O).as_posix());assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',raw),p.name
for name in [service,maint]:ns['scan']((R/name).read_bytes(),name)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'service_SHA256':sha((R/service).read_bytes()),'test_SHA256':sha((R/maint).read_bytes()),'author_validation_only':True}))
