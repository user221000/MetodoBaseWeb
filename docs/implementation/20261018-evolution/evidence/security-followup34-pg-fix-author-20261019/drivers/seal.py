from pathlib import Path,PurePosixPath
import ast,hashlib,importlib.metadata,io,json,re,subprocess,sys,tarfile,zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-followup34-author-sec-peer-20261019';PREFIX='docs/implementation/20261018-evolution/evidence/security-followup34-pg-fix-author-20261019';O=R/PREFIX;sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());load=lambda n:json.loads((O/n).read_bytes());git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
PRODUCT='7be9b758b731eb6c5fd96c7ee285b66d57e5920f';FINAL='a4f95fb573149c892ca1ab5d8fbca52abce62bf9';assert git('rev-parse','HEAD').decode().strip()==FINAL and not git('status','--porcelain','--untracked-files=no')
phases=load('phases-summary.json');assert len(phases)==6 and[x['cases']for x in phases]==[4,6,28,5,1,86]and all(x['exit']==0 for x in phases)
for row in phases:assert load(row['phase']+'-before.json')==load(row['phase']+'-after.json')
assert load('manager-before-summary.json')['outcomes']=={'passed':2,'failure':3,'error':0,'skipped':0}and load('manager-after-summary.json')['outcomes']=={'passed':5,'failure':0,'error':0,'skipped':0}
assert load('manager-before-before.json')==load('manager-before-after.json')and load('manager-after-before.json')==load('manager-after-after.json')
photo=load('manager-after-after.json')
for n,h in photo['source'].items():assert sha((R/n).read_bytes())==h
packages={d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()};assert packages==photo['packages']and len(packages)==92
assert sha(Path(sys.executable).read_bytes())==photo['python']and sha(Path(sys._base_executable).read_bytes())==photo['base_python']
original=R/'tests/test_security_followup34_postgres_peer.py';maint=R/'tests/integration_security_followup34_postgres_peer.py';assert original.read_bytes()==maint.read_bytes()and sha(original.read_bytes())=='cf32a69a8049272b1493e4802551c3f487b9f2a92eee019061c711f43e580ce1'
assert sha((R/'tests/test_security_followup34_sql_errors_peer.py').read_bytes())=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'
assert sha((R/'tests/test_followup34_sql_error_classification.py').read_bytes())=='f1a5aea20590b5b479e3639e3f0a03abfbf664c0acd55a074b95b149ad8682be'
target='web/database/alembic/schema_targets/20261019_followup_tasks_postgresql.json';assert sha((R/target).read_bytes())=='d1ebbaf5e9fdd41e1347f108d8f4ebcf4d8f7a88832d3fc8fef0b1faaf5ada80'
oldtargets=git('ls-tree','-r','--name-only','f848256ceac6a8c6a7c2cc8e3a8159d8b61e0759','--','web/database/alembic/schema_targets').decode().splitlines();rows=[]
for n in oldtargets:
 if n==target:continue
 before=git('show','f848256ceac6a8c6a7c2cc8e3a8159d8b61e0759:'+n);after=git('show',FINAL+':'+n);assert before==after;rows.append({'path':n,'Git_blob_SHA256':sha(before),'byte_exact_unchanged':True})
save('all-prior-targets-unchanged.json',rows)
# Preserve independent source scope: earlier matrix7be, final canonical guard only5SQLite.
service='web/services/followup_tasks.py';policy='web/database/followup_policy.py';names=[service,policy,target]
save('final-source-RAW-bindings.json',{'final_commit':FINAL,'initial_fix_commit':PRODUCT,'paths':{n:sha((R/n).read_bytes())for n in names},'final_guard_tests_SHA256':'4307ea74c3aeff440ddf26ce20194551d5320f83165ba1af8c3940009cf8e445','ROOT_peer_PG_after_handoff_pending':True})
closure=load('final-fresh-owned-absence.STRUCTURAL.json');assert closure['own_UUIDs']==12 and closure['all_closed_absent_fresh']and closure['lease_released_to_ROOT']
states=[json.loads(p.read_bytes())for p in(P/'leases').glob('*.json')];assert len(states)==12 and all(s['state']=='closed_absent'and s['sessions_before_drop']==0 for s in states)
# No connection, profile read or SQL occurs in this sealer.
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/'pip-final.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
(O/'drivers').mkdir(exist_ok=True)
for src,dst in [('metodobase-sec-followup34-pg-fix-capture-20261019.py','capture-target.py'),('metodobase-sec-followup34-pg-fix-replays-20261019.py','replays.py'),('metodobase-sec-followup34-manager-scope-run-20261019.py','manager-tuple-before-after.py'),('metodobase-sec-followup34-pg-fix-final-acl-20261019.ps1','final-acl.ps1'),('metodobase-sec-followup34-pg-fix-seal-20261019.py','seal.py')]:
 (O/'drivers'/dst).write_bytes((T/src).read_bytes())
acl=json.loads((P/'acl-final.private.json').read_bytes());assert acl['protected']and acl['parent_SDDL_unchanged'];save('private-ACL.STRUCTURAL.json',{**acl,'initial_SDDL_SHA256':sha((P/'acl-initial.private.txt').read_bytes())})
attrs=[]
for p in sorted(P.rglob('*')):
 if p.is_file():
  assert not p.is_symlink();h=hashlib.sha256()
  with p.open('rb')as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  st=p.stat();attrs.append({'private_relative_path':p.relative_to(P).as_posix(),'bytes':st.st_size,'SHA256':h.hexdigest(),'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'windows_file_attributes':getattr(st,'st_file_attributes',None)})
save('private-retention-attributes.STRUCTURAL.json',{'scope':'Original4RED, all6replay phases,5tuple before3RED/afterPASS, all Ruff/import-attempt RAW and synthetic restore artifacts. Payloads/URLs/factors remain private; no executionRAW reconstructed.','files':attrs})
review='''Author validation of web-only SEC20 and QA-21 fixes; ROOT independent acceptance pending. Independent original4RED remains immutable in f6f4c1bf. Product7be9b758 changes only service, invoker trigger body and current PostgreSQL34 target. Canonical eligibility followup a4f95fb5 changes one service line plus five direct SQLite controls. No global Backend34/35 acceptance is claimed.

SEC20: persisted manager-role hint now requires the same canonical _eligible tuple used by final authority. Discovery uses repo.task, including gym/client eligibility and assignee WHERE for non-managers, before deriving another account lock. A requested new assignee joins the lockset only for an eligible manager hint. Hints only narrow discovery; locked persistent authority, parent, role and SV remain final. Original real-MFA NutriB foreign task under only assigneeC lock: missing404/foreign409 becomes404/404 in both factories. New POST/PATCH controls reject non-manager403 without acquiring requested foreign-assignee locks.

The first product7be role-only hint still classified personal OWNER or owner/team-inconsistent tuples as managers. This was found statically before final acceptance. Five direct service controls observe actual extra delegated to real authority: canonical owner and accepted ADMIN are positive controls; personal OWNER plus two inconsistent OWNER/team tuples must never request another responsible account. Same5 tests give2PASS/3RED before and5PASS after _eligible guard; no assertion edits. They are not HTTP-authentication tests or claims that inconsistent tuples are reachable through supported API. No new PostgreSQL was run after lease handoff; ROOT is reviewing final a4f95 independently.

QA-21: Cliente SELECT FOR SHARE now adds NOWAIT in service and r34_event_guard. Known lock SQLSTATE55P03 remains409; timeout57014 is not reclassified and remains an unknown503. The original two client-contention variants503→409 pass unchanged. Additional real-trigger controls deliberately omit only the service lock clause; trigger context/55P03 is observed with no Task/Event or ACK, and a later explicit request commits one operation after release. No automatic retry/readback is introduced.

Own actual capture of target34 yields d1ebbaf5e9fdd41e1347f108d8f4ebcf4d8f7a88832d3fc8fef0b1faaf5ada80. FullJSON and byte inverse restores olda33 exactly; the only signature delta is r34_event_guard prosrc CLIENT FOR SHARE NOWAIT. No prior target, RPC, definer, RLS policy, role or global configuration changes. Migration source does not need editing because it installs the reviewed policy and verifies the exact target. ROOT was notified before target change and owns the35 predecessor update.

Executed against7be source: original4PGPASS;6newPGguardsPASS;28existing restricted-role PG service casesPASS;5PG migration casesPASS; complete populated restore34PASS preserving26–33;86affectedSQLitePASS including12QA18 and2SEC19. Counts are separate scopes, not repeated requirements. The anticipated91SQLite total included5SQLite migration cases not selected here; do not attribute them. Against finala4f95: only the same5directSQLite tuple controls were run. Package92 METADATA, bothPython binaries and source photos remain equal before/after each phase. Originalcanarycf32 is byte-identical in maintained integration module and RED artifact; QA18 originalc3a4/maintainedf1a5 unchanged. SEC19 authority and QA18 classifier functions remain ASTexact.

Ruff baseline rules on both product modules stay unchanged for7be. Immutable cf32 retains six existing I001/F401/F811 import diagnostics, not hidden or normalized. A module-import cleanup attempt was discarded in full and its RAW preserved; final copy is exactly the executed canary. New6guard and5tuple test modules Ruff0. This preserves all source and assertions for independent replay.

Twelve own exclusive-xb UUID leases were closed by normalDROP after0sessions with helper fresh absence; final separate fresh connection confirmed absence and0sessions for all12. No foreign process, DB, role/HBA or forced cleanup. PG55483 was explicitly returned to ROOT; no later PG connection/profile read or SQL is performed by this sealer. Final additional tests useSQLite only. RAW/XML, original failures, capture and restore artifacts remain private with ACL; public output contains structural metadata/code scanned with unchanged checkpoint119 plus JWT guard. No Desktop, Chrome, VM, Redis, live provider, dependency installation, push or deployment.
'''
(O/'review.md').write_bytes(review.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f';ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('source.json',{'role':'author validation; independent ROOT/QA review pending','RED_commit':'f6f4c1bff58d6a25aa3c59498ebed5840fef0a11','first_fix_commit':PRODUCT,'canonical_guard_followup_commit':FINAL,'original4_canary_SHA256':sha(original.read_bytes()),'first_fix_PG_functional_PASS':38,'first_fix_PG_migration_PASS':5,'first_fix_PG_complete_restore_PASS':1,'first_fix_affected_SQLite_PASS':86,'final_followup_SQLite_tuple_controls_PASS':5,'final_followup_before_PASS_RED':[2,3],'final_followup_PG_replayed_by_this_author':False,'independent_ROOT_final_peer_pending':True,'targetPG34_SHA256':sha((R/target).read_bytes()),'source_92_metadata_bothPython_quiet_per_phase':True,'pip_exit':0,'own_UUIDs_closed_fresh':12,'PG_lease_handed_to_ROOT':True,'no_later_author_PG':True,'global_Backend34_35_acceptance':False,'Desktop_work':False,'scanner119_AST_digest':digest})
save('public-safety-scan.json',{'unchanged_scanner119_AST_digest':digest,'additional_JWT_guard':True,'all_public_files_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in O.rglob('*'):
 if p.is_file():
  b=p.read_bytes();ns['scan'](b,p.relative_to(O).as_posix());assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',b),p.name
for n in ['tests/integration_security_followup34_postgres_peer.py','tests/integration_security_followup34_lock_guards.py','tests/test_followup34_hint_manager_scope.py']:ns['scan']((R/n).read_bytes(),n)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes()),'final_product':FINAL,'role':'author validation only','PG_handoff_preserved':True}))
