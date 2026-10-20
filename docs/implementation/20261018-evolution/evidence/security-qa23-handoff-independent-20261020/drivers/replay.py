from pathlib import Path
import hashlib, importlib.metadata, json, os, subprocess, sys, xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');P=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-qa23-peer-private-20261020');sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()=='4834c3c2fb632701275498d56196ac4209086298'
def photo():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')+['tests/test_security_qa23_handoff_peer.py','tests/test_security_followup34_postgres_peer.py','tests/test_security_followup34_sql_errors_peer.py']
 return {'source':{n:sha((R/n).read_bytes())for n in sorted(set(names))if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
save=lambda n,v:(P/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());before=photo();save('before.json',before)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(P/'pip-before.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
quota='tests/test_gym_generation_quota.py::';selected=['test_pending_reservation_consumes_per_client_day_and_retry_cannot_start_again','test_global_daily_cap_counts_historical_plans_and_pending_reservation','test_monthly_cap_includes_historical_previous_days','test_complete_replays_exact_response_and_rejects_changed_payload','test_failure_releases_once_and_allows_new_key','test_crash_after_plan_commit_never_refunds_even_after_reference_deleted','test_plan_link_requires_the_reserved_client_and_transaction_rolls_back']
files=['tests/test_gym_generation_handoff.py',*[quota+x for x in selected],'tests/test_nutrition35_http.py','tests/test_security_qa23_handoff_peer.py']
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*files,'-q','--tb=short','--basetemp='+str(P/'pytest'),'--junitxml='+str(P/'result.xml')];save('argv.json',cmd)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
for k in list(env):
 if k.startswith('METODOBASE_TEST_')or k in {'FOLLOWUP34_PRIVATE_LEASES','SEC_FOLLOWUP34_RECEIPTS','_METODOBASE_TEST_ROOT'}:env.pop(k,None)
env['_METODOBASE_TEST_ROOT']=str(P/'metodobase-test-qa23-isolation');Path(env['_METODOBASE_TEST_ROOT']).mkdir(exist_ok=False)
r=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=600);(P/'stdout.RAW.log').write_bytes(r.stdout);(P/'stderr.RAW.log').write_bytes(r.stderr)
cases=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(P/'result.xml').findall('.//testcase')];save('cases.STRUCTURAL.json',cases);after=photo();save('after.json',after);assert before==after
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(P/'pip-after.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
summary={'exit':r.returncode,'cases':len(cases),'own_cases':sum('test_security_qa23_handoff_peer'in c['case']for c in cases),'outcomes':{k:sum(c['outcome']==k for c in cases)for k in ['passed','failure','error','skipped']},'source_packages92_bothPython_quiet':True,'PG_SQL_or_private_profile':False};save('summary.json',summary);print(json.dumps(summary))
