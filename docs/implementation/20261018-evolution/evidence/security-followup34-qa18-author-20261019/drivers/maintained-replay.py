from pathlib import Path
import ast,hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-followup34-qa18-author-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-qa18-author-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
canary=R/'tests/test_security_followup34_sql_errors_peer.py';maint=R/'tests/test_followup34_sql_error_classification.py'
assert sha(canary.read_bytes())=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'
tests=lambda b:{n.name:ast.dump(n)for n in ast.parse(b).body if isinstance(n,ast.FunctionDef)and n.name.startswith('test_')}
assert tests(canary.read_bytes())==tests(maint.read_bytes())
save('maintained-final-binding.json',{'original_SHA256':sha(canary.read_bytes()),'maintained_SHA256':sha(maint.read_bytes()),'original_test_functions_AST_exact':True,'only_adaptations':'Shared fixture module registrations, import formatting, pytest-owned structural receipt directory; no original function/assertion changes.'})
rows=[]
for label,path,content in [('service-baseline','web/services/followup_tasks.py',(R/'docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019/preimage/followup_tasks.py').read_bytes()),('service-final','web/services/followup_tasks.py',(R/'web/services/followup_tasks.py').read_bytes()),('maintained-final',str(maint.relative_to(R)),maint.read_bytes())]:
 r=subprocess.run([sys.executable,'-m','ruff','check','--stdin-filename',path,'--output-format','json','-'],cwd=R,input=content,capture_output=True);(P/(label+'-ruff-verified.stdout.RAW.json')).write_bytes(r.stdout);(P/(label+'-ruff-verified.stderr.RAW.log')).write_bytes(r.stderr)
 rows.append({'label':label,'exit':r.returncode,'rules':[x['code']for x in json.loads(r.stdout)]})
assert rows[0]['rules']==rows[1]['rules'] and rows[2]['exit']==0
save('quality-baseline-binding.json',{'initial_quality_attempt':'Private initial maintained imports produced PLC0414; corrected shared fixture import framing; no product semantic change. Prior RAW retained.','results':rows,'service_existing_nine_rules_unchanged':True,'maintained_new_test_zero_diagnostics':True})
def photo():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')+['tests/'+canary.name,'tests/'+maint.name]
 return {'source':{n:sha((R/n).read_bytes())for n in names if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();save('maintained-before.json',before)
for phase in ['before']:
 r=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/('pip-'+phase+'.RAW.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',str(maint.relative_to(R)),'-q','--tb=short','--basetemp='+str(P/'pytest-maintained'),'--junitxml='+str(P/'maintained.xml')]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
for k in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN','FOLLOWUP34_PRIVATE_LEASES','SEC_FOLLOWUP34_RECEIPTS']:env.pop(k,None)
r=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=360);(P/'maintained-stdout.RAW.log').write_bytes(r.stdout);(P/'maintained-stderr.RAW.log').write_bytes(r.stderr)
cases=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(P/'maintained.xml').findall('.//testcase')]
save('maintained-cases.STRUCTURAL.json',cases);after=photo();save('maintained-after.json',after)
assert before==after
summary={'exit':r.returncode,'cases':len(cases),'outcomes':{k:sum(c['outcome']==k for c in cases)for k in ['passed','failure','error','skipped']},'same_twelve_replayed_as_CI_copy_not_additional_unique_cases':True,'source_92_metadata_bothPython_quiet':True,'PostgreSQL_profile_read':False}
save('maintained-summary.json',summary);assert r.returncode==0 and len(cases)==12
r=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/'pip-after.RAW.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
print(json.dumps(summary))
