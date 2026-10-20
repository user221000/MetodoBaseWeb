from pathlib import Path
import hashlib, importlib.metadata, json, os, subprocess, sys, xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');P=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-r31-browser-peer-private-20261020');BASE='b297df83e855197fd20e6c5b650136d5b19f3f6c';sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==BASE
phase=sys.argv[1];assert phase.replace('-','').isalnum();D=P/phase;D.mkdir(exist_ok=False);save=lambda n,v:(D/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def photo():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')+['tests/test_security_followup34_postgres_peer.py','tests/test_security_followup34_sql_errors_peer.py']+[p.relative_to(R).as_posix()for p in (R/'tests').glob('test_security_r31_*peer.py')]
 return {'source':{n:sha((R/n).read_bytes())for n in sorted(set(names))if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();save('before.json',before);pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(D/'pip-before.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*sys.argv[2:],'-q','--tb=short','--basetemp='+str(D/'pytest'),'--junitxml='+str(D/'result.xml')];save('argv.json',cmd)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
for k in list(env):
 if k.startswith('METODOBASE_TEST_')or k in {'FOLLOWUP34_PRIVATE_LEASES','SEC_FOLLOWUP34_RECEIPTS','_METODOBASE_TEST_ROOT'}:env.pop(k,None)
env['_METODOBASE_TEST_ROOT']=str(D/'metodobase-test-r31-isolation');Path(env['_METODOBASE_TEST_ROOT']).mkdir(exist_ok=False)
r=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=900);(D/'stdout.RAW.log').write_bytes(r.stdout);(D/'stderr.RAW.log').write_bytes(r.stderr)
cases=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(D/'result.xml').findall('.//testcase')];save('cases.STRUCTURAL.json',cases);after=photo();save('after.json',after);assert before==after
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(D/'pip-after.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
summary={'exit':r.returncode,'cases':len(cases),'own_cases':sum('test_security_r31_'in c['case']for c in cases),'outcomes':{k:sum(c['outcome']==k for c in cases)for k in ['passed','failure','error','skipped']},'source_packages92_bothPython_quiet':True,'PG_SQL_or_private_profile':False};save('summary.json',summary);print(json.dumps(summary))
