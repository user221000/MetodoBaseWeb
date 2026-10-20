from pathlib import Path
import glob,hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-followup34-author-sec-peer-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-pg-fix-author-20261019';sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
assert git('rev-parse','HEAD').decode().strip()=='f6f4c1bff58d6a25aa3c59498ebed5840fef0a11'
original='tests/test_security_followup34_postgres_peer.py';assert sha((R/original).read_bytes())=='cf32a69a8049272b1493e4802551c3f487b9f2a92eee019061c711f43e580ce1';assert (R/original).read_bytes()==(R/'tests/integration_security_followup34_postgres_peer.py').read_bytes()
assert sha((R/'tests/test_followup34_sql_error_classification.py').read_bytes())=='f1a5aea20590b5b479e3639e3f0a03abfbf664c0acd55a074b95b149ad8682be'
assert sha((R/'tests/test_security_followup34_sql_errors_peer.py').read_bytes())=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'
new=['tests/integration_security_followup34_postgres_peer.py','tests/integration_security_followup34_lock_guards.py',original,'tests/test_security_followup34_sql_errors_peer.py']
def photo():
 names=git('ls-files','-z').decode().split('\0')+new
 return {'source':{n:sha((R/n).read_bytes())for n in names if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
profile=json.loads((T/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes());restore=P/'restore-evidence';restore.mkdir()
env=dict(os.environ,**profile,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',FOLLOWUP34_PRIVATE_LEASES=str(P/'leases'),METODOBASE_TEST_EVIDENCE_DIR=str(restore))
phases=[('same-four-PG',[original]),('new-lock-guards-PG',['tests/integration_security_followup34_lock_guards.py']),('author-service-PG',['tests/integration_followup34_postgres.py']),('migrations-PG',['tests/integration_followup34_migrations.py','-k','postgresql']),('restore-PG',['tests/integration_followup34_restore.py']),('affected-SQLite',sorted(str(p.relative_to(R)).replace('\\','/')for p in(R/'tests').glob('test_followup34_*.py')))]
all_summary=[]
for name,selected in phases:
 before=photo();save(name+'-before.json',before);xml=P/(name+'.xml');cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*selected,'-q','--tb=short','--basetemp='+str(P/('pytest-'+name)),'--junitxml='+str(xml)]
 result=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=900 if name=='restore-PG'else 480);(P/(name+'-stdout.RAW.log')).write_bytes(result.stdout);(P/(name+'-stderr.RAW.log')).write_bytes(result.stderr)
 rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(xml).findall('.//testcase')];save(name+'-cases.STRUCTURAL.json',rows);after=photo();save(name+'-after.json',after);assert before==after
 leases=[json.loads(p.read_bytes())for p in(P/'leases').glob('*.json')];summary={'phase':name,'selected':selected,'exit':result.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows)for k in ['passed','failure','error','skipped']},'source_92_metadata_bothPython_quiet':True,'own_leases_total':len(leases),'all_own_leases_closed_absent':all(x['state']=='closed_absent'and x['sessions_before_drop']==0 for x in leases)};save(name+'-summary.json',summary);all_summary.append(summary);save('phases-summary.json',all_summary);print(json.dumps(summary),flush=True)
 if result.returncode:break
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/'pip-after.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
